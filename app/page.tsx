"use client";

import { useState, Fragment } from "react";
import Anthropic from "@anthropic-ai/sdk";
import { config } from "@/lib/config";

// Define the structure for table columns
interface ColumnStructure {
  attribute: string;
  inputType: string;
  defaultValue: string;
  hidden?: boolean;
}

export default function Home() {
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
    { attribute: "Run Freq.", inputType: "text", defaultValue: "" },
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

    try {
      // Call Anthropic API if prompt text exists and API key is configured
      if (promptText.trim() && config.anthropicApiKey) {
        const anthropic = new Anthropic({
          apiKey: config.anthropicApiKey,
          dangerouslyAllowBrowser: true, // Note: For production, use a backend API route
        });

        const message = await anthropic.messages.create({
          model: "claude-haiku-4-5-20251001",
          max_tokens: 500,
          system: config.systemPrompt,
          messages: [
            {
              role: "user",
              content: promptText,
            },
          ],
        });

        // Extract the JSON response from the LLM
        let responseText = message.content[0].type === "text" 
          ? message.content[0].text.trim() 
          : "";
        
        // Store the original response and stop_reason for debugging
        setLastLLMResponse(responseText);
        setLastStopReason(message.stop_reason || "");
        
        // Remove markdown code blocks if present
        responseText = responseText.replace(/```json\n?/g, '').replace(/```\n?/g, '').trim();
        
        try {
          // Parse the JSON response
          const jsonResponse = JSON.parse(responseText);
          
          if (jsonResponse.tableStructure && Array.isArray(jsonResponse.tableStructure)) {
            // Build the row based on the JSON structure
            newRow = jsonResponse.tableStructure.map((column: any) => ({
              type: column.inputType || "text",
              value: column.defaultValue || ""
            }));
          }
        } catch (parseError) {
          console.error("Error parsing JSON response:", parseError);
          console.log("Response text:", responseText);
          // Use default row structure on parse error
        }
      }
    } catch (error) {
      console.error("Error calling Anthropic API:", error);
      // Use default row structure on error
    } finally {
      setIsLoading(false);
    }

    setTableData([...tableData, newRow]);
  };

  const removeRow = (rowIndex: number) => {
    if (tableData.length > 1) {
      const newData = tableData.filter((_, index) => index !== rowIndex);
      setTableData(newData);
    }
  };

  // Define dropdown options for each column
  const workloadOptions = ["Ingestion", "Transformation", "Analysis", "Exploration", "ML Inference"];
  const skuOptions = [
    "Jobs Classic",
    "Jobs Serverless",
    "DLT Serverless",
    "DLT Core",
    "DLT Pro",
    "DLT Advanced",
    "SQL Classic",
    "SQL Pro",
    "SQL Serverless",
    "Classic All-Purpose",
    "Serverless All-Purpose"
  ];
  const driverInstanceOptions = [
    "c6id.12xlarge",
    "c6id.16xlarge",
    "c6id.24xlarge",
    "c6id.2xlarge",
    "c6id.32xlarge",
    "c6id.4xlarge",
    "c6id.8xlarge",
    "c6id.xlarge",
    "i3.2xlarge",
    "i3.4xlarge",
    "i3en.12xlarge",
    "i3en.24xlarge",
    "i3en.2xlarge",
    "i3en.3xlarge",
    "i3en.6xlarge",
    "i3en.large",
    "i3en.xlarge",
    "i4i.16xlarge",
    "i4i.2xlarge",
    "i4i.32xlarge",
    "i4i.4xlarge",
    "i4i.8xlarge",
    "i4i.large",
    "i4i.xlarge",
    "m5d.12xlarge",
    "m5d.16xlarge",
    "m5d.24xlarge",
    "m5d.2xlarge",
    "m5d.4xlarge",
    "m5d.8xlarge",
    "m5d.large",
    "m5d.xlarge",
    "m6gd.12xlarge",
    "m6gd.16xlarge",
    "m6gd.2xlarge",
    "m6gd.4xlarge",
    "m6gd.8xlarge",
    "m6gd.large",
    "m6gd.xlarge",
    "m6id.12xlarge",
    "m6id.16xlarge",
    "m6id.24xlarge",
    "m6id.2xlarge",
    "m6id.32xlarge",
    "m6id.4xlarge",
    "m6id.8xlarge",
    "m6id.large",
    "m6id.xlarge",
    "m6idn.12xlarge",
    "m6idn.16xlarge",
    "m6idn.24xlarge",
    "m6idn.2xlarge",
    "m6idn.32xlarge",
    "m6idn.4xlarge",
    "m6idn.8xlarge",
    "m6idn.large",
    "m6idn.xlarge",
    "m7gd.12xlarge",
    "m7gd.16xlarge",
    "m7gd.2xlarge",
    "m7gd.4xlarge",
    "m7gd.8xlarge",
    "m7gd.large",
    "m7gd.xlarge",
    "m7i.12xlarge",
    "m7i.16xlarge",
    "m7i.24xlarge",
    "m7i.2xlarge",
    "m7i.48xlarge",
    "m7i.4xlarge",
    "m7i.8xlarge",
    "m7i.large",
    "m7i.metal-24xl",
    "m7i.metal-48xl",
    "m7i.xlarge",
    "r5d.12xlarge",
    "r5d.16xlarge",
    "r5d.24xlarge",
    "r5d.2xlarge",
    "r5d.4xlarge",
    "r5d.8xlarge",
    "r5d.large",
    "r5d.xlarge",
    "r5dn.12xlarge",
    "r5dn.16xlarge",
    "r5dn.24xlarge",
    "r5dn.2xlarge",
    "r5dn.4xlarge",
    "r5dn.8xlarge",
    "r5dn.large",
    "r5dn.xlarge",
    "r6gd.12xlarge",
    "r6gd.16xlarge",
    "r6gd.2xlarge",
    "r6gd.4xlarge",
    "r6gd.8xlarge",
    "r6gd.large",
    "r6gd.xlarge",
    "r6i.12xlarge",
    "r6i.16xlarge",
    "r6i.24xlarge",
    "r6i.2xlarge",
    "r6i.32xlarge",
    "r6i.4xlarge",
    "r6i.8xlarge",
    "r6i.large",
    "r6i.xlarge",
    "r6id.12xlarge",
    "r6id.16xlarge",
    "r6id.24xlarge",
    "r6id.2xlarge",
    "r6id.32xlarge",
    "r6id.4xlarge",
    "r6id.8xlarge",
    "r6id.large",
    "r6id.xlarge",
    "r6idn.12xlarge",
    "r6idn.16xlarge",
    "r6idn.24xlarge",
    "r6idn.2xlarge",
    "r6idn.32xlarge",
    "r6idn.4xlarge",
    "r6idn.8xlarge",
    "r6idn.large",
    "r6idn.xlarge",
    "r7gd.12xlarge",
    "r7gd.16xlarge",
    "r7gd.2xlarge",
    "r7gd.4xlarge",
    "r7gd.8xlarge",
    "r7gd.large",
    "r7gd.xlarge",
    "r7i.12xlarge",
    "r7i.16xlarge",
    "r7i.24xlarge",
    "r7i.2xlarge",
    "r7i.48xlarge",
    "r7i.4xlarge",
    "r7i.8xlarge",
    "r7i.large",
    "r7i.metal-24xl",
    "r7i.metal-48xl",
    "r7i.xlarge",
    "2X-Small",
    "X-Small",
    "Small",
    "Medium",
    "Large",
    "X-Large",
    "2X-Large",
    "3X-Large",
    "4X-Large"
  ];
  const workerInstanceOptions = [
    "c6id.12xlarge",
    "c6id.16xlarge",
    "c6id.24xlarge",
    "c6id.2xlarge",
    "c6id.32xlarge",
    "c6id.4xlarge",
    "c6id.8xlarge",
    "c6id.xlarge",
    "i3.2xlarge",
    "i3.4xlarge",
    "i3en.12xlarge",
    "i3en.24xlarge",
    "i3en.2xlarge",
    "i3en.3xlarge",
    "i3en.6xlarge",
    "i3en.large",
    "i3en.xlarge",
    "i4i.16xlarge",
    "i4i.2xlarge",
    "i4i.32xlarge",
    "i4i.4xlarge",
    "i4i.8xlarge",
    "i4i.large",
    "i4i.xlarge",
    "m5d.12xlarge",
    "m5d.16xlarge",
    "m5d.24xlarge",
    "m5d.2xlarge",
    "m5d.4xlarge",
    "m5d.8xlarge",
    "m5d.large",
    "m5d.xlarge",
    "m6gd.12xlarge",
    "m6gd.16xlarge",
    "m6gd.2xlarge",
    "m6gd.4xlarge",
    "m6gd.8xlarge",
    "m6gd.large",
    "m6gd.xlarge",
    "m6id.12xlarge",
    "m6id.16xlarge",
    "m6id.24xlarge",
    "m6id.2xlarge",
    "m6id.32xlarge",
    "m6id.4xlarge",
    "m6id.8xlarge",
    "m6id.large",
    "m6id.xlarge",
    "m6idn.12xlarge",
    "m6idn.16xlarge",
    "m6idn.24xlarge",
    "m6idn.2xlarge",
    "m6idn.32xlarge",
    "m6idn.4xlarge",
    "m6idn.8xlarge",
    "m6idn.large",
    "m6idn.xlarge",
    "m7gd.12xlarge",
    "m7gd.16xlarge",
    "m7gd.2xlarge",
    "m7gd.4xlarge",
    "m7gd.8xlarge",
    "m7gd.large",
    "m7gd.xlarge",
    "m7i.12xlarge",
    "m7i.16xlarge",
    "m7i.24xlarge",
    "m7i.2xlarge",
    "m7i.48xlarge",
    "m7i.4xlarge",
    "m7i.8xlarge",
    "m7i.large",
    "m7i.metal-24xl",
    "m7i.metal-48xl",
    "m7i.xlarge",
    "r5d.12xlarge",
    "r5d.16xlarge",
    "r5d.24xlarge",
    "r5d.2xlarge",
    "r5d.4xlarge",
    "r5d.8xlarge",
    "r5d.large",
    "r5d.xlarge",
    "r5dn.12xlarge",
    "r5dn.16xlarge",
    "r5dn.24xlarge",
    "r5dn.2xlarge",
    "r5dn.4xlarge",
    "r5dn.8xlarge",
    "r5dn.large",
    "r5dn.xlarge",
    "r6gd.12xlarge",
    "r6gd.16xlarge",
    "r6gd.2xlarge",
    "r6gd.4xlarge",
    "r6gd.8xlarge",
    "r6gd.large",
    "r6gd.xlarge",
    "r6i.12xlarge",
    "r6i.16xlarge",
    "r6i.24xlarge",
    "r6i.2xlarge",
    "r6i.32xlarge",
    "r6i.4xlarge",
    "r6i.8xlarge",
    "r6i.large",
    "r6i.xlarge",
    "r6id.12xlarge",
    "r6id.16xlarge",
    "r6id.24xlarge",
    "r6id.2xlarge",
    "r6id.32xlarge",
    "r6id.4xlarge",
    "r6id.8xlarge",
    "r6id.large",
    "r6id.xlarge",
    "r6idn.12xlarge",
    "r6idn.16xlarge",
    "r6idn.24xlarge",
    "r6idn.2xlarge",
    "r6idn.32xlarge",
    "r6idn.4xlarge",
    "r6idn.8xlarge",
    "r6idn.large",
    "r6idn.xlarge",
    "r7gd.12xlarge",
    "r7gd.16xlarge",
    "r7gd.2xlarge",
    "r7gd.4xlarge",
    "r7gd.8xlarge",
    "r7gd.large",
    "r7gd.xlarge",
    "r7i.12xlarge",
    "r7i.16xlarge",
    "r7i.24xlarge",
    "r7i.2xlarge",
    "r7i.48xlarge",
    "r7i.4xlarge",
    "r7i.8xlarge",
    "r7i.large",
    "r7i.metal-24xl",
    "r7i.metal-48xl",
    "r7i.xlarge",
    "2X-Small",
    "X-Small",
    "Small",
    "Medium",
    "Large",
    "X-Large",
    "2X-Large",
    "3X-Large",
    "4X-Large"
  ];
  const workerCountOptions = Array.from({ length: 20 }, (_, i) => String(i + 1));

  // Function to get dropdown options based on attribute name
  const getDropdownOptions = (attribute: string) => {
    switch (attribute) {
      case "Workload":
        return workloadOptions;
      case "SKU":
        return skuOptions;
      case "Driver Instance":
        return driverInstanceOptions;
      case "Worker Instance":
        return workerInstanceOptions;
      case "Worker Count":
        return workerCountOptions;
      default:
        return [];
    }
  };

  // Get visible columns (non-hidden)
  const visibleColumns = tableStructure.filter(col => !col.hidden);

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 p-8">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-100 mb-8">
          Prompt Input & Data Table
        </h1>

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
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700 dark:text-gray-300 border-b dark:border-gray-600 whitespace-nowrap w-16">
                  </th>
                  {visibleColumns.map((column, colIndex) => (
                    <th
                      key={colIndex}
                      className={`px-4 py-3 text-left text-sm font-semibold text-gray-700 dark:text-gray-300 border-b dark:border-gray-600 whitespace-nowrap ${
                        column.attribute === "SKU" ? "w-56" : ""
                      }`}
                    >
                      {column.attribute}
                    </th>
                  ))}
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700 dark:text-gray-300 border-b dark:border-gray-600 whitespace-nowrap">
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
                                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-gray-100"
                              />
                            ) : (
                              <select
                                value={cell.value}
                                onChange={(e) =>
                                  handleTableChange(rowIndex, colIndex, e.target.value)
                                }
                                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-gray-100"
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
                          className="px-3 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 disabled:bg-gray-400 disabled:cursor-not-allowed rounded-md transition-colors"
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
                              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                                Original Input
                              </h3>
                              <div className="p-3 bg-white dark:bg-gray-800 rounded-md border border-gray-300 dark:border-gray-600">
                                <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                                  {row[7]?.value || "(empty)"}
                                </p>
                              </div>
                            </div>
                            
                            {/* Reasoning Output Section */}
                            <div>
                              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                                Reasoning Output
                              </h3>
                              <div className="p-3 bg-white dark:bg-gray-800 rounded-md border border-gray-300 dark:border-gray-600">
                                <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                                  {row[8]?.value || "(empty)"}
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
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors"
            >
              + Add Row
            </button>
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
