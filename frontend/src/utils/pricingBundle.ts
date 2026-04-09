/**
 * Static Pricing Bundle Loader
 * 
 * Loads pre-generated pricing data from static JSON files.
 * These files are generated from Lakebase reference tables at deploy time.
 * 
 * Benefits:
 * - Zero runtime API calls for pricing lookups
 * - Instant cost calculations (<1ms)
 * - Works offline after initial load
 * - Cached in memory for app lifetime
 */

// ============================================================================
// Types
// ============================================================================

export interface InstanceDBURate {
  dbu_rate: number
  vcpus: number | null
  memory_gb: number | null
  family: string | null
}

export interface DBUMultiplier {
  multiplier: number
  category: string | null
  feature: string  // 'photon', 'serverless_dlt', 'serverless_jobs', 'serverless_notebook', 'lakebase'
}

export interface DBSQLRate {
  dbu_per_hour: number
  sku_product_type: string
  includes_compute: boolean
}

export interface DBSQLWarehouseConfig {
  driver_count: number
  driver_instance_type: string
  worker_count: number
  worker_instance_type: string
}

export interface VectorSearchRate {
  dbu_rate: number
  input_divisor: number
  sku_product_type: string
  description: string | null
}

export interface ModelServingRate {
  dbu_rate: number
  sku_product_type: string
  description: string | null
}

export interface FMAPIRate {
  dbu_rate: number
  input_divisor: number
  is_hourly: boolean
  sku_product_type: string
}

export interface PricingBundle {
  instanceDBURates: Record<string, Record<string, InstanceDBURate>>  // cloud -> instance_type -> rate
  dbuMultipliers: Record<string, DBUMultiplier>                       // "cloud:sku_type:feature" -> multiplier (photon, serverless, lakebase)
  // NOTE: vmCosts removed - too large (50+ MB). VM costs are now fetched on-demand via API per instance.
  dbuRates: Record<string, Record<string, number>>                   // "cloud:region:tier" -> product_type -> price
  dbsqlRates: Record<string, DBSQLRate>                              // "cloud:type:size" -> rate
  dbsqlWarehouseConfig: Record<string, DBSQLWarehouseConfig>         // "cloud:type:size" -> config
  vectorSearchRates: Record<string, VectorSearchRate>                // "cloud:mode" -> rate
  modelServingRates: Record<string, ModelServingRate>                // "cloud:gpu_type" -> rate
  fmapiDatabricksRates: Record<string, FMAPIRate>                    // "cloud:model:rate_type" -> rate
  fmapiProprietaryRates: Record<string, FMAPIRate>                   // "cloud:provider:model:endpoint:context:rate_type" -> rate
  loadedAt: Date | null
  isLoaded: boolean
}

// ============================================================================
// Loader
// ============================================================================

const PRICING_BASE_URL = '/static/pricing'

async function loadJSON<T>(filename: string): Promise<T> {
  const response = await fetch(`${PRICING_BASE_URL}/${filename}`)
  if (!response.ok) {
    throw new Error(`Failed to load ${filename}: ${response.status}`)
  }
  return response.json()
}

/**
 * Load all pricing bundle files.
 * Call this on app initialization.
 */
export async function loadPricingBundle(): Promise<PricingBundle> {
  console.log('📦 Loading pricing bundle...')
  const startTime = Date.now()
  
  try {
    // NOTE: vm-costs.json excluded - too large (50+ MB). VM costs are now fetched on-demand via API.
    const [
      instanceDBURates,
      dbuMultipliers,
      dbuRates,
      dbsqlRates,
      dbsqlWarehouseConfig,
      vectorSearchRates,
      modelServingRates,
      fmapiDatabricksRates,
      fmapiProprietaryRates
    ] = await Promise.all([
      loadJSON<Record<string, Record<string, InstanceDBURate>>>('instance-dbu-rates.json'),
      loadJSON<Record<string, DBUMultiplier>>('dbu-multipliers.json'),
      loadJSON<Record<string, Record<string, number>>>('dbu-rates.json'),
      loadJSON<Record<string, DBSQLRate>>('dbsql-rates.json'),
      loadJSON<Record<string, DBSQLWarehouseConfig>>('dbsql-warehouse-config.json'),
      loadJSON<Record<string, VectorSearchRate>>('vector-search-rates.json'),
      loadJSON<Record<string, ModelServingRate>>('model-serving-rates.json'),
      loadJSON<Record<string, FMAPIRate>>('fmapi-databricks-rates.json'),
      loadJSON<Record<string, FMAPIRate>>('fmapi-proprietary-rates.json')
    ])
    
    const loadTime = Date.now() - startTime
    console.log(`✅ Pricing bundle loaded in ${loadTime}ms`)
    
    return {
      instanceDBURates,
      dbuMultipliers,
      dbuRates,
      dbsqlRates,
      dbsqlWarehouseConfig,
      vectorSearchRates,
      modelServingRates,
      fmapiDatabricksRates,
      fmapiProprietaryRates,
      loadedAt: new Date(),
      isLoaded: true
    }
  } catch (error) {
    console.error('❌ Failed to load pricing bundle:', error)
    // Return empty bundle - calculations will use fallback values
    return createEmptyBundle()
  }
}

