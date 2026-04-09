import axios from 'axios'
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
  VMInstanceType,
  ModelServingGPUType,
  FMAPIDatabricksConfig,
  FMAPIProprietaryConfig
} from '../types'

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Custom event for session expiration - dispatched to window so any component can listen
export const SESSION_EXPIRED_EVENT = 'lakemeter:session-expired'

// Helper: unwrap {success, data} API response envelope.
// Backend endpoints return {success: true, data: <payload>}. This extracts <payload>.
// Falls through to raw response if the envelope isn't present (legacy/direct endpoints).
function unwrap<T>(data: any): T {
  if (data && typeof data === 'object' && 'success' in data && 'data' in data) {
    return data.data as T
  }
  return data as T
}

// Track if we've already shown the session expired message to avoid spam
let sessionExpiredShown = false

export const resetSessionExpiredFlag = () => {
  sessionExpiredShown = false
}

// Response interceptor to handle authentication errors
api.interceptors.response.use(
  (response) => {
    // Successful response - session is valid
    return response
  },
  (error) => {
    // Check for session expiration (401 Unauthorized or 403 Forbidden)
    if (error.response?.status === 401 || error.response?.status === 403) {
      console.error('Session expired or authentication required')
      
      // Only dispatch the event once to avoid multiple modals
      if (!sessionExpiredShown) {
        sessionExpiredShown = true
        
        // Dispatch custom event that Layout component will listen to
        window.dispatchEvent(new CustomEvent(SESSION_EXPIRED_EVENT, {
          detail: {
            status: error.response?.status,
            message: error.response?.data?.detail || 'Your session has expired'
          }
        }))
      }
    }
    return Promise.reject(error)
  }
)

// ============================================================================
// Current User
// ============================================================================
export interface CurrentUser {
  user_id: string
  email: string
  full_name: string | null
  role: string | null
}

export const fetchCurrentUser = async (): Promise<CurrentUser> => {
  const { data } = await api.get('/estimates/me/info')
  return data
}

// ============================================================================
// Estimates
// ============================================================================
export const fetchEstimates = async (params?: { status?: string; cloud?: string }): Promise<EstimateListItem[]> => {
  const { data } = await api.get('/estimates/', { params })
  return data
}

export const fetchEstimate = async (id: string): Promise<Estimate> => {
  const { data } = await api.get(`/estimates/${id}`)
  return data
}

// Optimized: Fetch estimate + line items in a single request
export const fetchEstimateWithLineItems = async (id: string): Promise<{ estimate: Estimate; line_items: LineItem[] }> => {
  const { data } = await api.get(`/estimates/${id}/full`)
  return data
}

export const createEstimate = async (estimate: Partial<Estimate>): Promise<Estimate> => {
  const { data } = await api.post('/estimates/', estimate)
  return data
}

export const updateEstimate = async (id: string, estimate: Partial<Estimate>): Promise<Estimate> => {
  const { data } = await api.put(`/estimates/${id}`, estimate)
  return data
}

export const deleteEstimate = async (id: string): Promise<void> => {
  await api.delete(`/estimates/${id}`)
}

export const duplicateEstimate = async (id: string): Promise<Estimate> => {
  const { data } = await api.post(`/estimates/${id}/duplicate`)
  return data
}

// Clone estimate with optional new name
export const cloneEstimate = async (id: string, newName?: string): Promise<Estimate> => {
  const { data } = await api.post(`/estimates/${id}/clone`, { new_name: newName })
  return data
}

// Clone line item/workload with optional new name
export const cloneLineItem = async (lineItemId: string, newName?: string): Promise<LineItem> => {
  const { data } = await api.post(`/line-items/${lineItemId}/clone`, { new_name: newName })
  return data
}

// ============================================================================
// Line Items
// ============================================================================
export const fetchLineItems = async (estimateId: string): Promise<LineItem[]> => {
  const { data } = await api.get(`/line-items/estimate/${estimateId}`)
  return data
}

export const createLineItem = async (lineItem: Partial<LineItem> & { estimate_id: string }): Promise<LineItem> => {
  const { data } = await api.post('/line-items/', lineItem)
  return data
}

export const updateLineItem = async (id: string, lineItem: Partial<LineItem>): Promise<LineItem> => {
  const { data } = await api.put(`/line-items/${id}`, lineItem)
  return data
}

export const deleteLineItem = async (id: string): Promise<void> => {
  await api.delete(`/line-items/${id}`)
}

export const reorderLineItems = async (estimateId: string, itemIds: string[]): Promise<void> => {
  await api.post('/line-items/reorder', itemIds, { params: { estimate_id: estimateId } })
}

