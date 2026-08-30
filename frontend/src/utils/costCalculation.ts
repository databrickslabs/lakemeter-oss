/**
 * Cost Calculation Utilities
 * Shared logic for calculating workload costs locally (no API calls)
 * Used for instant feedback in both Calculator.tsx and WorkloadForm.tsx
 */

import type { LineItem, InstanceType, DBSQLSize, ModelServingGPUType } from '../types'
import type { VectorSearchMode, PhotonMultiplier } from '../api/client'
import { calculateLakebaseComputeUsage, resolveLakebaseAutoscaleConfig } from './lakebasePricing'
import { calculateAIRuntimeUsage } from './aiRuntime'

export const AI_GATEWAY_COMPONENT_RATES = {
  inferenceTables: 1.429,
  usageTracking: 1.429,
} as const

export const AGENT_EVALUATION_COMPONENT_RATES = {
  inputTokens: 2.143,
  outputTokens: 8.571,
  syntheticQuestions: 5,
} as const

export const AI_SEARCH_INCLUDED_STORAGE_GB = 30
export const AI_SEARCH_STANDARD_STORAGE_DSU_PER_GB = 10
export const AI_SEARCH_STORAGE_OPTIMIZED_DSU_PER_GB = 2
export const AI_SEARCH_RERANKER_DBU_PER_THOUSAND_REQUESTS = 28.571
export const MODEL_SERVING_GPU_CONCURRENCY_PER_REPLICA = 4
export const GENERAL_STORAGE_GB_PER_TB = 1024
export const GENERAL_STORAGE_STORED_DATA_DSU_PER_GB = 1
export const GENERAL_STORAGE_OPERATION_DSU_RATES = {
  aws: { tier1: 0.2174, tier2: 0.0174 },
  azure: { tier1: 0.3535, tier2: 0.0226 },
  gcp: { tier1: 0.2174, tier2: 0.0174 },
} as const
export const ZEROBUS_DBU_PER_GB = {
  standard: 0.143,
  otel: 0.222,
} as const

export const ALWAYS_ON_WORKLOAD_TYPES = new Set([
  'VECTOR_SEARCH',
  'MODEL_SERVING',
  'LAKEBASE',
  'DATABRICKS_APPS',
  'LAKEFLOW_CONNECT',
])

export function calculateHoursPerMonth(item: Partial<LineItem>): number {
  const workloadType = (item.workload_type || '').toUpperCase()
  if (
    workloadType === 'FMAPI_DATABRICKS'
    || workloadType === 'FMAPI_PROPRIETARY'
  ) {
    return 0
  }
  if (item.runs_per_day && item.avg_runtime_minutes) {
    return (
      item.runs_per_day
      * (item.avg_runtime_minutes / 60)
      * (item.days_per_month || 22)
    )
  }
  if (item.hours_per_month != null) {
    return item.hours_per_month
  }
  return ALWAYS_ON_WORKLOAD_TYPES.has(workloadType) ? 730 : 0
}

export function getGeneralStorageGB(item: Partial<LineItem>): number {
  const quantity = item.general_storage_quantity ?? 0
  return (item.general_storage_unit ?? 'gb') === 'tb'
    ? quantity * GENERAL_STORAGE_GB_PER_TB
    : quantity
}

export function getAISearchStorageDSUPerGB(mode?: string | null): number {
  return mode === 'storage_optimized'
    ? AI_SEARCH_STORAGE_OPTIMIZED_DSU_PER_GB
    : AI_SEARCH_STANDARD_STORAGE_DSU_PER_GB
}

export function calculateGeneralStorageDSU(
  item: Partial<LineItem>,
  cloud: string,
) {
  const normalizedCloud = cloud.toLowerCase() as keyof typeof GENERAL_STORAGE_OPERATION_DSU_RATES
  const rates = GENERAL_STORAGE_OPERATION_DSU_RATES[normalizedCloud]
    ?? GENERAL_STORAGE_OPERATION_DSU_RATES.aws
  const storedDataDSU = getGeneralStorageGB(item)
    * GENERAL_STORAGE_STORED_DATA_DSU_PER_GB
  const tier1OperationsThousands =
    item.general_storage_tier1_operations_thousands ?? 0
  const tier2OperationsThousands =
    item.general_storage_tier2_operations_thousands ?? 0
  const tier1OperationsDSU = tier1OperationsThousands * rates.tier1
  const tier2OperationsDSU = tier2OperationsThousands * rates.tier2
  return {
    storedDataDSU,
    tier1OperationsThousands,
    tier2OperationsThousands,
    tier1DSUPerThousand: rates.tier1,
    tier2DSUPerThousand: rates.tier2,
    tier1OperationsDSU,
    tier2OperationsDSU,
    totalDSU: storedDataDSU + tier1OperationsDSU + tier2OperationsDSU,
  }
}

export function calculateZerobusUsage(item: Partial<LineItem>) {
  const mode = item.zerobus_mode ?? 'standard'
  const monthlyIngestedGB = item.zerobus_monthly_ingested_gb ?? 0
  const dbuPerGB = ZEROBUS_DBU_PER_GB[mode]
  return {
    mode,
    monthlyIngestedGB,
    dbuPerGB,
    monthlyDBUs: monthlyIngestedGB * dbuPerGB,
  }
}

export function isModelServingGPUType(workloadType?: string | null): boolean {
  return !(workloadType || 'cpu').trim().toLowerCase().startsWith('cpu')
}

export function getModelServingBillingCapacityUnits(
  workloadType: string | null | undefined,
  concurrency: number,
): number {
  return isModelServingGPUType(workloadType)
    ? concurrency / MODEL_SERVING_GPU_CONCURRENCY_PER_REPLICA
    : concurrency
}

export function calculateModelServingDBUPerHour(
  dbuRate: number,
  workloadType: string | null | undefined,
  concurrency: number,
): number {
  return dbuRate * getModelServingBillingCapacityUnits(
    workloadType,
    concurrency,
  )
}