/**
 * Create an empty pricing bundle (for fallback/error cases).
 */
export function createEmptyBundle(): PricingBundle {
  return {
    instanceDBURates: {},
    dbuMultipliers: {},
    dbuRates: {},
    dbsqlRates: {},
    dbsqlWarehouseConfig: {},
    vectorSearchRates: {},
    modelServingRates: {},
    fmapiDatabricksRates: {},
    fmapiProprietaryRates: {},
    loadedAt: null,
    isLoaded: false
  }
}

// ============================================================================
// Lookup Helpers
// ============================================================================

/**
 * Get instance DBU rate.
 */
export function getInstanceDBURate(
  bundle: PricingBundle,
  cloud: string,
  instanceType: string
): number {
  const cloudData = bundle.instanceDBURates[cloud.toLowerCase()]
  if (!cloudData) return 0.5 // fallback
  
  const instance = cloudData[instanceType]
  return instance?.dbu_rate ?? 0.5 // fallback
}

/**
 * Get photon multiplier.
 * Key format in dbuMultipliers: "cloud:sku_type:feature"
 * For photon, feature = 'photon'
 */
export function getPhotonMultiplier(
  bundle: PricingBundle,
  cloud: string,
  skuType: string
): number {
  // Try exact match with photon feature
  const key = `${cloud.toLowerCase()}:${skuType}:photon`
  const data = bundle.dbuMultipliers[key]
  if (data?.multiplier) return data.multiplier
  
  // Try without feature (fallback for older data format)
  const keyNoFeature = `${cloud.toLowerCase()}:${skuType}`
  const dataNoFeature = bundle.dbuMultipliers[keyNoFeature]
  if (dataNoFeature?.multiplier) return dataNoFeature.multiplier
  
  return 2.0 // fallback
}

/**
 * Get serverless multiplier.
 * Key format in dbuMultipliers: "cloud:sku_type:feature"
 * For serverless, feature = 'serverless_dlt', 'serverless_jobs', or 'serverless_notebook'
 */
export function getServerlessMultiplier(
  bundle: PricingBundle,
  cloud: string,
  skuType: string,
  workloadType: string
): number {
  // Map workload type to feature name
  const featureMap: Record<string, string> = {
    'DLT': 'serverless_dlt',
    'JOBS': 'serverless_jobs',
    'ALL_PURPOSE': 'serverless_notebook'
  }
  const feature = featureMap[workloadType] || 'serverless_jobs'
  
  const key = `${cloud.toLowerCase()}:${skuType}:${feature}`
  const data = bundle.dbuMultipliers[key]
  return data?.multiplier ?? 1.0 // fallback (standard = 1x)
}

/**
 * Get VM cost per hour.
 * 
 * @deprecated VM costs are no longer stored in the pricing bundle (was 50+ MB).
 * Use the on-demand API via fetchVMCostForInstance() in useStore instead.
 * This function always returns 0 - the actual VM cost is fetched from the API
 * and cached in vmPricingMap when a specific instance type is selected.
 */
export function getVMCost(
  _bundle: PricingBundle,
  _cloud: string,
  _region: string,
  _instanceType: string,
  _pricingTier: string = 'on_demand',
  _paymentOption: string = 'NA'
): number {
  // VM costs are now fetched on-demand via API to avoid loading 50+ MB of data
  // The actual cost lookup happens in useStore.getVMPrice() which uses cached API responses
  return 0
}

/**
 * Get DBU price ($/DBU).
 */