export const reorderEstimates = async (estimateIds: string[]): Promise<void> => {
  await api.post('/estimates/reorder', estimateIds)
}

// ============================================================================
// Workload Types (from Lakebase database)
// ============================================================================
export const fetchWorkloadTypes = async (): Promise<WorkloadType[]> => {
  const { data } = await api.get('/workload-types')
  return data
}

// ============================================================================
// Cloud & Regions (NEW API)
// ============================================================================
export interface Region {
  region_code: string
  region_name: string
  cloud: string
}

export interface Tier {
  tier: string
  description?: string
}

export interface RegionResponse {
  region_code: string
  sku_region: string
}

export interface RegionsApiResponse {
  success: boolean
  data: {
    cloud: string
    count: number
    regions: RegionResponse[]
  }
}

export const fetchRegions = async (cloud: string): Promise<RegionResponse[]> => {
  const { data } = await api.get<RegionsApiResponse>('/regions', { params: { cloud: cloud.toUpperCase() } })
  if (data.success && data.data?.regions) {
    return data.data.regions
  }
  return []
}

export const fetchTiers = async (cloud?: string): Promise<Tier[]> => {
  const { data } = await api.get('/tiers', { params: cloud ? { cloud } : {} })
  const result = unwrap<any>(data)
  return Array.isArray(result) ? result : (result?.tiers || [])
}

// ============================================================================
// Reference Data (Legacy - for compatibility)
// ============================================================================
export const fetchCloudProviders = async (): Promise<CloudProvider[]> => {
  const { data } = await api.get('/clouds')
  if (Array.isArray(data) && data.length > 0 && data[0].id) {
    return data
  }
  throw new Error('Invalid cloud providers response')
}

export const fetchDBSQLSizes = async (): Promise<DBSQLSize[]> => {
  const { data } = await api.get('/dbsql/warehouse-sizes')
  const result = unwrap<any>(data)
  return Array.isArray(result) ? result : (result?.sizes || [])
}

export const fetchDLTEditions = async (): Promise<DLTEdition[]> => {
  const { data } = await api.get('/dlt/editions')
  const result = unwrap<any>(data)
  return Array.isArray(result) ? result : (result?.editions || [])
}

export const fetchFMAPIModels = async (): Promise<FMAPIProvider[]> => {
  const { data } = await api.get('/reference/fmapi-models')
  return data
}

// ============================================================================
// Compute - Instance Types (NEW API)
// ============================================================================
export interface InstanceFamily {
  family: string
}

export interface InstanceTypeWithPricing {
  instance_type: string
  instance_family: string
  vcpus: number
  memory_gb: number
  dbu_rate: number
}

export interface VMCost {
  cloud: string
  region: string
  instance_type: string
  pricing_tier: string
  payment_option: string
  cost_per_hour: number
  currency: string
}

export interface VMPricingOption {
  pricing_tier: string
  payment_option: string
  description?: string
}

export const fetchInstanceFamilies = async (): Promise<string[]> => {
  const { data } = await api.get('/instances/families')
  const result = unwrap<any>(data)
  return Array.isArray(result) ? result : (result?.families || [])
}

export const fetchInstanceTypes = async (cloud: string, region?: string, filters?: {
  instance_family?: string
  min_vcpus?: number
  max_vcpus?: number
  min_memory_gb?: number
  max_memory_gb?: number
  min_dbu_rate?: number
  max_dbu_rate?: number
  limit?: number
  offset?: number
}): Promise<InstanceType[]> => {
  const params: Record<string, string | number | undefined> = { cloud, limit: 1000 }
  if (region) params.region = region
  if (filters) {
    Object.assign(params, filters)
  }
  const { data } = await api.get('/instances/types', { params })
  // Transform API response to frontend format
  // API returns instance_type field, we map to both id and name
  const items = Array.isArray(data) ? data : (data?.data?.instance_types || data?.items || data?.data || [])
  return items.map((item: any) => {
    const instanceType = item.instance_type || item.id || item.name || ''
    return {
      id: instanceType,
      name: instanceType,
      vcpus: item.vcpus,
      memory_gb: item.memory_gb,
      dbu_rate: item.dbu_rate,
      instance_family: item.instance_family,
      vm_pricing: item.vm_pricing
    }
  })
}

