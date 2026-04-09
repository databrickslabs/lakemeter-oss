import { create } from 'zustand'
import type { 
  Estimate, 
  EstimateListItem, 
  LineItem, 
  WorkloadType,
  CloudProvider,
  InstanceType,
  DBSQLSize,
  DLTEdition,
  FMAPIProvider,
  VMPricing,
  VMPricingTier,
  VMPaymentOption,
  ModelServingGPUType,
  FMAPIDatabricksConfig,
  FMAPIProprietaryConfig
} from '../types'
import * as api from '../api/client'
import type { 
  CurrentUser, 
  CostCalculationResponse,
  RegionResponse,
  Tier,
  DBURate,
  ServerlessMode,
  PhotonMultiplier,
  VectorSearchMode,
  FMAPIDatabricksModel,
  FMAPIProprietaryModel
} from '../api/client'
import { 
  loadPricingBundle, 
  createEmptyBundle,
  // NOTE: getVMCost removed - VM costs are now fetched on-demand via API
  getDBUPrice as getBundleDBUPrice,
  type PricingBundle
} from '../utils/pricingBundle'

// =============================================================================
// IN-FLIGHT REQUEST DEDUPLICATION
// =============================================================================
// Tracks in-flight VM cost fetches by (cloud:region:instance_type) to prevent
// duplicate concurrent requests when loading estimates with many workloads.
const _vmCostInflight: Record<string, Promise<any>> = {}

// =============================================================================
// LOCAL STORAGE CACHE UTILITIES
// =============================================================================
const CACHE_VERSION = 'v7'  // Bumped - added DATABRICKS_APPS, AI_PARSE, SHUTTERSTOCK_IMAGEAI; removed CLEAN_ROOM, LAKEFLOW_CONNECT
const CACHE_KEY = `lakemeter_reference_data_${CACHE_VERSION}`
const CACHE_TTL = 4 * 60 * 60 * 1000 // 4 hours in milliseconds (reduced from 24h)

interface CachedReferenceData {
  workloadTypes: WorkloadType[]
  cloudProviders: CloudProvider[]
  dbsqlSizes: DBSQLSize[]
  dltEditions: DLTEdition[]
  fmapiProviders: FMAPIProvider[]
  vmPricingTiers: VMPricingTier[]
  vmPaymentOptions: VMPaymentOption[]
  fmapiDatabricksConfig: FMAPIDatabricksConfig | null
  fmapiProprietaryConfig: FMAPIProprietaryConfig | null
  serverlessModes: ServerlessMode[]
  instanceTypes: InstanceType[]
  modelServingGPUTypes: ModelServingGPUType[]
  regions: RegionResponse[]
  // Multi-cloud regions cache
  regionsMap: Record<string, RegionResponse[]>
  photonMultipliers: PhotonMultiplier[]
  instanceFamilies: string[]
  dbsqlWarehouseTypes: string[]
  fmapiDatabricksModels: string[]
  timestamp: number
}

function getCachedReferenceData(): CachedReferenceData | null {
  try {
    const cached = localStorage.getItem(CACHE_KEY)
    if (!cached) return null
    
    const data: CachedReferenceData = JSON.parse(cached)
    
    // Validate TTL
    if (Date.now() - data.timestamp > CACHE_TTL) {
      localStorage.removeItem(CACHE_KEY)
      return null
    }
    
    // Validate required fields exist
    if (!data.workloadTypes || !data.cloudProviders) {
      localStorage.removeItem(CACHE_KEY)
      return null
    }
    
    // Check for regionsMap (new cache format) or regions (old format)
    if (!data.regionsMap && !data.regions) {
      localStorage.removeItem(CACHE_KEY)
      return null
    }
    
    // CRITICAL: Check if regions are actually populated (not just empty arrays)
    // If regionsMap exists but all regions are empty, the cache is invalid
    if (data.regionsMap) {
      const hasAnyRegions = Object.values(data.regionsMap).some(
        (regions) => Array.isArray(regions) && regions.length > 0
      )
      if (!hasAnyRegions) {
        localStorage.removeItem(CACHE_KEY)
        return null
      }
    } else if (data.regions && data.regions.length === 0) {
      localStorage.removeItem(CACHE_KEY)
      return null
    }
    
    return data
  } catch (e) {
    localStorage.removeItem(CACHE_KEY)
    return null
  }
}

function setCachedReferenceData(data: Omit<CachedReferenceData, 'timestamp'>): void {
  try {
    const cacheData: CachedReferenceData = {
      ...data,
      timestamp: Date.now()
    }
    localStorage.setItem(CACHE_KEY, JSON.stringify(cacheData))
  } catch (e) {
    // Cache save failed - non-critical
  }
}

function clearReferenceDataCache(): void {
  try {
    localStorage.removeItem(CACHE_KEY)
  } catch (e) {
    // Cache clear failed - non-critical
  }
}

// =============================================================================
// HARDCODED STATIC DATA (rarely changes)
// =============================================================================
const STATIC_CLOUD_PROVIDERS: CloudProvider[] = [
  { cloud: 'aws', display_name: 'AWS', code: 'AWS' },
  { cloud: 'azure', display_name: 'Azure', code: 'AZURE' },
  { cloud: 'gcp', display_name: 'GCP', code: 'GCP' }
]

const STATIC_DBSQL_SIZES: DBSQLSize[] = [
  { id: '2X-Small', name: '2X-Small', dbu_per_hour: 4 },
  { id: 'X-Small', name: 'X-Small', dbu_per_hour: 6 },
  { id: 'Small', name: 'Small', dbu_per_hour: 12 },
  { id: 'Medium', name: 'Medium', dbu_per_hour: 24 },
  { id: 'Large', name: 'Large', dbu_per_hour: 40 },
  { id: 'X-Large', name: 'X-Large', dbu_per_hour: 80 },
  { id: '2X-Large', name: '2X-Large', dbu_per_hour: 144 },
  { id: '3X-Large', name: '3X-Large', dbu_per_hour: 272 },
  { id: '4X-Large', name: '4X-Large', dbu_per_hour: 528 }
]

const STATIC_DLT_EDITIONS: DLTEdition[] = [
  { id: 'CORE', name: 'Core' },
  { id: 'PRO', name: 'Pro' },
  { id: 'ADVANCED', name: 'Advanced' }
]

const STATIC_VM_PRICING_TIERS: VMPricingTier[] = [
  { id: 'on_demand', name: 'On Demand' },
  { id: '1yr_reserved', name: '1-Year Reserved' },
  { id: '3yr_reserved', name: '3-Year Reserved' }
]

const STATIC_VM_PAYMENT_OPTIONS: VMPaymentOption[] = [
  { id: 'no_upfront', name: 'No Upfront' },
  { id: 'partial_upfront', name: 'Partial Upfront' },
  { id: 'all_upfront', name: 'All Upfront' }
]

const STATIC_SERVERLESS_MODES: ServerlessMode[] = [
  { mode: 'standard', display_name: 'Standard' },
  { mode: 'performance', display_name: 'Performance' }
]

const STATIC_FMAPI_PROVIDERS: FMAPIProvider[] = [
  { provider: 'databricks', display_name: 'Databricks' },
  { provider: 'openai', display_name: 'OpenAI' },
  { provider: 'anthropic', display_name: 'Anthropic' },
  { provider: 'google', display_name: 'Google' }
]

interface Store {
  // Current User
  currentUser: CurrentUser | null
  isAuthenticated: boolean
  authError: string | null
  sessionExpired: boolean
  setSessionExpired: (expired: boolean) => void
  
  // Estimates
  estimates: EstimateListItem[]
  currentEstimate: Estimate | null
  lineItems: LineItem[]
  isLoading: boolean
  error: string | null
  _estimatesLastFetch: number  // Timestamp for SWR pattern
  
  // Reference Data
  workloadTypes: WorkloadType[]
  cloudProviders: CloudProvider[]
  regions: RegionResponse[]
  regionsMap: Record<string, RegionResponse[]>  // Multi-cloud regions cache { aws: [], azure: [], gcp: [] }
  tiers: Tier[]
  instanceTypes: InstanceType[]
  instanceFamilies: string[]
  dbsqlSizes: DBSQLSize[]
  dbsqlWarehouseTypes: string[]
  dltEditions: DLTEdition[]
  fmapiProviders: FMAPIProvider[]
  fmapiDatabricksModels: string[]
  selectedCloud: string
  selectedRegion: string
  selectedTier: string
  
  // Model Serving & Foundation Models Reference Data
  modelServingGPUTypes: ModelServingGPUType[]
  fmapiDatabricksConfig: FMAPIDatabricksConfig | null
  fmapiProprietaryConfig: FMAPIProprietaryConfig | null
  
