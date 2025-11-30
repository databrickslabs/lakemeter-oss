"use client";

import { useState, Fragment } from "react";
import { config } from "@/lib/config";
import { workloadOptions, skuOptions, instanceOptions, workerCountOptions } from "@/lib/dropdown-options";
import { dbuPerHourLookup, skuRatesLookup } from "@/lib/dbu-rates";

// Define the structure for table columns
interface ColumnStructure {
  attribute: string;
  inputType: string;
  defaultValue: string;
  hidden?: boolean;
}

export default function Home() {
  // State for the prompt path input
  const [promptPath, setPromptPath] = useState("prompts:/users.fajar_muharandy.lakemeter/1");

  // State for the large text input
  const [promptText, setPromptText] = useState("");
  
  // State for table data - starts with no rows
  const [tableData, setTableData] = useState<Array<Array<{type: string, value: string}>>>([]);
  
  // State for table structure (columns)
  const [tableStructure, setTableStructure] = useState<ColumnStructure[]>([
    { attribute: "Workload", inputType: "dropdown", defaultValue: "" },
    { attribute: "SKU", inputType: "dropdown", defaultValue: "" },
    { attribute: "Driver Instance", inputType: "dropdown", defaultValue: "" },
    { attribute: "Worker Instance", inputType: "dropdown", defaultValue: "" },
    { attribute: "Worker Count", inputType: "dropdown", defaultValue: "1" },
    { attribute: "Run Duration", inputType: "text", defaultValue: "" },
    { attribute: "Runs/Day", inputType: "text", defaultValue: "" },
    { attribute: "Days/Month", inputType: "text", defaultValue: "" },
    { attribute: "Original Input", inputType: "text", defaultValue: "", hidden: true },
    { attribute: "Reasoning Output", inputType: "text", defaultValue: "", hidden: true },
  ]);
  
  // Loading state for API call
  const [isLoading, setIsLoading] = useState(false);

  // State to track which rows have expanded accordion
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());

  // State to store the last LLM response for debugging
  const [lastLLMResponse, setLastLLMResponse] = useState<string>("");
  const [lastStopReason, setLastStopReason] = useState<string>("");

  // State for the second table (DBU calculation table)
  const [dbuTableData, setDbuTableData] = useState<Array<{
    workload: string;
    dbuPerHour: string;
    dbuPerDay: string;
    dbuPerMonth: string;
    dollarPerDBU: string;
  }>>([]);

  // Toggle accordion for a row
  const toggleAccordion = (rowIndex: number) => {
    const newExpandedRows = new Set(expandedRows);
    if (newExpandedRows.has(rowIndex)) {
      newExpandedRows.delete(rowIndex);
    } else {
      newExpandedRows.add(rowIndex);
    }
    setExpandedRows(newExpandedRows);
  };

  const handleTableChange = (rowIndex: number, colIndex: number, value: string) => {
    const newData = [...tableData];
    newData[rowIndex][colIndex].value = value;
    setTableData(newData);
  };

  const addRow = async () => {
    setIsLoading(true);
    
    // Default row structure based on tableStructure
    let newRow = tableStructure.map(col => ({
      type: col.inputType,
      value: col.defaultValue
    }));
    
    // Add corresponding row to DBU table
    const newDbuRow = {
      workload: "",
      dbuPerHour: "",
      dbuPerDay: "",
      dbuPerMonth: "",
      dollarPerDBU: ""
    };

    try {
      // Call Python backend API if prompt text exists
      if (promptText.trim()) {
        const response = await fetch('/api/llm', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            prompt_text: promptText,
            prompt_path: promptPath,
          }),
        });

        const result = await response.json();

        if (result.success && result.data) {
          // Store the original response for debugging
          setLastLLMResponse(JSON.stringify(result.data, null, 2));
          setLastStopReason(result.debug?.finish_reason || "");
          
          // Parse the response data
          if (result.data.tableStructure && Array.isArray(result.data.tableStructure)) {
            // Build the row based on the JSON structure
            newRow = result.data.tableStructure.map((column: any) => ({
              type: column.inputType || "text",
              value: column.defaultValue || ""
            }));
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
      // Use default row structure on error
    } finally {
      setIsLoading(false);
    }

    const newTableData = [...tableData, newRow];
    setTableData(newTableData);
    setDbuTableData([...dbuTableData, newDbuRow]);
  };

  const removeRow = (rowIndex: number) => {
    if (tableData.length > 1) {
      const newData = tableData.filter((_, index) => index !== rowIndex);
      setTableData(newData);
      const newDbuData = dbuTableData.filter((_, index) => index !== rowIndex);
      setDbuTableData(newDbuData);
    }
  };

  const handleDbuTableChange = (rowIndex: number, field: keyof typeof dbuTableData[0], value: string) => {
    const newData = [...dbuTableData];
    newData[rowIndex][field] = value;
    setDbuTableData(newData);
  };

  // Get workload values from main table to display in DBU table
  const getWorkloadValue = (rowIndex: number): string => {
    if (rowIndex < tableData.length) {
      const workloadColIndex = tableStructure.findIndex(col => col.attribute === "Workload");
      return tableData[rowIndex][workloadColIndex]?.value || "";
    }
    return "";
  };

  // Get DBU/Hour value based on Worker Instance from main table
  const getDbuPerHourValue = (rowIndex: number): string => {
    if (rowIndex < tableData.length) {
      const workerInstanceColIndex = tableStructure.findIndex(col => col.attribute === "Worker Instance");
      const workerInstance = tableData[rowIndex][workerInstanceColIndex]?.value || "";
      const dbuValue = dbuPerHourLookup[workerInstance];
      return dbuValue !== undefined ? dbuValue.toString() : "";
    }
    return "";
  };

  // Get DBU/Day value using formula: DBU/Hour * Run Duration * Runs/Day
  const getDbuPerDayValue = (rowIndex: number): string => {
    if (rowIndex < tableData.length) {
      // Get DBU/Hour
      const workerInstanceColIndex = tableStructure.findIndex(col => col.attribute === "Worker Instance");
      const workerInstance = tableData[rowIndex][workerInstanceColIndex]?.value || "";
      const dbuPerHour = dbuPerHourLookup[workerInstance];
      
      if (dbuPerHour === undefined) return "";
      
      // Get Run Duration
      const runDurationColIndex = tableStructure.findIndex(col => col.attribute === "Run Duration");
      const runDuration = parseFloat(tableData[rowIndex][runDurationColIndex]?.value || "0");
      
      // Get Runs/Day
      const runsPerDayColIndex = tableStructure.findIndex(col => col.attribute === "Runs/Day");
      const runsPerDay = parseFloat(tableData[rowIndex][runsPerDayColIndex]?.value || "0");
      
      // Calculate DBU/Day
      if (runDuration > 0 && runsPerDay > 0) {
        const dbuPerDay = dbuPerHour * runDuration * runsPerDay;
        return dbuPerDay.toString();
      }
    }
    return "";
  };

  // Get DBU/Month value using formula: DBU/Day * Days/Month
  const getDbuPerMonthValue = (rowIndex: number): string => {
    if (rowIndex < tableData.length) {
      // Get DBU/Day value
      const dbuPerDayStr = getDbuPerDayValue(rowIndex);
      const dbuPerDay = parseFloat(dbuPerDayStr);
      
      if (isNaN(dbuPerDay) || dbuPerDay === 0) return "";
      
      // Get Days/Month
      const daysPerMonthColIndex = tableStructure.findIndex(col => col.attribute === "Days/Month");
      const daysPerMonth = parseFloat(tableData[rowIndex][daysPerMonthColIndex]?.value || "0");
      
      // Calculate DBU/Month
      if (daysPerMonth > 0) {
        const dbuPerMonth = dbuPerDay * daysPerMonth;
        return dbuPerMonth.toString();
      }
    }
    return "";
  };

  // Get $DBU value using formula: DBU/Month * SKU Rate
  const getDollarPerDBUValue = (rowIndex: number): string => {
    if (rowIndex < tableData.length) {
      // Get DBU/Month value
      const dbuPerMonthStr = getDbuPerMonthValue(rowIndex);
      const dbuPerMonth = parseFloat(dbuPerMonthStr);
      
      if (isNaN(dbuPerMonth) || dbuPerMonth === 0) return "";
      
      // Get SKU
      const skuColIndex = tableStructure.findIndex(col => col.attribute === "SKU");
      const sku = tableData[rowIndex][skuColIndex]?.value || "";
      const skuRate = skuRatesLookup[sku];
      
      if (skuRate === undefined) return "";
      
      // Calculate $DBU
      const dollarPerDBU = dbuPerMonth * skuRate;
      return dollarPerDBU.toFixed(2); // Format to 2 decimal places for currency
    }
    return "";
  };

  // Function to get dropdown options based on attribute name
  const getDropdownOptions = (attribute: string) => {
    switch (attribute) {
      case "Workload":
        return workloadOptions;
      case "SKU":
        return skuOptions;
      case "Driver Instance":
        return instanceOptions;
      case "Worker Instance":
        return instanceOptions;
      case "Worker Count":
        return workerCountOptions;
      default:
        return [];
    }
  };

  // Get visible columns (non-hidden)
  const visibleColumns = tableStructure.filter(col => !col.hidden);

  // Function to export DBU table to CSV
  const exportToCSV = () => {
    if (tableData.length === 0) {
      alert("No data to export");
      return;
    }

    // CSV headers - combine both main table and DBU calculation columns
    const headers = [
      "Workload",
      "SKU",
      "Driver Instance",
      "Worker Instance",
      "Worker Count",
      "Run Duration",
      "Runs/Day",
      "Days/Month",
      "DBU/Hour",
      "DBU/Day",
      "DBU/Month",
      "$DBU",
      "Original Input",
      "Reasoning Output"
    ];
    
    // CSV rows - combine data from both tables
    const rows = tableData.map((row, rowIndex) => {
      return [
        row[0]?.value || "", // Workload
        row[1]?.value || "", // SKU
        row[2]?.value || "", // Driver Instance
        row[3]?.value || "", // Worker Instance
        row[4]?.value || "", // Worker Count
        row[5]?.value || "", // Run Duration
        row[6]?.value || "", // Runs/Day
        row[7]?.value || "", // Days/Month
        getDbuPerHourValue(rowIndex), // DBU/Hour
        getDbuPerDayValue(rowIndex), // DBU/Day
        getDbuPerMonthValue(rowIndex), // DBU/Month
        getDollarPerDBUValue(rowIndex), // $DBU
        row[8]?.value || "", // Original Input
        row[9]?.value || ""  // Reasoning Output
      ];
    });

    // Combine headers and rows
    const csvContent = [
      headers.join(","),
      ...rows.map(row => row.map(cell => `"${cell.replace(/"/g, '""')}"`).join(","))
    ].join("\n");

    // Create blob and download
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);
    
    link.setAttribute("href", url);
    link.setAttribute("download", `dbu_calculation_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = "hidden";
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 p-8">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-100 mb-8">
          Prompt Input & Data Table
        </h1>

        {/* Prompt Path Input Field */}
        <div className="mb-6">
          <label htmlFor="promptPath" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Prompt Path
          </label>
          <input
            id="promptPath"
            type="text"
            value={promptPath}
            onChange={(e) => setPromptPath(e.target.value)}
            placeholder="prompts:/users.fajar_muharandy.lakemeter/1"
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
            onClick={addRow}
            disabled={isLoading}
            className="mt-4 px-6 py-2 text-base font-medium text-white bg-green-600 hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed rounded-lg transition-colors shadow-md hover:shadow-lg"
          >
            {isLoading ? "Processing..." : "Submit"}
          </button>
        </div>

        {/* Table with dynamic columns based on tableStructure */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full border-collapse table-fixed">
              <thead>
                <tr className="bg-gray-100 dark:bg-gray-700">
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 border-b dark:border-gray-600 whitespace-nowrap w-16">
                  </th>
                  {visibleColumns.map((column, colIndex) => (
                    <th
                      key={colIndex}
                      className={`px-4 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 border-b dark:border-gray-600 whitespace-nowrap ${
                        column.attribute === "Workload" ? "w-50" : column.attribute === "SKU" ? "w-50" : ""
                      }`}
                    >
                      {column.attribute}
                    </th>
                  ))}
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 border-b dark:border-gray-600 whitespace-nowrap">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {tableData.map((row, rowIndex) => (
                  <Fragment key={rowIndex}>
                    {/* Main Row */}
                    <tr className="hover:bg-gray-50 dark:hover:bg-gray-750">
                      <td className="px-4 py-3 border-b dark:border-gray-600">
                        <button
                          onClick={() => toggleAccordion(rowIndex)}
                          className="p-1 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 transition-all duration-200"
                          title="Show/Hide Details"
                        >
                          <svg
                            className={`w-5 h-5 transition-transform duration-200 ${expandedRows.has(rowIndex) ? 'rotate-180' : ''}`}
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                          </svg>
                        </button>
                      </td>
                      {tableStructure.map((column, colIndex) => {
                        // Skip hidden columns
                        if (column.hidden) return null;
                        
                        const cell = row[colIndex];
                        return (
                          <td
                            key={colIndex}
                            className="px-4 py-3 border-b dark:border-gray-600"
                          >
                            {cell.type === "text" ? (
                              <input
                                type="text"
                                value={cell.value}
                                onChange={(e) =>
                                  handleTableChange(rowIndex, colIndex, e.target.value)
                                }
                                placeholder="Enter text..."
                                className="w-full px-3 py-2 text-xs border border-gray-300 dark:border-gray-600 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-gray-100"
                              />
                            ) : (
                              <select
                                value={cell.value}
                                onChange={(e) =>
                                  handleTableChange(rowIndex, colIndex, e.target.value)
                                }
                                className="w-full px-3 py-2 text-xs border border-gray-300 dark:border-gray-600 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-gray-100"
                              >
                                {getDropdownOptions(column.attribute).map((option: string) => (
                                  <option key={option} value={option}>
                                    {option}
                                  </option>
                                ))}
                              </select>
                            )}
                          </td>
                        );
                      })}
                      <td className="px-4 py-3 border-b dark:border-gray-600">
                        <button
                          onClick={() => removeRow(rowIndex)}
                          disabled={tableData.length === 1}
                          className="px-3 py-2 text-xs font-medium text-white bg-red-600 hover:bg-red-700 disabled:bg-gray-400 disabled:cursor-not-allowed rounded-md transition-colors"
                        >
                          Remove
                        </button>
                      </td>
                    </tr>
                    
                    {/* Accordion Row */}
                    {expandedRows.has(rowIndex) && (
                      <tr key={`accordion-${rowIndex}`} className="bg-gray-50 dark:bg-gray-750">
                        <td colSpan={visibleColumns.length + 2} className="px-4 py-4 border-b dark:border-gray-600">
                          <div className="space-y-4">
                            {/* Original Input Section */}
                            <div>
                              <h3 className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">
                                Original Input
                              </h3>
                              <div className="p-3 bg-white dark:bg-gray-800 rounded-md border border-gray-300 dark:border-gray-600">
                                <p className="text-xs text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                                  {row[8]?.value || "(empty)"}
                                </p>
                              </div>
                            </div>
                            
                            {/* Reasoning Output Section */}
                            <div>
                              <h3 className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">
                                Reasoning Output
                              </h3>
                              <div className="p-3 bg-white dark:bg-gray-800 rounded-md border border-gray-300 dark:border-gray-600">
                                <p className="text-xs text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                                  {row[9]?.value || "(empty)"}
                                </p>
                              </div>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
          
          {/* Add Row Button */}
          <div className="p-4 bg-gray-50 dark:bg-gray-750 border-t dark:border-gray-600">
            <button
              onClick={addRow}
              className="px-4 py-2 text-xs font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors"
            >
              + Add Row
            </button>
          </div>
        </div>

        {/* DBU Calculation Table */}
        <div className="mt-8 bg-white dark:bg-gray-800 rounded-lg shadow-lg overflow-hidden">
          <div className="px-4 py-3 bg-gray-100 dark:bg-gray-700 border-b dark:border-gray-600 flex justify-between items-center">
            <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100">
              DBU Calculation
            </h2>
            <button
              onClick={exportToCSV}
              disabled={dbuTableData.length === 0}
              className="px-4 py-2 text-xs font-medium text-white bg-green-600 hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed rounded-md transition-colors shadow-md hover:shadow-lg flex items-center gap-2"
              title="Export to CSV"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Export CSV
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse">
              <thead>
                <tr className="bg-gray-100 dark:bg-gray-700">
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 border-b dark:border-gray-600 whitespace-nowrap">
                    Workload
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 border-b dark:border-gray-600 whitespace-nowrap">
                    DBU/Hour
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 border-b dark:border-gray-600 whitespace-nowrap">
                    DBU/Day
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 border-b dark:border-gray-600 whitespace-nowrap">
                    DBU/Month
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 border-b dark:border-gray-600 whitespace-nowrap">
                    $DBU
                  </th>
                </tr>
              </thead>
              <tbody>
                {dbuTableData.map((row, rowIndex) => (
                  <tr key={rowIndex} className="hover:bg-gray-50 dark:hover:bg-gray-750">
                    <td className="px-4 py-3 border-b dark:border-gray-600">
                      <input
                        type="text"
                        value={getWorkloadValue(rowIndex)}
                        readOnly
                        className="w-full px-3 py-2 text-xs border border-gray-300 dark:border-gray-600 rounded-md bg-gray-100 dark:bg-gray-700 dark:text-gray-100 cursor-not-allowed"
                      />
                    </td>
                    <td className="px-4 py-3 border-b dark:border-gray-600">
                      <input
                        type="text"
                        value={getDbuPerHourValue(rowIndex)}
                        readOnly
                        className="w-full px-3 py-2 text-xs border border-gray-300 dark:border-gray-600 rounded-md bg-gray-100 dark:bg-gray-700 dark:text-gray-100 cursor-not-allowed"
                      />
                    </td>
                    <td className="px-4 py-3 border-b dark:border-gray-600">
                      <input
                        type="text"
                        value={getDbuPerDayValue(rowIndex)}
                        readOnly
                        className="w-full px-3 py-2 text-xs border border-gray-300 dark:border-gray-600 rounded-md bg-gray-100 dark:bg-gray-700 dark:text-gray-100 cursor-not-allowed"
                      />
                    </td>
                    <td className="px-4 py-3 border-b dark:border-gray-600">
                      <input
                        type="text"
                        value={getDbuPerMonthValue(rowIndex)}
                        readOnly
                        className="w-full px-3 py-2 text-xs border border-gray-300 dark:border-gray-600 rounded-md bg-gray-100 dark:bg-gray-700 dark:text-gray-100 cursor-not-allowed"
                      />
                    </td>
                    <td className="px-4 py-3 border-b dark:border-gray-600">
                      <input
                        type="text"
                        value={getDollarPerDBUValue(rowIndex)}
                        readOnly
                        className="w-full px-3 py-2 text-xs border border-gray-300 dark:border-gray-600 rounded-md bg-gray-100 dark:bg-gray-700 dark:text-gray-100 cursor-not-allowed"
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Display current values (for debugging/demo purposes) */}
        <div className="mt-8 p-4 bg-blue-50 dark:bg-blue-900 rounded-lg">
          <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-2">
            Current Values
          </h2>
          <div className="text-sm text-gray-700 dark:text-gray-300">
            <p className="mb-2">
              <strong>Prompt:</strong> {promptText || "(empty)"}
            </p>
            <p>
              <strong>Table Data:</strong>
            </p>
            <pre className="mt-2 p-2 bg-white dark:bg-gray-800 rounded overflow-auto text-xs">
              {JSON.stringify(tableData, null, 2)}
            </pre>
          </div>
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