export const fetchInstanceVMCosts = async (params: {
  cloud: string
  region: string
  instance_type: string
  pricing_tier?: string
  payment_option?: string
}): Promise<VMCost[]> => {
  // For on_demand and spot pricing tiers, payment_option should be NA or omitted
  // Only reserved_1y and reserved_3y have meaningful payment_options (no_upfront, partial_upfront, all_upfront)
  const cleanParams: Record<string, string> = {
    cloud: params.cloud,
    region: params.region,
    instance_type: params.instance_type
  }
  
  if (params.pricing_tier) {
    cleanParams.pricing_tier = params.pricing_tier
  }
  
  // Only include payment_option for reserved instances, or if explicitly NA
  const pricingTier = params.pricing_tier?.toLowerCase()
  if (pricingTier === 'reserved_1y' || pricingTier === 'reserved_3y') {
    // For reserved instances, include payment_option if specified
    if (params.payment_option && params.payment_option !== 'NA') {
      cleanParams.payment_option = params.payment_option
    }
  }
  // For on_demand and spot, don't send payment_option (API expects no payment_option or NA)
  
  const { data } = await api.get('/instances/vm-costs', { params: cleanParams })
  // API response structure: { success: true, data: { cloud, region, instance_type, instance_specs: { dbu_rate, ... }, pricing_options: [...] } }
  // Extract pricing_options and enrich with top-level fields, including dbu_rate from instance_specs
  if (data?.success && data?.data?.pricing_options) {
    const { cloud, region, instance_type, instance_specs } = data.data
    const dbuRate = instance_specs?.dbu_rate
    return data.data.pricing_options.map((option: { pricing_tier: string; payment_option: string; cost_per_hour: number }) => ({
      cloud,
      region,
      instance_type,
      pricing_tier: option.pricing_tier,
      payment_option: option.payment_option,
      cost_per_hour: option.cost_per_hour,
      currency: 'USD',
      dbu_rate: dbuRate  // Include DBU rate from instance_specs
    }))
  }
  // Fallback for direct array response
  if (Array.isArray(data)) {
    return data
  }
  return []
}

export const fetchVMPricingOptions = async (cloud?: string): Promise<VMPricingOption[]> => {
  const { data } = await api.get('/instances/vm-pricing-options', { params: cloud ? { cloud } : {} })
  return data
}

// ============================================================================
// DBSQL (NEW API)
// ============================================================================
export interface DBSQLWarehouseType {
  type: string
  description?: string
}

export interface DBSQLWarehouseSize {
  size: string
  dbu_per_hour: number
}

export interface DBSQLWarehouseVMCost {
  driver_vm_cost: number
  worker_vm_cost: number
  total_worker_vm_cost: number
  num_workers: number
  driver_instance_type: string
  worker_instance_type: string
}

export interface DBSQLWarehouseHardware {
  driver_instance_type: string
  driver_vcpus: number
  driver_memory_gb: number
  worker_instance_type: string
  worker_vcpus: number
  worker_memory_gb: number
  num_workers: number
}

export const fetchDBSQLWarehouseTypes = async (): Promise<string[]> => {
  const { data } = await api.get('/dbsql/warehouse-types')
  const result = unwrap<any>(data)
  return Array.isArray(result) ? result : (result?.warehouse_types || [])
}

export const fetchDBSQLWarehouseSizes = async (): Promise<DBSQLWarehouseSize[]> => {
  const { data } = await api.get('/dbsql/warehouse-sizes')
  const result = unwrap<any>(data)
  return Array.isArray(result) ? result : (result?.sizes || [])
}

export const fetchDBSQLWarehouseVMCosts = async (params: {
  cloud: string
  region: string
  warehouse_type: string
  warehouse_size: string
  pricing_tier?: string
  payment_option?: string
}): Promise<DBSQLWarehouseVMCost> => {
  const { data } = await api.get('/dbsql/warehouse-vm-costs', { params })
  return data
}

export const fetchDBSQLWarehouseHardware = async (params: {
  cloud: string
  warehouse_type: string
  warehouse_size: string
}): Promise<DBSQLWarehouseHardware> => {
  const { data } = await api.get('/dbsql/warehouse-hardware', { params })
  return data
}

// ============================================================================
// Vector Search (NEW API)
// ============================================================================
export interface VectorSearchMode {
  mode: string
  dbu_per_hour: number
  input_divisor: number
  description?: string
}

export const fetchVectorSearchModes = async (): Promise<string[]> => {
  const { data } = await api.get('/vector-search/list')
  const result = unwrap<any>(data)
  return Array.isArray(result) ? result : (result?.modes || [])
}

export const fetchVectorSearchModesWithPricing = async (cloud: string, mode?: string): Promise<VectorSearchMode[]> => {
  const { data } = await api.get('/vector-search/modes', { params: { cloud, mode } })
  const result = unwrap<any>(data)
  return Array.isArray(result) ? result : (result?.modes || [])
}