  // VM Pricing Data
  vmPricing: VMPricing[]
  vmPricingTiers: VMPricingTier[]
  vmPaymentOptions: VMPaymentOption[]
  vmPricingMap: Record<string, number>
  instanceDbuRateMap: Record<string, number>  // Map of "cloud:instance_type" -> dbu_rate
  
  // DBU Rates & Pricing (NEW)
  dbuRates: DBURate[]
  dbuRatesMap: Record<string, number>  // Map of "product_type" -> dbu_price
  serverlessModes: ServerlessMode[]
  photonMultipliers: PhotonMultiplier[]
  
  // Vector Search & FMAPI Pricing (for local calculations)
  vectorSearchModes: VectorSearchMode[]  // modes with dbu_per_hour and input_divisor
  fmapiDatabricksRates: Record<string, FMAPIDatabricksModel>  // "model:rate_type" -> rate data
  fmapiProprietaryRates: Record<string, FMAPIProprietaryModel>  // "provider:model:rate_type" -> rate data
  
  // Static Pricing Bundle (for instant local calculations)
  pricingBundle: PricingBundle
  isPricingBundleLoaded: boolean
  loadPricingBundle: () => Promise<void>
  
  // Cost Calculations (NEW)
  workloadCosts: Record<string, CostCalculationResponse>  // Map of line_item_id -> cost (API results)
  localCalculatedCosts: Record<string, { total: number; dbu: number; vm: number; dbus: number }>  // Map of line_item_id -> local calculation
  isCalculatingCost: boolean
  calculatingCostIds: Set<string>  // Track which individual line items are calculating
  
  // Actions - Auth
  fetchCurrentUser: () => Promise<void>
  clearAuthError: () => void
  
  // Actions - Estimates
  fetchEstimates: (forceRefresh?: boolean) => Promise<void>
  fetchEstimate: (id: string) => Promise<void>
  fetchEstimateWithLineItems: (id: string) => Promise<void>  // Optimized combined fetch
  createEstimate: (estimate: Partial<Estimate>) => Promise<Estimate>
  updateEstimate: (id: string, estimate: Partial<Estimate>) => Promise<Estimate>
  deleteEstimate: (id: string) => Promise<void>
  duplicateEstimate: (id: string) => Promise<Estimate>
  setCurrentEstimate: (estimate: Estimate | null) => void
  clearEstimateState: () => void
  
  // Actions - Line Items
  fetchLineItems: (estimateId: string) => Promise<void>
  createLineItem: (lineItem: Partial<LineItem> & { estimate_id: string }) => Promise<LineItem>
  updateLineItem: (id: string, lineItem: Partial<LineItem>) => Promise<LineItem>
  updateLineItemLocal: (id: string, lineItem: Partial<LineItem>) => void
  deleteLineItem: (id: string) => Promise<void>
  
  // Actions - Reference Data
  fetchReferenceData: (forceRefresh?: boolean) => Promise<void>
  clearReferenceCache: () => void
  isReferenceDataLoaded: boolean
  isLoadingReferenceData: boolean
  getRegionsForCloud: (cloud: string) => RegionResponse[]  // Get cached regions for a specific cloud
  fetchRegions: (cloud: string) => Promise<void>
  fetchTiers: (cloud?: string) => Promise<void>
  fetchInstanceTypes: (cloud: string, region?: string) => Promise<void>
  fetchInstanceFamilies: () => Promise<void>
  fetchModelServingGPUTypes: (cloud: string) => Promise<void>
  fetchDBSQLWarehouseTypes: () => Promise<void>
  fetchFMAPIDatabricksModels: () => Promise<void>
  setSelectedCloud: (cloud: string) => void
  setSelectedRegion: (region: string) => void
  setSelectedTier: (tier: string) => void
  
  // Actions - VM Pricing
  fetchVMPricing: (cloud: string, region?: string) => Promise<void>
  fetchVMCostForInstance: (cloud: string, region: string, instanceType: string, pricingTier?: string, paymentOption?: string) => Promise<number>
  getVMPrice: (cloud: string, region: string, instanceType: string, pricingTier?: string, paymentOption?: string) => number
  getInstanceDbuRate: (cloud: string, instanceType: string) => number
  
  // Actions - DBU Rates & Pricing (NEW)
  fetchDBURates: (cloud: string, region: string, tier: string) => Promise<void>
  getDBURate: (productType: string) => number
  fetchServerlessModes: () => Promise<void>
  fetchPhotonMultipliers: (cloud: string) => Promise<void>
  
  // Actions - Vector Search & FMAPI Pricing (for local calculations)
  fetchVectorSearchModes: (cloud: string) => Promise<void>
  getVectorSearchRate: (mode: string) => { dbu_per_hour: number; input_divisor: number } | null
  fetchFMAPIDatabricksRate: (model: string, cloud: string, rate_type: string) => Promise<FMAPIDatabricksModel | null>
  fetchFMAPIProprietaryRate: (provider: string, model: string, cloud: string, rate_type: string) => Promise<FMAPIProprietaryModel | null>
  getFMAPIDatabricksRate: (model: string, rate_type: string) => FMAPIDatabricksModel | null
  getFMAPIProprietaryRate: (provider: string, model: string, rate_type: string) => FMAPIProprietaryModel | null
  
  // Actions - Cost Calculation (NEW)
  calculateWorkloadCost: (lineItem: LineItem, estimateCloud: string, estimateRegion: string, estimateTier: string) => Promise<CostCalculationResponse | null>
  calculateAllWorkloadCosts: (estimateId: string, options?: { forceRecalculate?: boolean; onlyLineItemIds?: string[] }) => Promise<void>
  recalculateSingleWorkload: (lineItemId: string) => Promise<void>
  clearWorkloadCosts: () => void
  clearSingleWorkloadCost: (lineItemId: string) => void
  markItemCalculating: (lineItemId: string) => void
  setLocalCalculatedCosts: (costs: Record<string, { total: number; dbu: number; vm: number; dbus: number }>) => void
  isItemCalculating: (lineItemId: string) => boolean
  
  // Actions - Clone
  cloneEstimate: (estimateId: string, newName?: string) => Promise<Estimate | null>
  cloneLineItem: (lineItemId: string, newName?: string) => Promise<LineItem | null>
  
  // UI State
  clearError: () => void
}

