// API Types
export interface User {
  user_id: string
  email: string
  full_name?: string
  role?: string
  is_active: boolean
  last_login_at?: string
  created_at: string
  updated_at: string
}

export interface Estimate {
  estimate_id: string
  estimate_name: string
  owner_user_id?: string
  customer_name?: string
  cloud?: string
  region?: string
  tier?: string
  status?: string
  version: number
  template_id?: string
  original_prompt?: string
  is_deleted: boolean
  created_at: string
  updated_at: string
  updated_by?: string
  line_items: LineItemSummary[]
}

export interface LineItemSummary {
  line_item_id: string
  workload_name: string
  workload_type?: string
  display_order: number
}

export interface EstimateListItem {
  estimate_id: string
  estimate_name: string
  customer_name?: string
  cloud?: string
  region?: string
  tier?: string
  status?: string
  version: number
  line_item_count: number
  display_order?: number
  created_at: string
  updated_at: string
}

export interface LineItem {
  line_item_id: string
  estimate_id: string
  display_order: number
  workload_name: string
  workload_type?: string | null
  cloud?: string | null
  
  // Serverless toggle
  serverless_enabled?: boolean | null
  serverless_mode?: string | null
  
  // Classic Compute Configuration
  photon_enabled?: boolean | null
  driver_node_type?: string | null
  worker_node_type?: string | null
  num_workers?: number | null
  
  // DLT Configuration
  dlt_edition?: string | null
  
  // DBSQL Configuration
  dbsql_warehouse_type?: string | null
  dbsql_warehouse_size?: string | null
  dbsql_num_clusters?: number | null
  // Separate driver and worker pricing for DBSQL Pro/Classic
  dbsql_driver_pricing_tier?: string | null
  dbsql_driver_payment_option?: string | null
  dbsql_worker_pricing_tier?: string | null
  dbsql_worker_payment_option?: string | null
  
  // Vector Search Configuration
  vector_search_mode?: string | null
  vector_capacity_millions?: number | null
  vector_search_storage_gb?: number | null
  
  // Model Serving Configuration
  model_serving_gpu_type?: string | null
  model_serving_concurrency?: number | null
  model_serving_scale_out?: string | null
  
  // Databricks Apps Configuration
  databricks_apps_size?: string | null  // medium, large

  // Clean Room Configuration
  clean_room_collaborators?: number | null  // 1-10

  // AI Parse Configuration
  ai_parse_mode?: string | null  // dbu, pages
  ai_parse_complexity?: string | null  // low_text, low_images, medium, high
  ai_parse_pages_thousands?: number | null

  // Shutterstock ImageAI Configuration
  shutterstock_images?: number | null

  // Lakeflow Connect Configuration
  lakeflow_connect_pipeline_mode?: string | null
  lakeflow_connect_gateway_enabled?: boolean | null
  lakeflow_connect_gateway_instance?: string | null

  // Lakebase Configuration
  lakebase_cu?: number | null
  lakebase_storage_gb?: number | null
  lakebase_ha_nodes?: number | null
  lakebase_backup_retention_days?: number | null
  lakebase_pitr_gb?: number | null
  lakebase_snapshot_gb?: number | null
  
  // Foundation Model API Configuration (Proprietary)
  fmapi_provider?: string | null
  fmapi_model?: string | null
  fmapi_endpoint_type?: string | null
  fmapi_context_length?: string | null
  fmapi_rate_type?: string | null  // input_token, output_token, cache_read, cache_write
  fmapi_quantity?: number | null   // quantity in millions (M)
  
  // Usage Configuration
  runs_per_day?: number | null
  avg_runtime_minutes?: number | null
  days_per_month?: number | null
  hours_per_month?: number | null
  
  // Pricing Configuration
  driver_pricing_tier?: string | null
  worker_pricing_tier?: string | null
  driver_payment_option?: string | null
  worker_payment_option?: string | null
  
  // Additional Configuration
  workload_config?: Record<string, unknown> | null
  notes?: string | null
  
  created_at: string
  updated_at: string
}