// ============================================================================
// Lakebase (NEW API)
// ============================================================================
export interface LakebaseCUSize {
  cu_size: number
}

export interface LakebaseDBUCalculation {
  cu_size: number
  num_nodes: number
  dbu_per_hour: number
}

export const fetchLakebaseCUSizes = async (): Promise<number[]> => {
  const { data } = await api.get('/lakebase/list')
  const result = unwrap<any>(data)
  return Array.isArray(result) ? result : (result?.cu_sizes || [])
}

export const calculateLakebaseDBU = async (cu_size: number, num_nodes: number): Promise<LakebaseDBUCalculation> => {
  const { data } = await api.get('/lakebase/calculate', { params: { cu_size, num_nodes } })
  return data
}

// ============================================================================
// Photon Multipliers (NEW API)
// ============================================================================
export interface PhotonMultiplier {
  sku_type: string
  multiplier: number
  category?: string
}

export const fetchPhotonSKUTypes = async (cloud: string): Promise<string[]> => {
  const { data } = await api.get('/photon/list', { params: { cloud } })
  const result = unwrap<any>(data)
  return Array.isArray(result) ? result : (result?.sku_types || [])
}

export const fetchPhotonMultipliers = async (cloud: string, sku_type?: string): Promise<PhotonMultiplier[]> => {
  const { data } = await api.get('/photon/multipliers', { params: { cloud, sku_type } })
  const result = unwrap<any>(data)
  return Array.isArray(result) ? result : (result?.multipliers || [])
}

// ============================================================================
// Serverless Modes (NEW API)
// ============================================================================
export interface ServerlessMode {
  mode: string
  multiplier?: number
  display_name?: string
  description?: string
}

export const fetchServerlessModes = async (): Promise<ServerlessMode[]> => {
  const { data } = await api.get('/serverless/modes')
  const result = unwrap<any>(data)
  return Array.isArray(result) ? result : (result?.modes || [])
}

// ============================================================================
// Pricing - DBU Rates (NEW API - Critical for cost calculation!)
// ============================================================================
export interface ProductType {
  product_type: string
}

export interface DBURate {
  product_type: string
  dbu_price: number
  currency: string
}

export const fetchProductTypes = async (cloud: string, region: string, tier: string): Promise<string[]> => {
  const { data } = await api.get('/pricing/product-types', { params: { cloud, region, tier } })
  const result = unwrap<any>(data)
  return Array.isArray(result) ? result : (result?.product_types || [])
}

export const fetchDBURates = async (params: {
  cloud: string
  region: string
  tier: string
  product_type?: string
}): Promise<DBURate[]> => {
  const { data } = await api.get('/pricing/dbu-rates', { params })
  // API returns {success, data: {dbu_rates: [...]}} — unwrap to flat array
  return data?.data?.dbu_rates || data?.dbu_rates || (Array.isArray(data) ? data : [])
}

// ============================================================================
// Model Serving (NEW API)
// ============================================================================
export const fetchModelServingGPUTypes = async (cloud: string): Promise<ModelServingGPUType[]> => {
  const { data } = await api.get('/model-serving/gpu-types', { params: { cloud } })
  const result = unwrap<any>(data)
  return Array.isArray(result) ? result : (result?.gpu_types || [])
}

// ============================================================================
// FMAPI - Databricks Models (NEW API)
// ============================================================================
export interface FMAPIDatabricksModel {
  model: string
  cloud: string
  rate_type: string
  dbu_per_hour?: number
  dbu_per_1M_tokens?: number
  is_hourly: boolean
}

export const fetchFMAPIDatabricksModelsList = async (): Promise<string[]> => {
  const { data } = await api.get('/fmapi/databricks-models/list')
  const result = unwrap<any>(data)
  return Array.isArray(result) ? result : (result?.models || [])
}

export const fetchFMAPIDatabricksModels = async (model: string, cloud?: string, rate_type?: string): Promise<FMAPIDatabricksModel[]> => {
  const { data } = await api.get('/fmapi/databricks-models', { params: { model, cloud, rate_type } })
  const result = unwrap<any>(data)
  return Array.isArray(result) ? result : (result?.models || [])
}