export function calculateAISearchRerankerUsage(item: Partial<LineItem>) {
  const enabled = item.ai_search_reranker_enabled ?? false
  const requestsThousands = item.ai_search_reranker_requests_thousands ?? 0
  return {
    enabled,
    requestsThousands,
    monthlyDBUs: enabled
      ? requestsThousands * AI_SEARCH_RERANKER_DBU_PER_THOUSAND_REQUESTS
      : 0,
  }
}

export interface AgentEvaluationUsage {
  labelsEnabled: boolean
  syntheticDataEnabled: boolean
  inputTokensMillions: number
  outputTokensMillions: number
  syntheticQuestions: number
  inputTokenDBUs: number
  outputTokenDBUs: number
  evaluationTokenDBUs: number
  syntheticQuestionDBUs: number
  monthlyDBUs: number
}

export function calculateAgentEvaluationUsage(item: Partial<LineItem>): AgentEvaluationUsage {
  const labelsEnabled = item.agent_evaluation_labels_enabled ?? true
  const syntheticDataEnabled = item.agent_evaluation_synthetic_data_enabled ?? false
  const inputTokensMillions = item.agent_evaluation_input_tokens_millions ?? 1
  const outputTokensMillions = item.agent_evaluation_output_tokens_millions ?? 1
  const syntheticQuestions = item.agent_evaluation_synthetic_questions ?? 0
  const inputTokenDBUs = labelsEnabled
    ? inputTokensMillions * AGENT_EVALUATION_COMPONENT_RATES.inputTokens
    : 0
  const outputTokenDBUs = labelsEnabled
    ? outputTokensMillions * AGENT_EVALUATION_COMPONENT_RATES.outputTokens
    : 0
  const syntheticQuestionDBUs = syntheticDataEnabled
    ? syntheticQuestions * AGENT_EVALUATION_COMPONENT_RATES.syntheticQuestions
    : 0

  return {
    labelsEnabled,
    syntheticDataEnabled,
    inputTokensMillions,
    outputTokensMillions,
    syntheticQuestions,
    inputTokenDBUs,
    outputTokenDBUs,
    evaluationTokenDBUs: inputTokenDBUs + outputTokenDBUs,
    syntheticQuestionDBUs,
    monthlyDBUs: inputTokenDBUs + outputTokenDBUs + syntheticQuestionDBUs,
  }
}

export interface AIGatewayComponentUsage {
  enabled: boolean
  inputMethod: 'requests' | 'payload_gb'
  requestsMillions: number
  payloadKBPerRequest: number
  monthlyPayloadGB: number
  monthlyDBUs: number
}

function calculateAIGatewayComponent(
  enabled: boolean,
  inputMethod: 'requests' | 'payload_gb',
  requestsMillions: number,
  requestKB: number,
  responseKB: number,
  directPayloadGB: number,
  dbuPerGB: number,
): AIGatewayComponentUsage {
  const payloadKBPerRequest = requestKB + responseKB
  const monthlyPayloadGB = !enabled
    ? 0
    : inputMethod === 'payload_gb'
      ? directPayloadGB
      : requestsMillions * payloadKBPerRequest
  return {
    enabled,
    inputMethod,
    requestsMillions,
    payloadKBPerRequest,
    monthlyPayloadGB,
    monthlyDBUs: monthlyPayloadGB * dbuPerGB,
  }
}

export interface AIGatewayUsage {
  inferenceTables: AIGatewayComponentUsage
  usageTracking: AIGatewayComponentUsage
  monthlyDBUs: number
}

export function calculateAIGatewayUsage(item: Partial<LineItem>): AIGatewayUsage {
  const inferenceTables = calculateAIGatewayComponent(
    item.ai_gateway_inference_tables_enabled ?? true,
    item.ai_gateway_inference_tables_input_method ?? 'requests',
    item.ai_gateway_inference_tables_requests_millions ?? 1,
    item.ai_gateway_inference_tables_avg_request_payload_kb ?? 1,
    item.ai_gateway_inference_tables_avg_response_payload_kb ?? 1,
    item.ai_gateway_inference_tables_monthly_payload_gb ?? 2,
    AI_GATEWAY_COMPONENT_RATES.inferenceTables,
  )
  const usageTracking = calculateAIGatewayComponent(
    item.ai_gateway_usage_tracking_enabled ?? true,
    item.ai_gateway_usage_tracking_input_method ?? 'requests',
    item.ai_gateway_usage_tracking_requests_millions ?? 1,
    item.ai_gateway_usage_tracking_avg_request_payload_kb ?? 1,
    item.ai_gateway_usage_tracking_avg_response_payload_kb ?? 1,
    item.ai_gateway_usage_tracking_monthly_payload_gb ?? 2,
    AI_GATEWAY_COMPONENT_RATES.usageTracking,
  )

  return {
    inferenceTables,
    usageTracking,
    monthlyDBUs: inferenceTables.monthlyDBUs + usageTracking.monthlyDBUs,
  }
}

