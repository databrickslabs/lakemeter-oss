/**
 * Field mappings for different workload types
 * Based on the workload type, different fields should be shown
 */

export type WorkloadType =
  | "ALL_PURPOSE"
  | "JOBS_CLASSIC"
  | "JOBS_SERVERLESS"
  | "DLT"
  | "DBSQL"
  | "VECTOR_SEARCH"
  | "MODEL_SERVING"
  | "FMAPI_DATABRICKS"
  | "FMAPI_PROPRIETARY";

export interface FieldMapping {
  attribute: string;
  label: string;
  inputType: "text" | "dropdown" | "checkbox";
  category: "compute" | "configuration" | "scheduling" | "pricing" | "metadata";
}

// Mapping attribute names to display labels and categories
export const fieldDefinitions: Record<string, FieldMapping> = {
  // Compute fields
  driver_node_type: {
    attribute: "driver_node_type",
    label: "Driver Node Type",
    inputType: "dropdown",
    category: "compute"
  },
  worker_node_type: {
    attribute: "worker_node_type",
    label: "Worker Node Type",
    inputType: "dropdown",
    category: "compute"
  },
  num_workers: {
    attribute: "num_workers",
    label: "Number of Workers",
    inputType: "text",
    category: "compute"
  },
  autoscale_enabled: {
    attribute: "autoscale_enabled",
    label: "Autoscale Enabled",
    inputType: "checkbox",
    category: "compute"
  },
  autoscale_min_workers: {
    attribute: "autoscale_min_workers",
    label: "Min Workers",
    inputType: "text",
    category: "compute"
  },
  autoscale_max_workers: {
    attribute: "autoscale_max_workers",
    label: "Max Workers",
    inputType: "text",
    category: "compute"
  },
  photon_enabled: {
    attribute: "photon_enabled",
    label: "Photon Enabled",
    inputType: "checkbox",
    category: "configuration"
  },

  // DLT fields
  dlt_edition: {
    attribute: "dlt_edition",
    label: "DLT Edition",
    inputType: "dropdown",
    category: "configuration"
  },
  dlt_pipeline_mode: {
    attribute: "dlt_pipeline_mode",
    label: "DLT Pipeline Mode",
    inputType: "dropdown",
    category: "configuration"
  },

  // DBSQL fields
  dbsql_warehouse_type: {
    attribute: "dbsql_warehouse_type",
    label: "Warehouse Type",
    inputType: "dropdown",
    category: "compute"
  },
  dbsql_warehouse_size: {
    attribute: "dbsql_warehouse_size",
    label: "Warehouse Size",
    inputType: "dropdown",
    category: "compute"
  },

  // Serverless fields
  serverless_product: {
    attribute: "serverless_product",
    label: "Serverless Product",
    inputType: "dropdown",
    category: "compute"
  },
  serverless_size: {
    attribute: "serverless_size",
    label: "Serverless Size",
    inputType: "dropdown",
    category: "compute"
  },

  // FMAPI fields
  fmapi_provider: {
    attribute: "fmapi_provider",
    label: "Provider",
    inputType: "dropdown",
    category: "configuration"
  },
  fmapi_model: {
    attribute: "fmapi_model",
    label: "Model",
    inputType: "dropdown",
    category: "configuration"
  },
  fmapi_endpoint_type: {
    attribute: "fmapi_endpoint_type",
    label: "Endpoint Type",
    inputType: "dropdown",
    category: "configuration"
  },
  fmapi_context_length: {
    attribute: "fmapi_context_length",
    label: "Context Length",
    inputType: "text",
    category: "configuration"
  },
  fmapi_input_tokens_per_month: {
    attribute: "fmapi_input_tokens_per_month",
    label: "Input Tokens/Month",
    inputType: "text",
    category: "scheduling"
  },
  fmapi_output_tokens_per_month: {
    attribute: "fmapi_output_tokens_per_month",
    label: "Output Tokens/Month",
    inputType: "text",
    category: "scheduling"
  },

  // Scheduling fields
  hours_per_day: {
    attribute: "hours_per_day",
    label: "Hours per Day",
    inputType: "text",
    category: "scheduling"
  },
  days_per_month: {
    attribute: "days_per_month",
    label: "Days per Month",
    inputType: "text",
    category: "scheduling"
  },
  runs_per_day: {
    attribute: "runs_per_day",
    label: "Runs per Day",
    inputType: "text",
    category: "scheduling"
  },
  avg_runtime_minutes: {
    attribute: "avg_runtime_minutes",
    label: "Avg Runtime (mins)",
    inputType: "text",
    category: "scheduling"
  },

  // Pricing fields
  vm_pricing_tier: {
    attribute: "vm_pricing_tier",
    label: "Pricing Tier",
    inputType: "dropdown",
    category: "pricing"
  },
  vm_payment_option: {
    attribute: "vm_payment_option",
    label: "Payment Option",
    inputType: "dropdown",
    category: "pricing"
  },
  spot_percentage: {
    attribute: "spot_percentage",
    label: "Spot %",
    inputType: "text",
    category: "pricing"
  },

  // Metadata fields
  workload_config: {
    attribute: "workload_config",
    label: "Workload Config",
    inputType: "text",
    category: "metadata"
  },
  user_input: {
    attribute: "user_input",
    label: "User Input",
    inputType: "text",
    category: "metadata"
  },
  agent_response: {
    attribute: "agent_response",
    label: "Agent Response",
    inputType: "text",
    category: "metadata"
  }
};