// Fetch ALL FMAPI Databricks rates for all models (for pre-caching)
export const fetchAllFMAPIDatabricksRates = async (cloud: string): Promise<FMAPIDatabricksModel[]> => {
  const allRates: FMAPIDatabricksModel[] = []
  try {
    // Get all model names first
    const models = await fetchFMAPIDatabricksModelsList()
    // Fetch rates for each model in parallel (batched)
    const batchSize = 5
    for (let i = 0; i < models.length; i += batchSize) {
      const batch = models.slice(i, i + batchSize)
      const results = await Promise.all(
        batch.map(model => fetchFMAPIDatabricksModels(model, cloud).catch(() => []))
      )
      results.forEach(rates => allRates.push(...rates))
    }
  } catch (error) {
    console.warn('Failed to fetch all FMAPI Databricks rates:', error)
  }
  return allRates
}

// Foundation Models (Databricks) configuration (Legacy - for compatibility)
export const fetchFMAPIDatabricksConfig = async (): Promise<FMAPIDatabricksConfig> => {
  const { data } = await api.get('/fmapi-databricks')
  // Validate response shape — backend may return error arrays on 200
  if (data && data.model_types && Array.isArray(data.model_types)) {
    return data
  }
  throw new Error('Invalid FMAPI Databricks config response')
}

// ============================================================================
// FMAPI - Proprietary Models (NEW API)
// ============================================================================
export interface FMAPIProprietaryModel {
  provider: string
  model: string
  cloud: string
  endpoint_type: string
  context_length: string
  rate_type: string
  dbu_per_hour?: number
  dbu_per_1M_tokens?: number
  is_hourly: boolean
}

export interface FMAPIProprietaryModelOptions {
  endpoint_types: string[]
  context_lengths: string[]
  rate_types: string[]
}

export const fetchFMAPIProprietaryModelsList = async (provider: string): Promise<string[]> => {
  const { data } = await api.get('/fmapi/proprietary-models/list', { params: { provider } })
  const result = unwrap<any>(data)
  return Array.isArray(result) ? result : (result?.models || [])
}

export const fetchFMAPIProprietaryModelOptions = async (provider: string, model: string): Promise<FMAPIProprietaryModelOptions> => {
  const { data } = await api.get('/fmapi/proprietary-models/options', { params: { provider, model } })
  return data
}

export const fetchFMAPIProprietaryModels = async (params: {
  provider: string
  cloud?: string
  model?: string
  endpoint_type?: string
  context_length?: string
  rate_type?: string
}): Promise<FMAPIProprietaryModel[]> => {
  const { data } = await api.get('/fmapi/proprietary-models', { params })
  return data
}

// Fetch ALL FMAPI Proprietary rates for all providers (for pre-caching)
export const fetchAllFMAPIProprietaryRates = async (cloud: string): Promise<FMAPIProprietaryModel[]> => {
  const providers = ['openai', 'anthropic', 'google']
  const allRates: FMAPIProprietaryModel[] = []
  try {
    // Fetch rates for each provider in parallel
    const results = await Promise.all(
      providers.map(provider => 
        fetchFMAPIProprietaryModels({ provider, cloud }).catch(() => [])
      )
    )
    results.forEach(rates => allRates.push(...rates))
  } catch (error) {
    console.warn('Failed to fetch all FMAPI Proprietary rates:', error)
  }
  return allRates
}

// Foundation Models (Proprietary) configuration (Legacy - for compatibility)
export const fetchFMAPIProprietaryConfig = async (): Promise<FMAPIProprietaryConfig> => {
  const { data } = await api.get('/fmapi-proprietary')
  // Validate response shape — backend may return error arrays on 200,
  // or return clouds as providers (wrong data from DB)
  const KNOWN_PROVIDERS = new Set(['anthropic', 'openai', 'google', 'meta', 'cohere', 'ai21'])
  if (data && data.providers && Array.isArray(data.providers) && data.providers.length > 0
      && KNOWN_PROVIDERS.has(data.providers[0].id)) {
    return data
  }
  throw new Error('Invalid FMAPI Proprietary config response')
}

// ============================================================================
// VM Pricing (Legacy - for compatibility)
// ============================================================================
export const fetchVMPricing = async (params: {
  cloud: string
  region?: string
  instance_type?: string
  pricing_tier?: string
}): Promise<VMPricing[]> => {
  const { data } = await api.get('/vm-pricing', { params })
  return data
}

export const fetchVMInstanceTypes = async (cloud: string, region?: string): Promise<VMInstanceType[]> => {
  const { data } = await api.get('/vm-pricing/instance-types', { params: { cloud, region } })
  return data
}

export const fetchVMPrice = async (params: {
  cloud: string
  region: string
  instance_type: string
  pricing_tier?: string
  payment_option?: string
}): Promise<{ cost_per_hour: number; currency: string; pricing_tier: string; payment_option: string; source: string }> => {
  const { data } = await api.get('/vm-pricing/price', { params })
  return data
}