export function getDBUPrice(
  bundle: PricingBundle,
  cloud: string,
  region: string,
  tier: string,
  productType: string
): number {
  // Normalize tier to uppercase (JSON keys use PREMIUM, STANDARD, etc.)
  const normalizedTier = tier.toUpperCase()
  const key = `${cloud.toLowerCase()}:${region}:${normalizedTier}`
  const tierData = bundle.dbuRates[key]
  
  if (tierData && tierData[productType] !== undefined) {
    return tierData[productType]
  }
  
  // Fallback: try global rates (for products without regional pricing)
  const globalKey = `${cloud.toLowerCase()}:global:${normalizedTier}`
  const globalData = bundle.dbuRates[globalKey]
  if (globalData && globalData[productType] !== undefined) {
    return globalData[productType]
  }
  
  // Fallback: try any region with this tier
  for (const k of Object.keys(bundle.dbuRates)) {
    if (k.startsWith(`${cloud.toLowerCase()}:`) && k.endsWith(`:${normalizedTier}`)) {
      const data = bundle.dbuRates[k]
      if (data && data[productType] !== undefined) {
        return data[productType]
      }
    }
  }
  
  // Hardcoded fallbacks by SKU type
  const fallbacks: Record<string, number> = {
    'JOBS_COMPUTE': 0.15,
    'JOBS_COMPUTE_(PHOTON)': 0.20,
    'ALL_PURPOSE_COMPUTE': 0.40,
    'ALL_PURPOSE_COMPUTE_(PHOTON)': 0.55,
    'SQL_COMPUTE': 0.22,
    'SQL_PRO_COMPUTE': 0.55,
    'SERVERLESS_SQL_COMPUTE': 0.70,
    'SERVERLESS_REAL_TIME_INFERENCE': 0.07,
  }
  
  return fallbacks[productType] ?? 0.15
}

/**
 * Get DBSQL warehouse rate.
 */
export function getDBSQLRate(
  bundle: PricingBundle,
  cloud: string,
  warehouseType: string,
  warehouseSize: string
): DBSQLRate | null {
  const key = `${cloud.toLowerCase()}:${warehouseType.toLowerCase()}:${warehouseSize}`
  return bundle.dbsqlRates[key] ?? null
}

/**
 * Get DBSQL warehouse config (for VM cost calculation).
 */
export function getDBSQLWarehouseConfig(
  bundle: PricingBundle,
  cloud: string,
  warehouseType: string,
  warehouseSize: string
): DBSQLWarehouseConfig | null {
  const key = `${cloud.toLowerCase()}:${warehouseType.toLowerCase()}:${warehouseSize}`
  return bundle.dbsqlWarehouseConfig[key] ?? null
}

/**
 * Get Vector Search rate.
 */
export function getVectorSearchRate(
  bundle: PricingBundle,
  cloud: string,
  mode: string
): VectorSearchRate | null {
  const key = `${cloud.toLowerCase()}:${mode}`
  return bundle.vectorSearchRates[key] ?? null
}

/**
 * Get Model Serving GPU rate.
 */
export function getModelServingRate(
  bundle: PricingBundle,
  cloud: string,
  gpuType: string
): ModelServingRate | null {
  const key = `${cloud.toLowerCase()}:${gpuType}`
  return bundle.modelServingRates[key] ?? null
}

/**
 * Get FMAPI Databricks rate.
 */
export function getFMAPIDatabricksRate(
  bundle: PricingBundle,
  cloud: string,
  model: string,
  rateType: string
): FMAPIRate | null {
  const key = `${cloud.toLowerCase()}:${model}:${rateType}`
  return bundle.fmapiDatabricksRates[key] ?? null
}

/**
 * Get FMAPI Proprietary rate.
 */
export function getFMAPIProprietaryRate(
  bundle: PricingBundle,
  cloud: string,
  provider: string,
  model: string,
  endpointType: string,
  contextLength: string,
  rateType: string
): FMAPIRate | null {
  const key = `${cloud.toLowerCase()}:${provider}:${model}:${endpointType}:${contextLength}:${rateType}`
  return bundle.fmapiProprietaryRates[key] ?? null
}

// ============================================================================
// Regional Workload Availability
// ============================================================================

/**
 * Mapping of SKU product types to workload types.
 * Used to determine which workload types are available based on SKUs in a region.
 */
