/**
 * DBU rates and pricing lookups
 */

/**
 * DBU per hour rates based on Worker Instance type
 */
export const dbuPerHourLookup: { [key: string]: number } = {
  "2X-Small": 4,
  "X-Small": 6,
  "Small": 12,
  "Medium": 24,
  "Large": 40,
  "X-Large": 80,
  "2X-Large": 144,
  "3X-Large": 272,
  "4X-Large": 528
};

/**
 * SKU pricing rates (dollar per DBU)
 */
export const skuRatesLookup: { [key: string]: number } = {
  // "Jobs Classic": 0.200,
  // "Jobs Serverless": 0.500,
  // "DLT Serverless": 0.500,
  // "DLT Core": 0.200,
  // "DLT Pro": 0.250,
  // "DLT Advanced": 0.360,
  // "SQL Classic": 0.220,
  // "SQL Pro": 0.690,
  // "SQL Serverless": 0.880,
  // "Classic All-Purpose": 0.650,
  // "Serverless All-Purpose": 1.050
  "Lakeflow Connect serverless": 0.500,
  "Lakeflow Jobs serverless": 0.500,
  "Lakeflow Jobs classic": 0.200,
  "SQL Warehouse serverless": 0.880,
  "SQL Warehouse pro": 0.690,
  "All-Purpose Serverless": 0.650,
  "All-Purpose Classic": 1.050
};