export const fetchVMPricingTiers = async (): Promise<VMPricingTier[]> => {
  const { data } = await api.get('/vm-pricing/tiers')
  return data
}

export const fetchVMPaymentOptions = async (): Promise<VMPaymentOption[]> => {
  const { data } = await api.get('/vm-pricing/payment-options')
  return data
}

export const fetchVMRegions = async (cloud: string): Promise<{ region: string }[]> => {
  const { data } = await api.get('/vm-pricing/regions', { params: { cloud } })
  return data
}

// ============================================================================
// Export
// ============================================================================
export const exportEstimateToExcel = async (id: string): Promise<Blob> => {
  const { data } = await api.get(`/export/estimate/${id}/excel`, {
    responseType: 'blob'
  })
  return data
}

export const exportAllEstimatesToExcel = async (): Promise<Blob> => {
  const { data } = await api.get('/export/estimates/excel', {
    responseType: 'blob'
  })
  return data
}

// ============================================================================
// COST CALCULATION APIs (NEW - All POST endpoints)
// ============================================================================

// Base request types
interface BaseCalculationRequest {
  cloud: string
  region: string
  tier: string
}

interface RunBasedParams {
  runs_per_day?: number | null
  avg_runtime_minutes?: number | null
  days_per_month?: number | null
  hours_per_month?: number | null
}

// Response type for all calculation endpoints
// Matches the actual API response structure from the external Lakemeter API
export interface CostCalculationResponse {
  success: boolean
  data: {
    workload_type: string
    configuration?: Record<string, unknown>
    usage?: {
      runs_per_day?: number
      avg_runtime_minutes?: number
      days_per_month?: number
      hours_per_month?: number
    }
    // Standard compute workloads use dbu_calculation
    dbu_calculation?: {
      dbu_per_hour?: number
      dbu_per_month?: number
      dbu_price?: number
      dbu_cost_per_month?: number
    }
    // DBSQL workloads use dbu_costs
    dbu_costs?: {
      dbu_per_hour?: number
      dbu_per_month?: number
      dbu_price?: number
      dbu_cost_per_month?: number
    }
    vm_costs?: {
      driver_vm_cost_per_hour?: number
      worker_vm_cost_per_hour?: number
      total_vm_cost_per_hour?: number
      driver_vm_cost_per_month?: number
      total_worker_vm_cost_per_month?: number
      vm_cost_per_month?: number
    }
    // Standard compute/DBSQL workloads
    total_cost?: {
      cost_per_month?: number
      breakdown?: {
        dbu_cost?: number
        vm_cost?: number
      }
      note?: string
    }
    // FMAPI/token-based workloads use cost
    cost?: {
      total_cost?: number
      note?: string
    }
  }
}

// Jobs Classic
export interface JobsClassicRequest extends BaseCalculationRequest, RunBasedParams {
  driver_node_type: string
  worker_node_type: string
  num_workers: number
  photon_enabled?: boolean
  driver_pricing_tier?: string
  worker_pricing_tier?: string
  driver_payment_option?: string
  worker_payment_option?: string
}

export const calculateJobsClassic = async (request: JobsClassicRequest): Promise<CostCalculationResponse> => {
  const { data } = await api.post('/calculate/jobs-classic', request)
  return data
}

// All-Purpose Classic
export interface AllPurposeClassicRequest extends BaseCalculationRequest, RunBasedParams {
  driver_node_type: string
  worker_node_type: string
  num_workers: number
  photon_enabled?: boolean
  driver_pricing_tier?: string
  worker_pricing_tier?: string
  driver_payment_option?: string
  worker_payment_option?: string
}

export const calculateAllPurposeClassic = async (request: AllPurposeClassicRequest): Promise<CostCalculationResponse> => {
  const { data } = await api.post('/calculate/all-purpose-classic', request)
  return data
}

// Jobs Serverless
export interface JobsServerlessRequest extends BaseCalculationRequest, RunBasedParams {
  driver_node_type: string
  worker_node_type: string
  num_workers: number
  serverless_mode?: string
}

export const calculateJobsServerless = async (request: JobsServerlessRequest): Promise<CostCalculationResponse> => {
  const { data } = await api.post('/calculate/jobs-serverless', request)
  return data
}

// All-Purpose Serverless
export interface AllPurposeServerlessRequest extends BaseCalculationRequest, RunBasedParams {
  driver_node_type: string
  worker_node_type: string
  num_workers: number
  serverless_mode?: string
}