const SKU_TO_WORKLOAD_MAP: Record<string, string> = {
  // Jobs
  'JOBS_COMPUTE': 'JOBS',
  'JOBS_LIGHT_COMPUTE': 'JOBS',
  'AUTOMATED_JOBS_COMPUTE': 'JOBS',
  'AUTOMATED_JOBS_LIGHT_COMPUTE': 'JOBS',
  'JOBS_COMPUTE_(PHOTON)': 'JOBS',
  'JOBS_SERVERLESS_COMPUTE': 'JOBS',
  
  // All Purpose
  'ALL_PURPOSE_COMPUTE': 'ALL_PURPOSE',
  'ALL_PURPOSE_COMPUTE_(PHOTON)': 'ALL_PURPOSE',
  'ALL_PURPOSE_COMPUTE_(DLT)': 'ALL_PURPOSE',
  'ALL_PURPOSE_SERVERLESS_COMPUTE': 'ALL_PURPOSE',
  'INTERACTIVE_SERVERLESS_COMPUTE': 'ALL_PURPOSE',
  
  // DLT / Lakeflow Declarative Pipelines
  'DLT_CORE_COMPUTE': 'DLT',
  'DLT_PRO_COMPUTE': 'DLT',
  'DLT_ADVANCED_COMPUTE': 'DLT',
  'DLT_CORE_COMPUTE_(PHOTON)': 'DLT',
  'DLT_PRO_COMPUTE_(PHOTON)': 'DLT',
  'DLT_ADVANCED_COMPUTE_(PHOTON)': 'DLT',
  'DELTA_LIVE_TABLES_SERVERLESS': 'DLT',
  
  // DBSQL
  'SQL_COMPUTE': 'DBSQL',
  'SQL_PRO_COMPUTE': 'DBSQL',
  'SERVERLESS_SQL_COMPUTE': 'DBSQL',
  
  // Vector Search
  'VECTOR_SEARCH_ENDPOINT': 'VECTOR_SEARCH',
  'MOSAIC_AI_VECTOR_SEARCH': 'VECTOR_SEARCH',
  
  // Model Serving
  'SERVERLESS_REAL_TIME_INFERENCE': 'MODEL_SERVING',
  'SERVERLESS_REAL_TIME_INFERENCE_LAUNCH': 'MODEL_SERVING',
  'MODEL_SERVING_SERVERLESS': 'MODEL_SERVING',
  'MOSAIC_AI_MODEL_SERVING': 'MODEL_SERVING',
  
  // Foundation Models - Databricks
  'FOUNDATION_MODEL_TRAINING': 'FMAPI_DATABRICKS',
  'MODEL_TRAINING': 'FMAPI_DATABRICKS',
  'MOSAIC_AI_FOUNDATION_MODEL_SERVING': 'FMAPI_DATABRICKS',
  'DATABRICKS_FOUNDATION_MODEL_TRAINING': 'FMAPI_DATABRICKS',
  
  // Foundation Models - Proprietary
  'OPENAI_MODEL_SERVING': 'FMAPI_PROPRIETARY',
  'ANTHROPIC_MODEL_SERVING': 'FMAPI_PROPRIETARY',
  'GOOGLE_MODEL_SERVING': 'FMAPI_PROPRIETARY',
  'GEMINI_MODEL_SERVING': 'FMAPI_PROPRIETARY',
  'EXTERNAL_MODEL_SERVING': 'FMAPI_PROPRIETARY',
  
  // Lakebase
  'DATABASE_SERVERLESS_COMPUTE': 'LAKEBASE',
  'LAKEBASE_COMPUTE': 'LAKEBASE',
}

/**
 * All possible workload types for fallback.
 */
const ALL_WORKLOAD_TYPES = [
  'JOBS', 'ALL_PURPOSE', 'DLT', 'DBSQL',
  'VECTOR_SEARCH', 'MODEL_SERVING', 'FMAPI_DATABRICKS', 'FMAPI_PROPRIETARY', 'LAKEBASE',
  'DATABRICKS_APPS', 'AI_PARSE', 'SHUTTERSTOCK_IMAGEAI'
]

/**
 * Get available workload types for a specific cloud/region/tier combination from the pricing bundle.
 * Maps SKU product types to workload types.
 * 
 * Also checks serverless workloads (Vector Search, Model Serving, FMAPI, Lakebase) which are 
 * stored in separate bundle files and are typically available globally across regions.
 * 
 * @param bundle - The loaded pricing bundle
 * @param cloud - Cloud provider (aws, azure, gcp)
 * @param region - Region code (e.g., us-east-1, eastus, us-central1)
 * @param tier - Pricing tier (PREMIUM, ENTERPRISE)
 * @returns Array of available workload types, or all types if region not found (graceful fallback)
 */