// Fallback DBU rates if fetched data not available ($/DBU)
// These should match the actual Databricks pricing (PREMIUM tier defaults)
// Note: ENTERPRISE tier rates are typically higher (e.g., Jobs Compute $0.20 vs $0.15)
// The pricing bundle lookup will provide tier-specific rates when available
export const DEFAULT_DBU_PRICING: Record<string, Record<string, number>> = {
  aws: {
    'JOBS_COMPUTE': 0.15,  // PREMIUM: $0.15, ENTERPRISE: $0.20 (use bundle for tier-specific)
    'JOBS_COMPUTE_(PHOTON)': 0.15,  // PREMIUM: $0.15, ENTERPRISE: $0.20
    'JOBS_SERVERLESS_COMPUTE': 0.39,  // Serverless has higher $/DBU
    'ALL_PURPOSE_COMPUTE': 0.55,
    'ALL_PURPOSE_COMPUTE_(PHOTON)': 0.55,
    'ALL_PURPOSE_SERVERLESS_COMPUTE': 0.83,  // All-Purpose Serverless
    'DLT_CORE_COMPUTE': 0.20,
    'DLT_CORE_COMPUTE_(PHOTON)': 0.20,
    'DLT_PRO_COMPUTE': 0.25,
    'DLT_PRO_COMPUTE_(PHOTON)': 0.25,
    'DLT_ADVANCED_COMPUTE': 0.36,
    'DLT_ADVANCED_COMPUTE_(PHOTON)': 0.36,
    'DELTA_LIVE_TABLES_SERVERLESS': 0.30,
    'SQL_COMPUTE': 0.22,
    'SQL_PRO_COMPUTE': 0.55,
    'SERVERLESS_SQL_COMPUTE': 0.70,
    'SERVERLESS_REAL_TIME_INFERENCE': 0.07,  // Used for AI Search, Model Serving, FMAPI Databricks
    'SERVERLESS_REAL_TIME_INFERENCE_LAUNCH': 0.07,
    'MODEL_TRAINING': 0.65,
    'OPENAI_MODEL_SERVING': 0.07,
    'ANTHROPIC_MODEL_SERVING': 0.07,
    'GOOGLE_MODEL_SERVING': 0.07,
    'DATABASE_SERVERLESS_COMPUTE': 0.48,  // Lakebase pricing
  }
}

// Fallback DBSQL DBU rates by size
export const DBSQL_DBU_RATES: Record<string, number> = {
  '2X-Small': 4,
  'X-Small': 6,
  'Small': 12,
  'Medium': 24,
  'Large': 40,
  'X-Large': 80,
  '2X-Large': 144,
  '3X-Large': 272,
  '4X-Large': 528,
}

export interface CostBreakdown {
  monthlyDBUs: number
  dbuCost: number
  monthlyDSUs: number
  dsuCost: number
  vmCost: number
  databricksListCost: number
  totalCost: number
  // Optional fields for specific workload types
  unitsUsed?: number  // AI Search units
  dbuPerHour?: number // DBU per hour for display
  dbuPrice?: number   // $/DBU rate for display
  // Storage costs for AI Search and Lakebase
  storageCost?: number
  dsuPrice?: number
  storageDetails?: {
    totalStorageGB: number
    freeStorageGB?: number  // AI Search only
    billableStorageGB: number
    pricePerGB?: number     // AI Search
    dsuPerGB?: number       // Lakebase
    totalDSU?: number       // Lakebase
    pricePerDSU?: number    // Lakebase
  }
}

export interface DBSQLWarehouseConfig {
  driver_count: number
  worker_count: number
  driver_instance_type: string
  worker_instance_type: string
}

export interface CostCalculationContext {
  cloud: string
  region: string
  tier?: string  // Databricks tier (PREMIUM, STANDARD, ENTERPRISE)
  dbuRatesMap: Record<string, number>
  instanceTypes: InstanceType[]
  dbsqlSizes: DBSQLSize[]
  photonMultipliers: PhotonMultiplier[]
  modelServingGPUTypes: ModelServingGPUType[]
  vectorSearchModes: VectorSearchMode[]
  getVMPrice: (cloud: string, region: string, instanceType: string, pricingTier: string, paymentOption: string) => number
  getFMAPIDatabricksRate: (model: string, rateType: string) => {
    dbu_per_1M_tokens?: number
    dbu_per_hour?: number
    regional_uplift_percent?: number
  } | null
  getFMAPIProprietaryRate: (provider: string, model: string, rateType: string, endpointType?: string, contextLength?: string) => { dbu_per_1M_tokens?: number, dbu_per_hour?: number } | null
  getVectorSearchRate: (mode: string) => { dbu_per_hour?: number, input_divisor?: number } | null
  getDBSQLWarehouseConfig?: (warehouseType: string, warehouseSize: string) => DBSQLWarehouseConfig | null
  // Functions for pricing bundle lookups (for consistent calculations)
  getInstanceDBURate?: (instanceType: string) => number | null
  getPhotonMultiplier?: (skuType: string) => number | null
  getDBUPrice?: (productType: string) => number | null
  getExactDBUPrice?: (productType: string) => number | null
}

/**
 * Calculate cost for a workload item locally
 * This is the same logic used in Calculator.tsx for consistency
 */
