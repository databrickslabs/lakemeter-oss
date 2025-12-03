"use client";

import { useState, useEffect } from "react";
import {
  workloadOptions,
  dltEditionOptions,
  warehouseTypeOptions,
  warehouseSizeOptions,
  serverlessSizeOptions,
  fmapiProviderOptions,
  fmapiModelOptions,
  pricingTierOptions,
  paymentOptionOptions,
} from "@/lib/dropdown-options";

interface TableRow {
  attribute: string;
  inputType: string;
  defaultValue: any;
  hidden?: boolean;
}

interface TableDataRow {
  [key: string]: any;
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

    // Filter rows based on workload type and field mappings
    const filteredColumns = filterRowsByWorkloadType(tableStructure, workloadType);

    // Create a data row from the filtered columns
    const dataRow: TableDataRow = {};
    filteredColumns.forEach(col => {
      dataRow[col.attribute] = {
        value: col.defaultValue,
        inputType: col.inputType
      };
    });

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
    // Define field mappings based on screenshot
    const fieldMappings: Record<string, string[]> = {
      ALL_PURPOSE: ["workload_type", "driver_node_type", "worker_node_type", "photon_enabled", "hours_per_day"],
      JOBS_CLASSIC: ["workload_type", "driver_node_type", "worker_node_type", "photon_enabled", "runs_per_day", "avg_runtime_minutes"],
      JOBS_SERVERLESS: ["workload_type", "runs_per_day", "avg_runtime_minutes"],
      DLT: ["workload_type", "driver_node_type", "worker_node_type", "photon_enabled", "dlt_edition", "hours_per_day"],
      DBSQL: ["workload_type", "dbsql_warehouse_type", "dbsql_warehouse_size", "hours_per_day"],
      VECTOR_SEARCH: ["workload_type", "serverless_size", "hours_per_day"],
      MODEL_SERVING: ["workload_type", "serverless_size", "hours_per_day"],
      FMAPI_DATABRICKS: ["workload_type", "fmapi_model", "fmapi_input_tokens_per_month", "fmapi_output_tokens_per_month"],
      FMAPI_PROPRIETARY: ["workload_type", "fmapi_provider", "fmapi_model", "fmapi_input_tokens_per_month", "fmapi_output_tokens_per_month"],
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
      dbsql_warehouse_type: warehouseTypeOptions,
      dbsql_warehouse_size: warehouseSizeOptions,
      serverless_size: serverlessSizeOptions,
      fmapi_provider: fmapiProviderOptions,
      fmapi_model: fmapiModelOptions,
      vm_pricing_tier: pricingTierOptions,
      vm_payment_option: paymentOptionOptions,
    };