// FMAPI Rate Types for Foundation Model (Proprietary)
export interface FMAPIRateType {
  id: string
  name: string
  description?: string
}

export interface WorkloadType {
  workload_type: string
  display_name: string
  description?: string
  
  // Configuration visibility flags (all optional for flexibility)
  show_compute_config?: boolean
  show_serverless_toggle?: boolean
  show_serverless_performance_mode?: boolean
  show_photon_toggle?: boolean
  show_dlt_config?: boolean
  show_dbsql_config?: boolean
  show_serverless_product?: boolean
  show_fmapi_config?: boolean
  show_lakebase_config?: boolean
  show_vector_search_mode?: boolean
  show_vm_pricing?: boolean
  show_usage_hours?: boolean
  show_usage_runs?: boolean
  show_usage_tokens?: boolean
  
  // SKU product types
  sku_product_type_standard?: string
  sku_product_type_photon?: string
  sku_product_type_serverless?: string
  
  display_order?: number
}

export interface CloudProvider {
  cloud: string
  display_name: string
  code: string
}

export interface Region {
  region_code: string
  region_name: string
  cloud: string
}

export interface VMPricingCost {
  cost_per_hour: number
  monthly_cost: number
  savings_percent?: number
}

export interface VMPricingReserved {
  payment_option: string
  cost_per_hour: number
  monthly_cost: number
  savings_percent?: number
}

export interface VMPricing {
  on_demand?: VMPricingCost
  spot?: VMPricingCost
  reserved_1y?: VMPricingReserved[]
  reserved_3y?: VMPricingReserved[]
}

export interface InstanceType {
  id: string
  name: string
  vcpus: number
  memory_gb: number
  dbu_rate: number
  gpu?: boolean
  instance_family?: string
  vm_pricing?: VMPricing
}

export interface DBSQLSize {
  id: string
  name: string
  dbu_per_hour?: number
  size?: string
  min_clusters?: number
  max_clusters?: number
}

export interface DLTEdition {
  id: string
  name: string
  edition?: string
  display_name?: string
  dbu_multiplier?: number
}

export interface FMAPIProvider {
  provider: string
  display_name?: string
  models?: FMAPIModel[]
}

export interface FMAPIModel {
  id: string
  name: string
  input_price_per_million?: number
  output_price_per_million?: number
}

// Model Serving GPU Types
export interface ModelServingGPUType {
  id: string
  name: string
  dbu_per_hour: number
  description?: string
}

// Foundation Models (Databricks) Configuration
export interface FMAPIDatabricksConfig {
  model_types: FMAPIDatabricksModelType[]
  models: {
    llm: FMAPIModelOption[]
    embedding: FMAPIModelOption[]
  }
  inference_types: FMAPIInferenceType[]
}

export interface FMAPIDatabricksModelType {
  id: string
  name: string
  has_output_tokens: boolean
}

export interface FMAPIModelOption {
  id: string
  name: string
}

export interface FMAPIInferenceType {
  id: string
  name: string
  description?: string
}

// Foundation Models (Proprietary) Configuration
export interface FMAPIProprietaryConfig {
  providers: FMAPIProprietaryProvider[]
  endpoint_types: FMAPIEndpointType[]
  context_lengths: FMAPIContextLength[]
}

export interface FMAPIProprietaryProvider {
  id: string
  name: string
  models: FMAPIModelOption[]
}

export interface FMAPIEndpointType {
  id: string
  name: string
}

export interface FMAPIContextLength {
  id: string
  name: string
}

// VM Pricing types
export interface VMPricing {
  cloud: string
  region: string
  instance_type: string
  pricing_tier: string
  payment_option: string
  cost_per_hour: number
  currency: string
  source?: string
  fetched_at?: string
  updated_at?: string
}

export interface VMPricingTier {
  id: string
  name: string
  tier?: string
  display_name?: string
  description?: string
}

export interface VMPaymentOption {
  id: string
  name: string
  option?: string
  display_name?: string
  description?: string
}

export interface ServerlessMode {
  mode: string
  display_name?: string
  multiplier?: number
  description?: string
}

export interface VMInstanceType {
  instance_type: string
}

