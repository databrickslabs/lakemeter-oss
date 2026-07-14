export const SKU_GROUPS: Record<string, { label: string; color: string; bgColor: string; borderColor: string }> = {
  Compute: {
    label: 'Compute',
    color: 'text-blue-600 dark:text-blue-400',
    bgColor: 'bg-blue-50 dark:bg-blue-500/10',
    borderColor: 'border-blue-500',
  },
  SQL: {
    label: 'SQL',
    color: 'text-purple-600 dark:text-purple-400',
    bgColor: 'bg-purple-50 dark:bg-purple-500/10',
    borderColor: 'border-purple-500',
  },
  'Data Engineering': {
    label: 'Data Engineering',
    color: 'text-emerald-600 dark:text-emerald-400',
    bgColor: 'bg-emerald-50 dark:bg-emerald-500/10',
    borderColor: 'border-emerald-500',
  },
  'AI/ML': {
    label: 'AI/ML',
    color: 'text-amber-600 dark:text-amber-400',
    bgColor: 'bg-amber-50 dark:bg-amber-500/10',
    borderColor: 'border-amber-500',
  },
  Database: {
    label: 'Database',
    color: 'text-teal-600 dark:text-teal-400',
    bgColor: 'bg-teal-50 dark:bg-teal-500/10',
    borderColor: 'border-teal-500',
  },
  'Storage & Networking': {
    label: 'Storage & Networking',
    color: 'text-gray-600 dark:text-gray-400',
    bgColor: 'bg-gray-50 dark:bg-gray-500/10',
    borderColor: 'border-gray-400',
  },
}

export const GROUP_ORDER = ['Compute', 'SQL', 'Data Engineering', 'AI/ML', 'Database', 'Storage & Networking']

export const EXCLUDED_PRODUCT_TYPES = new Set([
  'DATABRICKS_STORAGE',
  'REGION_EGRESS',
  'CONTINENTAL_EGRESS',
  'AVAILABILITY_ZONE_EGRESS',
  'INTERNET_EGRESS',
  'CONNECTIVITY_DATA_PROCESSED',
  'CONNECTIVITY_ENDPOINT',
])

export function getSkuGroup(productType: string): string {
  const s = productType.toLowerCase()

  if (
    s.startsWith('jobs') ||
    s.startsWith('all_purpose') ||
    s.startsWith('automated_jobs') ||
    s.startsWith('interactive_serverless')
  ) {
    return 'Compute'
  }

  if (s.startsWith('sql') || s.startsWith('serverless_sql')) {
    return 'SQL'
  }

  if (s.startsWith('dlt') || s.includes('delta_live_tables') || s.includes('lakeflow')) {
    return 'Data Engineering'
  }

  if (
    s.includes('model_serving') ||
    s.includes('real_time_inference') ||
    s.includes('vector_search') ||
    s.includes('foundation_model') ||
    s.includes('openai') ||
    s.includes('anthropic') ||
    s.includes('google') ||
    s.includes('gemini') ||
    s.startsWith('ai_') ||
    s.startsWith('mosaic')
  ) {
    return 'AI/ML'
  }

  if (s.includes('database') || s.includes('lakebase')) {
    return 'Database'
  }

  if (s.includes('storage') || s.includes('egress') || s.includes('network') || s.includes('connectivity')) {
    return 'Storage & Networking'
  }

  return 'Compute'
}

export function formatRate(value: number, symbol = '$'): string {
  return `${symbol}${value.toFixed(3)}`
}

export function formatFeatureName(feature: string): string {
  return feature
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase())
    .replace('Dlt', 'DLT')
    .replace('Sql', 'SQL')
}

export function formatProductName(productType: string): string {
  const explicit: Record<string, string> = {
    JOBS_COMPUTE: 'Jobs',
    JOBS_COMPUTE_PHOTON: 'Jobs Photon',
    'JOBS_COMPUTE_(PHOTON)': 'Jobs Photon',
    JOBS_SERVERLESS_COMPUTE: 'Jobs SVLS',
    ALL_PURPOSE_COMPUTE: 'All Purpose',
    'ALL_PURPOSE_COMPUTE_(PHOTON)': 'All Purpose Photon',
    ALL_PURPOSE_SERVERLESS_COMPUTE: 'All Purpose SVLS',
    INTERACTIVE_SERVERLESS_COMPUTE: 'All Purpose SVLS',
    SQL_COMPUTE: 'SQL Classic',
    SQL_PRO_COMPUTE: 'SQL Pro',
    SERVERLESS_SQL_COMPUTE: 'SQL Serverless',
    DLT_CORE_COMPUTE: 'Lakeflow SDP Core',
    DLT_PRO_COMPUTE: 'Lakeflow SDP Pro',
    DLT_ADVANCED_COMPUTE: 'Lakeflow SDP Advanced',
    DELTA_LIVE_TABLES_SERVERLESS: 'Lakeflow SDP SVLS',
    SERVERLESS_REAL_TIME_INFERENCE: 'Model Serving',
    VECTOR_SEARCH_ENDPOINT: 'Vector Search Compute',
    DATABASE_SERVERLESS_COMPUTE: 'Lakebase Compute',
    DATABRICKS_STORAGE: 'Databricks Default Storage',
  }

  if (explicit[productType]) return explicit[productType]

  return productType
    .toLowerCase()
    .split('_')
    .filter(Boolean)
    .map((part) => (part.length <= 3 ? part.toUpperCase() : part[0].toUpperCase() + part.slice(1)))
    .join(' ')
    .replace(/\bDbu\b/g, 'DBU')
    .replace(/\bSql\b/g, 'SQL')
    .replace(/\bDlt\b/g, 'DLT')
}