export function getAvailableWorkloadTypesForRegion(
  bundle: PricingBundle,
  cloud: string,
  region: string,
  tier: string
): string[] {
  if (!bundle.isLoaded || !bundle.dbuRates) {
    // Bundle not loaded, return all types (graceful fallback)
    return ALL_WORKLOAD_TYPES
  }
  
  const cloudLower = cloud.toLowerCase()
  const key = `${cloudLower}:${region}:${tier.toUpperCase()}`
  const productTypes = bundle.dbuRates[key]
  
  if (!productTypes || Object.keys(productTypes).length === 0) {
    // Region not found in bundle - could be a new region or typo
    // Return all types as fallback (don't block users)
    return ALL_WORKLOAD_TYPES
  }
  
  // Map SKU product types to workload types from dbuRates
  const availableWorkloads = new Set<string>()
  
  for (const sku of Object.keys(productTypes)) {
    const workloadType = SKU_TO_WORKLOAD_MAP[sku]
    if (workloadType) {
      availableWorkloads.add(workloadType)
    }
  }
  
  // Check serverless workloads which are in separate bundle files
  // These are typically globally available and keyed by cloud (not region)
  
  // Vector Search: check if cloud has vector search rates
  if (bundle.vectorSearchRates) {
    const vsStandardKey = `${cloudLower}:standard`
    const vsOptimizedKey = `${cloudLower}:storage_optimized`
    if (bundle.vectorSearchRates[vsStandardKey] || bundle.vectorSearchRates[vsOptimizedKey]) {
      availableWorkloads.add('VECTOR_SEARCH')
    }
  }
  
  // Model Serving: check if cloud has model serving rates
  if (bundle.modelServingRates) {
    const hasMSRates = Object.keys(bundle.modelServingRates).some(k => k.startsWith(`${cloudLower}:`))
    if (hasMSRates) {
      availableWorkloads.add('MODEL_SERVING')
    }
  }
  
  // FMAPI Databricks: check if cloud has FMAPI Databricks rates
  if (bundle.fmapiDatabricksRates) {
    const hasFMAPIDB = Object.keys(bundle.fmapiDatabricksRates).some(k => k.startsWith(`${cloudLower}:`))
    if (hasFMAPIDB) {
      availableWorkloads.add('FMAPI_DATABRICKS')
    }
  }
  
  // FMAPI Proprietary: check if cloud has FMAPI Proprietary rates
  if (bundle.fmapiProprietaryRates) {
    const hasFMAPIProp = Object.keys(bundle.fmapiProprietaryRates).some(k => k.startsWith(`${cloudLower}:`))
    if (hasFMAPIProp) {
      availableWorkloads.add('FMAPI_PROPRIETARY')
    }
  }
  
  // Lakebase: check if DATABASE_SERVERLESS_COMPUTE exists in dbuRates for this region
  // (already handled by SKU_TO_WORKLOAD_MAP above, but ensure it's covered)

  // Databricks Apps: uses ALL_PURPOSE_SERVERLESS_COMPUTE — available wherever ALL_PURPOSE is
  if (availableWorkloads.has('ALL_PURPOSE')) {
    availableWorkloads.add('DATABRICKS_APPS')
  }

  // AI Parse: uses SERVERLESS_REAL_TIME_INFERENCE — available wherever Model Serving is
  if (availableWorkloads.has('MODEL_SERVING') || productTypes['SERVERLESS_REAL_TIME_INFERENCE']) {
    availableWorkloads.add('AI_PARSE')
    availableWorkloads.add('SHUTTERSTOCK_IMAGEAI')
  }

  return Array.from(availableWorkloads).sort()
}

/**
 * Get all unique regions available in the pricing bundle for a cloud.
 * Useful for populating region dropdowns with only regions that have pricing data.
 * 
 * @param bundle - The loaded pricing bundle
 * @param cloud - Cloud provider (aws, azure, gcp)
 * @returns Array of region codes
 */
export function getAvailableRegionsFromBundle(
  bundle: PricingBundle,
  cloud: string
): string[] {
  if (!bundle.isLoaded || !bundle.dbuRates) {
    return []
  }
  
  const cloudPrefix = `${cloud.toLowerCase()}:`
  const regions = new Set<string>()
  
  for (const key of Object.keys(bundle.dbuRates)) {
    if (key.startsWith(cloudPrefix)) {
      // Key format: cloud:region:tier
      const parts = key.split(':')
      if (parts.length >= 2) {
        regions.add(parts[1])
      }
    }
  }
  
  return Array.from(regions).sort()
}

/**
 * Check if a specific workload type is available in a region.
 * 
 * @param bundle - The loaded pricing bundle
 * @param cloud - Cloud provider
 * @param region - Region code
 * @param tier - Pricing tier
 * @param workloadType - Workload type to check
 * @returns true if available, false otherwise
 */
export function isWorkloadTypeAvailableInRegion(
  bundle: PricingBundle,
  cloud: string,
  region: string,
  tier: string,
  workloadType: string
): boolean {
  const available = getAvailableWorkloadTypesForRegion(bundle, cloud, region, tier)
  return available.includes(workloadType)
}