export const calculateAllPurposeServerless = async (request: AllPurposeServerlessRequest): Promise<CostCalculationResponse> => {
  const { data } = await api.post('/calculate/all-purpose-serverless', request)
  return data
}

// DBSQL Classic/Pro
export interface DBSQLClassicProRequest extends BaseCalculationRequest, RunBasedParams {
  warehouse_type: string
  warehouse_size: string
  num_clusters?: number
  vm_pricing_tier?: string
  vm_payment_option?: string
}

export const calculateDBSQLClassicPro = async (request: DBSQLClassicProRequest): Promise<CostCalculationResponse> => {
  const { data } = await api.post('/calculate/dbsql-classic-pro', request)
  return data
}

// DBSQL Serverless
export interface DBSQLServerlessRequest extends BaseCalculationRequest, RunBasedParams {
  warehouse_size: string
  num_clusters?: number
}

export const calculateDBSQLServerless = async (request: DBSQLServerlessRequest): Promise<CostCalculationResponse> => {
  const { data } = await api.post('/calculate/dbsql-serverless', request)
  return data
}

// DLT Classic
export interface DLTClassicRequest extends BaseCalculationRequest, RunBasedParams {
  dlt_edition: string
  photon_enabled?: boolean
  driver_node_type: string
  worker_node_type: string
  num_workers: number
  driver_pricing_tier?: string
  worker_pricing_tier?: string
  driver_payment_option?: string
  worker_payment_option?: string
}

export const calculateDLTClassic = async (request: DLTClassicRequest): Promise<CostCalculationResponse> => {
  const { data } = await api.post('/calculate/dlt-classic', request)
  return data
}

// DLT Serverless
export interface DLTServerlessRequest extends BaseCalculationRequest, RunBasedParams {
  driver_node_type: string
  worker_node_type: string
  num_workers: number
  serverless_mode?: string
}

export const calculateDLTServerless = async (request: DLTServerlessRequest): Promise<CostCalculationResponse> => {
  const { data } = await api.post('/calculate/dlt-serverless', request)
  return data
}

// Vector Search
export interface VectorSearchRequest extends BaseCalculationRequest {
  mode: string
  vector_capacity_millions: number
  hours_per_month?: number
}

export const calculateVectorSearch = async (request: VectorSearchRequest): Promise<CostCalculationResponse> => {
  const { data } = await api.post('/calculate/vector-search', request)
  return data
}

// Model Serving
export interface ModelServingRequest extends BaseCalculationRequest {
  gpu_type: string
  scale_out?: string
  custom_concurrency?: number
  hours_per_month?: number
}

export const calculateModelServing = async (request: ModelServingRequest): Promise<CostCalculationResponse> => {
  const { data } = await api.post('/calculate/model-serving', request)
  return data
}

// FMAPI (Generic)
export interface FMAPIRequest extends BaseCalculationRequest {
  provider: string
  model: string
  endpoint_type?: string
  context_length?: string
  rate_type: string
  quantity: number
}

export const calculateFMAPI = async (request: FMAPIRequest): Promise<CostCalculationResponse> => {
  const { data } = await api.post('/calculate/fmapi', request)
  return data
}

// FMAPI Databricks
export interface FMAPIDatabricksRequest extends BaseCalculationRequest {
  model: string
  rate_type: string
  quantity: number
}

export const calculateFMAPIDatabricks = async (request: FMAPIDatabricksRequest): Promise<CostCalculationResponse> => {
  const { data } = await api.post('/calculate/fmapi-databricks', request)
  return data
}

// FMAPI Proprietary
export interface FMAPIProprietaryRequest extends BaseCalculationRequest {
  provider: string
  model: string
  endpoint_type?: string
  context_length?: string
  rate_type: string
  quantity: number
}

export const calculateFMAPIProprietary = async (request: FMAPIProprietaryRequest): Promise<CostCalculationResponse> => {
  const { data } = await api.post('/calculate/fmapi-proprietary', request)
  return data
}

// Databricks Apps
export interface DatabricksAppsRequest extends BaseCalculationRequest {
  size?: string
  hours_per_month?: number
}

export const calculateDatabricksApps = async (request: DatabricksAppsRequest): Promise<CostCalculationResponse> => {
  const { data } = await api.post('/calculate/databricks-apps', request)
  return data
}

// Clean Room
export interface CleanRoomRequest extends BaseCalculationRequest {
  collaborators: number
  days_per_month?: number
}

