import { useState, useMemo, useCallback, useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import { 
  BeakerIcon, 
  PlayIcon, 
  CheckCircleIcon, 
  XCircleIcon,
  ArrowPathIcon,
  DocumentArrowDownIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  ExclamationTriangleIcon,
  CogIcon,
  AdjustmentsHorizontalIcon,
  PauseIcon,
  StopIcon,
  BoltIcon
} from '@heroicons/react/24/outline'
import { useStore } from '../store/useStore'
import { calculateWorkloadCost, type CostBreakdown, type CostCalculationContext } from '../utils/costCalculation'
import { 
  getInstanceDBURate as getBundleInstanceDBURate,
  getPhotonMultiplier as getBundlePhotonMultiplier,
  getDBUPrice as getBundleDBUPrice,
  getDBSQLWarehouseConfig,
  getAvailableWorkloadTypesForRegion,
  type PricingBundle
} from '../utils/pricingBundle'
import type { LineItem } from '../types'

// ===== TEST CONFIGURATION =====

// Default fallback environments (used when pricing bundle not loaded)
const DEFAULT_ENVIRONMENTS = {
  aws: {
    regions: ['us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1'],
    tiers: ['PREMIUM', 'ENTERPRISE'],
    vmTypes: ['c5.xlarge', 'c5.2xlarge', 'm5.xlarge', 'm5.2xlarge', 'r5.xlarge', 'i3.xlarge']
  },
  azure: {
    regions: ['eastus', 'westus2', 'westeurope', 'southeastasia'],
    tiers: ['PREMIUM'],
    vmTypes: ['Standard_D4s_v3', 'Standard_D8s_v3', 'Standard_E4s_v3', 'Standard_F4s_v2']
  },
  gcp: {
    regions: ['us-central1', 'us-east1', 'europe-west1', 'asia-southeast1'],
    tiers: ['PREMIUM', 'ENTERPRISE'],
    vmTypes: ['n2-standard-4', 'n2-standard-8', 'n2-highmem-4', 'c2-standard-4']
  }
}

// ===== HELPER: Get valid VM types from pricing bundle =====
// NOTE: vmCosts removed from bundle to save ~50 MB. VM types now extracted from instanceDBURates.
function getValidVMTypesForCloudRegion(
  bundle: PricingBundle | null,
  cloud: string,
  _region: string // Region not used since instanceDBURates are cloud-level
): string[] {
  if (!bundle?.isLoaded || !bundle.instanceDBURates) {
    // Fallback to defaults
    return DEFAULT_ENVIRONMENTS[cloud.toLowerCase() as keyof typeof DEFAULT_ENVIRONMENTS]?.vmTypes || []
  }
  
  // Extract VM types from instanceDBURates (format: cloud -> instance_type -> rate)
  const cloudKey = cloud.toLowerCase()
  const cloudRates = bundle.instanceDBURates[cloudKey]
  
  if (!cloudRates || Object.keys(cloudRates).length === 0) {
    return DEFAULT_ENVIRONMENTS[cloud.toLowerCase() as keyof typeof DEFAULT_ENVIRONMENTS]?.vmTypes || []
  }
  
  return Object.keys(cloudRates).sort()
}

// Get available regions for a cloud
// NOTE: vmCosts removed from bundle. Regions are now fetched via API and cached in regionsMap.
function getAvailableRegions(_bundle: PricingBundle | null, cloud: string): string[] {
  // Use DEFAULT_ENVIRONMENTS which has common regions for each cloud
  return DEFAULT_ENVIRONMENTS[cloud.toLowerCase() as keyof typeof DEFAULT_ENVIRONMENTS]?.regions || []
}

// Get tiers for a cloud
function getTiersForCloud(cloud: string): string[] {
  const cloudLower = cloud.toLowerCase()
  if (cloudLower === 'azure') {
    return ['PREMIUM']
  }
  return ['PREMIUM', 'ENTERPRISE']
}

// FMAPI Databricks models (validated against pricing bundle)
// LLMs support both input_token and output_token
// Embedding models only support input_token
const FMAPI_DATABRICKS_LLM_MODELS = [
  'llama-3-3-70b', 'llama-3-1-8b', 'llama-4-maverick',
  'gpt-oss-120b', 'gpt-oss-20b', 'gemma-3-12b'
]
const FMAPI_DATABRICKS_EMBEDDING_MODELS = [
  'bge-large', 'gte'
]

// FMAPI Proprietary configurations (validated against pricing bundle)
// Note: context lengths vary by model - use only valid combinations
const FMAPI_PROPRIETARY_CONFIGS = [
  { provider: 'openai', model: 'gpt-5', contexts: ['all'] },
  { provider: 'openai', model: 'gpt-5-mini', contexts: ['all'] },
  { provider: 'anthropic', model: 'claude-sonnet-4', contexts: ['short', 'long'] },
  { provider: 'anthropic', model: 'claude-sonnet-4-5', contexts: ['short', 'long'] },
  { provider: 'anthropic', model: 'claude-haiku-4-5', contexts: ['all'] },
  { provider: 'anthropic', model: 'claude-opus-4', contexts: ['all'] },
  { provider: 'google', model: 'gemini-2-5-flash', contexts: ['short', 'long'] },
  { provider: 'google', model: 'gemini-2-5-pro', contexts: ['short', 'long'] }
]

// DBSQL warehouse sizes
const DBSQL_SIZES = ['2X-Small', 'X-Small', 'Small', 'Medium', 'Large', 'X-Large', '2X-Large', '3X-Large', '4X-Large']

// Model serving GPU types by cloud (different clouds support different GPUs)
const GPU_TYPES_BY_CLOUD: Record<string, string[]> = {
  aws: ['cpu', 'gpu_small_t4', 'gpu_medium_a10g_1x', 'gpu_medium_a10g_4x'],
  azure: ['cpu', 'gpu_small_t4', 'gpu_xlarge_a100_80gb_1x'],
  gcp: ['cpu', 'gpu_medium_g2_standard_8']
}
// Fallback for backward compatibility
const GPU_TYPES = ['cpu', 'gpu_small_t4']

// Vector search modes
const VECTOR_MODES = ['standard', 'storage_optimized']

// Manual test environment configuration interface
interface ManualTestEnvironment {
  enabled: boolean
  cloud: string
  region: string
  tier: string
}

// ===== INTERFACES =====

interface TestCase {
  id: string
  name: string
  category: string
  workloadType: string
  config: Partial<LineItem>
  environment: {
    cloud: string
    region: string
    tier: string
  }
}

interface TestResult {
  testCase: TestCase
  localResult: CostBreakdown
  apiResult: CostBreakdown | null
  apiError?: string
  apiRequestBody?: Record<string, unknown>  // For debugging
  apiRawResponse?: Record<string, unknown>  // Raw API response for debugging
  localTimeMs: number
  apiTimeMs: number
  matches: boolean
  totalCostDiffPercent: number  // Specifically for totalCost comparison
  discrepancies: {
    field: string
    local: number
    api: number
    diff: number
    diffPercent: number
  }[]
}

interface TestConfig {
  clouds: string[]
  regionsPerCloud: number
  tiersPerCloud: number
  vmSamplesPerCloud: number
  includeJobs: boolean
  includeAllPurpose: boolean
  includeDLT: boolean
  includeDBSQL: boolean
  includeVectorSearch: boolean
  includeModelServing: boolean
  includeFMAPIDB: boolean
  includeFMAPIProp: boolean
  includeLakebase: boolean
  // Manual environment override (tests only this environment when enabled)
  manualEnvironment: ManualTestEnvironment
}

// ===== HELPER FUNCTIONS =====

// Random sample from array
function sampleArray<T>(arr: T[], count: number): T[] {
  const shuffled = [...arr].sort(() => Math.random() - 0.5)
  return shuffled.slice(0, Math.min(count, arr.length))
}

// Helper to generate tests for a single environment
function generateTestsForEnvironment(
  env: { cloud: string; region: string; tier: string },
  vmTypes: string[],
  config: TestConfig,
  startIdCounter: number,
  cloud: string,
  bundle: PricingBundle | null
): TestCase[] {
  const testCases: TestCase[] = []
  let idCounter = startIdCounter
  
  // Get available workload types for this region from pricing bundle
  // This filters out workloads not available in the region (e.g., no Vector Search in ap-southeast-3)
  const availableWorkloads = bundle?.isLoaded 
    ? getAvailableWorkloadTypesForRegion(bundle, env.cloud, env.region, env.tier)
    : null
  
  // Helper to check if a workload type is available in this region
  const isAvailable = (workloadType: string) => {
    if (!availableWorkloads) return true // No data = assume available (fallback)
    return availableWorkloads.includes(workloadType)
  }
  
  // Jobs tests
  if (config.includeJobs && isAvailable('JOBS')) {
    for (const vm of vmTypes.slice(0, 2)) {
      testCases.push({
        id: `${++idCounter}`,
        name: `Jobs Classic - ${vm}`,
        category: 'Jobs',
        workloadType: 'JOBS',
        environment: env,
        config: {
          serverless_enabled: false,
          photon_enabled: false,
          driver_node_type: vm,
          worker_node_type: vm,
          num_workers: 2,
          driver_pricing_tier: 'on_demand',
          worker_pricing_tier: 'spot',
          runs_per_day: 1,
          avg_runtime_minutes: 30,
          days_per_month: 22
        }
      })
      
      testCases.push({
        id: `${++idCounter}`,
        name: `Jobs Classic Photon - ${vm}`,
        category: 'Jobs',
        workloadType: 'JOBS',
        environment: env,
        config: {
          serverless_enabled: false,
          photon_enabled: true,
          driver_node_type: vm,
          worker_node_type: vm,
          num_workers: 4,
          driver_pricing_tier: 'on_demand',
          worker_pricing_tier: 'spot',
          runs_per_day: 2,
          avg_runtime_minutes: 45,
          days_per_month: 22
        }
      })
    }
    
    for (const mode of ['standard', 'performance']) {
      testCases.push({
        id: `${++idCounter}`,
        name: `Jobs Serverless ${mode}`,
        category: 'Jobs',
        workloadType: 'JOBS',
        environment: env,
        config: {
          serverless_enabled: true,
          serverless_mode: mode,
          driver_node_type: vmTypes[0] || 'c5.xlarge',
          worker_node_type: vmTypes[0] || 'c5.xlarge',
          num_workers: 2,
          runs_per_day: 3,
          avg_runtime_minutes: 20,
          days_per_month: 22
        }
      })
    }
  }
  
  // All Purpose tests
  if (config.includeAllPurpose && isAvailable('ALL_PURPOSE')) {
    for (const vm of vmTypes.slice(0, 2)) {
      testCases.push({
        id: `${++idCounter}`,
        name: `All Purpose Classic - ${vm}`,
        category: 'All Purpose',
        workloadType: 'ALL_PURPOSE',
        environment: env,
        config: {
          serverless_enabled: false,
          photon_enabled: false,
          driver_node_type: vm,
          worker_node_type: vm,
          num_workers: 2,
          driver_pricing_tier: 'on_demand',
          worker_pricing_tier: 'on_demand',
          hours_per_month: 160
        }
      })
    }
    
    testCases.push({
      id: `${++idCounter}`,
      name: 'All Purpose Serverless',
      category: 'All Purpose',
      workloadType: 'ALL_PURPOSE',
      environment: env,
      config: {
        serverless_enabled: true,
        serverless_mode: 'performance',
        driver_node_type: vmTypes[0] || 'c5.xlarge',
        worker_node_type: vmTypes[0] || 'c5.xlarge',
        num_workers: 2,
        hours_per_month: 100
      }
    })
  }
  
  // DLT tests
  if (config.includeDLT && isAvailable('DLT')) {
    for (const edition of ['CORE', 'PRO', 'ADVANCED']) {
      testCases.push({
        id: `${++idCounter}`,
        name: `DLT Classic ${edition}`,
        category: 'DLT',
        workloadType: 'DLT',
        environment: env,
        config: {
          serverless_enabled: false,
          photon_enabled: edition !== 'CORE',
          dlt_edition: edition,
          driver_node_type: vmTypes[0] || 'c5.xlarge',
          worker_node_type: vmTypes[0] || 'c5.xlarge',
          num_workers: 2,
          driver_pricing_tier: 'on_demand',
          worker_pricing_tier: 'spot',
          runs_per_day: 4,
          avg_runtime_minutes: 30,
          days_per_month: 30
        }
      })
    }
    
    testCases.push({
      id: `${++idCounter}`,
      name: 'DLT Serverless',
      category: 'DLT',
      workloadType: 'DLT',
      environment: env,
      config: {
        serverless_enabled: true,
        serverless_mode: 'standard',
        driver_node_type: vmTypes[0] || 'c5.xlarge',
        worker_node_type: vmTypes[0] || 'c5.xlarge',
        num_workers: 2,
        runs_per_day: 6,
        avg_runtime_minutes: 20,
        days_per_month: 30
      }
    })
  }
  
  // DBSQL tests
  if (config.includeDBSQL && isAvailable('DBSQL')) {
    for (const size of sampleArray(DBSQL_SIZES, 3)) {
      testCases.push({
        id: `${++idCounter}`,
        name: `DBSQL Serverless ${size}`,
        category: 'DBSQL',
        workloadType: 'DBSQL',
        environment: env,
        config: {
          dbsql_warehouse_type: 'SERVERLESS',
          dbsql_warehouse_size: size,
          dbsql_num_clusters: 1,
          hours_per_month: 160
        }
      })
    }
    
    for (const size of sampleArray(DBSQL_SIZES, 2)) {
      testCases.push({
        id: `${++idCounter}`,
        name: `DBSQL Pro ${size}`,
        category: 'DBSQL',
        workloadType: 'DBSQL',
        environment: env,
        config: {
          dbsql_warehouse_type: 'PRO',
          dbsql_warehouse_size: size,
          dbsql_num_clusters: 1,
          dbsql_driver_pricing_tier: 'on_demand',
          dbsql_worker_pricing_tier: 'on_demand',
          hours_per_month: 100
        }
      })
    }
    
    testCases.push({
      id: `${++idCounter}`,
      name: 'DBSQL Classic Medium',
      category: 'DBSQL',
      workloadType: 'DBSQL',
      environment: env,
      config: {
        dbsql_warehouse_type: 'CLASSIC',
        dbsql_warehouse_size: 'Medium',
        dbsql_num_clusters: 1,
        dbsql_driver_pricing_tier: 'on_demand',
        dbsql_worker_pricing_tier: 'on_demand',
        hours_per_month: 80
      }
    })
  }
  
  // Vector Search tests
  if (config.includeVectorSearch && isAvailable('VECTOR_SEARCH')) {
    for (const mode of VECTOR_MODES) {
      testCases.push({
        id: `${++idCounter}`,
        name: `Vector Search ${mode}`,
        category: 'Vector Search',
        workloadType: 'VECTOR_SEARCH',
        environment: env,
        config: {
          vector_search_mode: mode,
          vector_capacity_millions: 5,
          hours_per_month: 730
        }
      })
    }
  }
  
  // Model Serving tests
  if (config.includeModelServing && isAvailable('MODEL_SERVING')) {
    const cloudGPUs = GPU_TYPES_BY_CLOUD[cloud.toLowerCase()] || GPU_TYPES
    for (const gpu of cloudGPUs) {
      testCases.push({
        id: `${++idCounter}`,
        name: `Model Serving ${gpu}`,
        category: 'Model Serving',
        workloadType: 'MODEL_SERVING',
        environment: env,
        config: {
          model_serving_gpu_type: gpu,
          hours_per_month: 200
        }
      })
    }
  }
  
  // FMAPI Databricks tests
  if (config.includeFMAPIDB && isAvailable('FMAPI_DATABRICKS')) {
    // LLM models - support both input and output tokens
    for (const model of sampleArray(FMAPI_DATABRICKS_LLM_MODELS, 3)) {
      for (const rateType of ['input_token', 'output_token']) {
        testCases.push({
          id: `${++idCounter}`,
          name: `FMAPI DB ${model} ${rateType}`,
          category: 'FMAPI Databricks',
          workloadType: 'FMAPI_DATABRICKS',
          environment: env,
          config: {
            fmapi_model: model,
            fmapi_rate_type: rateType,
            fmapi_quantity: 10
          }
        })
      }
    }
    // Embedding models - only support input tokens
    for (const model of sampleArray(FMAPI_DATABRICKS_EMBEDDING_MODELS, 1)) {
      testCases.push({
        id: `${++idCounter}`,
        name: `FMAPI DB ${model} input_token`,
        category: 'FMAPI Databricks',
        workloadType: 'FMAPI_DATABRICKS',
        environment: env,
        config: {
          fmapi_model: model,
          fmapi_rate_type: 'input_token',
          fmapi_quantity: 10
        }
      })
    }
  }
  
  // FMAPI Proprietary tests
  if (config.includeFMAPIProp && isAvailable('FMAPI_PROPRIETARY')) {
    for (const propConfig of sampleArray(FMAPI_PROPRIETARY_CONFIGS, 4)) {
      for (const context of propConfig.contexts.slice(0, 2)) {
        for (const rateType of ['input_token', 'output_token']) {
          testCases.push({
            id: `${++idCounter}`,
            name: `FMAPI ${propConfig.provider} ${propConfig.model} ${context} ${rateType}`,
            category: 'FMAPI Proprietary',
            workloadType: 'FMAPI_PROPRIETARY',
            environment: env,
            config: {
              fmapi_provider: propConfig.provider,
              fmapi_model: propConfig.model,
              fmapi_endpoint_type: 'global',
              fmapi_context_length: context,
              fmapi_rate_type: rateType,
              fmapi_quantity: 10
            }
          })
        }
      }
    }
  }
  
  // Lakebase tests
  if (config.includeLakebase && isAvailable('LAKEBASE')) {
    for (const cuSize of [1, 2, 4]) {
      testCases.push({
        id: `${++idCounter}`,
        name: `Lakebase CU${cuSize}`,
        category: 'Lakebase',
        workloadType: 'LAKEBASE',
        environment: env,
        config: {
          lakebase_cu: cuSize,
          lakebase_ha_nodes: 1,
          hours_per_month: 730
        }
      })
    }
  }
  
  return testCases
}

// Generate all test cases based on config and pricing bundle
function generateTestCases(config: TestConfig, bundle: PricingBundle | null): TestCase[] {
  const testCases: TestCase[] = []
  let idCounter = 0
  
  // If manual environment is enabled, use only that environment
  if (config.manualEnvironment.enabled) {
    const { cloud, region, tier } = config.manualEnvironment
    const vmTypes = getValidVMTypesForCloudRegion(bundle, cloud, region)
    const sampledVMs = vmTypes.length > 0 ? sampleArray(vmTypes, config.vmSamplesPerCloud) : ['c5.xlarge']
    
    // Generate tests for this single environment
    return generateTestsForEnvironment(
      { cloud, region, tier }, 
      sampledVMs, 
      config, 
      idCounter,
      cloud,
      bundle
    )
  }
  
  for (const cloud of config.clouds) {
    // Get valid regions from pricing bundle, or use defaults
    const availableRegions = getAvailableRegions(bundle, cloud)
    const regions = sampleArray(availableRegions.length > 0 ? availableRegions : DEFAULT_ENVIRONMENTS[cloud as keyof typeof DEFAULT_ENVIRONMENTS]?.regions || [], config.regionsPerCloud)
    const tiers = sampleArray(getTiersForCloud(cloud), config.tiersPerCloud)
    
    for (const region of regions) {
      // Get valid VM types from pricing bundle for this specific cloud/region
      const validVMTypes = getValidVMTypesForCloudRegion(bundle, cloud, region)
      const vmTypes = validVMTypes.length > 0 
        ? sampleArray(validVMTypes, config.vmSamplesPerCloud)
        : DEFAULT_ENVIRONMENTS[cloud as keyof typeof DEFAULT_ENVIRONMENTS]?.vmTypes?.slice(0, config.vmSamplesPerCloud) || ['c5.xlarge']
      
      for (const tier of tiers) {
        // Use the shared function to generate tests for this environment
        // This ensures regional availability is respected
        const envTests = generateTestsForEnvironment(
          { cloud, region, tier },
          vmTypes,
          config,
          idCounter,
          cloud,
          bundle
        )
        testCases.push(...envTests)
        idCounter += envTests.length
      }
    }
  }
  
  return testCases
}

// API endpoint mapping
function getAPIEndpoint(workloadType: string, config: Partial<LineItem>): string {
  switch (workloadType) {
    case 'JOBS':
      return config.serverless_enabled 
        ? '/api/v1/calculate/jobs-serverless'
        : '/api/v1/calculate/jobs-classic'
    case 'ALL_PURPOSE':
      return config.serverless_enabled
        ? '/api/v1/calculate/all-purpose-serverless'
        : '/api/v1/calculate/all-purpose-classic'
    case 'DLT':
      return config.serverless_enabled
        ? '/api/v1/calculate/dlt-serverless'
        : '/api/v1/calculate/dlt-classic'
    case 'DBSQL':
      return config.dbsql_warehouse_type === 'SERVERLESS'
        ? '/api/v1/calculate/dbsql-serverless'
        : '/api/v1/calculate/dbsql-classic-pro'
    case 'VECTOR_SEARCH':
      return '/api/v1/calculate/vector-search'
    case 'MODEL_SERVING':
      return '/api/v1/calculate/model-serving'
    case 'LAKEBASE':
      return '/api/v1/calculate/lakebase'
    case 'FMAPI_DATABRICKS':
      return '/api/v1/calculate/fmapi-databricks'
    case 'FMAPI_PROPRIETARY':
      return '/api/v1/calculate/fmapi-proprietary'
    default:
      return '/api/v1/calculate/jobs-classic'
  }
}

// Build API request body
function buildAPIRequest(testCase: TestCase): Record<string, unknown> {
  const { workloadType, config, environment } = testCase
  // API expects uppercase cloud names
  const base = { 
    cloud: environment.cloud.toUpperCase(), 
    region: environment.region, 
    tier: environment.tier 
  }
  
  // Helper to build time-based params (either runs_per_day OR hours_per_month)
  const getTimeParams = () => {
    if (config.hours_per_month) {
      return { hours_per_month: config.hours_per_month }
    }
    return {
      runs_per_day: config.runs_per_day || 1,
      avg_runtime_minutes: config.avg_runtime_minutes || 30,
      days_per_month: config.days_per_month || 22
    }
  }
  
  switch (workloadType) {
    case 'JOBS':
    case 'ALL_PURPOSE':
      if (config.serverless_enabled) {
        // Jobs/All-Purpose Serverless
        return {
          ...base,
          driver_node_type: config.driver_node_type,
          worker_node_type: config.worker_node_type,
          num_workers: config.num_workers || 2,
          serverless_mode: config.serverless_mode || 'standard',
          ...getTimeParams()
        }
      }
      // Jobs/All-Purpose Classic
      return {
        ...base,
        driver_node_type: config.driver_node_type,
        worker_node_type: config.worker_node_type,
        num_workers: config.num_workers || 2,
        photon_enabled: config.photon_enabled || false,
        driver_pricing_tier: config.driver_pricing_tier || 'on_demand',
        worker_pricing_tier: config.worker_pricing_tier || 'spot',
        driver_payment_option: config.driver_payment_option || 'NA',
        worker_payment_option: config.worker_payment_option || 'NA',
        ...getTimeParams()
      }
      
    case 'DLT':
      if (config.serverless_enabled) {
        // DLT Serverless
        return {
          ...base,
          driver_node_type: config.driver_node_type,
          worker_node_type: config.worker_node_type,
          num_workers: config.num_workers || 2,
          serverless_mode: config.serverless_mode || 'standard',
          ...getTimeParams()
        }
      }
      // DLT Classic
      return {
        ...base,
        dlt_edition: config.dlt_edition || 'CORE',
        photon_enabled: config.photon_enabled || false,
        driver_node_type: config.driver_node_type,
        worker_node_type: config.worker_node_type,
        num_workers: config.num_workers || 2,
        driver_pricing_tier: config.driver_pricing_tier || 'on_demand',
        worker_pricing_tier: config.worker_pricing_tier || 'spot',
        driver_payment_option: config.driver_payment_option || 'NA',
        worker_payment_option: config.worker_payment_option || 'NA',
        ...getTimeParams()
      }
      
    case 'DBSQL':
      if (config.dbsql_warehouse_type === 'SERVERLESS') {
        // DBSQL Serverless - no VM pricing
        return {
          ...base,
          warehouse_size: config.dbsql_warehouse_size,
          num_clusters: config.dbsql_num_clusters || 1,
          ...getTimeParams()
        }
      }
      // DBSQL Classic/Pro - uses vm_pricing_tier and vm_payment_option
      return {
        ...base,
        warehouse_type: config.dbsql_warehouse_type,
        warehouse_size: config.dbsql_warehouse_size,
        num_clusters: config.dbsql_num_clusters || 1,
        vm_pricing_tier: config.dbsql_driver_pricing_tier || 'on_demand',
        vm_payment_option: config.dbsql_driver_payment_option || 'NA',
        ...getTimeParams()
      }
      
    case 'VECTOR_SEARCH':
      // Vector Search
      return {
        ...base,
        mode: config.vector_search_mode || 'standard',
        vector_capacity_millions: config.vector_capacity_millions || 1,
        hours_per_month: config.hours_per_month || 730
      }
      
    case 'MODEL_SERVING':
      // Model Serving
      return {
        ...base,
        gpu_type: config.model_serving_gpu_type || 'cpu',
        hours_per_month: config.hours_per_month || 730
      }
      
    case 'LAKEBASE':
      // Lakebase
      return {
        ...base,
        cu_size: config.lakebase_cu || 2,
        num_nodes: config.lakebase_ha_nodes || 1,
        hours_per_month: config.hours_per_month || 730
      }
      
    case 'FMAPI_DATABRICKS':
      // Foundation Model (Databricks)
      // For token-based: quantity = actual token count (e.g., 1000000 for 1M tokens)
      // For provisioned: quantity = hours
      {
        const isProvisioned = config.fmapi_rate_type?.includes('provisioned')
        const quantity = isProvisioned 
          ? (config.fmapi_quantity || 730) // hours for provisioned
          : (config.fmapi_quantity || 1) * 1000000 // convert millions to actual tokens
        return {
          ...base,
          model: config.fmapi_model,
          rate_type: config.fmapi_rate_type || 'input_token',
          quantity
        }
      }
      
    case 'FMAPI_PROPRIETARY':
      // Foundation Model (Proprietary)
      // For token-based: quantity = actual token count (e.g., 1000000 for 1M tokens)
      // For provisioned: quantity = hours
      {
        const isProvisioned = config.fmapi_rate_type?.includes('provisioned')
        const quantity = isProvisioned 
          ? (config.fmapi_quantity || 730) // hours for provisioned
          : (config.fmapi_quantity || 1) * 1000000 // convert millions to actual tokens
        return {
          ...base,
          provider: config.fmapi_provider || 'openai',
          model: config.fmapi_model,
          endpoint_type: config.fmapi_endpoint_type || 'global',
          context_length: config.fmapi_context_length || 'all',
          rate_type: config.fmapi_rate_type || 'input_token',
          quantity
        }
      }
      
    default:
      return base
  }
}

// Compare results
interface CompareResult {
  discrepancies: { field: string; local: number; api: number; diff: number; diffPercent: number }[]
  totalCostDiffPercent: number
}

function compareResults(
  local: CostBreakdown, 
  api: CostBreakdown | null,
  tolerancePercent: number = 1
): CompareResult {
  // If no API result, return 100% diff
  if (!api) {
    return {
      discrepancies: [],
      totalCostDiffPercent: local.totalCost > 0 ? 100 : 0
    }
  }
  
  const discrepancies: { field: string; local: number; api: number; diff: number; diffPercent: number }[] = []
  const fields: (keyof CostBreakdown)[] = ['monthlyDBUs', 'dbuCost', 'vmCost', 'totalCost']
  
  // Calculate totalCost diff specifically
  const localTotal = local.totalCost || 0
  const apiTotal = api.totalCost || 0
  const totalDiff = Math.abs(localTotal - apiTotal)
  const totalCostDiffPercent = apiTotal !== 0 
    ? (totalDiff / apiTotal) * 100 
    : (localTotal !== 0 ? 100 : 0)
  
  for (const field of fields) {
    const localVal = (local[field] as number) || 0
    const apiVal = (api[field] as number) || 0
    const diff = Math.abs(localVal - apiVal)
    const diffPercent = apiVal !== 0 ? (diff / apiVal) * 100 : (localVal !== 0 ? 100 : 0)
    
    if (diffPercent > tolerancePercent && diff > 0.01) {
      discrepancies.push({ field, local: localVal, api: apiVal, diff, diffPercent })
    }
  }
  
  return { discrepancies, totalCostDiffPercent }
}

// ===== MAIN COMPONENT =====

export default function TestCalculations() {
  const [results, setResults] = useState<TestResult[]>([])
  const [running, setRunning] = useState(false)
  const [paused, setPaused] = useState(false)
  const [stopped, setStopped] = useState(false)
  const [currentTest, setCurrentTest] = useState<string | null>(null)
  const [expandedResults, setExpandedResults] = useState<Set<string>>(new Set())
  const [selectedCategory, setSelectedCategory] = useState<string>('all')
  const [tolerancePercent, setTolerancePercent] = useState(1)
  const [showConfig, setShowConfig] = useState(false)
  const [showSingleTest, setShowSingleTest] = useState(false)
  const [progress, setProgress] = useState({ current: 0, total: 0 })
  
  // Single test configuration
  const [singleTestConfig, setSingleTestConfig] = useState({
    cloud: 'aws',
    region: 'us-east-1',
    tier: 'PREMIUM',
    workloadType: 'JOBS',
    serverless: false,
    photon: false,
    driverNode: 'c5.xlarge',
    workerNode: 'c5.xlarge',
    numWorkers: 2,
    runsPerDay: 1,
    avgRuntime: 30,
    daysPerMonth: 22,
    hoursPerMonth: 160
  })
  
  // Refs for pause/stop control
  const pausedRef = useRef(false)
  const stoppedRef = useRef(false)
  
  // Test configuration
  const [testConfig, setTestConfig] = useState<TestConfig>({
    clouds: ['aws'],
    regionsPerCloud: 2,
    tiersPerCloud: 2,
    vmSamplesPerCloud: 3,
    includeJobs: true,
    includeAllPurpose: true,
    includeDLT: true,
    includeDBSQL: true,
    includeVectorSearch: true,
    includeModelServing: true,
    includeFMAPIDB: true,
    includeFMAPIProp: true,
    includeLakebase: true,
    manualEnvironment: {
      enabled: false,
      cloud: 'aws',
      region: 'us-east-1',
      tier: 'PREMIUM'
    }
  })
  
  const {
    dbuRatesMap,
    instanceTypes,
    dbsqlSizes,
    photonMultipliers,
    modelServingGPUTypes,
    vectorSearchModes,
    pricingBundle,
    isPricingBundleLoaded,
    loadPricingBundle,
    getVMPrice,
    fetchVMCostForInstance,  // For pre-fetching VM prices before local calculation
    getFMAPIDatabricksRate,
    getFMAPIProprietaryRate,
    getVectorSearchRate
  } = useStore()
  
  // Load pricing bundle on mount
  useEffect(() => {
    loadPricingBundle()
  }, [loadPricingBundle])
  
  // Generate test cases based on config and pricing bundle
  const testCases = useMemo(() => generateTestCases(testConfig, pricingBundle), [testConfig, pricingBundle])
  
  // Filter by category
  const filteredTests = useMemo(() => {
    if (selectedCategory === 'all') return testCases
    return testCases.filter(t => t.category === selectedCategory)
  }, [testCases, selectedCategory])
  
  // Get unique categories
  const categories = useMemo(() => {
    const cats = new Set(testCases.map(t => t.category))
    return ['all', ...Array.from(cats)]
  }, [testCases])
  
  // Build context for a specific environment
  const buildContext = useCallback((cloud: string, region: string, tier: string): CostCalculationContext => {
    // Transform model serving GPU types from pricing bundle to expected format
    // The pricing bundle has dbu_rate, but the calculation expects id, name, dbu_per_hour
    const transformedModelServingGPUTypes = isPricingBundleLoaded && pricingBundle.modelServingRates
      ? Object.entries(pricingBundle.modelServingRates)
          .filter(([key]) => key.startsWith(`${cloud.toLowerCase()}:`))
          .map(([key, data]) => {
            const gpuType = key.split(':')[1]
            return {
              id: gpuType,
              name: gpuType,
              dbu_per_hour: (data as { dbu_rate: number }).dbu_rate
            }
          })
      : modelServingGPUTypes
    
    return {
      cloud,
      region,
      tier,
      dbuRatesMap,
      instanceTypes,
      dbsqlSizes,
      photonMultipliers,
      modelServingGPUTypes: transformedModelServingGPUTypes,
      vectorSearchModes,
      getVMPrice,
      // Transform FMAPI Databricks rate from pricing bundle (dbu_rate -> dbu_per_1M_tokens/dbu_per_hour)
      getFMAPIDatabricksRate: (model: string, rateType: string) => {
        if (isPricingBundleLoaded && pricingBundle.fmapiDatabricksRates) {
          const key = `${cloud.toLowerCase()}:${model}:${rateType}`
          const data = pricingBundle.fmapiDatabricksRates[key]
          if (data) {
            return {
              dbu_per_1M_tokens: data.is_hourly ? undefined : data.dbu_rate,
              dbu_per_hour: data.is_hourly ? data.dbu_rate : undefined
            }
          }
        }
        return getFMAPIDatabricksRate(model, rateType)
      },
      // Transform FMAPI Proprietary rate from pricing bundle
      getFMAPIProprietaryRate: (provider: string, model: string, rateType: string, endpointType?: string, contextLength?: string) => {
        if (isPricingBundleLoaded && pricingBundle.fmapiProprietaryRates) {
          const ep = endpointType || 'global'
          const ctx = contextLength || 'all'
          const key = `${cloud.toLowerCase()}:${provider.toLowerCase()}:${model.toLowerCase()}:${ep}:${ctx}:${rateType}`
          const data = pricingBundle.fmapiProprietaryRates[key]
          if (data) {
            return {
              dbu_per_1M_tokens: data.is_hourly ? undefined : data.dbu_rate,
              dbu_per_hour: data.is_hourly ? data.dbu_rate : undefined
            }
          }
        }
        return getFMAPIProprietaryRate(provider, model, rateType)
      },
      // Transform Vector Search rate from pricing bundle (dbu_rate -> dbu_per_hour)
      getVectorSearchRate: (mode: string) => {
        if (isPricingBundleLoaded && pricingBundle.vectorSearchRates) {
          const key = `${cloud.toLowerCase()}:${mode}`
          const data = pricingBundle.vectorSearchRates[key]
          if (data) {
            return {
              dbu_per_hour: data.dbu_rate,
              input_divisor: data.input_divisor
            }
          }
        }
        return getVectorSearchRate(mode)
      },
      getInstanceDBURate: (instanceType: string) => {
        if (!isPricingBundleLoaded) return null
        return getBundleInstanceDBURate(pricingBundle, cloud, instanceType)
      },
      getPhotonMultiplier: (skuType: string) => {
        if (!isPricingBundleLoaded) return null
        return getBundlePhotonMultiplier(pricingBundle, cloud, skuType)
      },
      getDBUPrice: (productType: string) => {
        if (!isPricingBundleLoaded) return null
        return getBundleDBUPrice(pricingBundle, cloud, region, tier, productType)
      },
      getDBSQLWarehouseConfig: (warehouseType: string, warehouseSize: string) => {
        if (!isPricingBundleLoaded) return null
        return getDBSQLWarehouseConfig(pricingBundle, cloud, warehouseType, warehouseSize)
      }
    }
  }, [dbuRatesMap, instanceTypes, dbsqlSizes, photonMultipliers, modelServingGPUTypes, vectorSearchModes, isPricingBundleLoaded, pricingBundle, getVMPrice, getFMAPIDatabricksRate, getFMAPIProprietaryRate, getVectorSearchRate])
  
  // Run a single test
  const runSingleTest = async (testCase: TestCase): Promise<TestResult> => {
    const { environment, workloadType, config } = testCase
    const context = buildContext(environment.cloud, environment.region, environment.tier)
    
    const lineItem: Partial<LineItem> = {
      ...config,
      workload_type: workloadType
    }
    
    // Pre-fetch VM prices for accurate local calculation (if not serverless)
    // This ensures vmPricingMap has the prices before local calculation runs
    const vmFetchPromises: Promise<number>[] = []
    
    // Handle DBSQL Classic/Pro warehouses - get instance types from warehouse config
    if (workloadType === 'DBSQL' && config.dbsql_warehouse_type !== 'SERVERLESS') {
      const warehouseConfig = getDBSQLWarehouseConfig(
        pricingBundle,
        environment.cloud,
        config.dbsql_warehouse_type || 'PRO',
        config.dbsql_warehouse_size || 'Small'
      )
      
      if (warehouseConfig) {
        // Fetch driver instance type VM cost
        const driverTier = config.dbsql_driver_pricing_tier || 'on_demand'
        const driverPayment = config.dbsql_driver_payment_option || 'NA'
        vmFetchPromises.push(
          fetchVMCostForInstance(
            environment.cloud,
            environment.region,
            warehouseConfig.driver_instance_type,
            driverTier,
            driverPayment
          )
        )
        
        // Fetch worker instance type VM cost
        const workerTier = config.dbsql_worker_pricing_tier || 'on_demand'
        const workerPayment = config.dbsql_worker_payment_option || 'NA'
        vmFetchPromises.push(
          fetchVMCostForInstance(
            environment.cloud,
            environment.region,
            warehouseConfig.worker_instance_type,
            workerTier,
            workerPayment
          )
        )
      }
    } else if (!config.serverless_enabled && config.driver_node_type) {
      // Regular compute workloads (Jobs, All Purpose, DLT)
      // Fetch driver VM price
      vmFetchPromises.push(
        fetchVMCostForInstance(
          environment.cloud,
          environment.region,
          config.driver_node_type,
          config.driver_pricing_tier || 'on_demand',
          config.driver_payment_option || 'NA'
        )
      )
      
      // Fetch worker VM price (if different from driver)
      if (config.worker_node_type) {
        vmFetchPromises.push(
          fetchVMCostForInstance(
            environment.cloud,
            environment.region,
            config.worker_node_type,
            config.worker_pricing_tier || 'spot',
            config.worker_payment_option || 'NA'
          )
        )
      }
    }
    
    // Wait for VM prices to be fetched and cached
    if (vmFetchPromises.length > 0) {
      await Promise.all(vmFetchPromises)
    }
    
    // Local calculation (now with VM prices in cache)
    const localStart = performance.now()
    const localResult = calculateWorkloadCost(lineItem, context)
    const localTimeMs = performance.now() - localStart
    
    // API calculation
    const apiStart = performance.now()
    let apiResult: CostBreakdown | null = null
    let apiError: string | undefined
    let apiRawResponse: Record<string, unknown> | undefined
    const endpoint = getAPIEndpoint(workloadType, config)
    const body = buildAPIRequest(testCase)
    
    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      })
      
      if (response.ok) {
        const responseData = await response.json()
        apiRawResponse = responseData  // Store raw response for debugging
        
        // Parse API response - handle nested structure: { success: true, data: { ... } }
        const data = responseData.data || responseData
        
        // Extract from nested structure with detailed logging
        const monthlyDBUs = data.dbu_calculation?.dbu_per_month ?? 
          data.dbu_per_month ?? 
          (data.dbu_calculation?.dbu_per_hour ?? data.dbu_per_hour ?? 0) * (config.hours_per_month || 730)
        
        const dbuCost = data.dbu_calculation?.dbu_cost_per_month ?? 
          data.total_cost?.breakdown?.dbu_cost ??
          data.dbu_cost_per_month ?? 
          data.dbu_cost ?? 0
        
        const vmCost = data.vm_costs?.vm_cost_per_month ?? 
          data.total_cost?.breakdown?.vm_cost ??
          data.vm_cost_per_month ?? 
          data.vm_cost ?? 0
        
        // Handle totalCost - be careful with 'total_cost' as object vs number
        let totalCost = 0
        if (typeof data.total_cost === 'object' && data.total_cost !== null) {
          totalCost = data.total_cost.cost_per_month ?? (dbuCost + vmCost)
        } else if (typeof data.total_cost === 'number') {
          totalCost = data.total_cost
        } else {
          totalCost = data.total_cost_per_month ?? (dbuCost + vmCost)
        }
        
        apiResult = { monthlyDBUs, dbuCost, vmCost, totalCost }
        
        // Debug logging for first few tests
        if (testCase.name.includes('Serverless')) {
          console.log(`[DEBUG] ${testCase.name}:`, {
            rawResponse: responseData,
            parsed: apiResult
          })
        }
      } else {
        const errorText = await response.text()
        // Try to parse JSON error
        try {
          const errorJson = JSON.parse(errorText)
          apiError = `HTTP ${response.status}: ${errorJson.detail?.message || errorJson.detail || errorJson.message || errorText}`
        } catch {
          apiError = `HTTP ${response.status}: ${errorText}`
        }
      }
    } catch (e) {
      apiError = e instanceof Error ? e.message : 'Unknown error'
    }
    const apiTimeMs = performance.now() - apiStart
    
    const { discrepancies, totalCostDiffPercent } = compareResults(localResult, apiResult, tolerancePercent)
    
    // Consider match if totalCost is within tolerance AND no API error
    const matches = totalCostDiffPercent <= tolerancePercent && !apiError
    
    return {
      testCase,
      localResult,
      apiResult,
      apiError,
      apiRequestBody: body,
      apiRawResponse,  // Store raw response for debugging
      localTimeMs,
      apiTimeMs,
      matches,
      totalCostDiffPercent,
      discrepancies
    }
  }
  
  // Pause/Resume/Stop handlers
  const handlePause = () => {
    pausedRef.current = true
    setPaused(true)
  }
  
  const handleResume = () => {
    pausedRef.current = false
    setPaused(false)
  }
  
  const handleStop = () => {
    stoppedRef.current = true
    setStopped(true)
    pausedRef.current = false
    setPaused(false)
  }
  
  // Wait while paused
  const waitIfPaused = async () => {
    while (pausedRef.current && !stoppedRef.current) {
      await new Promise(resolve => setTimeout(resolve, 100))
    }
  }
  
  // Run all tests
  const runAllTests = async () => {
    setRunning(true)
    setPaused(false)
    setStopped(false)
    pausedRef.current = false
    stoppedRef.current = false
    setResults([])
    setProgress({ current: 0, total: filteredTests.length })
    
    for (let i = 0; i < filteredTests.length; i++) {
      // Check for stop
      if (stoppedRef.current) break
      
      // Wait if paused
      await waitIfPaused()
      if (stoppedRef.current) break
      
      const testCase = filteredTests[i]
      setCurrentTest(testCase.id)
      setProgress({ current: i + 1, total: filteredTests.length })
      const result = await runSingleTest(testCase)
      setResults(prev => [...prev, result])
    }
    
    setCurrentTest(null)
    setRunning(false)
    setPaused(false)
    setStopped(false)
  }
  
  // Run a custom single test
  const runCustomSingleTest = async () => {
    const { cloud, region, tier, workloadType, serverless, photon, driverNode, workerNode, numWorkers, runsPerDay, avgRuntime, daysPerMonth, hoursPerMonth } = singleTestConfig
    
    const testCase: TestCase = {
      id: 'custom-single',
      name: `Custom ${workloadType} Test`,
      category: workloadType,
      workloadType,
      environment: { cloud, region, tier },
      config: {
        serverless_enabled: serverless,
        photon_enabled: photon,
        driver_node_type: driverNode,
        worker_node_type: workerNode,
        num_workers: numWorkers,
        runs_per_day: runsPerDay,
        avg_runtime_minutes: avgRuntime,
        days_per_month: daysPerMonth,
        hours_per_month: hoursPerMonth,
        driver_pricing_tier: 'on_demand',
        worker_pricing_tier: 'spot'
      }
    }
    
    setRunning(true)
    setCurrentTest('custom-single')
    const result = await runSingleTest(testCase)
    setResults([result])
    setCurrentTest(null)
    setRunning(false)
  }
  
  // Stats
  const stats = useMemo(() => {
    const passed = results.filter(r => r.matches).length
    const failed = results.filter(r => !r.matches).length
    const apiErrors = results.filter(r => r.apiError).length
    const avgLocalTime = results.length > 0 
      ? results.reduce((sum, r) => sum + r.localTimeMs, 0) / results.length 
      : 0
    const avgApiTime = results.length > 0
      ? results.reduce((sum, r) => sum + r.apiTimeMs, 0) / results.length
      : 0
    const byCategory: Record<string, { passed: number; failed: number }> = {}
    results.forEach(r => {
      const cat = r.testCase.category
      if (!byCategory[cat]) byCategory[cat] = { passed: 0, failed: 0 }
      if (r.matches) byCategory[cat].passed++
      else byCategory[cat].failed++
    })
    return { passed, failed, apiErrors, avgLocalTime, avgApiTime, byCategory }
  }, [results])
  
  // Export CSV
  const exportCSV = () => {
    const headers = ['Test ID', 'Test Name', 'Category', 'Cloud', 'Region', 'Tier', 'Status', 'Local Total', 'API Total', 'Diff %', 'Local Time (ms)', 'API Time (ms)', 'Error']
    const rows = results.map(r => [
      r.testCase.id,
      r.testCase.name,
      r.testCase.category,
      r.testCase.environment.cloud,
      r.testCase.environment.region,
      r.testCase.environment.tier,
      r.matches ? 'PASS' : 'FAIL',
      r.localResult.totalCost.toFixed(2),
      r.apiResult?.totalCost.toFixed(2) || 'N/A',
      r.totalCostDiffPercent.toFixed(2),
      r.localTimeMs.toFixed(1),
      r.apiTimeMs.toFixed(1),
      r.apiError || ''
    ])
    
    const csv = [headers.join(','), ...rows.map(r => r.map(c => `"${c}"`).join(','))].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `calculation-tests-${new Date().toISOString().split('T')[0]}.csv`
    a.click()
  }
  
  const toggleExpanded = (id: string) => {
    const newExpanded = new Set(expandedResults)
    if (newExpanded.has(id)) {
      newExpanded.delete(id)
    } else {
      newExpanded.add(id)
    }
    setExpandedResults(newExpanded)
  }
  
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value)
  }
  
  const formatNumber = (value: number) => {
    if (value >= 1000) {
      return `${(value / 1000).toFixed(2)}K`
    }
    return value.toFixed(2)
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-purple-500/10 flex items-center justify-center">
            <BeakerIcon className="w-6 h-6 text-purple-500" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-[var(--text-primary)]">Calculation Test Suite</h1>
            <p className="text-sm text-[var(--text-muted)]">
              Bulk testing across clouds, regions, tiers, and workload types
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowSingleTest(!showSingleTest)}
            className={`btn ${showSingleTest ? 'btn-primary' : 'btn-secondary'} flex items-center gap-2`}
          >
            <BoltIcon className="w-4 h-4" />
            Single Test
          </button>
          <button
            onClick={() => setShowConfig(!showConfig)}
            className={`btn ${showConfig ? 'btn-primary' : 'btn-secondary'} flex items-center gap-2`}
          >
            <AdjustmentsHorizontalIcon className="w-4 h-4" />
            Configure
          </button>
          {results.length > 0 && (
            <button
              onClick={exportCSV}
              className="btn btn-secondary flex items-center gap-2"
            >
              <DocumentArrowDownIcon className="w-4 h-4" />
              Export
            </button>
          )}
          
          {/* Run controls */}
          {running && !paused && (
            <button
              onClick={handlePause}
              className="btn btn-secondary flex items-center gap-2 bg-yellow-500/10 hover:bg-yellow-500/20 text-yellow-600"
            >
              <PauseIcon className="w-4 h-4" />
              Pause
            </button>
          )}
          {running && paused && (
            <button
              onClick={handleResume}
              className="btn btn-secondary flex items-center gap-2 bg-green-500/10 hover:bg-green-500/20 text-green-600"
            >
              <PlayIcon className="w-4 h-4" />
              Resume
            </button>
          )}
          {running && (
            <button
              onClick={handleStop}
              className="btn btn-secondary flex items-center gap-2 bg-red-500/10 hover:bg-red-500/20 text-red-600"
            >
              <StopIcon className="w-4 h-4" />
              Stop
            </button>
          )}
          {!running && (
            <button
              onClick={runAllTests}
              className="btn btn-primary flex items-center gap-2"
            >
              <PlayIcon className="w-4 h-4" />
              Run {filteredTests.length} Tests
            </button>
          )}
        </div>
      </div>
      
      {/* Single Test Panel */}
      {showSingleTest && (
        <motion.div 
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="card p-4 mb-6 border-2 border-lava-600/30"
        >
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <BoltIcon className="w-5 h-5 text-lava-600" />
              <h3 className="font-semibold text-[var(--text-primary)]">Single Test Configuration</h3>
            </div>
            <button
              onClick={runCustomSingleTest}
              disabled={running}
              className="btn btn-primary flex items-center gap-2"
            >
              <PlayIcon className="w-4 h-4" />
              Run Single Test
            </button>
          </div>
          
          <div className="grid grid-cols-6 gap-4">
            {/* Environment */}
            <div>
              <label className="block text-xs font-medium text-[var(--text-muted)] mb-1">Cloud</label>
              <select
                value={singleTestConfig.cloud}
                onChange={(e) => setSingleTestConfig({ ...singleTestConfig, cloud: e.target.value })}
                className="w-full text-sm"
              >
                <option value="aws">AWS</option>
                <option value="azure">Azure</option>
                <option value="gcp">GCP</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-[var(--text-muted)] mb-1">Region (type or select)</label>
              <input
                type="text"
                value={singleTestConfig.region}
                onChange={(e) => setSingleTestConfig({ ...singleTestConfig, region: e.target.value })}
                className="w-full text-sm"
                placeholder="e.g., us-east-1"
                list="single-test-regions"
              />
              <datalist id="single-test-regions">
                {getAvailableRegions(pricingBundle, singleTestConfig.cloud).slice(0, 20).map(r => (
                  <option key={r} value={r}>{r}</option>
                ))}
              </datalist>
            </div>
            <div>
              <label className="block text-xs font-medium text-[var(--text-muted)] mb-1">Tier</label>
              <select
                value={singleTestConfig.tier}
                onChange={(e) => setSingleTestConfig({ ...singleTestConfig, tier: e.target.value })}
                className="w-full text-sm"
              >
                {getTiersForCloud(singleTestConfig.cloud).map(t => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-[var(--text-muted)] mb-1">Workload</label>
              <select
                value={singleTestConfig.workloadType}
                onChange={(e) => setSingleTestConfig({ ...singleTestConfig, workloadType: e.target.value })}
                className="w-full text-sm"
              >
                <option value="JOBS">Jobs</option>
                <option value="ALL_PURPOSE">All Purpose</option>
                <option value="DLT">DLT</option>
                <option value="DBSQL">DBSQL</option>
              </select>
            </div>
            <div className="flex items-end gap-4">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={singleTestConfig.serverless}
                  onChange={(e) => setSingleTestConfig({ ...singleTestConfig, serverless: e.target.checked })}
                  className="rounded"
                />
                Serverless
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={singleTestConfig.photon}
                  onChange={(e) => setSingleTestConfig({ ...singleTestConfig, photon: e.target.checked })}
                  className="rounded"
                />
                Photon
              </label>
            </div>
          </div>
          
          <div className="grid grid-cols-6 gap-4 mt-4">
            <div>
              <label className="block text-xs font-medium text-[var(--text-muted)] mb-1">Driver Node (type or select)</label>
              <input
                type="text"
                value={singleTestConfig.driverNode}
                onChange={(e) => setSingleTestConfig({ ...singleTestConfig, driverNode: e.target.value })}
                className="w-full text-sm"
                placeholder="e.g., c5.xlarge"
                list="single-test-driver-vms"
              />
              <datalist id="single-test-driver-vms">
                {getValidVMTypesForCloudRegion(pricingBundle, singleTestConfig.cloud, singleTestConfig.region).slice(0, 50).map(vm => (
                  <option key={vm} value={vm}>{vm}</option>
                ))}
              </datalist>
            </div>
            <div>
              <label className="block text-xs font-medium text-[var(--text-muted)] mb-1">Worker Node (type or select)</label>
              <input
                type="text"
                value={singleTestConfig.workerNode}
                onChange={(e) => setSingleTestConfig({ ...singleTestConfig, workerNode: e.target.value })}
                className="w-full text-sm"
                placeholder="e.g., c5.xlarge"
                list="single-test-worker-vms"
              />
              <datalist id="single-test-worker-vms">
                {getValidVMTypesForCloudRegion(pricingBundle, singleTestConfig.cloud, singleTestConfig.region).slice(0, 50).map(vm => (
                  <option key={vm} value={vm}>{vm}</option>
                ))}
              </datalist>
            </div>
            <div>
              <label className="block text-xs font-medium text-[var(--text-muted)] mb-1">Workers</label>
              <input
                type="number"
                value={singleTestConfig.numWorkers}
                onChange={(e) => setSingleTestConfig({ ...singleTestConfig, numWorkers: parseInt(e.target.value) || 1 })}
                min={0}
                max={100}
                className="w-full text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-[var(--text-muted)] mb-1">Runs/Day</label>
              <input
                type="number"
                value={singleTestConfig.runsPerDay}
                onChange={(e) => setSingleTestConfig({ ...singleTestConfig, runsPerDay: parseInt(e.target.value) || 1 })}
                min={1}
                className="w-full text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-[var(--text-muted)] mb-1">Avg Runtime (min)</label>
              <input
                type="number"
                value={singleTestConfig.avgRuntime}
                onChange={(e) => setSingleTestConfig({ ...singleTestConfig, avgRuntime: parseInt(e.target.value) || 1 })}
                min={1}
                className="w-full text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-[var(--text-muted)] mb-1">Days/Month</label>
              <input
                type="number"
                value={singleTestConfig.daysPerMonth}
                onChange={(e) => setSingleTestConfig({ ...singleTestConfig, daysPerMonth: parseInt(e.target.value) || 1 })}
                min={1}
                max={31}
                className="w-full text-sm"
              />
            </div>
          </div>
        </motion.div>
      )}
      
      {/* Configuration Panel */}
      {showConfig && (
        <motion.div 
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="card p-4 mb-6"
        >
          <div className="flex items-center gap-2 mb-4">
            <CogIcon className="w-5 h-5 text-[var(--text-muted)]" />
            <h3 className="font-semibold text-[var(--text-primary)]">Test Configuration</h3>
          </div>
          
          {/* Manual Environment Override */}
          <div className="mb-4 p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
            <label className="flex items-center gap-2 mb-3">
              <input
                type="checkbox"
                checked={testConfig.manualEnvironment.enabled}
                onChange={(e) => setTestConfig({
                  ...testConfig,
                  manualEnvironment: { ...testConfig.manualEnvironment, enabled: e.target.checked }
                })}
                className="rounded"
              />
              <span className="text-sm font-medium text-blue-700 dark:text-blue-300">Override: Test specific environment only</span>
            </label>
            
            {testConfig.manualEnvironment.enabled && (
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs font-medium text-[var(--text-muted)] mb-1">Cloud</label>
                  <select
                    value={testConfig.manualEnvironment.cloud}
                    onChange={(e) => setTestConfig({
                      ...testConfig,
                      manualEnvironment: { ...testConfig.manualEnvironment, cloud: e.target.value }
                    })}
                    className="w-full text-sm"
                  >
                    <option value="aws">AWS</option>
                    <option value="azure">Azure</option>
                    <option value="gcp">GCP</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-[var(--text-muted)] mb-1">Region (type or select)</label>
                  <input
                    type="text"
                    value={testConfig.manualEnvironment.region}
                    onChange={(e) => setTestConfig({
                      ...testConfig,
                      manualEnvironment: { ...testConfig.manualEnvironment, region: e.target.value }
                    })}
                    className="w-full text-sm"
                    placeholder="e.g., us-east-1"
                    list="available-regions"
                  />
                  <datalist id="available-regions">
                    {getAvailableRegions(pricingBundle, testConfig.manualEnvironment.cloud).slice(0, 20).map(r => (
                      <option key={r} value={r}>{r}</option>
                    ))}
                  </datalist>
                </div>
                <div>
                  <label className="block text-xs font-medium text-[var(--text-muted)] mb-1">Tier</label>
                  <select
                    value={testConfig.manualEnvironment.tier}
                    onChange={(e) => setTestConfig({
                      ...testConfig,
                      manualEnvironment: { ...testConfig.manualEnvironment, tier: e.target.value }
                    })}
                    className="w-full text-sm"
                  >
                    {getTiersForCloud(testConfig.manualEnvironment.cloud).map(t => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                </div>
              </div>
            )}
            
            {testConfig.manualEnvironment.enabled && (
              <p className="text-xs text-blue-600 dark:text-blue-400 mt-2">
                VM types will be auto-detected from pricing bundle for {testConfig.manualEnvironment.cloud.toUpperCase()} / {testConfig.manualEnvironment.region}
              </p>
            )}
          </div>
          
          <div className="grid grid-cols-4 gap-6">
            {/* Cloud Selection */}
            <div className={testConfig.manualEnvironment.enabled ? 'opacity-50 pointer-events-none' : ''}>
              <label className="block text-xs font-medium text-[var(--text-muted)] mb-2">Clouds</label>
              <div className="space-y-1">
                {['aws', 'azure', 'gcp'].map(cloud => (
                  <label key={cloud} className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={testConfig.clouds.includes(cloud)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setTestConfig({ ...testConfig, clouds: [...testConfig.clouds, cloud] })
                        } else {
                          setTestConfig({ ...testConfig, clouds: testConfig.clouds.filter(c => c !== cloud) })
                        }
                      }}
                      className="rounded"
                      disabled={testConfig.manualEnvironment.enabled}
                    />
                    {cloud.toUpperCase()}
                  </label>
                ))}
              </div>
            </div>
            
            {/* Sampling */}
            <div>
              <label className="block text-xs font-medium text-[var(--text-muted)] mb-2">Sampling</label>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <label className="text-xs text-[var(--text-muted)] w-24">Regions/Cloud:</label>
                  <input
                    type="number"
                    min={1}
                    max={4}
                    value={testConfig.regionsPerCloud}
                    onChange={(e) => setTestConfig({ ...testConfig, regionsPerCloud: parseInt(e.target.value) || 1 })}
                    className="w-16 text-sm"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <label className="text-xs text-[var(--text-muted)] w-24">Tiers/Cloud:</label>
                  <input
                    type="number"
                    min={1}
                    max={3}
                    value={testConfig.tiersPerCloud}
                    onChange={(e) => setTestConfig({ ...testConfig, tiersPerCloud: parseInt(e.target.value) || 1 })}
                    className="w-16 text-sm"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <label className="text-xs text-[var(--text-muted)] w-24">VM Samples:</label>
                  <input
                    type="number"
                    min={1}
                    max={10}
                    value={testConfig.vmSamplesPerCloud}
                    onChange={(e) => setTestConfig({ ...testConfig, vmSamplesPerCloud: parseInt(e.target.value) || 1 })}
                    className="w-16 text-sm"
                  />
                </div>
              </div>
            </div>
            
            {/* Workload Types - Column 1 */}
            <div>
              <label className="block text-xs font-medium text-[var(--text-muted)] mb-2">Workloads (1)</label>
              <div className="space-y-1">
                {[
                  { key: 'includeJobs', label: 'Jobs' },
                  { key: 'includeAllPurpose', label: 'All Purpose' },
                  { key: 'includeDLT', label: 'DLT' },
                  { key: 'includeDBSQL', label: 'DBSQL' },
                  { key: 'includeVectorSearch', label: 'Vector Search' }
                ].map(({ key, label }) => (
                  <label key={key} className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={testConfig[key as keyof TestConfig] as boolean}
                      onChange={(e) => setTestConfig({ ...testConfig, [key]: e.target.checked })}
                      className="rounded"
                    />
                    {label}
                  </label>
                ))}
              </div>
            </div>
            
            {/* Workload Types - Column 2 */}
            <div>
              <label className="block text-xs font-medium text-[var(--text-muted)] mb-2">Workloads (2)</label>
              <div className="space-y-1">
                {[
                  { key: 'includeModelServing', label: 'Model Serving' },
                  { key: 'includeFMAPIDB', label: 'FMAPI Databricks' },
                  { key: 'includeFMAPIProp', label: 'FMAPI Proprietary' },
                  { key: 'includeLakebase', label: 'Lakebase' }
                ].map(({ key, label }) => (
                  <label key={key} className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={testConfig[key as keyof TestConfig] as boolean}
                      onChange={(e) => setTestConfig({ ...testConfig, [key]: e.target.checked })}
                      className="rounded"
                    />
                    {label}
                  </label>
                ))}
              </div>
            </div>
          </div>
          
          <div className="mt-4 pt-4 border-t border-[var(--border-primary)] flex items-center justify-between">
            <p className="text-sm text-[var(--text-muted)]">
              <span className="font-semibold text-[var(--text-primary)]">{testCases.length}</span> test cases will be generated
            </p>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <label className="text-xs text-[var(--text-muted)]">Tolerance %:</label>
                <input
                  type="number"
                  value={tolerancePercent}
                  onChange={(e) => setTolerancePercent(parseFloat(e.target.value) || 1)}
                  min={0}
                  max={100}
                  step={0.5}
                  className="w-16 text-sm"
                />
              </div>
              <div className="flex items-center gap-2">
                <label className="text-xs text-[var(--text-muted)]">Category:</label>
                <select
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  className="text-sm"
                >
                  {categories.map(cat => (
                    <option key={cat} value={cat}>
                      {cat === 'all' ? `All (${testCases.length})` : cat}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        </motion.div>
      )}
      
      {/* Bundle Status */}
      <div className="card p-3 mb-6 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className={`flex items-center gap-2 ${isPricingBundleLoaded ? 'text-green-500' : 'text-yellow-500'}`}>
            {isPricingBundleLoaded ? <CheckCircleIcon className="w-5 h-5" /> : <ExclamationTriangleIcon className="w-5 h-5" />}
            <span className="text-sm font-medium">
              Pricing Bundle: {isPricingBundleLoaded ? 'Loaded' : 'Not Loaded (using fallbacks)'}
            </span>
          </div>
        </div>
        <div className="text-sm text-[var(--text-muted)]">
          Testing: {testConfig.clouds.map(c => c.toUpperCase()).join(', ')} • 
          {testConfig.regionsPerCloud} regions × {testConfig.tiersPerCloud} tiers × {testConfig.vmSamplesPerCloud} VMs
        </div>
      </div>
      
      {/* Stats */}
      {results.length > 0 && (
        <div className="grid grid-cols-5 gap-4 mb-6">
          <div className="card p-4 text-center">
            <p className="text-2xl font-bold text-green-500">{stats.passed}</p>
            <p className="text-xs text-[var(--text-muted)]">Passed</p>
          </div>
          <div className="card p-4 text-center">
            <p className="text-2xl font-bold text-red-500">{stats.failed}</p>
            <p className="text-xs text-[var(--text-muted)]">Failed</p>
          </div>
          <div className="card p-4 text-center">
            <p className="text-2xl font-bold text-yellow-500">{stats.apiErrors}</p>
            <p className="text-xs text-[var(--text-muted)]">API Errors</p>
          </div>
          <div className="card p-4 text-center">
            <p className="text-2xl font-bold text-blue-500">{stats.avgLocalTime.toFixed(1)}ms</p>
            <p className="text-xs text-[var(--text-muted)]">Avg Local</p>
          </div>
          <div className="card p-4 text-center">
            <p className="text-2xl font-bold text-purple-500">{stats.avgApiTime.toFixed(0)}ms</p>
            <p className="text-xs text-[var(--text-muted)]">Avg API</p>
          </div>
        </div>
      )}
      
      {/* Category Breakdown */}
      {results.length > 0 && Object.keys(stats.byCategory).length > 0 && (
        <div className="card p-4 mb-6">
          <h3 className="text-sm font-semibold text-[var(--text-secondary)] mb-3">Results by Category</h3>
          <div className="flex flex-wrap gap-3">
            {Object.entries(stats.byCategory).map(([cat, { passed, failed }]) => (
              <div key={cat} className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[var(--bg-tertiary)]">
                <span className="text-sm text-[var(--text-primary)]">{cat}</span>
                <span className="text-xs text-green-500">{passed} ✓</span>
                {failed > 0 && <span className="text-xs text-red-500">{failed} ✗</span>}
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* Progress bar */}
      {running && (
        <div className="mb-6">
          <div className="h-2 bg-[var(--bg-tertiary)] rounded-full overflow-hidden">
            <motion.div
              className={`h-full ${paused ? 'bg-yellow-500' : 'bg-lava-600'}`}
              initial={{ width: 0 }}
              animate={{ width: `${(progress.current / progress.total) * 100}%` }}
            />
          </div>
          <p className="text-xs text-[var(--text-muted)] mt-1 text-center">
            {progress.current} / {progress.total} tests completed
            {paused && <span className="ml-2 text-yellow-500 font-medium">(PAUSED)</span>}
            {stopped && <span className="ml-2 text-red-500 font-medium">(STOPPED)</span>}
          </p>
        </div>
      )}
      
      {/* Results Table */}
      <div className="card overflow-hidden">
        <div className="max-h-[600px] overflow-y-auto">
          <table className="w-full text-sm">
            <thead className="bg-[var(--bg-tertiary)] sticky top-0">
              <tr>
                <th className="text-left p-3 font-medium text-[var(--text-secondary)]">Test</th>
                <th className="text-left p-3 font-medium text-[var(--text-secondary)]">Category</th>
                <th className="text-left p-3 font-medium text-[var(--text-secondary)]">Environment</th>
                <th className="text-right p-3 font-medium text-[var(--text-secondary)]">Local</th>
                <th className="text-right p-3 font-medium text-[var(--text-secondary)]">API</th>
                <th className="text-right p-3 font-medium text-[var(--text-secondary)]">Diff %</th>
                <th className="text-center p-3 font-medium text-[var(--text-secondary)]">Status</th>
              </tr>
            </thead>
            <tbody>
              {filteredTests.map((test) => {
                const result = results.find(r => r.testCase.id === test.id)
                const isExpanded = expandedResults.has(test.id)
                const isRunning = currentTest === test.id
                
                return (
                  <>
                    <tr
                      key={test.id}
                      className={`
                        border-t border-[var(--border-primary)] 
                        ${result && !result.matches ? 'bg-red-500/5' : ''}
                        ${isRunning ? 'bg-blue-500/10' : ''}
                        hover:bg-[var(--bg-hover)] cursor-pointer
                      `}
                      onClick={() => result && toggleExpanded(test.id)}
                    >
                      <td className="p-3">
                        <div className="flex items-center gap-2">
                          {result && (
                            isExpanded 
                              ? <ChevronDownIcon className="w-4 h-4 text-[var(--text-muted)]" />
                              : <ChevronRightIcon className="w-4 h-4 text-[var(--text-muted)]" />
                          )}
                          <span className="font-medium text-[var(--text-primary)] truncate max-w-[200px]" title={test.name}>
                            {test.name}
                          </span>
                        </div>
                      </td>
                      <td className="p-3 text-[var(--text-muted)]">{test.category}</td>
                      <td className="p-3">
                        <div className="flex items-center gap-1">
                          <span className="px-1.5 py-0.5 text-xs rounded bg-blue-500/10 text-blue-500">{test.environment.cloud}</span>
                          <span className="text-xs text-[var(--text-muted)]">{test.environment.region}</span>
                          <span className="px-1.5 py-0.5 text-xs rounded bg-purple-500/10 text-purple-500">{test.environment.tier}</span>
                        </div>
                      </td>
                      <td className="p-3 text-right font-mono text-[var(--text-primary)]">
                        {result ? formatCurrency(result.localResult.totalCost) : '-'}
                      </td>
                      <td className="p-3 text-right font-mono text-[var(--text-primary)]">
                        {result?.apiResult ? formatCurrency(result.apiResult.totalCost) : result?.apiError ? 'Error' : '-'}
                      </td>
                      <td className="p-3 text-right font-mono">
                        {result ? (
                          <span className={result.totalCostDiffPercent <= 1 ? 'text-green-500' : 'text-red-500'}>
                            {result.totalCostDiffPercent.toFixed(1)}%
                          </span>
                        ) : '-'}
                      </td>
                      <td className="p-3 text-center">
                        {isRunning ? (
                          <ArrowPathIcon className="w-5 h-5 text-blue-500 animate-spin mx-auto" />
                        ) : result ? (
                          result.matches ? (
                            <CheckCircleIcon className="w-5 h-5 text-green-500 mx-auto" />
                          ) : (
                            <XCircleIcon className="w-5 h-5 text-red-500 mx-auto" />
                          )
                        ) : (
                          <span className="text-[var(--text-muted)]">-</span>
                        )}
                      </td>
                    </tr>
                    
                    {/* Expanded details */}
                    {result && isExpanded && (
                      <tr key={`${test.id}-details`} className="bg-[var(--bg-tertiary)]">
                        <td colSpan={7} className="p-4">
                          <div className="grid grid-cols-2 gap-6">
                            {/* Local Result */}
                            <div>
                              <h4 className="font-semibold text-[var(--text-primary)] mb-2">Local Calculation</h4>
                              <div className="bg-[var(--bg-primary)] rounded-lg p-3 space-y-1 font-mono text-xs">
                                <div className="flex justify-between">
                                  <span className="text-[var(--text-muted)]">Monthly DBUs:</span>
                                  <span className="text-[var(--text-primary)]">{formatNumber(result.localResult.monthlyDBUs)}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-[var(--text-muted)]">DBU Cost:</span>
                                  <span className="text-[var(--text-primary)]">{formatCurrency(result.localResult.dbuCost)}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-[var(--text-muted)]">VM Cost:</span>
                                  <span className="text-[var(--text-primary)]">{formatCurrency(result.localResult.vmCost)}</span>
                                </div>
                                <div className="flex justify-between border-t border-[var(--border-primary)] pt-1 mt-1">
                                  <span className="text-[var(--text-secondary)] font-semibold">Total:</span>
                                  <span className="text-lava-600 font-semibold">{formatCurrency(result.localResult.totalCost)}</span>
                                </div>
                                {result.localResult.dbuPrice && (
                                  <div className="flex justify-between text-[10px]">
                                    <span className="text-[var(--text-muted)]">$/DBU:</span>
                                    <span className="text-pink-500">${result.localResult.dbuPrice.toFixed(2)}</span>
                                  </div>
                                )}
                              </div>
                            </div>
                            
                            {/* API Result */}
                            <div>
                              <h4 className="font-semibold text-[var(--text-primary)] mb-2">API Calculation</h4>
                              {result.apiError ? (
                                <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3">
                                  <p className="text-red-500 text-xs break-all">{result.apiError}</p>
                                </div>
                              ) : result.apiResult ? (
                                <div className="bg-[var(--bg-primary)] rounded-lg p-3 space-y-1 font-mono text-xs">
                                  <div className="flex justify-between">
                                    <span className="text-[var(--text-muted)]">Monthly DBUs:</span>
                                    <span className={result.discrepancies.some(d => d.field === 'monthlyDBUs') ? 'text-red-500' : 'text-[var(--text-primary)]'}>
                                      {formatNumber(result.apiResult.monthlyDBUs)}
                                    </span>
                                  </div>
                                  <div className="flex justify-between">
                                    <span className="text-[var(--text-muted)]">DBU Cost:</span>
                                    <span className={result.discrepancies.some(d => d.field === 'dbuCost') ? 'text-red-500' : 'text-[var(--text-primary)]'}>
                                      {formatCurrency(result.apiResult.dbuCost)}
                                    </span>
                                  </div>
                                  <div className="flex justify-between">
                                    <span className="text-[var(--text-muted)]">VM Cost:</span>
                                    <span className={result.discrepancies.some(d => d.field === 'vmCost') ? 'text-red-500' : 'text-[var(--text-primary)]'}>
                                      {formatCurrency(result.apiResult.vmCost)}
                                    </span>
                                  </div>
                                  <div className="flex justify-between border-t border-[var(--border-primary)] pt-1 mt-1">
                                    <span className="text-[var(--text-secondary)] font-semibold">Total:</span>
                                    <span className={result.discrepancies.some(d => d.field === 'totalCost') ? 'text-red-500 font-semibold' : 'text-lava-600 font-semibold'}>
                                      {formatCurrency(result.apiResult.totalCost)}
                                    </span>
                                  </div>
                                </div>
                              ) : null}
                            </div>
                          </div>
                          
                          {/* Discrepancies */}
                          {result.discrepancies.length > 0 && (
                            <div className="mt-4">
                              <h4 className="font-semibold text-red-500 mb-2">Discrepancies</h4>
                              <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3">
                                <table className="w-full text-xs">
                                  <thead>
                                    <tr className="text-red-400">
                                      <th className="text-left pb-1">Field</th>
                                      <th className="text-right pb-1">Local</th>
                                      <th className="text-right pb-1">API</th>
                                      <th className="text-right pb-1">Diff</th>
                                      <th className="text-right pb-1">Diff %</th>
                                    </tr>
                                  </thead>
                                  <tbody className="font-mono">
                                    {result.discrepancies.map((d, i) => (
                                      <tr key={i} className="text-red-300">
                                        <td className="py-0.5">{d.field}</td>
                                        <td className="text-right">{d.local.toFixed(2)}</td>
                                        <td className="text-right">{d.api.toFixed(2)}</td>
                                        <td className="text-right">{d.diff.toFixed(2)}</td>
                                        <td className="text-right">{d.diffPercent.toFixed(2)}%</td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            </div>
                          )}
                          
                          {/* API Raw Response */}
                          {result.apiRawResponse && (
                            <div className="mt-4">
                              <h4 className="font-semibold text-green-500 mb-2">API Raw Response (from server)</h4>
                              <pre className="bg-green-500/10 border border-green-500/30 rounded-lg p-3 text-xs overflow-x-auto">
                                <code className="text-green-300">{JSON.stringify(result.apiRawResponse, null, 2)}</code>
                              </pre>
                            </div>
                          )}
                          
                          {/* API Request Body */}
                          {result.apiRequestBody && (
                            <div className="mt-4">
                              <h4 className="font-semibold text-blue-500 mb-2">API Request Body (sent to server)</h4>
                              <pre className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3 text-xs overflow-x-auto">
                                <code className="text-blue-300">{JSON.stringify(result.apiRequestBody, null, 2)}</code>
                              </pre>
                            </div>
                          )}
                          
                          {/* Test Config */}
                          <div className="mt-4">
                            <h4 className="font-semibold text-[var(--text-secondary)] mb-2">Test Configuration (internal)</h4>
                            <pre className="bg-[var(--bg-primary)] rounded-lg p-3 text-xs overflow-x-auto">
                              {JSON.stringify({ environment: result.testCase.environment, config: result.testCase.config }, null, 2)}
                            </pre>
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