export const useStore = create<Store>((set, get) => ({
  // Initial state
  currentUser: null,
  isAuthenticated: false,
  authError: null,
  sessionExpired: false,
  setSessionExpired: (expired: boolean) => set({ sessionExpired: expired }),
  
  estimates: [],
  currentEstimate: null,
  lineItems: [],
  isLoading: false,
  error: null,
  
  // Fallback workload types in case API fails
  // Note: display_name uses new Lakeflow branding, but workload_type remains unchanged for backend compatibility
  workloadTypes: [
    { workload_type: 'JOBS', display_name: 'Lakeflow Jobs', description: 'Batch job workloads', sku_product_type_standard: 'JOBS_COMPUTE', sku_product_type_photon: 'JOBS_COMPUTE_(PHOTON)', sku_product_type_serverless: 'JOBS_SERVERLESS_COMPUTE', show_compute_config: true, show_serverless_toggle: true, show_photon_toggle: true, show_usage_runs: true },
    { workload_type: 'ALL_PURPOSE', display_name: 'All Purpose Compute', description: 'Interactive compute', sku_product_type_standard: 'ALL_PURPOSE_COMPUTE', sku_product_type_photon: 'ALL_PURPOSE_COMPUTE_(PHOTON)', sku_product_type_serverless: 'INTERACTIVE_SERVERLESS_COMPUTE', show_compute_config: true, show_serverless_toggle: true, show_photon_toggle: true, show_usage_runs: true },
    { workload_type: 'DLT', display_name: 'Lakeflow Spark Declarative Pipelines', description: 'Spark Declarative Pipelines', sku_product_type_standard: 'DLT_CORE_COMPUTE', sku_product_type_photon: 'DLT_CORE_COMPUTE_(PHOTON)', sku_product_type_serverless: 'DELTA_LIVE_TABLES_SERVERLESS', show_compute_config: true, show_serverless_toggle: true, show_photon_toggle: true, show_dlt_config: true, show_usage_runs: true },
    { workload_type: 'DBSQL', display_name: 'Databricks SQL', description: 'SQL warehouse workloads', sku_product_type_standard: 'SQL_COMPUTE', sku_product_type_photon: 'SQL_PRO_COMPUTE', sku_product_type_serverless: 'SERVERLESS_SQL_COMPUTE', show_dbsql_config: true, show_usage_runs: true },
    { workload_type: 'VECTOR_SEARCH', display_name: 'Vector Search', description: 'Vector search endpoints', sku_product_type_standard: 'VECTOR_SEARCH_ENDPOINT', show_vector_search_mode: true },
    { workload_type: 'MODEL_SERVING', display_name: 'Model Serving', description: 'Real-time ML inference', sku_product_type_standard: 'SERVERLESS_REAL_TIME_INFERENCE', show_model_serving_config: true },
    { workload_type: 'FMAPI_DATABRICKS', display_name: 'Foundation Models (Databricks)', description: 'Databricks foundation model APIs', sku_product_type_standard: 'FOUNDATION_MODEL_TRAINING', show_fmapi_config: true },
    { workload_type: 'FMAPI_PROPRIETARY', display_name: 'Foundation Models (Proprietary)', description: 'External foundation model APIs', sku_product_type_standard: 'FOUNDATION_MODEL_TRAINING', show_fmapi_config: true },
    { workload_type: 'LAKEBASE', display_name: 'Lakebase', description: 'Database workloads', sku_product_type_standard: 'DATABASE_SERVERLESS_COMPUTE', show_lakebase_config: true },
    { workload_type: 'DATABRICKS_APPS', display_name: 'Databricks Apps', description: 'Managed app hosting', sku_product_type_standard: 'ALL_PURPOSE_SERVERLESS_COMPUTE', show_usage_hours: true },
    { workload_type: 'AI_PARSE', display_name: 'AI Parse (Document AI)', description: 'Document parsing and extraction', sku_product_type_standard: 'SERVERLESS_REAL_TIME_INFERENCE' },
    { workload_type: 'SHUTTERSTOCK_IMAGEAI', display_name: 'Shutterstock ImageAI', description: 'AI image generation', sku_product_type_standard: 'SERVERLESS_REAL_TIME_INFERENCE' },
  ] as WorkloadType[],
  // Use static data as defaults - instant display, no waiting for API
  cloudProviders: STATIC_CLOUD_PROVIDERS,
  regions: [],
  regionsMap: {},  // Multi-cloud regions: { aws: [], azure: [], gcp: [] }
  tiers: [],
  instanceTypes: [],
  instanceFamilies: [],
  dbsqlSizes: STATIC_DBSQL_SIZES,
  dbsqlWarehouseTypes: [],
  dltEditions: STATIC_DLT_EDITIONS,
  fmapiProviders: STATIC_FMAPI_PROVIDERS,
  fmapiDatabricksModels: [],
  selectedCloud: 'aws',
  selectedRegion: '',
  selectedTier: 'PREMIUM',
  
  // Model Serving & Foundation Models
  modelServingGPUTypes: [],
  fmapiDatabricksConfig: null,
  fmapiProprietaryConfig: null,
  
  // VM Pricing
  vmPricing: [],
  vmPricingTiers: STATIC_VM_PRICING_TIERS,
  vmPaymentOptions: STATIC_VM_PAYMENT_OPTIONS,
  vmPricingMap: {},
  instanceDbuRateMap: {},
  
  // DBU Rates & Pricing
  dbuRates: [],
  dbuRatesMap: {},
  serverlessModes: STATIC_SERVERLESS_MODES,
  photonMultipliers: [],
  
  // Vector Search & FMAPI Pricing (for local calculations)
  vectorSearchModes: [],
  fmapiDatabricksRates: {},
  fmapiProprietaryRates: {},
  
  // Static Pricing Bundle (for instant local calculations)
  pricingBundle: createEmptyBundle(),
  isPricingBundleLoaded: false,
  
  // Cost Calculations
  workloadCosts: {},
  localCalculatedCosts: {},
  isCalculatingCost: false,
  calculatingCostIds: new Set<string>(),
  
  // Reference Data Loading State
  isReferenceDataLoaded: false,
  isLoadingReferenceData: false,
  
  // Caching (in-memory for session-specific data)
  _regionsCache: {} as Record<string, { data: any[]; timestamp: number }>,
  _dbuRatesCache: {} as Record<string, { data: any; timestamp: number }>,
  _instanceTypesCache: {} as Record<string, { data: any[]; timestamp: number }>,
  _estimatesLastFetch: 0,
  
  // Auth Actions
  fetchCurrentUser: async () => {
    try {
      const user = await api.fetchCurrentUser()
      set({ currentUser: user, isAuthenticated: true, authError: null })
    } catch (error: unknown) {
      const errorMessage = error instanceof Error && 'response' in error 
        ? (error as { response?: { status?: number } }).response?.status === 401
          ? 'Please access through Databricks Apps or set LOCAL_DEV_EMAIL environment variable.'
          : 'Failed to authenticate'
        : 'Failed to authenticate'
      set({ currentUser: null, isAuthenticated: false, authError: errorMessage })
    }
  },
  
  clearAuthError: () => set({ authError: null }),
  
  // Estimates
  fetchEstimates: async (forceRefresh = false) => {
    const currentEstimates = get().estimates
    const lastFetchTime = (get() as any)._estimatesLastFetch || 0
    const STALE_TIME = 5 * 1000 // 5 seconds before considering stale (faster refresh for "Modified" timestamps)
    
    // If we have cached data and not forcing refresh, show it immediately
    // and fetch in background if stale
    if (currentEstimates.length > 0 && !forceRefresh) {
      const isStale = Date.now() - lastFetchTime > STALE_TIME
      
      if (isStale) {
        // Background refresh - don't show loading spinner
        try {
          const estimates = await api.fetchEstimates()
          set({ 
            estimates,
            _estimatesLastFetch: Date.now()
          })
        } catch (error) {
          console.error('Background refresh failed:', error)
        }
      }
      return // Don't show loading - we have cached data
    }
    
    // No cached data or force refresh - show loading
    set({ isLoading: true, error: null })
    try {
      const estimates = await api.fetchEstimates()
      set({ 
        estimates, 
        isLoading: false,
        _estimatesLastFetch: Date.now()
      })
    } catch (error) {
      set({ error: 'Failed to fetch estimates', isLoading: false })
    }
  },
  
  fetchEstimate: async (id: string) => {
    set({ isLoading: true, error: null })
    try {
      const estimate = await api.fetchEstimate(id)
      set({ currentEstimate: estimate, isLoading: false })
    } catch (error) {
      set({ error: 'Failed to fetch estimate', isLoading: false })
    }
  },
  
  // Optimized: Fetch estimate + line items in one API call
  fetchEstimateWithLineItems: async (id: string) => {
    set({ isLoading: true, error: null })
    try {
      const { estimate, line_items } = await api.fetchEstimateWithLineItems(id)
      set({ 
        currentEstimate: estimate, 
        lineItems: line_items,
        isLoading: false 
      })
    } catch (error) {
      set({ error: 'Failed to fetch estimate', isLoading: false })
    }
  },
  
  createEstimate: async (estimate) => {
    set({ isLoading: true, error: null })
    try {
      const newEstimate = await api.createEstimate(estimate)
      set((state) => ({
        estimates: [{ ...newEstimate, line_item_count: 0 } as EstimateListItem, ...state.estimates],
        currentEstimate: newEstimate,
        isLoading: false
      }))
      return newEstimate
    } catch (error) {
      set({ error: 'Failed to create estimate', isLoading: false })
      throw error
    }
  },
  
  updateEstimate: async (id, estimate) => {
    set({ isLoading: true, error: null })
    try {
      const updated = await api.updateEstimate(id, estimate)
      set((state) => ({
        estimates: state.estimates.map((e) => 
          e.estimate_id === id ? { ...e, ...updated } : e
        ),
        currentEstimate: state.currentEstimate?.estimate_id === id 
          ? { ...state.currentEstimate, ...updated }
          : state.currentEstimate,
        isLoading: false
      }))
      return updated
    } catch (error) {
      set({ error: 'Failed to update estimate', isLoading: false })
      throw error
    }
  },
  
  deleteEstimate: async (id) => {
    set({ isLoading: true, error: null })
    try {
      await api.deleteEstimate(id)
      set((state) => ({
        estimates: state.estimates.filter((e) => e.estimate_id !== id),
        currentEstimate: state.currentEstimate?.estimate_id === id 
          ? null 
          : state.currentEstimate,
        isLoading: false
      }))
    } catch (error) {
      set({ error: 'Failed to delete estimate', isLoading: false })
      throw error
    }
  },
  
  duplicateEstimate: async (id) => {
    set({ isLoading: true, error: null })
    try {
      const newEstimate = await api.duplicateEstimate(id)
      set((state) => ({
        estimates: [{ ...newEstimate, line_item_count: state.estimates.find(e => e.estimate_id === id)?.line_item_count || 0 } as EstimateListItem, ...state.estimates],
        isLoading: false
      }))
      return newEstimate
    } catch (error) {
      set({ error: 'Failed to duplicate estimate', isLoading: false })
      throw error
    }
  },
  
  setCurrentEstimate: (estimate) => set({ currentEstimate: estimate }),
  
  clearEstimateState: () => set({ 
    currentEstimate: null, 
    lineItems: [], 
    workloadCosts: {}
  }),

  // Line Items
  fetchLineItems: async (estimateId) => {
    set({ isLoading: true, error: null })
    try {
      const lineItems = await api.fetchLineItems(estimateId)
      set({ lineItems, isLoading: false })
    } catch (error) {
      set({ error: 'Failed to fetch line items', isLoading: false })
    }
  },
  
  createLineItem: async (lineItem) => {
    set({ isLoading: true, error: null })
    try {
      const newItem = await api.createLineItem(lineItem)
      set((state) => ({
        lineItems: [...state.lineItems, newItem],
        isLoading: false
      }))
      return newItem
    } catch (error) {
      set({ error: 'Failed to create line item', isLoading: false })
      throw error
    }
  },
  
  updateLineItem: async (id, lineItem) => {
    set({ isLoading: true, error: null })
    try {
      const updated = await api.updateLineItem(id, lineItem)
      set((state) => ({
        lineItems: state.lineItems.map((item) => 
          item.line_item_id === id ? { ...item, ...updated } : item
        ),
        isLoading: false
      }))
      return updated
    } catch (error) {
      set({ error: 'Failed to update line item', isLoading: false })
      throw error
    }
  },
  
  updateLineItemLocal: (id, lineItem) => {
    set((state) => ({
      lineItems: state.lineItems.map((item) => 
        item.line_item_id === id ? { ...item, ...lineItem } : item
      )
    }))
  },
  
  deleteLineItem: async (id) => {
    set({ isLoading: true, error: null })
    try {
      await api.deleteLineItem(id)
      set((state) => ({
        lineItems: state.lineItems.filter((item) => item.line_item_id !== id),
        workloadCosts: Object.fromEntries(
          Object.entries(state.workloadCosts).filter(([key]) => key !== id)
        ),
        isLoading: false
      }))
    } catch (error) {
      set({ error: 'Failed to delete line item', isLoading: false })
      throw error
    }
  },
  
  // Reference Data (with localStorage caching)
  fetchReferenceData: async (forceRefresh = false) => {
    // Check if already loaded or loading (prevent duplicate calls)
    const state = get()
    if (state.isLoadingReferenceData) {
      return
    }
    
    // Skip if already loaded from cache (unless force refresh)
    if (!forceRefresh && state.isReferenceDataLoaded) {
      return
    }
    
    // Try to use localStorage cache first (unless force refresh)
    if (!forceRefresh) {
      const cached = getCachedReferenceData()
      if (cached) {
        // Reconstruct regionsMap from cache (support both old and new format)
        const regionsMap = cached.regionsMap || { aws: cached.regions || [] }
        // Merge cached workload types with fallback (ensure new types added to code but not yet in cache still appear)
        const cachedTypes = cached.workloadTypes || []
        const cachedTypeSet = new Set(cachedTypes.map((wt: WorkloadType) => wt.workload_type))
        const mergedCachedWorkloadTypes = [
          ...cachedTypes,
          ...state.workloadTypes.filter((wt: WorkloadType) => !cachedTypeSet.has(wt.workload_type)),
        ]
        set({
          workloadTypes: mergedCachedWorkloadTypes.length > 0 ? mergedCachedWorkloadTypes : state.workloadTypes,
          cloudProviders: cached.cloudProviders || STATIC_CLOUD_PROVIDERS,
          dbsqlSizes: cached.dbsqlSizes || STATIC_DBSQL_SIZES,
          dltEditions: cached.dltEditions || STATIC_DLT_EDITIONS,
          fmapiProviders: cached.fmapiProviders || STATIC_FMAPI_PROVIDERS,
          vmPricingTiers: cached.vmPricingTiers || STATIC_VM_PRICING_TIERS,
          vmPaymentOptions: cached.vmPaymentOptions || STATIC_VM_PAYMENT_OPTIONS,
          fmapiDatabricksConfig: (!Array.isArray(cached.fmapiDatabricksConfig) && cached.fmapiDatabricksConfig?.models?.llm) ? cached.fmapiDatabricksConfig : null,
          fmapiProprietaryConfig: (!Array.isArray(cached.fmapiProprietaryConfig) && cached.fmapiProprietaryConfig?.providers && (cached.fmapiProprietaryConfig.providers as any[]).length > 0 && !['aws','azure','gcp'].includes((cached.fmapiProprietaryConfig.providers as any[])[0]?.id)) ? cached.fmapiProprietaryConfig : null,
          serverlessModes: cached.serverlessModes || STATIC_SERVERLESS_MODES,
          instanceTypes: cached.instanceTypes || [],
          modelServingGPUTypes: cached.modelServingGPUTypes || [],
          regions: cached.regions || regionsMap['aws'] || [],
          regionsMap,
          photonMultipliers: cached.photonMultipliers || [],
          instanceFamilies: cached.instanceFamilies || [],
          dbsqlWarehouseTypes: cached.dbsqlWarehouseTypes || [],
          fmapiDatabricksModels: cached.fmapiDatabricksModels || [],
          isReferenceDataLoaded: true,
          isLoadingReferenceData: false
        })
        return
      }
    }
    
    // No cache or force refresh - fetch from API
    // OPTIMIZATION: All API calls run in parallel (single batch instead of 3 sequential batches)
    set({ isLoadingReferenceData: true })
    
    const defaultCloud = 'aws'
    
    try {
      // ALL API calls in ONE parallel batch (was 3 sequential batches = 3 round-trips)
      const [
        workloadTypes, 
        cloudProviders, 
        dbsqlSizes, 
        dltEditions, 
        fmapiProviders, 
        vmPricingTiers, 
        vmPaymentOptions,
        fmapiDatabricksConfig,
        fmapiProprietaryConfig,
        serverlessModes,
        // Cloud-specific data (previously in batch 2)
        instanceTypes, 
        modelServingGPUTypes, 
        awsRegions, 
        azureRegions, 
        gcpRegions, 
        photonMultipliers, 
        vectorSearchModes, 
        fmapiDbxRates, 
        fmapiPropRates,
        // Additional data (previously in batch 3)
        instanceFamilies,
        dbsqlWarehouseTypes,
        fmapiDatabricksModels
      ] = await Promise.all([
        // Batch 1 items
        api.fetchWorkloadTypes().catch(() => state.workloadTypes),
        api.fetchCloudProviders().catch(() => STATIC_CLOUD_PROVIDERS),
        api.fetchDBSQLSizes().catch(() => STATIC_DBSQL_SIZES),
        api.fetchDLTEditions().catch(() => STATIC_DLT_EDITIONS),
        api.fetchFMAPIModels().catch(() => STATIC_FMAPI_PROVIDERS),
        api.fetchVMPricingTiers().catch(() => STATIC_VM_PRICING_TIERS),
        api.fetchVMPaymentOptions().catch(() => STATIC_VM_PAYMENT_OPTIONS),
        api.fetchFMAPIDatabricksConfig().catch(() => null),
        api.fetchFMAPIProprietaryConfig().catch(() => null),
        api.fetchServerlessModes().catch(() => STATIC_SERVERLESS_MODES),
        // Batch 2 items (cloud-specific)
        // Instance types require region (set when estimate is loaded), skip on initial load
        Promise.resolve([]),
        api.fetchModelServingGPUTypes(defaultCloud).catch(() => []),
        api.fetchRegions('aws').catch(() => []),
        api.fetchRegions('azure').catch(() => []),
        api.fetchRegions('gcp').catch(() => []),
        api.fetchPhotonMultipliers(defaultCloud).catch(() => []),
        api.fetchVectorSearchModesWithPricing(defaultCloud).catch(() => []),
        api.fetchAllFMAPIDatabricksRates(defaultCloud).catch(() => []),
        api.fetchAllFMAPIProprietaryRates(defaultCloud).catch(() => []),
        // Batch 3 items
        api.fetchInstanceFamilies().catch(() => []),
        api.fetchDBSQLWarehouseTypes().catch(() => []),
        api.fetchFMAPIDatabricksModelsList().catch(() => [])
      ])
      
      const regionsMap = { aws: awsRegions, azure: azureRegions, gcp: gcpRegions }
      const regions = awsRegions // Default to AWS regions for backwards compatibility
      
      // Build FMAPI rate lookup maps
      const fmapiDatabricksRates: Record<string, any> = {}
      fmapiDbxRates.forEach((rate: any) => {
        const key = `${rate.model}:${rate.rate_type}`
        fmapiDatabricksRates[key] = rate
      })
      
      const fmapiProprietaryRates: Record<string, any> = {}
      fmapiPropRates.forEach((rate: any) => {
        const key = `${rate.provider}:${rate.model}:${rate.rate_type}`
        fmapiProprietaryRates[key] = rate
      })
      
      // Merge API workload types with fallback (ensure new types not yet in DB still appear)
      const apiTypeSet = new Set((workloadTypes as WorkloadType[]).map((wt: WorkloadType) => wt.workload_type))
      const mergedWorkloadTypes = [
        ...(workloadTypes as WorkloadType[]),
        ...state.workloadTypes.filter((wt: WorkloadType) => !apiTypeSet.has(wt.workload_type)),
      ]

      // Set all state in one update
      set({
        workloadTypes: mergedWorkloadTypes,
        cloudProviders, 
        dbsqlSizes, 
        dltEditions, 
        fmapiProviders,
        vmPricingTiers,
        vmPaymentOptions,
        fmapiDatabricksConfig,
        fmapiProprietaryConfig,
        serverlessModes,
        instanceTypes, 
        modelServingGPUTypes, 
        regions, 
        regionsMap, 
        photonMultipliers, 
        vectorSearchModes,
        fmapiDatabricksRates, 
        fmapiProprietaryRates,
        instanceFamilies,
        dbsqlWarehouseTypes,
        fmapiDatabricksModels,
        isReferenceDataLoaded: true, 
        isLoadingReferenceData: false
      })
      
      // Reference data loaded successfully
      
      // Save to localStorage cache (including all cloud regions)
      setCachedReferenceData({
        workloadTypes,
        cloudProviders,
        dbsqlSizes,
        dltEditions,
        fmapiProviders,
        vmPricingTiers,
        vmPaymentOptions,
        fmapiDatabricksConfig,
        fmapiProprietaryConfig,
        serverlessModes,
        instanceTypes,
        modelServingGPUTypes,
        regions,
        regionsMap,
        photonMultipliers,
        instanceFamilies,
        dbsqlWarehouseTypes,
        fmapiDatabricksModels
      })
    } catch (error) {
      console.error('Failed to fetch reference data:', error)
      // Keep using static defaults, don't set error that blocks UI
      set({ isReferenceDataLoaded: true, isLoadingReferenceData: false })
    }
  },
  
  clearReferenceCache: () => {
    clearReferenceDataCache()
    set({ isReferenceDataLoaded: false })
  },
  
  // Load static pricing bundle for instant local calculations
  loadPricingBundle: async () => {
    const state = get()
    if (state.isPricingBundleLoaded) {
      return
    }
    
    try {
      const bundle = await loadPricingBundle()
      set({ pricingBundle: bundle, isPricingBundleLoaded: bundle.isLoaded })
      // NOTE: vmCosts removed from bundle to save ~50 MB - VM costs are now fetched on-demand via API
    } catch (error) {
      // Pricing bundle failed to load - will use API-based fallback
      console.warn('[PricingBundle] Failed to load, using API fallback')
    }
  },
  
  // Get cached regions for a specific cloud (instant, no API call)
  getRegionsForCloud: (cloud: string) => {
    const state = get()
    const cloudKey = cloud.toLowerCase()
    return state.regionsMap[cloudKey] || []
  },
  
  fetchRegions: async (cloud) => {
    const cacheKey = cloud.toLowerCase()
    const cache = (get() as any)._regionsCache?.[cacheKey]
    const CACHE_TTL = 5 * 60 * 1000 // 5 minutes
    
    // Return cached data if fresh
    if (cache && Date.now() - cache.timestamp < CACHE_TTL) {
      set({ regions: cache.data })
      return
    }
    
    try {
      const regions = await api.fetchRegions(cloud)
      set((state: any) => ({ 
        regions,
        _regionsCache: {
          ...state._regionsCache,
          [cacheKey]: { data: regions, timestamp: Date.now() }
        }
      }))
    } catch (error) {
      console.error('Failed to fetch regions:', error)
    }
  },
  
  fetchTiers: async (cloud) => {
    try {
      const tiers = await api.fetchTiers(cloud)
      set({ tiers })
    } catch (error) {
      console.error('Failed to fetch tiers:', error)
    }
  },
  
  fetchInstanceTypes: async (cloud, region) => {
    const cacheKey = `${cloud.toLowerCase()}-${region || 'all'}`
    const cache = (get() as any)._instanceTypesCache?.[cacheKey]
    const CACHE_TTL = 10 * 60 * 1000 // 10 minutes
    
    // Return cached data if fresh
    if (cache && Date.now() - cache.timestamp < CACHE_TTL) {
      set({ instanceTypes: cache.data, selectedCloud: cloud })
      return
    }
    
    try {
      const instanceTypes = await api.fetchInstanceTypes(cloud, region)
      set((state: any) => ({ 
        instanceTypes, 
        selectedCloud: cloud,
        _instanceTypesCache: {
          ...state._instanceTypesCache,
          [cacheKey]: { data: instanceTypes, timestamp: Date.now() }
        }
      }))
    } catch (error) {
      console.error('Failed to fetch instance types:', error)
    }
  },
  
  fetchInstanceFamilies: async () => {
    try {
      const instanceFamilies = await api.fetchInstanceFamilies()
      set({ instanceFamilies })
    } catch (error) {
      console.error('Failed to fetch instance families:', error)
    }
  },
  
  fetchModelServingGPUTypes: async (cloud) => {
    try {
      const raw = await api.fetchModelServingGPUTypes(cloud)
      // Transform API response {gpu_type, dbu_rate} to component format {id, name, dbu_per_hour}
      const modelServingGPUTypes = Array.isArray(raw) ? raw.map((item: any) => ({
        id: item.id || item.gpu_type || item,
        name: item.name || item.gpu_type || item,
        dbu_per_hour: item.dbu_per_hour ?? item.dbu_rate ?? 0,
      })) : []
      set({ modelServingGPUTypes })
    } catch (error) {
      console.error('Failed to fetch model serving GPU types:', error)
    }
  },
  
  fetchDBSQLWarehouseTypes: async () => {
    try {
      const dbsqlWarehouseTypes = await api.fetchDBSQLWarehouseTypes()
      set({ dbsqlWarehouseTypes })
    } catch (error) {
      console.error('Failed to fetch DBSQL warehouse types:', error)
    }
  },
  
  fetchFMAPIDatabricksModels: async () => {
    try {
      const fmapiDatabricksModels = await api.fetchFMAPIDatabricksModelsList()
      set({ fmapiDatabricksModels })
    } catch (error) {
      console.error('Failed to fetch FMAPI Databricks models:', error)
    }
  },
  
  setSelectedCloud: (cloud) => {
    set({ selectedCloud: cloud })
    const region = get().selectedRegion
    get().fetchRegions(cloud)
    // Only fetch instance types if region is set (region is required by the API)
    if (region) {
      get().fetchInstanceTypes(cloud, region)
    }
    get().fetchModelServingGPUTypes(cloud)
    // NOTE: Removed fetchVMPricing (16+ MB) - VM costs are now fetched on-demand per instance
    get().fetchPhotonMultipliers(cloud)
    get().fetchVectorSearchModes(cloud)
  },
  
  setSelectedRegion: (region) => {
    set({ selectedRegion: region })
    const cloud = get().selectedCloud
    const tier = get().selectedTier
    // Only fetch instance types if region is set (region is required by the API)
    if (region) {
      get().fetchInstanceTypes(cloud, region)
    }
    // NOTE: Removed fetchVMPricing (16+ MB) - VM costs are now fetched on-demand per instance
    // Fetch DBU rates when region changes
    if (region) {
      get().fetchDBURates(cloud, region, tier)
    }
  },
  
  setSelectedTier: (tier) => {
    set({ selectedTier: tier })
    const cloud = get().selectedCloud
    const region = get().selectedRegion
    // Fetch DBU rates when tier changes
    if (region) {
      get().fetchDBURates(cloud, region, tier)
    }
  },
  
  // VM Pricing
  fetchVMPricing: async (cloud, region) => {
    try {
      const vmPricing = await api.fetchVMPricing({ cloud, region })
      
      const vmPricingMap: Record<string, number> = {}
      vmPricing.forEach(p => {
        const key = `${p.cloud.toLowerCase()}:${p.region}:${p.instance_type}:${p.pricing_tier}:${p.payment_option}`
        vmPricingMap[key] = p.cost_per_hour
      })
      
      set({ vmPricing, vmPricingMap })
    } catch (error) {
      console.error('Failed to fetch VM pricing:', error)
    }
  },
  
  // Fetch VM cost for a specific instance on-demand using the new API
  // Deduplicates in-flight requests: if the same (cloud, region, instance_type) is already
  // being fetched, all callers share the same promise instead of firing parallel HTTP requests.
  // This prevents DB connection pool exhaustion when loading estimates with many workloads.
  fetchVMCostForInstance: async (cloud, region, instanceType, pricingTier = 'on_demand', paymentOption = 'NA') => {
    // Return 0 immediately if no instance type provided
    if (!instanceType || instanceType.trim() === '') {
      return 0
    }

    // Normalize payment option: on_demand and spot don't have payment options (always NA)
    const normalizedPaymentOption = (pricingTier === 'on_demand' || pricingTier === 'spot')
      ? 'NA'
      : (paymentOption || 'NA')

    // Check if already in cache (before making API call)
    const exactKey = `${cloud.toLowerCase()}:${region}:${instanceType}:${pricingTier}:${normalizedPaymentOption}`
    const currentCache = get().vmPricingMap
    if (currentCache[exactKey] !== undefined) {
      return currentCache[exactKey]
    }

    // Deduplicate in-flight requests: fetch ALL tiers for this instance type at once
    // (no pricing_tier filter), so one request serves all pricing tier lookups
    const inflightKey = `${cloud.toLowerCase()}:${region}:${instanceType}`

    // If there's already an in-flight request for this instance type, wait for it
    if (inflightKey in _vmCostInflight) {
      await _vmCostInflight[inflightKey]
      // After the shared request completes, check cache again
      const cached = get().vmPricingMap[exactKey]
      return cached !== undefined ? cached : 0
    }

    // Create a new request (no pricing_tier filter → returns ALL tiers in one call)
    const fetchPromise = api.fetchInstanceVMCosts({
      cloud: cloud.toUpperCase(),
      region,
      instance_type: instanceType,
    })
    _vmCostInflight[inflightKey] = fetchPromise

    try {
      const vmCosts = await fetchPromise

      // Update cache with ALL returned pricing tiers
      if (vmCosts && vmCosts.length > 0) {
        const newEntries: Record<string, number> = {}
        let dbuRate: number | undefined
        vmCosts.forEach((vc: any) => {
          const key = `${cloud.toLowerCase()}:${region}:${instanceType}:${vc.pricing_tier}:${vc.payment_option}`
          newEntries[key] = vc.cost_per_hour
          if (vc.dbu_rate !== undefined && dbuRate === undefined) {
            dbuRate = vc.dbu_rate
          }
        })

        set(state => ({
          vmPricingMap: { ...state.vmPricingMap, ...newEntries },
          instanceDbuRateMap: dbuRate !== undefined
            ? { ...state.instanceDbuRateMap, [`${cloud.toLowerCase()}:${instanceType}`]: dbuRate }
            : state.instanceDbuRateMap
        }))

        // Return the requested pricing tier
        const matchedCost = vmCosts.find(vc =>
          vc.pricing_tier === pricingTier &&
          (vc.payment_option === normalizedPaymentOption || normalizedPaymentOption === 'NA')
        )
        return matchedCost?.cost_per_hour || vmCosts[0]?.cost_per_hour || 0
      }

      return 0
    } catch (error) {
      if (error instanceof Error && !error.message.includes('404')) {
        console.error(`[VM Cost] Fetch failed for ${instanceType}:`, error.message)
      }
      return 0
    } finally {
      delete _vmCostInflight[inflightKey]
    }
  },
  
  getVMPrice: (cloud, region, instanceType, pricingTier = 'on_demand', paymentOption = 'NA') => {
    // Return 0 immediately if no instance type provided (serverless workloads, etc.)
    if (!instanceType || instanceType.trim() === '') {
      return 0
    }
    
    // Normalize payment option: on_demand and spot don't have payment options (always NA)
    const normalizedPaymentOption = (pricingTier === 'on_demand' || pricingTier === 'spot') 
      ? 'NA' 
      : (paymentOption || 'NA')
    
    const { vmPricingMap } = get()
    const cloudLower = cloud.toLowerCase()
    
    // Look up in runtime-cached vmPricingMap (populated by on-demand API calls)
    const exactKey = `${cloudLower}:${region}:${instanceType}:${pricingTier}:${normalizedPaymentOption}`
    if (vmPricingMap[exactKey] !== undefined) {
      return vmPricingMap[exactKey]
    }
    
    const keyNoPayment = `${cloudLower}:${region}:${instanceType}:${pricingTier}:NA`
    if (vmPricingMap[keyNoPayment] !== undefined) {
      return vmPricingMap[keyNoPayment]
    }
    
    // Try with different payment options for same pricing tier
    for (const key of Object.keys(vmPricingMap)) {
      const parts = key.split(':')
      if (parts[0] === cloudLower && parts[2] === instanceType && parts[3] === pricingTier) {
        return vmPricingMap[key]
      }
    }
    
    // Try matching just cloud and instance type (any pricing tier as fallback)
    for (const key of Object.keys(vmPricingMap)) {
      const parts = key.split(':')
      if (parts[0] === cloudLower && parts[2] === instanceType) {
        return vmPricingMap[key]
      }
    }
    
    // VM price not found - return 0, will be populated when fetch completes
    return 0
  },
  
  getInstanceDbuRate: (cloud, instanceType) => {
    if (!instanceType || instanceType.trim() === '') {
      return 0
    }
    const { instanceDbuRateMap } = get()
    const key = `${cloud.toLowerCase()}:${instanceType}`
    return instanceDbuRateMap[key] || 0
  },
  
  // DBU Rates & Pricing
  fetchDBURates: async (cloud, region, tier) => {
    const cacheKey = `${cloud}-${region}-${tier}`.toLowerCase()
    const cache = (get() as any)._dbuRatesCache?.[cacheKey]
    const CACHE_TTL = 10 * 60 * 1000 // 10 minutes
    
    // Return cached data if fresh
    if (cache && Date.now() - cache.timestamp < CACHE_TTL) {
      set({ dbuRates: cache.data.dbuRates, dbuRatesMap: cache.data.dbuRatesMap })
      return
    }
    
    try {
      const dbuRates = await api.fetchDBURates({ cloud, region, tier })
      
      const dbuRatesMap: Record<string, number> = {}
      dbuRates.forEach(rate => {
        dbuRatesMap[rate.product_type] = rate.dbu_price
      })
      
      set((state: any) => ({ 
        dbuRates, 
        dbuRatesMap,
        _dbuRatesCache: {
          ...state._dbuRatesCache,
          [cacheKey]: { data: { dbuRates, dbuRatesMap }, timestamp: Date.now() }
        }
      }))
    } catch (error) {
      console.error('Failed to fetch DBU rates:', error)
    }
  },
  
  getDBURate: (productType, cloud?: string, region?: string, tier?: string) => {
    const { dbuRatesMap, pricingBundle, isPricingBundleLoaded } = get()
    
    // Try pricing bundle first (static data - instant lookup)
    if (isPricingBundleLoaded && cloud && region && tier) {
      const bundlePrice = getBundleDBUPrice(pricingBundle, cloud, region, tier, productType)
      if (bundlePrice > 0) {
        return bundlePrice
      }
    }
    
    // Fall back to runtime-cached dbuRatesMap
    return dbuRatesMap[productType] || 0
  },
  
  fetchServerlessModes: async () => {
    try {
      const serverlessModes = await api.fetchServerlessModes()
      set({ serverlessModes })
    } catch (error) {
      console.error('Failed to fetch serverless modes:', error)
    }
  },
  
  fetchPhotonMultipliers: async (cloud) => {
    try {
      const photonMultipliers = await api.fetchPhotonMultipliers(cloud)
      set({ photonMultipliers })
    } catch (error) {
      console.error('Failed to fetch photon multipliers:', error)
    }
  },
  
  // Vector Search & FMAPI Pricing Actions
  fetchVectorSearchModes: async (cloud) => {
    try {
      const vectorSearchModes = await api.fetchVectorSearchModesWithPricing(cloud)
      set({ vectorSearchModes })
    } catch (error) {
      console.error('Failed to fetch vector search modes:', error)
    }
  },
  
  getVectorSearchRate: (mode) => {
    const { vectorSearchModes } = get()
    const found = vectorSearchModes.find(m => m.mode === mode)
    return found ? { dbu_per_hour: found.dbu_per_hour, input_divisor: found.input_divisor } : null
  },
  
  fetchFMAPIDatabricksRate: async (model, cloud, rate_type) => {
    try {
      const results = await api.fetchFMAPIDatabricksModels(model, cloud, rate_type)
      if (results.length > 0) {
        const rate = results[0]
        const cacheKey = `${model}:${rate_type}`
        set((state) => ({
          fmapiDatabricksRates: { ...state.fmapiDatabricksRates, [cacheKey]: rate }
        }))
        return rate
      }
      return null
    } catch (error) {
      console.error('Failed to fetch FMAPI Databricks rate:', error)
      return null
    }
  },
  
  fetchFMAPIProprietaryRate: async (provider, model, cloud, rate_type) => {
    try {
      const results = await api.fetchFMAPIProprietaryModels({ provider, model, cloud, rate_type })
      if (results.length > 0) {
        const rate = results[0]
        const cacheKey = `${provider}:${model}:${rate_type}`
        set((state) => ({
          fmapiProprietaryRates: { ...state.fmapiProprietaryRates, [cacheKey]: rate }
        }))
        return rate
      }
      return null
    } catch (error) {
      console.error('Failed to fetch FMAPI Proprietary rate:', error)
      return null
    }
  },
  
  getFMAPIDatabricksRate: (model, rate_type) => {
    const { fmapiDatabricksRates } = get()
    const cacheKey = `${model}:${rate_type}`
    return fmapiDatabricksRates[cacheKey] || null
  },
  
  getFMAPIProprietaryRate: (provider, model, rate_type) => {
    const { fmapiProprietaryRates } = get()
    const cacheKey = `${provider}:${model}:${rate_type}`
    return fmapiProprietaryRates[cacheKey] || null
  },
  
  // Cost Calculation
  calculateWorkloadCost: async (lineItem, estimateCloud, estimateRegion, estimateTier) => {
    if (!lineItem.workload_type || !estimateCloud || !estimateRegion || !estimateTier) {
      return null
    }
    
    // Mark this specific item as calculating (if not already tracked by calculateAllWorkloadCosts)
    set((state) => ({
      calculatingCostIds: new Set([...state.calculatingCostIds, lineItem.line_item_id])
    }))
    
    try {
      // Build the request parameters based on workload type
      const baseParams = {
        cloud: estimateCloud.toUpperCase(),
        region: estimateRegion,
        tier: estimateTier.toUpperCase()
      }
      
      let result: CostCalculationResponse | null = null
      
      // Determine usage params: either run-based OR hours-based (not both)
      // If hours_per_month is set and > 0, use direct hours mode
      // Otherwise use run-based mode
      const useDirectHours = lineItem.hours_per_month && lineItem.hours_per_month > 0 && !lineItem.runs_per_day
      const usageParams = useDirectHours
        ? { hours_per_month: lineItem.hours_per_month }
        : { 
            runs_per_day: lineItem.runs_per_day || 1,
            avg_runtime_minutes: lineItem.avg_runtime_minutes || 30,
            days_per_month: lineItem.days_per_month || 22
          }
      
      switch (lineItem.workload_type) {
        case 'JOBS':
        case 'ALL_PURPOSE':
          if (lineItem.serverless_enabled) {
            result = await api.calculateWorkloadCost(lineItem.workload_type, true, {
              ...baseParams,
              driver_node_type: lineItem.driver_node_type || 'm5.xlarge',
              worker_node_type: lineItem.worker_node_type || 'm5.xlarge',
              num_workers: lineItem.num_workers || 1,
              serverless_mode: lineItem.serverless_mode || 'standard',
              ...usageParams
            })
          } else {
            const driverTier = lineItem.driver_pricing_tier || 'on_demand'
            const workerTier = lineItem.worker_pricing_tier || 'spot'
            
            // Payment option is "NA" for on_demand/spot, or the actual payment option for reserved
            const driverPayment = (driverTier === 'on_demand' || driverTier === 'spot') 
              ? 'NA' 
              : (lineItem.driver_payment_option || 'NA')
            const workerPayment = (workerTier === 'on_demand' || workerTier === 'spot')
              ? 'NA'
              : (lineItem.worker_payment_option || 'NA')
            
            result = await api.calculateWorkloadCost(lineItem.workload_type, false, {
              ...baseParams,
              driver_node_type: lineItem.driver_node_type || 'm5.xlarge',
              worker_node_type: lineItem.worker_node_type || 'm5.xlarge',
              num_workers: lineItem.num_workers || 1,
              photon_enabled: lineItem.photon_enabled || false,
              driver_pricing_tier: driverTier,
              worker_pricing_tier: workerTier,
              driver_payment_option: driverPayment,
              worker_payment_option: workerPayment,
              ...usageParams
            })
          }
          break
          
        case 'DLT':
          if (lineItem.serverless_enabled) {
            result = await api.calculateDLTServerless({
              ...baseParams,
              driver_node_type: lineItem.driver_node_type || 'm5.xlarge',
              worker_node_type: lineItem.worker_node_type || 'm5.xlarge',
              num_workers: lineItem.num_workers || 1,
              serverless_mode: lineItem.serverless_mode || 'standard',
              ...usageParams
            })
          } else {
            const dltDriverTier = lineItem.driver_pricing_tier || 'on_demand'
            const dltWorkerTier = lineItem.worker_pricing_tier || 'spot'
            const dltDriverPayment = (dltDriverTier === 'on_demand' || dltDriverTier === 'spot')
              ? 'NA'
              : (lineItem.driver_payment_option || 'NA')
            const dltWorkerPayment = (dltWorkerTier === 'on_demand' || dltWorkerTier === 'spot')
              ? 'NA'
              : (lineItem.worker_payment_option || 'NA')
            
            result = await api.calculateDLTClassic({
              ...baseParams,
              dlt_edition: lineItem.dlt_edition || 'CORE',
              photon_enabled: lineItem.photon_enabled || false,
              driver_node_type: lineItem.driver_node_type || 'm5.xlarge',
              worker_node_type: lineItem.worker_node_type || 'm5.xlarge',
              num_workers: lineItem.num_workers || 1,
              driver_pricing_tier: dltDriverTier,
              worker_pricing_tier: dltWorkerTier,
              driver_payment_option: dltDriverPayment,
              worker_payment_option: dltWorkerPayment,
              ...usageParams
            })
          }
          break
          
        case 'DBSQL':
          const warehouseType = lineItem.dbsql_warehouse_type?.toUpperCase() || 'SERVERLESS'
          if (warehouseType === 'SERVERLESS') {
            result = await api.calculateDBSQLServerless({
              ...baseParams,
              warehouse_size: lineItem.dbsql_warehouse_size || 'Medium',
              num_clusters: lineItem.dbsql_num_clusters || 1,
              ...usageParams
            })
          } else {
            // Use driver pricing tier for API (API doesn't support separate driver/worker pricing)
            const dbsqlVMTier = lineItem.dbsql_driver_pricing_tier || lineItem.driver_pricing_tier || 'on_demand'
            const dbsqlVMPayment = (dbsqlVMTier === 'on_demand' || dbsqlVMTier === 'spot')
              ? 'NA'
              : (lineItem.dbsql_driver_payment_option || lineItem.driver_payment_option || 'NA')
            
            result = await api.calculateDBSQLClassicPro({
              ...baseParams,
              warehouse_type: warehouseType,
              warehouse_size: lineItem.dbsql_warehouse_size || 'Medium',
              num_clusters: lineItem.dbsql_num_clusters || 1,
              vm_pricing_tier: dbsqlVMTier,
              vm_payment_option: dbsqlVMPayment,
              ...usageParams
            })
          }
          break
          
        case 'VECTOR_SEARCH':
          result = await api.calculateVectorSearch({
            ...baseParams,
            mode: lineItem.vector_search_mode || 'standard',
            vector_capacity_millions: lineItem.vector_capacity_millions || 1,
            hours_per_month: lineItem.hours_per_month || 730
          })
          break
          
        case 'MODEL_SERVING':
          result = await api.calculateModelServing({
            ...baseParams,
            gpu_type: lineItem.model_serving_gpu_type || 'cpu',
            scale_out: lineItem.model_serving_scale_out || 'small',
            ...(lineItem.model_serving_scale_out === 'custom' ? { custom_concurrency: lineItem.model_serving_concurrency || 4 } : {}),
            hours_per_month: lineItem.hours_per_month || 730
          })
          break
          
        case 'FMAPI_DATABRICKS':
          result = await api.calculateFMAPIDatabricks({
            ...baseParams,
            model: lineItem.fmapi_model || 'llama-3-3-70b',
            rate_type: lineItem.fmapi_rate_type || 'input_token',
            quantity: lineItem.fmapi_quantity || 1000000
          })
          break
          
        case 'FMAPI_PROPRIETARY':
          result = await api.calculateFMAPIProprietary({
            ...baseParams,
            provider: lineItem.fmapi_provider || 'anthropic',
            model: lineItem.fmapi_model || 'claude-opus-4-6',
            endpoint_type: lineItem.fmapi_endpoint_type || 'global',
            context_length: lineItem.fmapi_context_length || 'all',
            rate_type: lineItem.fmapi_rate_type || 'input_token',
            quantity: lineItem.fmapi_quantity || 1000000
          })
          break
          
        case 'LAKEBASE':
          result = await api.calculateLakebase({
            ...baseParams,
            cu_size: lineItem.lakebase_cu || 2,
            num_nodes: lineItem.lakebase_ha_nodes || 1,
            hours_per_month: lineItem.hours_per_month || 730,
            storage_gb: lineItem.lakebase_storage_gb || 0,
            pitr_gb: lineItem.lakebase_pitr_gb || 0,
            snapshot_gb: lineItem.lakebase_snapshot_gb || 0,
          })
          break

        case 'DATABRICKS_APPS':
          result = await api.calculateDatabricksApps({
            ...baseParams,
            size: lineItem.databricks_apps_size || 'medium',
            hours_per_month: lineItem.hours_per_month || 730,
          })
          break

        case 'AI_PARSE':
          result = await api.calculateAIParse({
            ...baseParams,
            mode: 'pages',
            complexity: lineItem.ai_parse_complexity || 'medium',
            pages_thousands: lineItem.ai_parse_pages_thousands || 1,
          })
          break

        case 'SHUTTERSTOCK_IMAGEAI':
          result = await api.calculateShutterstockImageAI({
            ...baseParams,
            images_per_month: lineItem.shutterstock_images || 100,
          })
          break
      }
      
      if (result) {
        set((state) => {
          const newCalcIds = new Set(state.calculatingCostIds)
          newCalcIds.delete(lineItem.line_item_id)
          return {
            workloadCosts: {
              ...state.workloadCosts,
              [lineItem.line_item_id]: result
            },
            calculatingCostIds: newCalcIds,
            isCalculatingCost: newCalcIds.size > 0
          }
        })
      }
      
      return result
    } catch (error) {
      console.error('Failed to calculate workload cost:', error)
      set((state) => {
        const newCalcIds = new Set(state.calculatingCostIds)
        newCalcIds.delete(lineItem.line_item_id)
        return { 
          calculatingCostIds: newCalcIds,
          isCalculatingCost: newCalcIds.size > 0
        }
      })
      return null
    }
  },
  
  calculateAllWorkloadCosts: async (estimateId, options?: { forceRecalculate?: boolean; onlyLineItemIds?: string[] }) => {
    const { lineItems, currentEstimate, workloadCosts } = get()
    
    if (!currentEstimate) return
    
    const estimateCloud = currentEstimate.cloud || 'AWS'
    const estimateRegion = currentEstimate.region || 'us-east-1'
    const estimateTier = currentEstimate.tier || 'PREMIUM'
    
    let estimateLineItems = lineItems.filter(li => li.estimate_id === estimateId)
    
    if (estimateLineItems.length === 0) return
    
    // If specific line item IDs are provided, only calculate those
    if (options?.onlyLineItemIds && options.onlyLineItemIds.length > 0) {
      estimateLineItems = estimateLineItems.filter(li => 
        options.onlyLineItemIds!.includes(li.line_item_id)
      )
    } else if (!options?.forceRecalculate) {
      // Smart calculation: skip items that already have cached costs
      // Only recalculate new items (no cached cost) or items marked for recalculation
      estimateLineItems = estimateLineItems.filter(li => {
        const cachedCost = workloadCosts[li.line_item_id]
        // Recalculate if: no cached cost, or cached cost has an error
        return !cachedCost || !cachedCost.success
      })
      
      // If all workloads have cached costs, nothing to do
      if (estimateLineItems.length === 0) {
        return
      }
    }
    
    // Mark only the items that need calculation
    const idsToCalculate = new Set(estimateLineItems.map(li => li.line_item_id))
    set({ isCalculatingCost: true, calculatingCostIds: idsToCalculate })
    
    // Process in chunks of 6 (browser connection limit per origin)
    const CHUNK_SIZE = 6
    const chunks: LineItem[][] = []
    for (let i = 0; i < estimateLineItems.length; i += CHUNK_SIZE) {
      chunks.push(estimateLineItems.slice(i, i + CHUNK_SIZE))
    }
    
    // Process chunks sequentially, items within chunk in parallel
    // This ensures progressive loading: first 6 complete, then next 6, etc.
    for (const chunk of chunks) {
      await Promise.all(
        chunk.map(async (lineItem) => {
          try {
            await get().calculateWorkloadCost(lineItem, estimateCloud, estimateRegion, estimateTier)
          } finally {
            // Remove this item from calculating set (progressive update)
            set((state) => {
              const newSet = new Set(state.calculatingCostIds)
              newSet.delete(lineItem.line_item_id)
              return { 
                calculatingCostIds: newSet,
                // Only set isCalculatingCost to false when ALL are done
                isCalculatingCost: newSet.size > 0
              }
            })
          }
        })
      )
    }
    
    // Ensure final state is clean
    set({ isCalculatingCost: false, calculatingCostIds: new Set() })
  },
  
  // Recalculate only specific workloads (for updates)
  recalculateSingleWorkload: async (lineItemId: string) => {
    const { lineItems, currentEstimate } = get()
    
    if (!currentEstimate) return
    
    const lineItem = lineItems.find(li => li.line_item_id === lineItemId)
    if (!lineItem) return
    
    const estimateCloud = currentEstimate.cloud || 'AWS'
    const estimateRegion = currentEstimate.region || 'us-east-1'
    const estimateTier = currentEstimate.tier || 'PREMIUM'
    
    // Mark this item as calculating
    set((state) => ({
      calculatingCostIds: new Set([...state.calculatingCostIds, lineItemId]),
      isCalculatingCost: true
    }))
    
    try {
      await get().calculateWorkloadCost(lineItem, estimateCloud, estimateRegion, estimateTier)
    } finally {
      set((state) => {
        const newSet = new Set(state.calculatingCostIds)
        newSet.delete(lineItemId)
        return { 
          calculatingCostIds: newSet,
          isCalculatingCost: newSet.size > 0
        }
      })
    }
  },
  
  clearWorkloadCosts: () => set({ workloadCosts: {}, localCalculatedCosts: {}, calculatingCostIds: new Set() }),
  
  setLocalCalculatedCosts: (costs) => set({ localCalculatedCosts: costs }),
  
  clearSingleWorkloadCost: (lineItemId: string) => set((state) => {
    const newCosts = { ...state.workloadCosts }
    delete newCosts[lineItemId]
    return { workloadCosts: newCosts }
  }),
  
  markItemCalculating: (lineItemId: string) => set((state) => ({
    calculatingCostIds: new Set([...state.calculatingCostIds, lineItemId]),
    isCalculatingCost: true
  })),
  
  isItemCalculating: (lineItemId: string) => {
    return get().calculatingCostIds.has(lineItemId)
  },
  
  // Clone functions
  cloneEstimate: async (estimateId: string, newName?: string) => {
    set({ isLoading: true, error: null })
    try {
      const clonedEstimate = await api.cloneEstimate(estimateId, newName)
      // Add to estimates list - need to add line_item_count from original
      const originalEstimate = get().estimates.find(e => e.estimate_id === estimateId)
      const estimateListItem: EstimateListItem = {
        ...clonedEstimate,
        line_item_count: originalEstimate?.line_item_count || 0
      }
      set((state) => ({
        estimates: [estimateListItem, ...state.estimates],
        isLoading: false
      }))
      return clonedEstimate
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to clone estimate'
      set({ error: errorMessage, isLoading: false })
      return null
    }
  },
  
  cloneLineItem: async (lineItemId: string, newName?: string) => {
    set({ isLoading: true, error: null })
    try {
      const clonedItem = await api.cloneLineItem(lineItemId, newName)
      // Add to line items list
      set((state) => ({
        lineItems: [...state.lineItems, clonedItem],
        isLoading: false
      }))
      // Recalculate only the new cloned item
      get().recalculateSingleWorkload(clonedItem.line_item_id)
      return clonedItem
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to clone workload'
      set({ error: errorMessage, isLoading: false })
      return null
    }
  },
  
  clearError: () => set({ error: null })
}))