export const calculateCleanRoom = async (request: CleanRoomRequest): Promise<CostCalculationResponse> => {
  const { data } = await api.post('/calculate/clean-room', request)
  return data
}

// AI Parse
export interface AIParseRequest extends BaseCalculationRequest {
  mode?: string
  complexity?: string
  pages_thousands?: number
  hours_per_month?: number
}

export const calculateAIParse = async (request: AIParseRequest): Promise<CostCalculationResponse> => {
  const { data } = await api.post('/calculate/ai-parse', request)
  return data
}

// Shutterstock ImageAI
export interface ShutterstockImageAIRequest extends BaseCalculationRequest {
  images_per_month: number
}

export const calculateShutterstockImageAI = async (request: ShutterstockImageAIRequest): Promise<CostCalculationResponse> => {
  const { data } = await api.post('/calculate/shutterstock-imageai', request)
  return data
}

// Lakeflow Connect
export interface LakeflowConnectRequest extends BaseCalculationRequest {
  dlt_edition?: string
  runs_per_day?: number
  avg_runtime_minutes?: number
  days_per_month?: number
  hours_per_month?: number
  gateway_enabled?: boolean
  gateway_instance_type?: string
  gateway_pricing_tier?: string
  gateway_payment_option?: string
  gateway_hours_per_month?: number
}

export const calculateLakeflowConnect = async (request: LakeflowConnectRequest): Promise<CostCalculationResponse> => {
  const { data } = await api.post('/calculate/lakeflow-connect', request)
  return data
}

// Lakebase
export interface LakebaseRequest extends BaseCalculationRequest {
  cu_size: number
  num_nodes: number
  hours_per_month?: number
  storage_gb?: number
  pitr_gb?: number
  snapshot_gb?: number
}

export const calculateLakebase = async (request: LakebaseRequest): Promise<CostCalculationResponse> => {
  const { data } = await api.post('/calculate/lakebase', request)
  return data
}

// ============================================================================
// Helper function to calculate cost based on workload type
// ============================================================================
export const calculateWorkloadCost = async (
  workloadType: string,
  serverlessEnabled: boolean,
  params: Record<string, unknown>
): Promise<CostCalculationResponse> => {
  switch (workloadType) {
    case 'JOBS':
      if (serverlessEnabled) {
        return calculateJobsServerless(params as unknown as JobsServerlessRequest)
      }
      return calculateJobsClassic(params as unknown as JobsClassicRequest)
    
    case 'ALL_PURPOSE':
      if (serverlessEnabled) {
        return calculateAllPurposeServerless(params as unknown as AllPurposeServerlessRequest)
      }
      return calculateAllPurposeClassic(params as unknown as AllPurposeClassicRequest)
    
    case 'DLT':
      if (serverlessEnabled) {
        return calculateDLTServerless(params as unknown as DLTServerlessRequest)
      }
      return calculateDLTClassic(params as unknown as DLTClassicRequest)
    
    case 'DBSQL':
      const warehouseType = (params as { warehouse_type?: string }).warehouse_type?.toUpperCase()
      if (warehouseType === 'SERVERLESS') {
        return calculateDBSQLServerless(params as unknown as DBSQLServerlessRequest)
      }
      return calculateDBSQLClassicPro(params as unknown as DBSQLClassicProRequest)
    
    case 'VECTOR_SEARCH':
      return calculateVectorSearch(params as unknown as VectorSearchRequest)
    
    case 'MODEL_SERVING':
      return calculateModelServing(params as unknown as ModelServingRequest)
    
    case 'FMAPI_DATABRICKS':
      return calculateFMAPIDatabricks(params as unknown as FMAPIDatabricksRequest)
    
    case 'FMAPI_PROPRIETARY':
      return calculateFMAPIProprietary(params as unknown as FMAPIProprietaryRequest)
    
    case 'LAKEBASE':
      return calculateLakebase(params as unknown as LakebaseRequest)

    case 'DATABRICKS_APPS':
      return calculateDatabricksApps(params as unknown as DatabricksAppsRequest)

    case 'CLEAN_ROOM':
      return calculateCleanRoom(params as unknown as CleanRoomRequest)

    case 'AI_PARSE':
      return calculateAIParse(params as unknown as AIParseRequest)

    case 'SHUTTERSTOCK_IMAGEAI':
      return calculateShutterstockImageAI(params as unknown as ShutterstockImageAIRequest)

    case 'LAKEFLOW_CONNECT':
      return calculateLakeflowConnect(params as unknown as LakeflowConnectRequest)

    default:
      throw new Error(`Unknown workload type: ${workloadType}`)
  }
}

export default api