// Define which fields are relevant for each workload type
// Based on the screenshot mapping
export const workloadFieldMapping: Record<WorkloadType, string[]> = {
  ALL_PURPOSE: [
    "driver_node_type",
    "worker_node_type",
    "photon_enabled",
    "hours_per_day"
  ],
  JOBS_CLASSIC: [
    "driver_node_type",
    "worker_node_type",
    "photon_enabled",
    "runs_per_day",
    "avg_runtime_minutes"
  ],
  JOBS_SERVERLESS: [
    "runs_per_day",
    "avg_runtime_minutes"
  ],
  DLT: [
    "driver_node_type",
    "worker_node_type",
    "photon_enabled",
    "dlt_edition",
    "hours_per_day"
  ],
  DBSQL: [
    "dbsql_warehouse_type",
    "dbsql_warehouse_size",
    "hours_per_day"
  ],
  VECTOR_SEARCH: [
    "serverless_size",
    "hours_per_day"
  ],
  MODEL_SERVING: [
    "serverless_size",
    "hours_per_day"
  ],
  FMAPI_DATABRICKS: [
    "fmapi_model",
    "fmapi_input_tokens_per_month",
    "fmapi_output_tokens_per_month"
  ],
  FMAPI_PROPRIETARY: [
    "fmapi_provider",
    "fmapi_model",
    "fmapi_input_tokens_per_month",
    "fmapi_output_tokens_per_month"
  ]
};

// Helper function to get relevant fields for a workload type
export function getRelevantFields(workloadType: WorkloadType): FieldMapping[] {
  const fieldNames = workloadFieldMapping[workloadType] || [];
  return fieldNames
    .map(name => fieldDefinitions[name])
    .filter(Boolean);
}

// Helper function to filter table structure by workload type
export function filterTableByWorkloadType(
  tableStructure: any[],
  workloadType: WorkloadType
): any[] {
  const relevantFields = workloadFieldMapping[workloadType] || [];

  return tableStructure.filter(item => {
    // Always include workload_type
    if (item.attribute === "workload_type") return true;

    // Include if in relevant fields
    if (relevantFields.includes(item.attribute)) return true;

    // Exclude hidden fields
    if (item.hidden === true) return false;

    return false;
  });
}