    return optionsMap[attribute] || [];
  };

  // Helper function to format attribute names to readable labels
  const formatLabel = (attribute: string): string => {
    const labelMap: Record<string, string> = {
      workload_type: "Workload Type",
      driver_node_type: "Driver",
      worker_node_type: "Workers",
      photon_enabled: "Photon",
      hours_per_day: "Hours per Day",
      runs_per_day: "Runs per Day",
      avg_runtime_minutes: "Avg Runtime",
      dlt_edition: "DLT Edition",
      dbsql_warehouse_type: "Warehouse Type",
      dbsql_warehouse_size: "Warehouse Size",
      serverless_size: "Serverless Size",
      fmapi_provider: "FMAPI Provider",
      fmapi_model: "FMAPI Model",
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
        ALL_PURPOSE: ["workload_type", "driver_node_type", "worker_node_type", "photon_enabled", "hours_per_day"],
        JOBS_CLASSIC: ["workload_type", "driver_node_type", "worker_node_type", "photon_enabled", "runs_per_day", "avg_runtime_minutes"],
        JOBS_SERVERLESS: ["workload_type", "runs_per_day", "avg_runtime_minutes"],
        DLT: ["workload_type", "driver_node_type", "worker_node_type", "photon_enabled", "dlt_edition", "hours_per_day"],
        DBSQL: ["workload_type", "dbsql_warehouse_type", "dbsql_warehouse_size", "hours_per_day"],
        VECTOR_SEARCH: ["workload_type", "serverless_size", "hours_per_day"],
        MODEL_SERVING: ["workload_type", "serverless_size", "hours_per_day"],
        FMAPI_DATABRICKS: ["workload_type", "fmapi_model", "fmapi_input_tokens_per_month", "fmapi_output_tokens_per_month"],
        FMAPI_PROPRIETARY: ["workload_type", "fmapi_provider", "fmapi_model", "fmapi_input_tokens_per_month", "fmapi_output_tokens_per_month"],
      };

      const columns: TableRow[] = (fieldMappings[workloadType] || []).map(attr => ({
        attribute: attr,
        inputType: attr === "photon_enabled" ? "checkbox" :
                   attr === "driver_node_type" || attr === "worker_node_type" ? "text" :
                   attr.includes("token") || attr.includes("runtime") || attr.includes("hours") || attr.includes("runs") ? "text" : "dropdown",
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

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 p-8">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-100 mb-8">
          Prompt Input & Data Table
        </h1>

        {/* Prompt Path Dropdown Field */}
        <div className="mb-6">
          <label htmlFor="promptPath" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Prompt Path
          </label>
          <select
            id="promptPath"
            value={promptPath}
            onChange={(e) => setPromptPath(e.target.value)}
            disabled={isLoadingPrompts}
            className="w-full p-3 text-base border-2 border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:text-gray-100 transition-all disabled:bg-gray-100 disabled:cursor-not-allowed"
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

        {/* Prompt Version Input Field */}
        <div className="mb-6">
          <label htmlFor="promptVersion" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Prompt Version
          </label>
          <input
            id="promptVersion"
            type="text"
            value={promptVersion}
            onChange={(e) => setPromptVersion(e.target.value)}
            placeholder="1"
            className="w-full p-3 text-base border-2 border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:text-gray-100 transition-all"
          />
        </div>

        {/* Large Text Input Field */}
        <div className="mb-8">
          <label htmlFor="prompt" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Enter Your Prompt
          </label>
          <textarea
            id="prompt"
            value={promptText}
            onChange={(e) => setPromptText(e.target.value)}
            placeholder="Type your prompt here..."
            className="w-full min-h-[200px] p-4 text-base border-2 border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:text-gray-100 resize-y transition-all"
            rows={8}
          />
          <button
            onClick={handleSubmit}
            disabled={isLoading}
            className="mt-4 px-6 py-2 text-base font-medium text-white bg-green-600 hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed rounded-lg transition-colors shadow-md hover:shadow-lg"
          >
            {isLoading ? "Processing..." : "Submit"}
          </button>
        </div>

        {/* Render Tables by Workload Type */}
        <div className="mt-8 space-y-4">
          <h2 className="text-2xl font-bold text-gray-800 dark:text-gray-100 mb-4">
            Configuration Tables
          </h2>
          {getAllWorkloadTypeDefinitions().map((table, tableIndex) => {
            // Safety check: skip tables with invalid structure
            if (!table.columns || !Array.isArray(table.columns)) {
              return null;
            }

            const hasData = table.dataRows && table.dataRows.length > 0;
            const isExpanded = expandedTables.has(table.workloadType);

            return (
              <div
                key={table.workloadType}
                className="bg-white dark:bg-gray-800 rounded-lg shadow-lg overflow-hidden transition-all duration-500 ease-in-out"
                style={{
                  animation: hasData ? 'slideIn 0.5s ease-out' : 'none'
                }}
              >
                <div
                  className={`px-6 py-3 flex justify-between items-center cursor-pointer ${
                    hasData ? 'bg-blue-600 dark:bg-blue-700 hover:bg-blue-700 dark:hover:bg-blue-800' : 'bg-gray-400 dark:bg-gray-600'
                  }`}
                  onClick={() => hasData && toggleTable(table.workloadType)}
                >
                  <h3 className="text-xl font-semibold text-white">
                    {workloadOptions.find(opt => opt.value === table.workloadType)?.label || table.workloadType}
                    {hasData && <span className="ml-2 text-sm">({table.dataRows.length} row{table.dataRows.length !== 1 ? 's' : ''})</span>}
                  </h3>
                  {hasData && (
                    <svg
                      className={`w-6 h-6 text-white transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  )}
                </div>

                <div
                  className={`overflow-hidden transition-all duration-300 ease-in-out ${
                    hasData && isExpanded ? 'max-h-[2000px] opacity-100' : 'max-h-0 opacity-0'
                  }`}
                >
                  {hasData && (
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead>
                          <tr className="bg-gray-100 dark:bg-gray-700">
                            {table.columns.map((col, colIndex) => (
                              <th key={colIndex} className="px-4 py-3 text-left text-xs font-medium text-gray-600 dark:text-gray-300 uppercase tracking-wider whitespace-nowrap">
                                {formatLabel(col.attribute)}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {table.dataRows.map((dataRow, rowIndex) => (
                            <tr key={rowIndex} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                              {table.columns.map((col, colIndex) => {
                                const cellData = dataRow[col.attribute];
                                const value = cellData?.value;
                                const inputType = cellData?.inputType || col.inputType;

                                return (
                                  <td key={colIndex} className="px-4 py-4 text-sm text-gray-700 dark:text-gray-300">
                                    {inputType === "dropdown" ? (
                                      <select
                                        className="w-full min-w-[150px] p-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800"
                                        defaultValue={value}
                                      >
                                        <option value="">Select...</option>
                                        {getDropdownOptions(col.attribute).map((option: any, optIdx: number) => (
                                          <option key={optIdx} value={option.value}>
                                            {option.label}
                                          </option>
                                        ))}
                                      </select>
                                    ) : inputType === "checkbox" ? (
                                      <input
                                        type="checkbox"
                                        defaultChecked={value}
                                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                                      />
                                    ) : (
                                      <input
                                        type="text"
                                        defaultValue={value}
                                        className="w-full min-w-[120px] p-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800"
                                      />
                                    )}
                                  </td>
                                );
                              })}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Debug: Last LLM Response */}
        {lastLLMResponse && (
          <div className="mt-8 p-4 bg-yellow-50 dark:bg-yellow-900 rounded-lg">
            <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-2">
              Debug: Last LLM Response
            </h2>
            <div className="text-sm text-gray-700 dark:text-gray-300 space-y-2">
              <div>
                <p className="font-semibold mb-1">Stop Reason: <span className="font-normal">{lastStopReason || "N/A"}</span></p>
              </div>
              <div>
                <p className="font-semibold mb-1">Response:</p>
                <pre className="p-2 bg-white dark:bg-gray-800 rounded overflow-auto text-xs whitespace-pre-wrap">
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
