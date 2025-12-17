"use client";

import React, { useState, useEffect } from "react";
import {
  workloadOptions,
  dltEditionOptions,
  dltPipelineModeOptions,
  warehouseTypeOptions,
  warehouseSizeOptions,
  serverlessSizeOptions,
  fmapiProviderOptions,
  fmapiModelOptions,
  fmapiEndpointTypeOptions,
  pricingTierOptions,
  paymentOptionOptions,
} from "@/lib/dropdown-options";
import Header from "@/components/Header";
import { Check, ChevronDown, Info, Layers } from "lucide-react";

interface TableRow {
  attribute: string;
  inputType: string;
  defaultValue: any;
  hidden?: boolean;
}

interface TableDataRow {
  [key: string]: any;
  user_input?: string;
  agent_response?: string;
}

interface TableData {
  workloadType: string;
  columns: TableRow[];
  dataRows: TableDataRow[];
}

export default function Home() {
  // State for the prompt path input
  const [promptPath, setPromptPath] = useState("prompts:/users.fajar_muharandy.lakemeter/1");

  // State for available prompt options
  const [promptOptions, setPromptOptions] = useState<string[]>([]);
  const [isLoadingPrompts, setIsLoadingPrompts] = useState(false);

  // State for prompt version
  const [promptVersion, setPromptVersion] = useState("1");

  // State for the large text input
  const [promptText, setPromptText] = useState("");

  // Loading state for API call
  const [isLoading, setIsLoading] = useState(false);

  // State to store the last LLM response for debugging
  const [lastLLMResponse, setLastLLMResponse] = useState<string>("");
  const [lastStopReason, setLastStopReason] = useState<string>("");

  // State to store parsed table data
  const [tableData, setTableData] = useState<TableData[]>([]);

  // State to track which tables are expanded
  const [expandedTables, setExpandedTables] = useState<Set<string>>(new Set());

  // State to track which rows are expanded (format: "workloadType-rowIndex")
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

  // State for agent selection
  const [selectedAgent, setSelectedAgent] = useState<string>("Knowledge Assistant Agent");
  const [openaiModel, setOpenaiModel] = useState<string>("ka-5cb2e157-endpoint");
  const [useResponsesApi, setUseResponsesApi] = useState<boolean>(true);

  // State for prompt configuration accordion
  const [isPromptConfigExpanded, setIsPromptConfigExpanded] = useState<boolean>(true);

  // Fetch available prompts on component mount
  useEffect(() => {
    const fetchPrompts = async () => {
      setIsLoadingPrompts(true);
      try {
        const response = await fetch('/api/prompts', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            action: 'search',
            catalog: 'users',
            schema: 'fajar_muharandy',
          }),
        });

        const result = await response.json();

        if (result.success && result.data && Array.isArray(result.data)) {
          const paths = result.data.map((prompt: any) => prompt.path);
          setPromptOptions(paths);

          // Set the first prompt as default if available and current is default
          if (paths.length > 0 && promptPath === "prompts:/users.fajar_muharandy.lakemeter/1") {
            setPromptPath(paths[0]);
          }
        }
      } catch (error) {
        console.error('Error fetching prompts:', error);
      } finally {
        setIsLoadingPrompts(false);
      }
    };

    fetchPrompts();
  }, []);

  const handleSubmit = async () => {
    setIsLoading(true);

    try {
      // Call Python backend API if prompt text exists
      if (promptText.trim()) {
        // Combine prompt path with version
        const fullPromptPath = promptVersion.trim()
          ? `${promptPath}/${promptVersion.trim()}`
          : promptPath;

        const response = await fetch('/api/llm', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            prompt_text: promptText,
            prompt_path: fullPromptPath,
            openai_model: openaiModel,
            use_responses_api: useResponsesApi,
          }),
        });

        const result = await response.json();

        if (result.success && result.data) {
          // Store the original response for debugging
          setLastLLMResponse(JSON.stringify(result.data, null, 2));
          setLastStopReason(result.debug?.finish_reason || "");

          // Parse table structure from response
          if (result.data.tableStructure && Array.isArray(result.data.tableStructure)) {
            parseTableStructure(result.data.tableStructure);
          }
        } else {
          console.error("Error from API:", result.error);
          setLastLLMResponse(result.raw_response || result.error || "Unknown error");
          setLastStopReason("error");
        }
      }
    } catch (error) {
      console.error("Error calling Python backend:", error);
      setLastLLMResponse(error instanceof Error ? error.message : "Unknown error");
      setLastStopReason("error");
    } finally {
      setIsLoading(false);
    }
  };

  // Helper function to parse table structure and group by workload type
  const parseTableStructure = (tableStructure: TableRow[]) => {
    // Find the workload type from the table
    const workloadTypeRow = tableStructure.find(row => row.attribute === "workload_type");
    const workloadType = workloadTypeRow?.defaultValue || "JOBS_CLASSIC";

    // Filter rows based on workload type and field mappings (for column definitions)
    const filteredColumns = filterRowsByWorkloadType(tableStructure, workloadType);

    // Create a data row from ALL attributes (not just filtered ones)
    const dataRow: TableDataRow = {};
    tableStructure.forEach(col => {
      // Skip hidden fields for now, we'll handle them separately
      if (col.hidden) return;

      dataRow[col.attribute] = {
        value: col.defaultValue,
        inputType: col.inputType
      };
    });

    // Capture user_input and agent_response from the table structure
    const userInputRow = tableStructure.find(row => row.attribute === "user_input");
    const agentResponseRow = tableStructure.find(row => row.attribute === "agent_response");

    if (userInputRow) {
      dataRow.user_input = userInputRow.defaultValue;
    }
    if (agentResponseRow) {
      dataRow.agent_response = agentResponseRow.defaultValue;
    }

    // Find existing table for this workload type or create new one
    setTableData(prevData => {
      const existingTableIndex = prevData.findIndex(t => t.workloadType === workloadType);

      if (existingTableIndex >= 0) {
        // Add new row to existing table, preserving columns
        const updatedData = [...prevData];
        const existingTable = updatedData[existingTableIndex];
        updatedData[existingTableIndex] = {
          workloadType: existingTable.workloadType,
          columns: existingTable.columns, // Preserve existing columns
          dataRows: [...existingTable.dataRows, dataRow]
        };
        return updatedData;
      } else {
        // Create new table for this workload type
        return [...prevData, {
          workloadType,
          columns: filteredColumns,
          dataRows: [dataRow]
        }];
      }
    });

    // Auto-expand the table when new data is added
    setExpandedTables(prev => {
      const newSet = new Set(prev);
      newSet.add(workloadType);
      return newSet;
    });
  };

  // Helper function to determine which fields to show based on workload type
  const filterRowsByWorkloadType = (rows: TableRow[], workloadType: string): TableRow[] => {
    // Define field mappings based on required attributes
    const fieldMappings: Record<string, string[]> = {
      ALL_PURPOSE: ["workload_type", "serverless_enabled", "photon_enabled", "driver_node_type", "worker_node_type", "num_workers", "hours_per_day", "days_per_month"],
      JOBS_CLASSIC: ["workload_type", "serverless_enabled", "photon_enabled", "driver_node_type", "worker_node_type", "num_workers", "runs_per_day", "avg_runtime_minutes", "vm_pricing_tier"],
      JOBS_SERVERLESS: ["workload_type", "serverless_enabled", "photon_enabled", "driver_node_type", "worker_node_type", "num_workers", "runs_per_day", "avg_runtime_minutes"],
      DLT: ["workload_type", "serverless_enabled", "photon_enabled", "dlt_edition", "dlt_pipeline_mode", "driver_node_type", "worker_node_type", "num_workers", "hours_per_day", "vm_pricing_tier", "vm_payment_option"],
      DBSQL: ["workload_type", "dbsql_warehouse_type", "dbsql_warehouse_size", "hours_per_day", "days_per_month"],
      VECTOR_SEARCH: ["workload_type", "serverless_size", "hours_per_day"],
      MODEL_SERVING: ["workload_type", "serverless_size", "hours_per_day"],
      FMAPI_DATABRICKS: ["workload_type", "fmapi_provider", "fmapi_model", "fmapi_endpoint_type", "fmapi_context_length", "fmapi_input_tokens_per_month", "fmapi_output_tokens_per_month"],
      FMAPI_PROPRIETARY: ["workload_type", "fmapi_provider", "fmapi_model", "fmapi_endpoint_type", "fmapi_context_length", "fmapi_input_tokens_per_month", "fmapi_output_tokens_per_month"],
    };

    const relevantFields = fieldMappings[workloadType] || [];

    return rows.filter(row => {
      // Always exclude hidden fields
      if (row.hidden) return false;

      // Include if in relevant fields for this workload type
      return relevantFields.includes(row.attribute);
    });
  };

  // Helper function to get dropdown options for a field
  const getDropdownOptions = (attribute: string) => {
    const optionsMap: Record<string, any[]> = {
      workload_type: workloadOptions,
      dlt_edition: dltEditionOptions,
      dlt_pipeline_mode: dltPipelineModeOptions,
      dbsql_warehouse_type: warehouseTypeOptions,
      dbsql_warehouse_size: warehouseSizeOptions,
      serverless_size: serverlessSizeOptions,
      fmapi_provider: fmapiProviderOptions,
      fmapi_model: fmapiModelOptions,
      fmapi_endpoint_type: fmapiEndpointTypeOptions,
      vm_pricing_tier: pricingTierOptions,
      vm_payment_option: paymentOptionOptions,
    };

    return optionsMap[attribute] || [];
  };

  // Helper function to format attribute names to readable labels
  const formatLabel = (attribute: string): string => {
    const labelMap: Record<string, string> = {
      workload_type: "Workload Type",
      serverless_enabled: "Serverless",
      photon_enabled: "Photon",
      driver_node_type: "Driver",
      worker_node_type: "Workers",
      num_workers: "# Workers",
      hours_per_day: "Hours per Day",
      days_per_month: "Days per Month",
      runs_per_day: "Runs per Day",
      avg_runtime_minutes: "Avg Runtime",
      vm_pricing_tier: "VM Pricing Tier",
      vm_payment_option: "VM Payment Option",
      dlt_edition: "DLT Edition",
      dlt_pipeline_mode: "Pipeline Mode",
      dbsql_warehouse_type: "Warehouse Type",
      dbsql_warehouse_size: "Warehouse Size",
      serverless_size: "Serverless Size",
      fmapi_provider: "FMAPI Provider",
      fmapi_model: "FMAPI Model",
      fmapi_endpoint_type: "Endpoint Type",
      fmapi_context_length: "Context Length",
      fmapi_input_tokens_per_month: "Input Tokens",
      fmapi_output_tokens_per_month: "Output Tokens",
    };

    return labelMap[attribute] || attribute.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  // Helper function to get all workload types with their column definitions
  const getAllWorkloadTypeDefinitions = (): TableData[] => {
    const allWorkloadTypes: string[] = [
      "ALL_PURPOSE",
      "JOBS_CLASSIC",
      "JOBS_SERVERLESS",
      "DLT",
      "DBSQL",
      "VECTOR_SEARCH",
      "MODEL_SERVING",
      "FMAPI_DATABRICKS",
      "FMAPI_PROPRIETARY"
    ];

    const tables = allWorkloadTypes.map(workloadType => {
      // Create dummy columns to get the field mapping
      const fieldMappings: Record<string, string[]> = {
        ALL_PURPOSE: ["workload_type", "serverless_enabled", "photon_enabled", "driver_node_type", "worker_node_type", "num_workers", "hours_per_day", "days_per_month"],
        JOBS_CLASSIC: ["workload_type", "serverless_enabled", "photon_enabled", "driver_node_type", "worker_node_type", "num_workers", "runs_per_day", "avg_runtime_minutes", "vm_pricing_tier"],
        JOBS_SERVERLESS: ["workload_type", "serverless_enabled", "photon_enabled", "driver_node_type", "worker_node_type", "num_workers", "runs_per_day", "avg_runtime_minutes"],
        DLT: ["workload_type", "serverless_enabled", "photon_enabled", "dlt_edition", "dlt_pipeline_mode", "driver_node_type", "worker_node_type", "num_workers", "hours_per_day", "vm_pricing_tier", "vm_payment_option"],
        DBSQL: ["workload_type", "dbsql_warehouse_type", "dbsql_warehouse_size", "hours_per_day", "days_per_month"],
        VECTOR_SEARCH: ["workload_type", "serverless_size", "hours_per_day"],
        MODEL_SERVING: ["workload_type", "serverless_size", "hours_per_day"],
        FMAPI_DATABRICKS: ["workload_type", "fmapi_provider", "fmapi_model", "fmapi_endpoint_type", "fmapi_context_length", "fmapi_input_tokens_per_month", "fmapi_output_tokens_per_month"],
        FMAPI_PROPRIETARY: ["workload_type", "fmapi_provider", "fmapi_model", "fmapi_endpoint_type", "fmapi_context_length", "fmapi_input_tokens_per_month", "fmapi_output_tokens_per_month"],
      };

      const columns: TableRow[] = (fieldMappings[workloadType] || []).map(attr => ({
        attribute: attr,
        inputType: attr === "photon_enabled" || attr === "serverless_enabled" ? "checkbox" :
                   attr === "driver_node_type" || attr === "worker_node_type" ? "text" :
                   attr.includes("token") || attr.includes("runtime") || attr.includes("hours") ||
                   attr.includes("runs") || attr === "num_workers" || attr === "days_per_month" ||
                   attr === "fmapi_context_length" ? "text" : "dropdown",
        defaultValue: ""
      }));

      // Find existing data for this workload type
      const existingTable = tableData.find(t => t.workloadType === workloadType);

      return {
        workloadType,
        columns,
        dataRows: existingTable?.dataRows || []
      };
    });

    // Sort: tables with data first, then empty tables
    return tables.sort((a, b) => {
      const aHasData = a.dataRows.length > 0;
      const bHasData = b.dataRows.length > 0;

      if (aHasData && !bHasData) return -1;
      if (!aHasData && bHasData) return 1;
      return 0;
    });
  };

  // Toggle table expansion
  const toggleTable = (workloadType: string) => {
    setExpandedTables(prev => {
      const newSet = new Set(prev);
      if (newSet.has(workloadType)) {
        newSet.delete(workloadType);
      } else {
        newSet.add(workloadType);
      }
      return newSet;
    });
  };

  // Toggle row expansion
  const toggleRow = (workloadType: string, rowIndex: number) => {
    const rowKey = `${workloadType}-${rowIndex}`;
    setExpandedRows(prev => {
      const newSet = new Set(prev);
      if (newSet.has(rowKey)) {
        newSet.delete(rowKey);
      } else {
        newSet.add(rowKey);
      }
      return newSet;
    });
  };

  return (
    <div className="min-h-screen bg-[#F9FAFB]">
      <Header />

      {/* Main Content */}
      <div className="p-6">
        {/* Two Column Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Workloads */}
          <div className="lg:col-span-2 space-y-6">
            {/* Workloads Section */}
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Layers className="h-4 w-4 text-gray-400" />
                  <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">Workloads</h2>
                  <span className="text-xs text-gray-500">({tableData.reduce((sum, t) => sum + t.dataRows.length, 0)})</span>
                </div>
              </div>

              <div className="space-y-3">
                {getAllWorkloadTypeDefinitions().map((table) => {
                  const hasData = table.dataRows && table.dataRows.length > 0;
                  const isExpanded = expandedTables.has(table.workloadType);

                  if (!hasData) return null;

                  return (
                    <div key={table.workloadType} className="border border-gray-200 rounded-lg overflow-hidden">
                      <button
                        onClick={() => toggleTable(table.workloadType)}
                        className="w-full px-4 py-3 bg-gray-50 hover:bg-gray-100 flex items-center justify-between transition-colors"
                      >
                        <div className="flex items-center gap-3">
                          <Layers className="h-4 w-4 text-gray-500" />
                          <span className="text-sm font-medium text-gray-900">
                            {workloadOptions.find(opt => opt.value === table.workloadType)?.label || table.workloadType}
                          </span>
                          <span className="text-xs text-gray-500">
                            ({table.dataRows.length} item{table.dataRows.length !== 1 ? 's' : ''})
                          </span>
                        </div>
                        <div className="flex items-center gap-3">
                          <ChevronDown className={`h-4 w-4 text-gray-500 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
                        </div>
                      </button>

                      {isExpanded && (
                        <div className="p-4 bg-white border-t border-gray-200">
                          {table.dataRows.map((row, rowIndex) => {
                            // Define required attributes per workload type
                            const requiredAttributesMap: Record<string, string[]> = {
                              ALL_PURPOSE: ["serverless_enabled", "photon_enabled", "driver_node_type", "worker_node_type", "num_workers", "runs_per_day", "avg_runtime_minutes", "days_per_month", "vm_pricing_tier", "vm_payment_option", "spot_percentage"],
                              JOBS_CLASSIC: ["serverless_enabled", "photon_enabled", "driver_node_type", "worker_node_type", "num_workers", "runs_per_day", "avg_runtime_minutes", "days_per_month", "vm_pricing_tier"],
                              JOBS_SERVERLESS: ["serverless_enabled", "photon_enabled", "driver_node_type", "worker_node_type", "num_workers", "runs_per_day", "avg_runtime_minutes"],
                              DLT: ["serverless_enabled", "photon_enabled", "dlt_edition", "dlt_pipeline_mode", "driver_node_type", "worker_node_type", "num_workers", "runs_per_day", "avg_runtime_minutes", "days_per_month", "vm_pricing_tier"],
                              DBSQL: ["dbsql_warehouse_type", "dbsql_warehouse_size", "dbsql_num_clusters", "runs_per_day", "avg_runtime_minutes", "days_per_month"],
                              VECTOR_SEARCH: ["serverless_product", "serverless_size", "runs_per_day", "avg_runtime_minutes", "days_per_month"],
                              MODEL_SERVING: ["serverless_product", "serverless_size", "runs_per_day", "avg_runtime_minutes", "days_per_month"],
                              FMAPI_DATABRICKS: ["fmapi_model", "fmapi_input_tokens_per_month", "fmapi_output_tokens_per_month"],
                              FMAPI_PROPRIETARY: ["fmapi_provider", "fmapi_model", "fmapi_endpoint_type", "fmapi_context_length", "fmapi_input_tokens_per_month", "fmapi_output_tokens_per_month"],
                            };

                            const requiredAttributes = requiredAttributesMap[table.workloadType] || [];
                            const attributes: { label: string; value: string }[] = [];

                            // Iterate through required attributes for this workload type
                            requiredAttributes.forEach(key => {
                              const cellData = row[key];
                              // Get value from cellData.value if it exists
                              const value = cellData?.value !== undefined ? cellData.value : null;

                              // Check if value exists and is not empty string
                              if (value !== undefined && value !== null && value !== "" && value !== false) {
                                attributes.push({
                                  label: formatLabel(key),
                                  value: typeof value === 'boolean' ? (value ? 'Yes' : 'No') : String(value)
                                });
                              }
                            });

                            // Check if we have user_input or agent_response
                            const hasAccordionData = row.user_input || row.agent_response;
                            const rowKey = `${table.workloadType}-${rowIndex}`;
                            const isRowExpanded = expandedRows.has(rowKey);

                            return (
                              <div key={rowIndex} className={`${rowIndex > 0 ? 'mt-4 pt-4 border-t border-gray-100' : ''}`}>
                                <div className="space-y-2">
                                  {attributes.map((attr, attrIndex) => (
                                    <div key={attrIndex} className="flex items-center justify-between text-xs">
                                      <span className="text-gray-600">{attr.label}:</span>
                                      <span className="font-medium text-gray-900">{attr.value}</span>
                                    </div>
                                  ))}
                                  {attributes.length === 0 && (
                                    <div className="text-xs text-gray-500 italic">No configuration data</div>
                                  )}
                                </div>

                                {/* Accordion for user_input and agent_response */}
                                {hasAccordionData && (
                                  <div className="mt-3">
                                    <button
                                      onClick={() => toggleRow(table.workloadType, rowIndex)}
                                      className="flex items-center gap-2 text-xs text-[#FF5F1F] hover:text-[#E54E0F] font-medium transition-colors"
                                    >
                                      <ChevronDown className={`h-3 w-3 transition-transform ${isRowExpanded ? 'rotate-180' : ''}`} />
                                      <span>{isRowExpanded ? 'Hide Details' : 'Show Details'}</span>
                                    </button>

                                    {isRowExpanded && (
                                      <div className="mt-3 space-y-3 pl-5 border-l-2 border-gray-200">
                                        {row.user_input && (
                                          <div>
                                            <h5 className="text-xs font-semibold text-gray-700 mb-1">User Input:</h5>
                                            <p className="text-xs text-gray-600 leading-relaxed">{row.user_input}</p>
                                          </div>
                                        )}
                                        {row.agent_response && (
                                          <div>
                                            <h5 className="text-xs font-semibold text-gray-700 mb-1">Agent Response:</h5>
                                            <p className="text-xs text-gray-600 leading-relaxed">{row.agent_response}</p>
                                          </div>
                                        )}
                                      </div>
                                    )}
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Right Column - Configuration & Prompt */}
          <div className="lg:col-span-1 space-y-6">
            {/* Cloud Provider Configuration */}
            <div className="bg-white rounded-lg border border-gray-200 overflow-hidden sticky top-24">
              <button
                onClick={() => setIsPromptConfigExpanded(!isPromptConfigExpanded)}
                className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <Info className="h-4 w-4 text-gray-400" />
                  <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">Prompt Configuration</h2>
                </div>
                <ChevronDown className={`h-4 w-4 text-gray-500 transition-transform ${isPromptConfigExpanded ? 'rotate-180' : ''}`} />
              </button>

              {isPromptConfigExpanded && (
                <div className="px-6 pb-6 space-y-4 border-t border-gray-200 pt-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-3">Select Agent</label>
                  <div className="grid grid-cols-3 gap-2">
                    {[
                      { name: "Knowledge Assistant Agent", line1: "Knowledge", line2: "Assistant", model: "ka-5cb2e157-endpoint", useResponses: true },
                      { name: "System Prompt Agent", line1: "System", line2: "Prompt", model: "databricks-gpt-5-1", useResponses: false },
                      { name: "Tools Calling Agent", line1: "Tools", line2: "Calling", model: "mas-3096a75e-endpoint", useResponses: true }
                    ].map((agent) => (
                      <button
                        key={agent.name}
                        onClick={() => {
                          setSelectedAgent(agent.name);
                          setOpenaiModel(agent.model);
                          setUseResponsesApi(agent.useResponses);
                        }}
                        className={`relative py-3 px-2 border-2 rounded-lg font-semibold text-xs transition-all text-center ${
                          selectedAgent === agent.name
                            ? "border-[#FF5F1F] bg-[#FEF3EE] text-[#FF5F1F]"
                            : "border-gray-200 bg-white text-gray-700 hover:border-gray-300"
                        }`}
                      >
                        {selectedAgent === agent.name && (
                          <Check className="absolute top-1 right-1 h-3 w-3 text-[#FF5F1F]" />
                        )}
                        <div className="flex flex-col items-center leading-tight">
                          <span>{agent.line1}</span>
                          <span>{agent.line2}</span>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label htmlFor="promptPath" className="block text-sm font-medium text-gray-700 mb-2">
                    Prompt Path
                  </label>
                  <select
                    id="promptPath"
                    value={promptPath}
                    onChange={(e) => setPromptPath(e.target.value)}
                    disabled={isLoadingPrompts}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#FF5F1F] focus:border-[#FF5F1F] bg-white disabled:bg-gray-100 disabled:cursor-not-allowed appearance-none"
                  >
                    {isLoadingPrompts ? (
                      <option value="">Loading prompts...</option>
                    ) : promptOptions.length > 0 ? (
                      promptOptions.map((path) => (
                        <option key={path} value={path}>
                          {path}
                        </option>
                      ))
                    ) : (
                      <option value="">No prompts available</option>
                    )}
                  </select>
                </div>

                <div>
                  <label htmlFor="promptVersion" className="block text-sm font-medium text-gray-700 mb-2">
                    Prompt Version
                  </label>
                  <input
                    id="promptVersion"
                    type="text"
                    value={promptVersion}
                    onChange={(e) => setPromptVersion(e.target.value)}
                    placeholder="1"
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#FF5F1F] focus:border-[#FF5F1F] bg-white"
                  />
                </div>
                </div>
              )}
            </div>

            {/* Workload Description */}
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <div className="flex items-center gap-2 mb-6">
                <Info className="h-4 w-4 text-gray-400" />
                <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">Workload Description</h2>
              </div>

              <div className="space-y-4">
                <div>
                  <label htmlFor="prompt" className="block text-sm font-medium text-gray-700 mb-2">
                    Enter Your Prompt
                  </label>
                  <textarea
                    id="prompt"
                    value={promptText}
                    onChange={(e) => setPromptText(e.target.value)}
                    placeholder="Type your prompt here..."
                    className="w-full min-h-[200px] px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#FF5F1F] focus:border-[#FF5F1F] bg-white resize-y"
                    rows={8}
                  />
                </div>

                <button
                  onClick={handleSubmit}
                  disabled={isLoading}
                  className="w-full px-4 py-2 text-sm font-medium text-white bg-[#FF5F1F] hover:bg-[#E54E0F] disabled:bg-gray-400 disabled:cursor-not-allowed rounded-lg transition-colors"
                >
                  {isLoading ? "Processing..." : "Submit"}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Debug Section */}
        {lastLLMResponse && (
          <div className="mt-6 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <h2 className="text-sm font-semibold text-gray-900 mb-2">
              Debug: Last LLM Response
            </h2>
            <div className="text-xs text-gray-700 space-y-2">
              <div>
                <p className="font-semibold mb-1">Stop Reason: <span className="font-normal">{lastStopReason || "N/A"}</span></p>
              </div>
              <div>
                <p className="font-semibold mb-1">Response:</p>
                <pre className="p-2 bg-white rounded overflow-auto text-xs whitespace-pre-wrap max-h-60">
                  {lastLLMResponse}
                </pre>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