export function calculateWorkloadCost(
  item: Partial<LineItem>,
  context: CostCalculationContext
): CostBreakdown {
  const {
    cloud, region, tier, dbuRatesMap, instanceTypes, dbsqlSizes, photonMultipliers, modelServingGPUTypes,
    getVMPrice, getFMAPIDatabricksRate, getFMAPIProprietaryRate, getVectorSearchRate,
    getInstanceDBURate, getPhotonMultiplier: getBundlePhotonMultiplier, getDBUPrice,
    getExactDBUPrice
  } = context
  
  // If no region selected, return zero costs
  if (!region) {
    return {
      monthlyDBUs: 0,
      dbuCost: 0,
      monthlyDSUs: 0,
      dsuCost: 0,
      vmCost: 0,
      databricksListCost: 0,
      totalCost: 0,
    }
  }
  
  // Try to use dynamic DBU rates first, fall back to hardcoded
  const pricing = Object.keys(dbuRatesMap).length > 0 ? dbuRatesMap : (DEFAULT_DBU_PRICING[cloud] || DEFAULT_DBU_PRICING.aws)
  const numWorkers = item.num_workers || 0
  
  // ========================================
  // Step 1: Calculate hours per month
  // ========================================
  const hoursPerMonth = calculateHoursPerMonth(item)
  
  // ========================================
  // Step 2: Determine product_type_for_pricing (SKU)
  // ========================================
  let productType = ''
  const dltEdition = (item.dlt_edition || 'CORE').toUpperCase()
  
  switch (item.workload_type) {
    case 'JOBS':
      if (item.serverless_enabled) {
        productType = 'JOBS_SERVERLESS_COMPUTE'
      } else if (item.photon_enabled) {
        productType = 'JOBS_COMPUTE_(PHOTON)'
      } else {
        productType = 'JOBS_COMPUTE'
      }
      break
    
    case 'ALL_PURPOSE':
      if (item.serverless_enabled) {
        productType = 'ALL_PURPOSE_SERVERLESS_COMPUTE'
      } else if (item.photon_enabled) {
        productType = 'ALL_PURPOSE_COMPUTE_(PHOTON)'
      } else {
        productType = 'ALL_PURPOSE_COMPUTE'
      }
      break
    
    case 'DLT':
      if (item.serverless_enabled) {
        // DLT Serverless uses same rate as Jobs Serverless ($0.39)
        productType = 'JOBS_SERVERLESS_COMPUTE'
      } else {
        productType = `DLT_${dltEdition}_COMPUTE`
        if (item.photon_enabled) {
          productType += '_(PHOTON)'
        }
      }
      break
    
    case 'DBSQL':
      const warehouseType = (item.dbsql_warehouse_type || 'SERVERLESS').toUpperCase()
      if (warehouseType === 'SERVERLESS') {
        productType = 'SERVERLESS_SQL_COMPUTE'
      } else if (warehouseType === 'PRO') {
        productType = 'SQL_PRO_COMPUTE'
      } else {
        productType = 'SQL_COMPUTE'
      }
      break
    
    case 'VECTOR_SEARCH':
      // AI Search uses SERVERLESS_REAL_TIME_INFERENCE pricing
      productType = 'SERVERLESS_REAL_TIME_INFERENCE'
      break
    
    case 'MODEL_SERVING':
      productType = 'SERVERLESS_REAL_TIME_INFERENCE'
      break

    case 'AI_RUNTIME':
      productType = 'MODEL_TRAINING'
      break

    case 'GENERAL_STORAGE':
      productType = 'DATABRICKS_STORAGE'
      break

    case 'ZEROBUS':
      productType = 'JOBS_SERVERLESS_COMPUTE'
      break
    
    case 'FMAPI_DATABRICKS':
      // FMAPI uses SERVERLESS_REAL_TIME_INFERENCE pricing
      productType = 'SERVERLESS_REAL_TIME_INFERENCE'
      break
    
    case 'FMAPI_PROPRIETARY':
      // Proprietary models use their provider-specific pricing
      // Note: Provider names must match the bundle keys (ANTHROPIC, OPENAI, GEMINI - not GOOGLE)
      const provider = (item.fmapi_provider || 'openai').toLowerCase()
      const providerMapping: Record<string, string> = {
        'google': 'GEMINI',  // Google uses GEMINI_MODEL_SERVING in the bundle
        'anthropic': 'ANTHROPIC',
        'openai': 'OPENAI'
      }
      productType = `${providerMapping[provider] || provider.toUpperCase()}_MODEL_SERVING`
      break
    
    case 'LAKEBASE':
      productType = 'DATABASE_SERVERLESS_COMPUTE'
      break

    case 'DATABRICKS_APPS':
      productType = 'ALL_PURPOSE_SERVERLESS_COMPUTE'
      break

    case 'AI_PARSE':
    case 'AI_EXTRACT':
    case 'AI_CLASSIFY':
    case 'AI_GATEWAY':
    case 'AGENT_EVALUATION':
    case 'SHUTTERSTOCK_IMAGEAI':
      productType = 'SERVERLESS_REAL_TIME_INFERENCE'
      break

    case 'LAKEFLOW_CONNECT':
      productType = 'DELTA_LIVE_TABLES_SERVERLESS'
      break

    default:
      productType = 'JOBS_COMPUTE'
  }
  
  // Get DBU price for this product type - try pricing bundle function first
  let dbuPrice: number | null = null
  if (
    item.workload_type === 'AI_GATEWAY'
    || item.workload_type === 'AGENT_EVALUATION'
    || item.workload_type === 'AI_RUNTIME'
    || item.workload_type === 'GENERAL_STORAGE'
    || item.workload_type === 'ZEROBUS'
  ) {
    dbuPrice = getExactDBUPrice?.(productType) ?? dbuRatesMap[productType] ?? 0
  } else if (getDBUPrice) {
    const bundlePrice = getDBUPrice(productType)
    if (bundlePrice !== null && bundlePrice > 0) {
      dbuPrice = bundlePrice
    }
  }
  // Only fall back to hardcoded pricing if bundle didn't provide a price
  if (dbuPrice === null) {
    dbuPrice = pricing[productType] || 0.20
  }
  console.log(`[LiveEstimate] productType=${productType}, dbuPrice=${dbuPrice}, serverless=${item.serverless_enabled}, photon=${item.photon_enabled}`)
  
  // ========================================
  // Step 3: Calculate DBU per hour based on workload type
  // ========================================
  let dbuPerHour = 0
  let monthlyDBUs = 0
  let vmCost = 0
  let monthlyDSUs = 0
  let dsuCost = 0
  let dsuPrice = 0
  let unitsUsed: number | undefined = undefined  // For AI Search
  let storageCost: number | undefined = undefined  // For AI Search and Lakebase
  let storageDetails: CostBreakdown['storageDetails'] = undefined
  
  // Use the legacy fallback only for a selected but unknown instance.
  // An empty node selection contributes no hidden DBUs.
  let driverDBURate = item.driver_node_type ? 0.5 : 0
  let workerDBURate = item.worker_node_type ? 0.5 : 0
  
  if (getInstanceDBURate && item.driver_node_type) {
    const bundleRate = getInstanceDBURate(item.driver_node_type)
    if (bundleRate !== null && bundleRate > 0) driverDBURate = bundleRate
  }
  if (item.driver_node_type && driverDBURate === 0.5) {
    const driverInstance = instanceTypes.find(it => it.id === item.driver_node_type || it.name === item.driver_node_type)
    if (driverInstance?.dbu_rate) driverDBURate = driverInstance.dbu_rate
  }
  
  if (getInstanceDBURate && item.worker_node_type) {
    const bundleRate = getInstanceDBURate(item.worker_node_type)
    if (bundleRate !== null && bundleRate > 0) workerDBURate = bundleRate
  }
  if (item.worker_node_type && workerDBURate === 0.5) {
    const workerInstance = instanceTypes.find(it => it.id === item.worker_node_type || it.name === item.worker_node_type)
    if (workerInstance?.dbu_rate) workerDBURate = workerInstance.dbu_rate
  }
  
  // Get photon multiplier - try pricing bundle function first, then fetched photonMultipliers
  // NOTE: For serverless workloads, photon is ALWAYS enabled (built-in)
  const getPhotonMultiplierValue = (): number => {
    // For classic, only apply if photon is explicitly enabled
    if (!item.serverless_enabled && !item.photon_enabled) return 1.0
    
    // Strip _(PHOTON) suffix but keep _COMPUTE suffix for bundle lookup
    // Bundle keys are like: aws:DLT_ADVANCED_COMPUTE:photon, aws:JOBS_COMPUTE:photon
    let skuTypeForLookup = productType.replace('_(PHOTON)', '')
    
    // For SERVERLESS workloads, use the corresponding CLASSIC SKU type for photon lookup
    // e.g., JOBS_SERVERLESS_COMPUTE -> JOBS_COMPUTE (photon multiplier is same as classic)
    if (item.serverless_enabled) {
      if (item.workload_type === 'JOBS') {
        skuTypeForLookup = 'JOBS_COMPUTE'
      } else if (item.workload_type === 'ALL_PURPOSE') {
        skuTypeForLookup = 'ALL_PURPOSE_COMPUTE'
      } else if (item.workload_type === 'DLT') {
        // DLT serverless uses JOBS_SERVERLESS_COMPUTE for pricing, but photon from edition-specific SKU
        skuTypeForLookup = `DLT_${dltEdition}_COMPUTE`
      }
    }
    
    // Try pricing bundle function first
    if (getBundlePhotonMultiplier) {
      const bundleMultiplier = getBundlePhotonMultiplier(skuTypeForLookup)
      if (bundleMultiplier !== null && bundleMultiplier > 1.0) return bundleMultiplier
    }
    
    // Fall back to fetched photonMultipliers
    const multiplierEntry = photonMultipliers.find(pm => 
      pm.sku_type === skuTypeForLookup || 
      pm.sku_type === productType ||
      pm.sku_type?.includes(item.workload_type || '')
    )
    return multiplierEntry?.multiplier || 2.0  // Default to 2.0 (standard photon multiplier)
  }
  const photonMultiplier = getPhotonMultiplierValue()
  
  // Serverless mode multiplier
  // Note: All-Purpose Serverless ONLY supports Performance mode (always 2x)
  // Jobs/DLT Serverless support both Standard (1x) and Performance (2x)
  const serverlessMultiplier = !item.serverless_enabled ? 1 
    : (item.workload_type === 'ALL_PURPOSE') ? 2  // All-Purpose Serverless is always Performance (2x)
    : (item.serverless_mode === 'performance') ? 2 : 1
  
  switch (item.workload_type) {
    case 'ALL_PURPOSE':
    case 'JOBS':
      if (item.serverless_enabled) {
        // Serverless: DBU/Hour = base_dbu_rate × photon_multiplier (always on) × serverless_multiplier
        // Photon is ALWAYS enabled in serverless (built-in)
        dbuPerHour = (driverDBURate + (workerDBURate * numWorkers)) * photonMultiplier * serverlessMultiplier
      } else {
        // Classic: DBU/Hour = (driver_dbu_rate + worker_dbu_rate × num_workers) × photon_multiplier
        dbuPerHour = (driverDBURate + (workerDBURate * numWorkers)) * photonMultiplier
        
        // VM costs for classic compute
        const driverPricingTier = item.driver_pricing_tier || 'on_demand'
        const driverPaymentOption = item.driver_payment_option || 'NA'
        const workerPricingTier = item.worker_pricing_tier || 'spot'
        const workerPaymentOption = item.worker_payment_option || 'NA'
        
        const driverVMCostPerHour = getVMPrice(cloud, region, item.driver_node_type || '', driverPricingTier, driverPaymentOption)
        const workerVMCostPerHour = getVMPrice(cloud, region, item.worker_node_type || '', workerPricingTier, workerPaymentOption)
        
        const totalVMCostPerHour = driverVMCostPerHour + (workerVMCostPerHour * numWorkers)
        vmCost = totalVMCostPerHour * hoursPerMonth
      }
      monthlyDBUs = dbuPerHour * hoursPerMonth
      break
    
    case 'DLT':
      if (item.serverless_enabled) {
        // DLT Serverless: DBU/Hour = base_dbu_rate × photon_multiplier (always on) × serverless_multiplier
        // Photon is ALWAYS enabled in serverless (built-in)
        dbuPerHour = (driverDBURate + (workerDBURate * numWorkers)) * photonMultiplier * serverlessMultiplier
      } else {
        // DLT Classic: DBU/Hour = (driver_dbu + worker_dbu × workers) × photon_multiplier
        dbuPerHour = (driverDBURate + (workerDBURate * numWorkers)) * photonMultiplier
        
        const driverPricingTier = item.driver_pricing_tier || 'on_demand'
        const driverPaymentOption = item.driver_payment_option || 'NA'
        const workerPricingTier = item.worker_pricing_tier || 'spot'
        const workerPaymentOption = item.worker_payment_option || 'NA'
        
        const driverVMCostPerHour = getVMPrice(cloud, region, item.driver_node_type || '', driverPricingTier, driverPaymentOption)
        const workerVMCostPerHour = getVMPrice(cloud, region, item.worker_node_type || '', workerPricingTier, workerPaymentOption)
        
        const totalVMCostPerHour = driverVMCostPerHour + (workerVMCostPerHour * numWorkers)
        vmCost = totalVMCostPerHour * hoursPerMonth
      }
      monthlyDBUs = dbuPerHour * hoursPerMonth
      break
    
    case 'DBSQL':
      const dbsqlSize = dbsqlSizes.find(s => s.id === item.dbsql_warehouse_size || s.name === item.dbsql_warehouse_size)
      const warehouseDBUs = dbsqlSize?.dbu_per_hour || DBSQL_DBU_RATES[item.dbsql_warehouse_size || 'Small'] || 12
      const numClusters = item.dbsql_num_clusters || 1
      
      dbuPerHour = warehouseDBUs * numClusters
      monthlyDBUs = dbuPerHour * hoursPerMonth
      
      const dbsqlWarehouseType = (item.dbsql_warehouse_type || 'SERVERLESS').toUpperCase()
      if (dbsqlWarehouseType !== 'SERVERLESS') {
        // DBSQL has separate driver and worker pricing tier selections
        const dbsqlDriverPricingTier = item.dbsql_driver_pricing_tier || item.driver_pricing_tier || 'on_demand'
        const dbsqlDriverPaymentOption = item.dbsql_driver_payment_option || item.driver_payment_option || 'NA'
        const dbsqlWorkerPricingTier = item.dbsql_worker_pricing_tier || item.worker_pricing_tier || 'spot'
        const dbsqlWorkerPaymentOption = item.dbsql_worker_payment_option || item.worker_payment_option || 'NA'
        
        // Try to get warehouse config for VM instance types
        const warehouseConfig = context.getDBSQLWarehouseConfig?.(dbsqlWarehouseType, item.dbsql_warehouse_size || 'Small')
        
        if (warehouseConfig) {
          // Use warehouse config for instance types
          const dbsqlDriverVMCost = getVMPrice(cloud, region, warehouseConfig.driver_instance_type, dbsqlDriverPricingTier, dbsqlDriverPaymentOption)
          const dbsqlWorkerVMCost = getVMPrice(cloud, region, warehouseConfig.worker_instance_type, dbsqlWorkerPricingTier, dbsqlWorkerPaymentOption)
          
          const dbsqlVMCostPerHour = (
            (warehouseConfig.driver_count * dbsqlDriverVMCost) + 
            (warehouseConfig.worker_count * dbsqlWorkerVMCost)
          ) * numClusters
          vmCost = dbsqlVMCostPerHour * hoursPerMonth
        } else if (item.driver_node_type) {
          // Fallback: use driver/worker node types if specified
          const dbsqlDriverVMCost = getVMPrice(cloud, region, item.driver_node_type, dbsqlDriverPricingTier, dbsqlDriverPaymentOption)
          const dbsqlWorkerVMCost = item.worker_node_type 
            ? getVMPrice(cloud, region, item.worker_node_type, dbsqlWorkerPricingTier, dbsqlWorkerPaymentOption)
            : 0
          const dbsqlNumWorkers = item.num_workers || 0
          
          const dbsqlVMCostPerHour = (dbsqlDriverVMCost + (dbsqlWorkerVMCost * dbsqlNumWorkers)) * numClusters
          vmCost = dbsqlVMCostPerHour * hoursPerMonth
        }
      }
      break
    
    case 'VECTOR_SEARCH':
      // AI Search: Units = CEILING(vector_capacity / divisor)
      // Standard: 2M vectors per unit, 4.00 DBU/hour per unit
      // Storage Optimized: 64M vectors per unit, 18.29 DBU/hour per unit
      const vectorMode = item.vector_search_mode || 'standard'
      const vectorCapacity = item.vector_capacity_millions || 1
      
      // Get rate data from context or use defaults
      // input_divisor is in total vectors (e.g., 2000000 = 2M)
      const vectorRateData = getVectorSearchRate(vectorMode)
      const vectorDivisor = vectorRateData?.input_divisor || (vectorMode === 'storage_optimized' ? 64000000 : 2000000)
      const vectorModeDBURate = vectorRateData?.dbu_per_hour || (vectorMode === 'storage_optimized' ? 18.29 : 4.0)
      
      // Convert vector capacity from millions to total vectors
      const vectorsTotal = vectorCapacity * 1000000
      const vectorUnitsUsed = Math.ceil(vectorsTotal / vectorDivisor)
      unitsUsed = vectorUnitsUsed  // Store for return
      
      // DBU/Hour = units_used × mode_dbu_rate
      dbuPerHour = vectorUnitsUsed * vectorModeDBURate
      monthlyDBUs = (
        dbuPerHour * hoursPerMonth
        + calculateAISearchRerankerUsage(item).monthlyDBUs
      )
      
      // Storage calculation for AI Search
      // The first 30 GB of storage is included
      // Billable Storage = MAX(0, storage_gb - free_storage_gb)
      // Storage cost = billable GB × 10 DSU/GB × exact regional $/DSU.
      const vectorStorageGB = item.vector_search_storage_gb || 0
      const vectorFreeStorageGB = vectorUnitsUsed > 0
        ? AI_SEARCH_INCLUDED_STORAGE_GB
        : 0
      const vectorBillableStorageGB = Math.max(0, vectorStorageGB - vectorFreeStorageGB)
      dsuPrice = getExactDBUPrice?.('DATABRICKS_STORAGE')
        ?? dbuRatesMap.DATABRICKS_STORAGE
        ?? 0
      const vectorStorageDSUPerGB = getAISearchStorageDSUPerGB(
        item.vector_search_mode,
      )
      monthlyDSUs = vectorBillableStorageGB * vectorStorageDSUPerGB
      const vectorStorageCost = monthlyDSUs * dsuPrice

      if (vectorStorageGB > 0) {
        dsuCost = vectorStorageCost
        storageCost = vectorStorageCost
        storageDetails = {
          totalStorageGB: vectorStorageGB,
          freeStorageGB: vectorFreeStorageGB,
          billableStorageGB: vectorBillableStorageGB,
          dsuPerGB: vectorStorageDSUPerGB,
          totalDSU: monthlyDSUs,
          pricePerDSU: dsuPrice,
        }
      }
      break
    
    case 'MODEL_SERVING':
      const gpuType = item.model_serving_gpu_type || 'cpu'
      const gpuTypeData = modelServingGPUTypes.find(g => g.id === gpuType || g.name === gpuType)
      const gpuDBURate = gpuTypeData?.dbu_per_hour || 2
      const msScaleOut = item.model_serving_scale_out || 'small'
      const msScaleOutPresets: Record<string, number> = { small: 4, medium: 12, large: 40 }
      const msConcurrency = msScaleOut === 'custom'
        ? (item.model_serving_concurrency || 4)
        : (msScaleOutPresets[msScaleOut] || 4)

      dbuPerHour = calculateModelServingDBUPerHour(
        gpuDBURate,
        gpuType,
        msConcurrency,
      )
      monthlyDBUs = dbuPerHour * hoursPerMonth
      break
    
    case 'LAKEBASE':
      const lakebaseNodes = item.lakebase_ha_nodes || 1
      // DBU multiplier per CU-hour varies by cloud/tier
      // Azure Premium = AWS/GCP Enterprise per pricing page footnote
      const lakebaseDBURates: Record<string, Record<string, number>> = {
        'aws': { 'PREMIUM': 0.230, 'ENTERPRISE': 0.213 },
        'azure': { 'PREMIUM': 0.213, 'ENTERPRISE': 0.213 },
      }
      const lakebaseCloudRates = lakebaseDBURates[cloud] || lakebaseDBURates['aws']
      const lakebaseDBUPerCU = lakebaseCloudRates[tier?.toUpperCase() || 'PREMIUM'] || 0.213

      const lakebaseAutoscaleConfig = resolveLakebaseAutoscaleConfig(item)
      const lakebaseComputeUsage = calculateLakebaseComputeUsage(
        lakebaseAutoscaleConfig,
        lakebaseDBUPerCU,
        lakebaseNodes,
      )
      dbuPerHour = lakebaseComputeUsage.equivalentDbuPerHour
      monthlyDBUs = lakebaseComputeUsage.totalBillableDbu
      
      // Storage calculation for Lakebase
      // Total DSU = storage_gb × 15 (each GB consumes 15 DSU)
      // Storage Cost = Total DSU × exact regional price_per_dsu
      // Max storage: 8192 GB (8 TB)
      const lakebaseStorageGB = Math.min(item.lakebase_storage_gb || 0, 8192)
      const lakebaseDSUPerGB = 15
      const lakebaseTotalDSU = lakebaseStorageGB * lakebaseDSUPerGB
      dsuPrice = getExactDBUPrice?.('DATABRICKS_STORAGE')
        ?? dbuRatesMap.DATABRICKS_STORAGE
        ?? 0
      const lakebaseStorageCost = lakebaseTotalDSU * dsuPrice
      
      // PITR: 8.7x DSU multiplier
      const pitrGB = item.lakebase_pitr_gb || 0
      const pitrDSUPerGB = 8.7
      const pitrDSU = pitrGB * pitrDSUPerGB
      const pitrCost = pitrDSU * dsuPrice

      // Snapshots: 3.91x DSU multiplier
      const snapshotGB = item.lakebase_snapshot_gb || 0
      const snapshotDSUPerGB = 3.91
      const snapshotDSU = snapshotGB * snapshotDSUPerGB
      const snapshotCost = snapshotDSU * dsuPrice

      if (lakebaseStorageGB > 0 || pitrGB > 0 || snapshotGB > 0) {
        monthlyDSUs = lakebaseTotalDSU + pitrDSU + snapshotDSU
        dsuCost = lakebaseStorageCost + pitrCost + snapshotCost
        storageCost = lakebaseStorageCost + pitrCost + snapshotCost
        storageDetails = {
          totalStorageGB: lakebaseStorageGB,
          billableStorageGB: lakebaseStorageGB,
          dsuPerGB: lakebaseDSUPerGB,
          totalDSU: monthlyDSUs,
          pricePerDSU: dsuPrice
        }
      }
      break
    
    case 'FMAPI_DATABRICKS':
      const fmapiDbxQuantity = item.fmapi_quantity || 0
      const fmapiDbxRateType = item.fmapi_rate_type || 'input_token'
      const fmapiDbxIsProvisioned = fmapiDbxRateType.startsWith('provisioned_')
      
      const dbxRateData = item.fmapi_model 
        ? getFMAPIDatabricksRate(item.fmapi_model, fmapiDbxRateType) 
        : null
      const useRegionalProcessing = item.fmapi_endpoint_type === 'regional'
      const regionalMultiplier = useRegionalProcessing
        ? (
            dbxRateData?.regional_uplift_percent
              ? 1 + dbxRateData.regional_uplift_percent / 100
              : 0
          )
        : 1
      
      if (fmapiDbxIsProvisioned) {
        const provisionedDbxDbuPerHour = dbxRateData?.dbu_per_hour || 0
        monthlyDBUs = (
          fmapiDbxQuantity
          * provisionedDbxDbuPerHour
          * regionalMultiplier
        )
      } else {
        const tokenDbxRate = dbxRateData?.dbu_per_1M_tokens || 0
        monthlyDBUs = fmapiDbxQuantity * tokenDbxRate * regionalMultiplier
      }
      break
    
    case 'FMAPI_PROPRIETARY':
      const fmapiPropQuantity = item.fmapi_quantity || 0
      const fmapiPropRateType = item.fmapi_rate_type || 'input_token'
      const fmapiPropIsProvisioned = fmapiPropRateType === 'batch_inference'
      const fmapiEndpointType = item.fmapi_endpoint_type || 'global'
      const fmapiContextLength = item.fmapi_context_length || 'long'
      
      const propRateData = (item.fmapi_provider && item.fmapi_model)
        ? getFMAPIProprietaryRate(item.fmapi_provider, item.fmapi_model, fmapiPropRateType, fmapiEndpointType, fmapiContextLength)
        : null
      
      if (fmapiPropIsProvisioned) {
        const provisionedPropDbuPerHour = propRateData?.dbu_per_hour || 0
        monthlyDBUs = fmapiPropQuantity * provisionedPropDbuPerHour
      } else {
        const tokenPropRate = propRateData?.dbu_per_1M_tokens || 0
        monthlyDBUs = fmapiPropQuantity * tokenPropRate
      }
      break
    
    case 'DATABRICKS_APPS':
      const appsSize = (item.databricks_apps_size || 'medium').toLowerCase()
      const appsDbuRates: Record<string, number> = { medium: 0.5, large: 1.0 }
      dbuPerHour = appsDbuRates[appsSize] || 0.5
      monthlyDBUs = dbuPerHour * hoursPerMonth
      break

    case 'AI_RUNTIME': {
      const usage = calculateAIRuntimeUsage(
        cloud,
        item.ai_runtime_accelerator_type,
        hoursPerMonth,
      )
      dbuPerHour = usage.dbuPerNodeHour
      monthlyDBUs = usage.monthlyDBUs
      break
    }

    case 'GENERAL_STORAGE': {
      const storageGB = getGeneralStorageGB(item)
      const usage = calculateGeneralStorageDSU(item, cloud)
      monthlyDSUs = usage.totalDSU
      dsuPrice = dbuPrice
      dsuCost = monthlyDSUs * dsuPrice
      storageCost = dsuCost
      storageDetails = {
        totalStorageGB: storageGB,
        billableStorageGB: storageGB,
        dsuPerGB: GENERAL_STORAGE_STORED_DATA_DSU_PER_GB,
        totalDSU: monthlyDSUs,
        pricePerDSU: dsuPrice,
      }
      break
    }

    case 'AI_PARSE': {
      const complexityRates: Record<string, number> = {
        low_text: 12.5, low_images: 22.5, medium: 62.5, high: 87.5
      }
      const aiComplexity = (item.ai_parse_complexity || 'medium').toLowerCase()
      const pagesK = item.ai_parse_pages_thousands || 0
      monthlyDBUs = pagesK * (complexityRates[aiComplexity] || 62.5)
      break
    }

    case 'AI_EXTRACT': {
      const extractRates: Record<string, number> = {
        short_text: 45,
        invoice: 45,
        complex_reasoning: 562.5,
        deep_nesting: 537.5,
      }
      const docType = (item.ai_extract_document_type || 'invoice').toLowerCase()
      const rate = docType === 'custom'
        ? (item.ai_extract_dbus_per_thousand || 0)
        : (extractRates[docType] || 45)
      monthlyDBUs = ((item.ai_extract_num_inputs || 0) / 1000) * rate
      break
    }

    case 'AI_CLASSIFY': {
      const classifyRates: Record<string, number> = {
        short_text: 4.5,
        rental_contract: 50,
      }
      const docType = (item.ai_classify_document_type || 'short_text').toLowerCase()
      const rate = docType === 'custom'
        ? (item.ai_classify_dbus_per_thousand || 0)
        : (classifyRates[docType] || 4.5)
      monthlyDBUs = ((item.ai_classify_num_docs || 0) / 1000) * rate
      break
    }

    case 'AI_GATEWAY': {
      monthlyDBUs = calculateAIGatewayUsage(item).monthlyDBUs
      break
    }

    case 'AGENT_EVALUATION': {
      monthlyDBUs = calculateAgentEvaluationUsage(item).monthlyDBUs
      break
    }

    case 'ZEROBUS': {
      monthlyDBUs = calculateZerobusUsage(item).monthlyDBUs
      break
    }

    case 'SHUTTERSTOCK_IMAGEAI': {
      const ssImages = item.shutterstock_images || 0
      monthlyDBUs = ssImages * 0.857
      break
    }

    default:
      monthlyDBUs = 0
  }
  
  // ========================================
  // Step 4: Calculate final costs with NaN guards
  // ========================================
  const rawDbuCost = monthlyDBUs * dbuPrice
  const safeDSUCost = !isNaN(dsuCost) ? dsuCost : 0
  const safeStorageCost = storageCost !== undefined && !isNaN(storageCost) ? storageCost : 0
  const rawTotalCost = rawDbuCost + vmCost + safeDSUCost
  
  // NaN guards - ensure we never return NaN values
  const safeDbuCost = isNaN(rawDbuCost) ? 0 : rawDbuCost
  const safeVmCost = isNaN(vmCost) ? 0 : vmCost
  const safeTotalCost = isNaN(rawTotalCost) ? safeDbuCost : rawTotalCost
  const safeMonthlyDBUs = isNaN(monthlyDBUs) ? 0 : monthlyDBUs
  const safeDbuPerHour = isNaN(dbuPerHour) ? 0 : dbuPerHour
  const safeDbuPrice = isNaN(dbuPrice) ? 0.15 : dbuPrice
  
  return { 
    monthlyDBUs: safeMonthlyDBUs, 
    dbuCost: safeDbuCost, 
    monthlyDSUs: isNaN(monthlyDSUs) ? 0 : monthlyDSUs,
    dsuCost: safeDSUCost,
    vmCost: safeVmCost, 
    databricksListCost: safeDbuCost + safeDSUCost,
    totalCost: safeTotalCost,
    unitsUsed,  // For AI Search
    dbuPerHour: safeDbuPerHour, // For display
    dbuPrice: safeDbuPrice,    // $/DBU rate for display
    dsuPrice,
    storageCost: safeStorageCost > 0 ? safeStorageCost : undefined,
    storageDetails
  }
}

