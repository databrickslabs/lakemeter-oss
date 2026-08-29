import React, { useEffect, useState, useMemo, useCallback, useRef, Component, ErrorInfo, ReactNode } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors, DragEndEvent } from '@dnd-kit/core'
import { SortableContext, verticalListSortingStrategy, useSortable } from '@dnd-kit/sortable'
import { restrictToVerticalAxis } from '@dnd-kit/modifiers'
import { CSS } from '@dnd-kit/utilities'
import {
  PlusIcon,
  ArrowDownTrayIcon,
  ArrowLeftIcon,
  ArrowPathIcon,
  CheckIcon,
  TrashIcon,
  DocumentDuplicateIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  BoltIcon,
  CpuChipIcon,
  CurrencyDollarIcon,
  ServerStackIcon,
  ExclamationTriangleIcon,
  PlayCircleIcon,
  CircleStackIcon,
  ArrowsRightLeftIcon,
  MagnifyingGlassCircleIcon,
  SparklesIcon,
  ServerIcon,
  TableCellsIcon,
  Squares2X2Icon,
  ListBulletIcon,
  XMarkIcon,
  CalculatorIcon,
  BarsArrowDownIcon,
  BarsArrowUpIcon,
  Bars3Icon,
  ShieldCheckIcon,
  BeakerIcon
} from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'
import clsx from 'clsx'
import { useStore } from '../store/useStore'
import {
  exportEstimateToExcel,
  reorderLineItems as apiReorderLineItems,
  type RegionResponse
} from '../api/client'
import { saveAs } from 'file-saver'
import WorkloadForm from '../components/WorkloadForm'
import type { LineItem, PlatformAddonType } from '../types'
import {
  getInstanceDBURate as getBundleInstanceDBURate,
  getPhotonMultiplier as getBundlePhotonMultiplier,
  getDBUPrice as getBundleDBUPrice,
  getDBSQLRate as getBundleDBSQLRate,
  getDBSQLWarehouseConfig as getBundleDBSQLWarehouseConfig,
  getVectorSearchRate as getBundleVectorSearchRate,
  getModelServingRate as getBundleModelServingRate,
  getFMAPIDatabricksRate as getBundleFMAPIDatabricksRate,
  getFMAPIProprietaryRate as getBundleFMAPIProprietaryRate,
  getAvailableRegionsFromBundle,
  getExactRegionalDBUPrice
} from '../utils/pricingBundle'
import { calculateLakebaseComputeUsage, resolveLakebaseAutoscaleConfig } from '../utils/lakebasePricing'
import {
  AGENT_EVALUATION_COMPONENT_RATES,
  AI_SEARCH_INCLUDED_STORAGE_GB,
  AI_SEARCH_RERANKER_DBU_PER_THOUSAND_REQUESTS,
  calculateAgentEvaluationUsage,
  calculateAISearchRerankerUsage,
  calculateAIGatewayUsage,
  calculateGeneralStorageDSU,
  calculateModelServingDBUPerHour,
  calculateZerobusUsage,
  getAISearchStorageDSUPerGB,
  getGeneralStorageGB,
  getModelServingBillingCapacityUnits,
  isModelServingGPUType,
} from '../utils/costCalculation'
import { calculateAIRuntimeUsage } from '../utils/aiRuntime'
import {
  PLATFORM_ADDON_TYPES,
  calculatePlatformAddonCost,
  getPlatformAddonAvailabilityError,
  getPlatformAddonDefinition,
  getPlatformAddonDiscountPct,
} from '../utils/platformAddons'

// Error Boundary for catching render errors
interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

class WorkloadErrorBoundary extends Component<{ children: ReactNode; onReset?: () => void }, ErrorBoundaryState> {
  constructor(props: { children: ReactNode; onReset?: () => void }) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Workload render error:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-4 rounded-lg border border-red-500/30 bg-red-500/10">
          <p className="text-sm text-red-600 dark:text-red-400 mb-2">
            Something went wrong rendering this workload.
          </p>
          <button
            onClick={() => {
              this.setState({ hasError: false, error: null })
              this.props.onReset?.()
            }}
            className="text-xs text-red-500 underline hover:no-underline"
          >
            Try again
          </button>
        </div>
      )
    }

    return this.props.children
  }
}

interface ServerlessComputeDbuBreakdownProps {
  workloadType: string
  serverlessMode?: string | null
  driverNode: string
  workerNode: string
  driverDBURate: number
  workerDBURate: number
  numWorkers: number
  dbuPerHour: number
}

const ServerlessComputeDbuBreakdown: React.FC<ServerlessComputeDbuBreakdownProps> = ({
  workloadType,
  serverlessMode,
  driverNode,
  workerNode,
  driverDBURate,
  workerDBURate,
  numWorkers,
  dbuPerHour,
}) => {
  const baseDBUPerHour = driverDBURate + (workerDBURate * numWorkers)
  const performanceOptimized = workloadType === 'ALL_PURPOSE'
    || serverlessMode === 'performance'
  const modeMultiplier = performanceOptimized ? 2 : 1
  const calculatedPhotonMultiplier = baseDBUPerHour > 0
    ? dbuPerHour / (baseDBUPerHour * modeMultiplier)
    : 0
  const photonMultiplier = Number.isFinite(calculatedPhotonMultiplier)
    ? calculatedPhotonMultiplier
    : 0

  return (
    <>
      <span>(</span>
      <span className="font-medium text-[var(--text-primary)]">Driver</span>
      <span>{driverNode || 'Not selected'}</span>
      <span className="text-[var(--text-muted)]">
        ({driverDBURate.toFixed(2)} DBU/hr)
      </span>
      {numWorkers > 0 ? (
        <>
          <span>+</span>
          <span className="font-medium text-[var(--text-primary)]">
            {numWorkers} worker{numWorkers !== 1 ? 's' : ''}
          </span>
          <span>{workerNode || 'Not selected'}</span>
          <span className="text-[var(--text-muted)]">
            ({workerDBURate.toFixed(2)} DBU/hr each)
          </span>
        </>
      ) : (
        <span className="text-[var(--text-muted)]">Single node — driver only</span>
      )}
      <span>)</span>
      <span>×</span>
      <span className="text-[var(--text-muted)]">
        Photon {photonMultiplier.toFixed(2)}×
      </span>
      <span>×</span>
      <span className="text-[var(--text-muted)]">
        {performanceOptimized ? 'Performance Optimized' : 'Standard'} {modeMultiplier}×
      </span>
      <span>=</span>
      <span className="font-semibold">{dbuPerHour.toFixed(2)} DBU/hr</span>
    </>
  )
}

// Cloud provider visual options
const CLOUD_PROVIDERS = [
  { id: 'aws', name: 'AWS', logo: '/aws.svg', bgClass: 'from-amber-600/20 to-amber-900/10' },
  { id: 'azure', name: 'Azure', logo: '/azure.svg', bgClass: 'from-sky-600/20 to-sky-900/10' },
  { id: 'gcp', name: 'GCP', logo: '/gcp.svg', bgClass: 'from-red-600/20 to-red-900/10' }
]

// Workload type visual config - icons, colors, and labels
const WORKLOAD_TYPE_CONFIG: Record<string, { 
  icon: React.ComponentType<React.SVGProps<SVGSVGElement>>, 
  color: string, 
  bgColor: string,
  label: string 
}> = {
  'JOBS': { 
    icon: PlayCircleIcon, 
    color: 'text-emerald-500', 
    bgColor: 'bg-emerald-500/10',
    label: 'Jobs'
  },
  'ALL_PURPOSE': { 
    icon: CpuChipIcon, 
    color: 'text-blue-500', 
    bgColor: 'bg-blue-500/10',
    label: 'AP'
  },
  'DLT': { 
    icon: ArrowsRightLeftIcon, 
    color: 'text-purple-500', 
    bgColor: 'bg-purple-500/10',
    label: 'SDP'
  },
  'DBSQL': { 
    icon: CircleStackIcon, 
    color: 'text-cyan-500', 
    bgColor: 'bg-cyan-500/10',
    label: 'DB SQL'
  },
  'VECTOR_SEARCH': { 
    icon: MagnifyingGlassCircleIcon, 
    color: 'text-rose-500', 
    bgColor: 'bg-rose-500/10',
    label: 'AI Search'
  },
  'MODEL_SERVING': { 
    icon: SparklesIcon, 
    color: 'text-amber-500', 
    bgColor: 'bg-amber-500/10',
    label: 'MS'
  },
  'FMAPI_DATABRICKS': { 
    icon: SparklesIcon, 
    color: 'text-lava-600', 
    bgColor: 'bg-lava-600/10',
    label: 'FMAPI DBX'
  },
  'FMAPI_PROPRIETARY': { 
    icon: SparklesIcon, 
    color: 'text-pink-500', 
    bgColor: 'bg-pink-500/10',
    label: 'FMAPI Prop'
  },
  'LAKEBASE': { 
    icon: ServerIcon, 
    color: 'text-indigo-500', 
    bgColor: 'bg-indigo-500/10',
    label: 'Lakebase'
  },
  'AI_GATEWAY': {
    icon: ShieldCheckIcon,
    color: 'text-violet-500',
    bgColor: 'bg-violet-500/10',
    label: 'AI Gateway'
  },
  'AGENT_EVALUATION': {
    icon: BeakerIcon,
    color: 'text-fuchsia-500',
    bgColor: 'bg-fuchsia-500/10',
    label: 'Agent Eval'
  },
  'AI_RUNTIME': {
    icon: CpuChipIcon,
    color: 'text-cyan-500',
    bgColor: 'bg-cyan-500/10',
    label: 'AI Runtime'
  },
  'GENERAL_STORAGE': {
    icon: CircleStackIcon,
    color: 'text-emerald-500',
    bgColor: 'bg-emerald-500/10',
    label: 'Storage'
  },
  'ZEROBUS': {
    icon: ArrowsRightLeftIcon,
    color: 'text-sky-500',
    bgColor: 'bg-sky-500/10',
    label: 'Zerobus'
  }
}

// Get workload type visual config with fallback
const getWorkloadTypeConfig = (workloadType: string | null | undefined) => {
  if (!workloadType) {
    return { 
      icon: CpuChipIcon, 
      color: 'text-lava-600', 
      bgColor: 'bg-lava-600/10',
      label: 'Workload'
    }
  }
  return WORKLOAD_TYPE_CONFIG[workloadType] || { 
    icon: CpuChipIcon, 
    color: 'text-lava-600', 
    bgColor: 'bg-lava-600/10',
    label: workloadType
  }
}

// ============================================
// SHARED UTILITIES - Used across all views
// ============================================

const formatCurrency = (amount: number) => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(amount)
}

const formatCurrencyCompact = (amount: number) => {
  if (Math.abs(amount) >= 1_000_000) {
    return `$${(amount / 1_000_000).toFixed(2)}M`
  }
  if (Math.abs(amount) >= 1_000) {
    return `$${(amount / 1_000).toFixed(1)}K`
  }
  return formatCurrency(amount)
}

const formatNumber = (num: number, decimals: number = 2) => {
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  }).format(num)
}

// ============================================
// SHARED COMPONENTS - Used across all views
// ============================================

interface CostBreakdown {
  totalCost: number
  dbuCost: number
  dsuCost: number
  vmCost: number
  databricksListCost: number
  monthlyDBUs: number
  monthlyDSUs: number
  unitsUsed?: number
}

// Shared cost display component - consistent across table, compact, and expanded views
interface WorkloadCostDisplayProps {
  costs: CostBreakdown
  size?: 'sm' | 'md' | 'lg'
  showDBUs?: boolean
  isLoading?: boolean
  className?: string
}

interface VMCalculationLineProps {
  driverType: string
  driverRate: number
  workerType: string
  workerRate: number
  workerCount: number
  hours: number
  total: number
  clusters?: number
  status?: string
}

const VMCalculationLine: React.FC<VMCalculationLineProps> = React.memo(({
  driverType,
  driverRate,
  workerType,
  workerRate,
  workerCount,
  hours,
  total,
  clusters,
  status,
}) => (
  <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
    <span className="text-teal-600 font-semibold">VM:</span>
    {status ? (
      <span className="font-medium text-amber-700 dark:text-amber-300">{status}</span>
    ) : (
      <>
        <span>(</span>
        <span className="font-medium text-[var(--text-primary)]">Driver</span>
        <span>{driverType}</span>
        <span className="text-[var(--text-muted)]">(${driverRate.toFixed(4)}/hr)</span>
        {workerCount > 0 ? (
          <>
            <span>+</span>
            <span className="font-medium text-[var(--text-primary)]">
              {workerCount} worker{workerCount !== 1 ? 's' : ''}
            </span>
            <span>{workerType}</span>
            <span className="text-[var(--text-muted)]">(${workerRate.toFixed(4)}/hr each)</span>
          </>
        ) : (
          <span className="text-[var(--text-muted)]">Single node — driver VM only</span>
        )}
        <span>)</span>
        {clusters !== undefined && (
          <>
            <span>×</span>
            <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">
              {clusters} cluster{clusters !== 1 ? 's' : ''}
            </span>
          </>
        )}
        <span>×</span>
        <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">
          {hours}h
        </span>
        <span>=</span>
        <span className="text-teal-600 font-semibold">{formatCurrency(total)}</span>
      </>
    )}
  </div>
))

const WorkloadCostDisplay: React.FC<WorkloadCostDisplayProps> = React.memo(({ 
  costs, 
  size = 'md', 
  showDBUs = true,
  isLoading = false,
  className
}) => {
  const sizeClasses = {
    sm: { cost: 'text-sm', dbu: 'text-[10px]' },
    md: { cost: 'text-base', dbu: 'text-xs' },
    lg: { cost: 'text-lg', dbu: 'text-xs' }
  }
  
  return (
    <div className={clsx("flex flex-col items-end justify-center min-w-[80px]", isLoading && "opacity-60", className)}>
      <span className={clsx("font-medium text-[var(--text-primary)] tabular-nums", sizeClasses[size].cost)}>
        {formatCurrency(costs.totalCost)}
        {isLoading && <span className="text-xs font-normal text-[var(--text-muted)] ml-1">...</span>}
      </span>
      {showDBUs && (
        <span className={clsx("text-[var(--text-muted)] tabular-nums", sizeClasses[size].dbu)}>
          {formatNumber(costs.monthlyDBUs)} DBUs/mo
        </span>
      )}
      {costs.monthlyDSUs > 0 && (
        <span className={clsx("text-purple-600 dark:text-purple-400 tabular-nums", sizeClasses[size].dbu)}>
          {formatNumber(costs.monthlyDSUs)} DSUs/mo
        </span>
      )}
    </div>
  )
})

// ============================================
// END SHARED COMPONENTS
// ============================================

// DBU Pricing ($/DBU) - PREMIUM tier fallback values
// Note: Actual prices come from pricing bundle or API, these are fallbacks
const DBU_PRICING: Record<string, Record<string, number>> = {
  aws: {
    'JOBS_COMPUTE': 0.15,
    'JOBS_COMPUTE_(PHOTON)': 0.15,  // Photon doesn't change $/DBU, only consumption
    'JOBS_SERVERLESS_COMPUTE': 0.39,  // Serverless has higher $/DBU
    'ALL_PURPOSE_COMPUTE': 0.40,
    'ALL_PURPOSE_COMPUTE_(PHOTON)': 0.40,
    'ALL_PURPOSE_SERVERLESS_COMPUTE': 0.83,  // All-Purpose Serverless
    'DLT_CORE_COMPUTE': 0.20,
    'DLT_PRO_COMPUTE': 0.25,
    'DLT_ADVANCED_COMPUTE': 0.30,
    'DLT_CORE_COMPUTE_(PHOTON)': 0.25,
    'DELTA_LIVE_TABLES_SERVERLESS': 0.30,
    'SQL_COMPUTE': 0.22,
    'SQL_PRO_COMPUTE': 0.55,
    'SERVERLESS_SQL_COMPUTE': 0.70,
    'SERVERLESS_REAL_TIME_INFERENCE': 0.07,  // AI Search, Model Serving, FMAPI Databricks
    'DATABASE_SERVERLESS_COMPUTE': 0.48  // Lakebase
  },
  azure: {
    'JOBS_COMPUTE': 0.15,
    'JOBS_COMPUTE_(PHOTON)': 0.15,
    'JOBS_SERVERLESS_COMPUTE': 0.39,
    'ALL_PURPOSE_COMPUTE': 0.40,
    'ALL_PURPOSE_COMPUTE_(PHOTON)': 0.40,
    'ALL_PURPOSE_SERVERLESS_COMPUTE': 0.83,
    'DLT_CORE_COMPUTE': 0.20,
    'DLT_PRO_COMPUTE': 0.25,
    'DLT_ADVANCED_COMPUTE': 0.30,
    'DLT_CORE_COMPUTE_(PHOTON)': 0.25,
    'DELTA_LIVE_TABLES_SERVERLESS': 0.30,
    'SQL_COMPUTE': 0.22,
    'SQL_PRO_COMPUTE': 0.55,
    'SERVERLESS_SQL_COMPUTE': 0.70,
    'SERVERLESS_REAL_TIME_INFERENCE': 0.07,  // AI Search, Model Serving, FMAPI Databricks
    'DATABASE_SERVERLESS_COMPUTE': 0.48  // Lakebase
  },
  gcp: {
    'JOBS_COMPUTE': 0.15,
    'JOBS_COMPUTE_(PHOTON)': 0.15,
    'JOBS_SERVERLESS_COMPUTE': 0.39,
    'ALL_PURPOSE_COMPUTE': 0.40,
    'ALL_PURPOSE_COMPUTE_(PHOTON)': 0.40,
    'ALL_PURPOSE_SERVERLESS_COMPUTE': 0.83,
    'DLT_CORE_COMPUTE': 0.20,
    'DLT_PRO_COMPUTE': 0.25,
    'DLT_ADVANCED_COMPUTE': 0.30,
    'DLT_CORE_COMPUTE_(PHOTON)': 0.25,
    'DELTA_LIVE_TABLES_SERVERLESS': 0.30,
    'SQL_COMPUTE': 0.22,
    'SQL_PRO_COMPUTE': 0.55,
    'SERVERLESS_SQL_COMPUTE': 0.70,
    'SERVERLESS_REAL_TIME_INFERENCE': 0.07,  // AI Search, Model Serving, FMAPI Databricks
    'DATABASE_SERVERLESS_COMPUTE': 0.48  // Lakebase
  }
}

const SERVERLESS_REAL_TIME_INFERENCE_WORKLOADS = new Set([
  'VECTOR_SEARCH',
  'MODEL_SERVING',
  'FMAPI_DATABRICKS',
  'AI_PARSE',
  'AI_EXTRACT',
  'AI_CLASSIFY',
  'AI_GATEWAY',
  'AGENT_EVALUATION',
  'SHUTTERSTOCK_IMAGEAI',
])

const formatDbuPrice = (workloadType: string, price: number): string =>
  SERVERLESS_REAL_TIME_INFERENCE_WORKLOADS.has(workloadType)
    ? price.toFixed(3)
    : price.toFixed(2)

// Note: Instance DBU rates are now fetched dynamically from instanceTypes
// The hardcoded INSTANCE_DBU_RATES has been replaced with lookups using instanceTypes.dbu_rate


// DBSQL warehouse DBU rates (keys must match database CHECK constraint: chk_dbsql_warehouse_size)
const DBSQL_DBU_RATES: Record<string, number> = {
  '2X-Small': 4, 'X-Small': 6, 'Small': 12, 'Medium': 24,
  'Large': 40, 'X-Large': 80, '2X-Large': 144, '3X-Large': 272, '4X-Large': 528
}

interface CostBreakdown {
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

function AIGatewayCostFormula({
  item,
  costs,
  dbuPriceDisplay,
}: {
  item: Partial<LineItem>
  costs: CostBreakdown
  dbuPriceDisplay: string
}) {
  const usage = calculateAIGatewayUsage(item)
  const components = [
    {
      label: 'Inference Tables',
      usage: usage.inferenceTables,
      requestKB: item.ai_gateway_inference_tables_avg_request_payload_kb ?? 1,
      responseKB: item.ai_gateway_inference_tables_avg_response_payload_kb ?? 1,
    },
    {
      label: 'Usage Tracking',
      usage: usage.usageTracking,
      requestKB: item.ai_gateway_usage_tracking_avg_request_payload_kb ?? 1,
      responseKB: item.ai_gateway_usage_tracking_avg_response_payload_kb ?? 1,
    },
  ].filter(component => component.usage.enabled)

  return (
    <div className="space-y-2">
      {components.map(component => {
        const subtotal = usage.monthlyDBUs > 0
          ? costs.totalCost * component.usage.monthlyDBUs / usage.monthlyDBUs
          : 0
        return (
          <div key={component.label} className="rounded border border-[var(--border-primary)] p-2 space-y-1">
            <div className="text-[10px] font-semibold text-[var(--text-secondary)]">{component.label}</div>
            <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
              {component.usage.inputMethod === 'payload_gb' ? (
                <span>Direct metered payload</span>
              ) : (
                <>
                  <span>{component.usage.requestsMillions.toLocaleString()}M requests</span>
                  <span>×</span>
                  <span>({component.requestKB} + {component.responseKB}) KB/request</span>
                  <span>=</span>
                </>
              )}
              <span className="font-medium">{formatNumber(component.usage.monthlyPayloadGB, 3)} GB</span>
              <span>×</span>
              <span>1.429 DBU/GB</span>
              <span>=</span>
              <span className="font-medium">{formatNumber(component.usage.monthlyDBUs, 3)} DBUs</span>
              <span>→</span>
              <span className="font-semibold">{formatCurrency(subtotal)}</span>
            </div>
          </div>
        )
      })}
      <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
        <span className="text-blue-600 font-semibold">Combined total:</span>
        <span>{formatNumber(costs.monthlyDBUs)} DBUs/mo</span>
        <span>×</span>
        <span>${dbuPriceDisplay}/DBU</span>
        <span>=</span>
        <span className="font-semibold">{formatCurrency(costs.totalCost)}</span>
      </div>
      <p className="text-[10px] text-[var(--text-muted)]">
        Direct GB is preferred when metered billable payload is known. Excludes underlying Model Serving/Foundation Model API inference and guardrail evaluator costs; add those as separate workloads.
      </p>
    </div>
  )
}

function AgentEvaluationCostFormula({
  item,
  costs,
  dbuPriceDisplay,
}: {
  item: Partial<LineItem>
  costs: CostBreakdown
  dbuPriceDisplay: string
}) {
  const usage = calculateAgentEvaluationUsage(item)
  const dbuPrice = costs.dbuPrice || 0

  return (
    <div className="space-y-2">
      {usage.labelsEnabled && (
        <div className="rounded border border-[var(--border-primary)] p-2 space-y-1">
          <div className="text-[10px] font-semibold text-[var(--text-secondary)]">Evaluation Labels</div>
          <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
            <span className="font-medium">{formatNumber(usage.inputTokensMillions, 3)}M input tokens</span>
            <span>×</span>
            <span>{AGENT_EVALUATION_COMPONENT_RATES.inputTokens.toFixed(3)} DBU/M</span>
            <span>=</span>
            <span className="font-medium">{formatNumber(usage.inputTokenDBUs, 3)} DBUs</span>
            <span>×</span>
            <span>${dbuPriceDisplay}/DBU</span>
            <span>=</span>
            <span className="font-semibold">{formatCurrency(usage.inputTokenDBUs * dbuPrice)}</span>
          </div>
          <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
            <span className="font-medium">{formatNumber(usage.outputTokensMillions, 3)}M output tokens</span>
            <span>×</span>
            <span>{AGENT_EVALUATION_COMPONENT_RATES.outputTokens.toFixed(3)} DBU/M</span>
            <span>=</span>
            <span className="font-medium">{formatNumber(usage.outputTokenDBUs, 3)} DBUs</span>
            <span>×</span>
            <span>${dbuPriceDisplay}/DBU</span>
            <span>=</span>
            <span className="font-semibold">{formatCurrency(usage.outputTokenDBUs * dbuPrice)}</span>
          </div>
          <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap pt-1 border-t border-dashed border-[var(--border-primary)]">
            <span className="font-semibold">Labels subtotal:</span>
            <span>{formatNumber(usage.evaluationTokenDBUs, 3)} DBUs</span>
            <span>×</span>
            <span>${dbuPriceDisplay}/DBU</span>
            <span>=</span>
            <span className="font-semibold">{formatCurrency(usage.evaluationTokenDBUs * dbuPrice)}</span>
          </div>
        </div>
      )}
      {usage.syntheticDataEnabled && (
        <div className="rounded border border-[var(--border-primary)] p-2 space-y-1">
          <div className="text-[10px] font-semibold text-[var(--text-secondary)]">Synthetic Data</div>
          <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
            <span className="font-medium">{usage.syntheticQuestions.toLocaleString()} questions</span>
            <span>×</span>
            <span>{AGENT_EVALUATION_COMPONENT_RATES.syntheticQuestions.toFixed(3)} DBU/question</span>
            <span>=</span>
            <span className="font-medium">{formatNumber(usage.syntheticQuestionDBUs, 3)} DBUs</span>
            <span>×</span>
            <span>${dbuPriceDisplay}/DBU</span>
            <span>=</span>
            <span className="font-semibold">{formatCurrency(usage.syntheticQuestionDBUs * dbuPrice)}</span>
          </div>
          <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap pt-1 border-t border-dashed border-[var(--border-primary)]">
            <span className="font-semibold">Synthetic subtotal:</span>
            <span>{formatNumber(usage.syntheticQuestionDBUs, 3)} DBUs</span>
            <span>×</span>
            <span>${dbuPriceDisplay}/DBU</span>
            <span>=</span>
            <span className="font-semibold">{formatCurrency(usage.syntheticQuestionDBUs * dbuPrice)}</span>
          </div>
        </div>
      )}
      <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
        <span className="text-blue-600 font-semibold">Combined total:</span>
        <span>{formatNumber(costs.monthlyDBUs, 3)} DBUs/mo</span>
        <span>×</span>
        <span>${dbuPriceDisplay}/DBU</span>
        <span>=</span>
        <span className="font-semibold">{formatCurrency(costs.totalCost)}</span>
      </div>
      <p className="text-[10px] text-[var(--text-muted)]">
        Evaluated application or model inference is excluded. Add it separately as a Model Serving or Foundation Model API workload.
      </p>
    </div>
  )
}

function AIRuntimeCostFormula({
  item,
  costs,
  cloud,
  dbuPriceDisplay,
}: {
  item: Partial<LineItem>
  costs: CostBreakdown
  cloud: string
  dbuPriceDisplay: string
}) {
  const isRunBased = Boolean(
    item.runs_per_day
    && item.avg_runtime_minutes
    && item.hours_per_month == null,
  )
  const runtimeHours = isRunBased
    ? (
        (item.runs_per_day || 0)
        * ((item.avg_runtime_minutes || 0) / 60)
        * (item.days_per_month || 22)
      )
    : (item.hours_per_month || 0)
  const usage = calculateAIRuntimeUsage(
    cloud,
    item.ai_runtime_accelerator_type,
    runtimeHours,
  )

  return (
    <div className="space-y-1">
      {isRunBased && (
        <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
          <span className="font-semibold">Runtime:</span>
          <span>{item.runs_per_day} runs/day</span>
          <span>×</span>
          <span>{item.avg_runtime_minutes} min/run</span>
          <span>÷ 60</span>
          <span>×</span>
          <span>{item.days_per_month || 22} days/mo</span>
          <span>=</span>
          <span className="font-medium">{formatNumber(runtimeHours, 3)} node-hours/mo</span>
        </div>
      )}
      <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
        <span className="text-blue-600 font-semibold">DBU:</span>
        <span className="font-medium">{formatNumber(runtimeHours, 3)} node-hours/mo</span>
        <span>×</span>
        <span>{usage.accelerator?.gpuCount || 0} GPU/node</span>
        <span>×</span>
        <span>{formatNumber(usage.accelerator?.dbuPerGpuHour || 0, 3)} DBU/GPU-hr</span>
        <span>=</span>
        <span className="font-medium">{formatNumber(costs.monthlyDBUs, 3)} DBUs/mo</span>
      </div>
      <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
        <span className="text-blue-600 font-semibold">Cost:</span>
        <span>{formatNumber(costs.monthlyDBUs, 3)} DBUs/mo</span>
        <span>×</span>
        <span>${dbuPriceDisplay}/DBU</span>
        <span>=</span>
        <span className="font-semibold">{formatCurrency(costs.totalCost)}</span>
      </div>
      <p className="text-[10px] text-[var(--text-muted)]">
        Billing origin AI_RUNTIME is charged on the MODEL_TRAINING SKU.
      </p>
    </div>
  )
}

function GeneralStorageCostFormula({
  item,
  costs,
  cloud,
  unitPrice,
}: {
  item: Partial<LineItem>
  costs: CostBreakdown
  cloud: string
  unitPrice: number
}) {
  const quantity = item.general_storage_quantity ?? 0
  const unit = (item.general_storage_unit ?? 'gb').toUpperCase()
  const billableGB = getGeneralStorageGB(item)
  const usage = calculateGeneralStorageDSU(item, cloud)
  return (
    <div className="space-y-1">
      <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
        <span>{quantity.toLocaleString()} {unit}/month</span>
        {unit === 'TB' && (
          <>
            <span>=</span>
            <span>{billableGB.toLocaleString()} GB-month</span>
          </>
        )}
      </div>
      <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
        <span className="text-purple-600 font-semibold">Stored Data:</span>
        <span>{billableGB.toLocaleString()} GB-month</span>
        <span>×</span>
        <span>1 DSU/GB-month</span>
        <span>=</span>
        <span>{formatNumber(usage.storedDataDSU, 4)} DSUs</span>
      </div>
      <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
        <span className="text-purple-600 font-semibold">Tier 1:</span>
        <span>{formatNumber(usage.tier1OperationsThousands, 3)}K operations</span>
        <span>×</span>
        <span>{usage.tier1DSUPerThousand} DSU/1K</span>
        <span>=</span>
        <span>{formatNumber(usage.tier1OperationsDSU, 4)} DSUs</span>
      </div>
      <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
        <span className="text-purple-600 font-semibold">Tier 2:</span>
        <span>{formatNumber(usage.tier2OperationsThousands, 3)}K operations</span>
        <span>×</span>
        <span>{usage.tier2DSUPerThousand} DSU/1K</span>
        <span>=</span>
        <span>{formatNumber(usage.tier2OperationsDSU, 4)} DSUs</span>
      </div>
      <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap pt-1 border-t border-dashed border-[var(--border-primary)]">
        <span>{formatNumber(costs.monthlyDSUs, 4)} DSUs</span>
        <span>×</span>
        <span>${unitPrice.toFixed(3)}/DSU</span>
        <span>=</span>
        <span className="font-semibold">{formatCurrency(costs.dsuCost)}</span>
      </div>
      <p className="text-[10px] text-[var(--text-muted)]">
        Tier 1 includes PUT, COPY, POST, and LIST. Tier 2 includes other API operations.
      </p>
    </div>
  )
}

function ZerobusCostFormula({
  item,
  costs,
  dbuPriceDisplay,
}: {
  item: Partial<LineItem>
  costs: CostBreakdown
  dbuPriceDisplay: string
}) {
  const usage = calculateZerobusUsage(item)
  const modeName = usage.mode === 'otel'
    ? 'Zerobus OTel Ingest'
    : 'Zerobus Ingest'
  return (
    <div className="space-y-1">
      <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
        <span className="text-blue-600 font-semibold">{modeName}:</span>
        <span>{formatNumber(usage.monthlyIngestedGB, 3)} GB/mo</span>
        <span>×</span>
        <span>{usage.dbuPerGB.toFixed(3)} DBU/GB</span>
        <span>=</span>
        <span className="font-medium">
          {formatNumber(usage.monthlyDBUs, 3)} DBUs/mo
        </span>
      </div>
      <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
        <span>{formatNumber(usage.monthlyDBUs, 3)} DBUs/mo</span>
        <span>×</span>
        <span>${dbuPriceDisplay}/DBU</span>
        <span>=</span>
        <span className="font-semibold">{formatCurrency(costs.dbuCost)}</span>
      </div>
      <p className="text-[10px] text-[var(--text-muted)]">
        Uses the regional Jobs Serverless list price. Producer compute,
        target storage, downstream processing, and transfer are excluded.
      </p>
    </div>
  )
}

function AISearchCostFormula({
  item,
  costs,
  dbuPriceDisplay,
}: {
  item: Partial<LineItem>
  costs: CostBreakdown
  dbuPriceDisplay: string
}) {
  const capacity = item.vector_capacity_millions || 1
  const mode = item.vector_search_mode || 'standard'
  const divisor = mode === 'storage_optimized' ? 64 : 2
  const unitsUsed = Math.ceil(capacity / divisor)
  const hoursPerMonth = item.hours_per_month || 730
  const dbuPerUnit = unitsUsed > 0
    ? (costs.dbuPerHour || (mode === 'storage_optimized' ? 18.29 : 4)) / unitsUsed
    : 0
  const servingDBUs = unitsUsed * dbuPerUnit * hoursPerMonth
  const reranker = calculateAISearchRerankerUsage(item)
  const dbuPrice = costs.dbuPrice || 0
  const storageGB = item.vector_search_storage_gb || 0
  const freeStorageGB = unitsUsed > 0 ? AI_SEARCH_INCLUDED_STORAGE_GB : 0
  const billableStorageGB = Math.max(0, storageGB - freeStorageGB)
  const storageDSUPerGB = getAISearchStorageDSUPerGB(mode)
  const storageDSUs = billableStorageGB * storageDSUPerGB
  const dsuPrice = costs.dsuPrice || 0
  const storageCost = storageDSUs * dsuPrice

  return (
    <div className="space-y-1">
      <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
        <span className="text-blue-600 font-semibold">Serving:</span>
        <span>⌈<span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{capacity}M</span> vectors ÷ {divisor}M⌉</span>
        <span>=</span>
        <span className="font-semibold">{unitsUsed} unit{unitsUsed !== 1 ? 's' : ''}</span>
        <span>×</span>
        <span>{dbuPerUnit.toFixed(2)} DBU/hr/unit</span>
        <span>×</span>
        <span>{hoursPerMonth}h</span>
        <span>=</span>
        <span>{formatNumber(servingDBUs, 3)} DBUs</span>
        <span>×</span>
        <span>${dbuPriceDisplay}/DBU</span>
        <span>=</span>
        <span className="text-blue-500 font-semibold">{formatCurrency(servingDBUs * dbuPrice)}</span>
      </div>
      {reranker.enabled && (
        <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
          <span className="text-rose-600 font-semibold">Reranker:</span>
          <span>{formatNumber(reranker.requestsThousands, 3)}K requests</span>
          <span>×</span>
          <span>{AI_SEARCH_RERANKER_DBU_PER_THOUSAND_REQUESTS.toFixed(3)} DBU/1K</span>
          <span>=</span>
          <span>{formatNumber(reranker.monthlyDBUs, 3)} DBUs</span>
          <span>×</span>
          <span>${dbuPriceDisplay}/DBU</span>
          <span>=</span>
          <span className="text-rose-500 font-semibold">{formatCurrency(reranker.monthlyDBUs * dbuPrice)}</span>
        </div>
      )}
      {storageGB > 0 && (
        <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
          <span className="text-purple-600 font-semibold">Storage:</span>
          <span>{storageGB} GB</span>
          <span>−</span>
          <span>{freeStorageGB} GB free</span>
          <span className="text-[var(--text-muted)]">(first 30 GB included)</span>
          <span>=</span>
          <span>{billableStorageGB} GB</span>
          <span>×</span>
          <span>{storageDSUPerGB} DSU/GB</span>
          <span>=</span>
          <span>{formatNumber(storageDSUs, 3)} DSUs</span>
          <span>×</span>
          <span>${dsuPrice.toFixed(3)}/DSU</span>
          <span>=</span>
          <span className="text-purple-500 font-semibold">{formatCurrency(storageCost)}</span>
        </div>
      )}
      <div className="flex items-center gap-1 text-[10px] font-mono flex-wrap pt-1 border-t border-dashed border-[var(--border-primary)]">
        <span className="text-[var(--text-secondary)] font-semibold">Total:</span>
        <span>{formatNumber(costs.monthlyDBUs, 3)} DBUs × ${dbuPriceDisplay}/DBU</span>
        {storageGB > 0 && (
          <>
            <span>+</span>
            <span>{formatCurrency(storageCost)} DSU</span>
          </>
        )}
        <span>=</span>
        <span className="text-[var(--text-primary)] font-medium">{formatCurrency(costs.totalCost)}</span>
      </div>
    </div>
  )
}

function SortableRow({ id, disabled, children }: { id: string; disabled?: boolean; children: React.ReactNode }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id, disabled })
  return (
    <div ref={setNodeRef} style={{ transform: CSS.Transform.toString(transform), transition, opacity: isDragging ? 0.5 : 1, zIndex: isDragging ? 50 : undefined, position: 'relative' as const }} {...attributes}>
      <div className="flex items-stretch">
        {!disabled && (
          <div {...listeners} className="flex items-center px-1 cursor-grab active:cursor-grabbing text-[var(--text-muted)] hover:text-[var(--text-secondary)] touch-none" title="Drag to reorder">
            <Bars3Icon className="w-3.5 h-3.5" />
          </div>
        )}
        <div className="flex-1 min-w-0">{children}</div>
      </div>
    </div>
  )
}

export default function Calculator() {
  const { id } = useParams()
  const navigate = useNavigate()
  const {
    currentEstimate,
    lineItems,
    workloadTypes,
    fetchEstimateWithLineItems,
    fetchReferenceData, // Still needed for manual refresh button
    clearReferenceCache,
    isLoadingReferenceData,
    isReferenceDataLoaded,
    regionsMap,
    getRegionsForCloud,
    createEstimate,
    updateEstimate,
    deleteEstimate,
    deleteLineItem,
    cloneLineItem,
    setSelectedCloud,
    setSelectedRegion,
    fetchVMCostForInstance,
    getVMPrice,
    getInstanceDbuRate,
    // VM pricing map - subscribe to trigger re-render when prices are fetched
    vmPricingMap,
    // Instance DBU Rate map - subscribe to trigger re-render when DBU rates are fetched
    instanceDbuRateMap,
    // DBU Rates
    dbuRatesMap,
    fetchDBURates,
    // Instance types for DBU rate lookup
    instanceTypes,
    // Photon multipliers
    photonMultipliers,
    // DBSQL sizes for warehouse DBU rates
    dbsqlSizes,
    // Model Serving GPU types for DBU rates
    modelServingGPUTypes,
    // AI Search modes for DBU rates
    vectorSearchModes,
    getVectorSearchRate,
    // FMAPI rates (cached lookups)
    getFMAPIDatabricksRate,
    getFMAPIProprietaryRate,
    // Pricing Bundle (for instant local calculations)
    pricingBundle,
    isPricingBundleLoaded,
    // NOTE: loadPricingBundle is now called in Layout.tsx at app startup
    // State management
    clearEstimateState,
    // Local cost sync (for AI Assistant)
    setLocalCalculatedCosts
  } = useStore()
  
  const [isSaving, setIsSaving] = useState(false)
  const [isExporting, setIsExporting] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [showWorkloadDeleteConfirm, setShowWorkloadDeleteConfirm] = useState(false)
  const [workloadToDelete, setWorkloadToDelete] = useState<LineItem | null>(null)
  const [showBulkDeleteConfirm, setShowBulkDeleteConfirm] = useState(false)
  const [isDeletingWorkload, setIsDeletingWorkload] = useState(false)
  const [showUnsavedChangesConfirm, setShowUnsavedChangesConfirm] = useState(false)
  const [showAddForm, setShowAddForm] = useState(false)
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set())
  const [formulaVisibleItems, setFormulaVisibleItems] = useState<Set<string>>(new Set())
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)
  
  // Pending form edits for real-time cost updates
  const [pendingFormEdits, setPendingFormEdits] = useState<Record<string, Partial<LineItem>>>({})
  const [isLoadingEstimate, setIsLoadingEstimate] = useState(false)
  const [isLoadingLineItems, setIsLoadingLineItems] = useState(false)
  const [lineItemsLoaded, setLineItemsLoaded] = useState(false)
  // Track VM cost loading to show proper loading state instead of "jumping" prices
  const [isLoadingVMCosts, setIsLoadingVMCosts] = useState(false)
  
  // Regions data (fetched from API based on cloud)
  const [regions, setRegions] = useState<RegionResponse[]>([])
  const [isLoadingRegions, setIsLoadingRegions] = useState(false)
  
  // Form state - using correct column names
  const [formData, setFormData] = useState({
    estimate_name: '',
    customer_name: '',
    cloud: 'aws',
    region: '',
    tier: '',  // No default - must be selected
    platform_addons: [] as PlatformAddonType[],
  })
  
  // Configuration panel collapsed state - auto-collapse for saved estimates
  const [isConfigCollapsed, setIsConfigCollapsed] = useState(!!id)
  
  // Cost summary panel collapsed state
  const [isCostSummaryCollapsed, setIsCostSummaryCollapsed] = useState(false)
  // Show workload breakdown in collapsed view
  const [showCollapsedBreakdown, setShowCollapsedBreakdown] = useState(false)
  
  // Workloads view mode: 'table' (default), 'cards' (compact), 'expanded'
  const [workloadsViewMode, setWorkloadsViewMode] = useState<'cards' | 'expanded' | 'table'>('table')
  const [sortField, setSortField] = useState<'order' | 'name' | 'type' | 'cost'>('order')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc')
  
  // Bulk selection for delete
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set())
  const [isBulkSelectMode, setIsBulkSelectMode] = useState(false)
  
  // Refs for workload cards - to enable click-to-scroll from Cost Summary
  const workloadRefs = useRef<Record<string, HTMLElement | null>>({})
  
  // Scroll to a specific workload
  const scrollToWorkload = useCallback((lineItemId: string) => {
    const ref = workloadRefs.current[lineItemId]
    if (ref) {
      ref.scrollIntoView({ behavior: 'smooth', block: 'center' })
      // Brief highlight effect - use background color instead of ring for better alignment
      ref.style.backgroundColor = 'rgba(255, 54, 33, 0.1)'
      ref.style.transition = 'background-color 0.3s ease'
      setTimeout(() => {
        if (workloadRefs.current[lineItemId]) {
          workloadRefs.current[lineItemId]!.style.backgroundColor = ''
        }
      }, 1500)
    }
  }, [])
  
  // Track changes
  const markAsChanged = useCallback(() => {
    setHasUnsavedChanges(true)
  }, [])
  
  // Browser beforeunload warning
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (hasUnsavedChanges) {
        e.preventDefault()
        e.returnValue = ''
      }
    }
    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => window.removeEventListener('beforeunload', handleBeforeUnload)
  }, [hasUnsavedChanges])
  
  // NOTE: fetchReferenceData() and loadPricingBundle() are now called in Layout.tsx at app startup
  // This significantly speeds up Calculator page load
  
  // NOTE: Removed bulk fetchVMPricing call (was loading 16+ MB of data)
  // VM pricing is now fetched on-demand via fetchVMCostForInstance for each selected instance type
  // This reduces data transfer from ~16 MB to ~1 KB per instance
  
  // Fetch VM costs for all unique instance types used in line items
  // This ensures VM pricing is available for cost calculations
  // NOTE: Also depends on lineItemsLoaded to ensure formData is populated from currentEstimate
  useEffect(() => {
    // Wait for estimate to be fully loaded (formData populated AND lineItems loaded)
    if (!formData.cloud || !formData.region || lineItems.length === 0 || !lineItemsLoaded) {
      return
    }
    
    // Collect all unique (instanceType, pricingTier) combinations from line items
    const fetchConfigs = new Set<string>()
    lineItems.forEach(item => {
      const effectiveItem = pendingFormEdits[item.line_item_id]
        ? { ...item, ...pendingFormEdits[item.line_item_id] }
        : item

      // Skip serverless workloads (no VM costs)
      if (effectiveItem.serverless_enabled) return
      
      // Handle DBSQL Classic/Pro warehouses - get instance types from warehouse config
      if (effectiveItem.workload_type === 'DBSQL' && (effectiveItem.dbsql_warehouse_type || '').toUpperCase() !== 'SERVERLESS') {
        const warehouseConfig = getBundleDBSQLWarehouseConfig(
          pricingBundle,
          formData.cloud,
          (effectiveItem.dbsql_warehouse_type || 'PRO').toUpperCase(),
          effectiveItem.dbsql_warehouse_size || 'Small'
        )
        
        if (warehouseConfig) {
          // Fetch driver instance type VM cost
          const driverTier = effectiveItem.dbsql_driver_pricing_tier || effectiveItem.driver_pricing_tier || 'on_demand'
          const driverPayment = effectiveItem.dbsql_driver_payment_option || effectiveItem.driver_payment_option || 'NA'
          fetchConfigs.add(`${warehouseConfig.driver_instance_type}:${driverTier}:${driverPayment}`)
          
          // Fetch worker instance type VM cost
          const workerTier = effectiveItem.dbsql_worker_pricing_tier || effectiveItem.worker_pricing_tier || 'on_demand'
          const workerPayment = effectiveItem.dbsql_worker_payment_option || effectiveItem.worker_payment_option || 'NA'
          fetchConfigs.add(`${warehouseConfig.worker_instance_type}:${workerTier}:${workerPayment}`)
        }
        return // Don't process driver_node_type/worker_node_type for DBSQL
      }
      
      // Driver pricing (for non-DBSQL workloads)
      if (effectiveItem.driver_node_type) {
        const driverTier = effectiveItem.driver_pricing_tier || 'on_demand'
        const driverPayment = effectiveItem.driver_payment_option || 'NA'
        fetchConfigs.add(`${effectiveItem.driver_node_type}:${driverTier}:${driverPayment}`)
      }
      
      // Worker pricing (for non-DBSQL workloads)
      if (effectiveItem.worker_node_type) {
        const workerTier = effectiveItem.worker_pricing_tier || 'spot'
        const workerPayment = effectiveItem.worker_payment_option || 'NA'
        fetchConfigs.add(`${effectiveItem.worker_node_type}:${workerTier}:${workerPayment}`)
      }
    })
    
    // Fetch VM costs for each unique configuration (async, non-blocking)
    // Uses Promise.all to batch all fetches and trigger single re-render when all complete
    const fetchPromises = Array.from(fetchConfigs).map(config => {
      const [instanceType, pricingTier, paymentOption] = config.split(':')
      return fetchVMCostForInstance(formData.cloud, formData.region, instanceType, pricingTier, paymentOption)
    })
    
    // Track loading state so UI can show "calculating" instead of partial costs
    if (fetchPromises.length > 0) {
      setIsLoadingVMCosts(true)
      // Race against a 10s timeout so the UI never shows "..." permanently
      const timeout = new Promise(resolve => setTimeout(resolve, 10000))
      Promise.race([Promise.all(fetchPromises), timeout])
        .catch(() => {})
        .finally(() => setIsLoadingVMCosts(false))
    }
  }, [formData.cloud, formData.region, lineItems, pendingFormEdits, lineItemsLoaded, fetchVMCostForInstance, pricingBundle])
  
  // Use cached regions from store (pre-loaded for all clouds)
  // Filter to only show regions that have actual Databricks control planes (i.e., regions in pricing bundle)
  useEffect(() => {
    if (!formData.cloud) return
    
    // Get regions from store cache (instant lookup)
    const cachedRegions = getRegionsForCloud(formData.cloud)
    
    if (cachedRegions.length > 0) {
      // Filter regions to only include those with control planes (in pricing bundle)
      // This ensures users can only select regions where Databricks is actually available
      const availableRegionsInBundle = isPricingBundleLoaded 
        ? getAvailableRegionsFromBundle(pricingBundle, formData.cloud)
        : []
      
      if (availableRegionsInBundle.length > 0) {
        // Filter cached regions to only those in the pricing bundle
        const filteredRegions = cachedRegions.filter(r => 
          availableRegionsInBundle.includes(r.region_code)
        )
        setRegions(filteredRegions)
      } else {
        // Bundle not loaded yet or no regions - show all cached regions as fallback
        setRegions(cachedRegions)
      }
      setIsLoadingRegions(false)
    } else if (!isReferenceDataLoaded) {
      // Still loading reference data
      setIsLoadingRegions(true)
    } else {
      // Reference data loaded but no regions for this cloud
      setRegions([])
      setIsLoadingRegions(false)
    }
  }, [formData.cloud, regionsMap, isReferenceDataLoaded, getRegionsForCloud, pricingBundle, isPricingBundleLoaded])
  
  useEffect(() => {
    const loadEstimateData = async () => {
      if (id) {
        setIsLoadingEstimate(true)
        setIsLoadingLineItems(true)
        setLineItemsLoaded(false)
        
        // Use combined endpoint for single round-trip (much faster)
        try {
          await fetchEstimateWithLineItems(id)
        } catch (error) {
          console.error('Error loading estimate data:', error)
        } finally {
          setIsLoadingEstimate(false)
          setIsLoadingLineItems(false)
          setLineItemsLoaded(true)
        }
      } else {
        // Creating new estimate - immediately clear any stale data from previous estimate
        clearEstimateState()
        setLineItemsLoaded(false)
      }
    }
    loadEstimateData()
  }, [id, fetchEstimateWithLineItems, clearEstimateState])
  
  // Default form values for new estimates
  const defaultEstimateFormData = {
    estimate_name: '',
    customer_name: '',
    cloud: 'aws',
    region: '',
    tier: '',
    platform_addons: [] as PlatformAddonType[],
  }

  useEffect(() => {
    if (currentEstimate && id) {
      // Editing existing estimate - load saved values
      setFormData({
        estimate_name: currentEstimate.estimate_name,
        customer_name: currentEstimate.customer_name || '',
        // Convert to lowercase for UI matching (DB stores uppercase)
        cloud: (currentEstimate.cloud || 'aws').toLowerCase(),
        region: currentEstimate.region || '',
        tier: (currentEstimate.tier || '').toLowerCase(),
        platform_addons: currentEstimate.discount_config?.platform_addons || [],
      })
      if (currentEstimate.cloud) {
        setSelectedCloud(currentEstimate.cloud.toLowerCase())
      }
      if (currentEstimate.region) {
        setSelectedRegion(currentEstimate.region)
      }
    } else if (!id) {
      // Creating new estimate - reset to defaults
      setFormData(defaultEstimateFormData)
      setSelectedCloud('aws')
      setHasUnsavedChanges(false)
    }
  }, [currentEstimate, id, setSelectedCloud, setSelectedRegion])
  
  // Fetch DBU rates when cloud/region/tier changes
  useEffect(() => {
    if (formData.cloud && formData.region && formData.tier) {
      fetchDBURates(formData.cloud.toUpperCase(), formData.region, formData.tier.toUpperCase())
    }
  }, [formData.cloud, formData.region, formData.tier, fetchDBURates])
  
  // NOTE: API cost calculation is disabled - using LOCAL calculations only for instant feedback
  // All reference data (instanceTypes, dbuRatesMap, vectorSearchModes, fmapiRates, etc.) is pre-fetched on app load
  // Benefits: No network latency, instant updates as user types, works offline
  // The calculateItemCost function below uses only cached data
  
  // Check if required fields are set for workload creation
  const canAddWorkload = Boolean(formData.region && formData.tier)
  
  // Calculate cost for a single line item with full breakdown
  // Uses LOCAL calculation for instant feedback - no API dependency
  // All reference data (instanceTypes, dbuRatesMap, vectorSearchModes, etc.) is pre-fetched
  // Supports pending form edits for real-time cost preview during editing
  const calculateItemCost = (item: LineItem, pendingEdits?: Partial<LineItem>): CostBreakdown => {
    // Merge saved item with pending edits for real-time calculation
    const effectiveItem = pendingEdits ? { ...item, ...pendingEdits } : item
    
    // ========================================================================
    // LOCAL CALCULATION - Instant feedback using pre-fetched reference data
    // All pricing data is fetched on app load: instanceTypes, dbuRatesMap, 
    // photonMultipliers, vectorSearchModes, fmapiDatabricksRates, etc.
    // Benefits: No network latency, instant updates (<1ms), works offline
    // ========================================================================
    // No network calls, no loading states, immediate results as user types
    const cloud = formData.cloud || 'aws'
    const region = formData.region // No default - must be set
    // Try to use dynamic DBU rates first, fall back to hardcoded
    const pricing = Object.keys(dbuRatesMap).length > 0 ? dbuRatesMap : (DBU_PRICING[cloud] || DBU_PRICING.aws)
    const numWorkers = effectiveItem.num_workers || 0
    
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
    
    // ========================================
    // Step 1: Calculate hours per month
    // Formula: runs_per_day * (avg_runtime_minutes / 60) * days_per_month
    // ========================================
    let hoursPerMonth = 0
    if (effectiveItem.workload_type !== 'FMAPI_DATABRICKS' && effectiveItem.workload_type !== 'FMAPI_PROPRIETARY') {
      if (effectiveItem.hours_per_month) {
        // Direct hours input
        hoursPerMonth = effectiveItem.hours_per_month
      } else if (effectiveItem.runs_per_day && effectiveItem.avg_runtime_minutes) {
        // Calculate from runs: runs_per_day * (avg_runtime_minutes / 60) * days_per_month
        hoursPerMonth = (effectiveItem.runs_per_day * (effectiveItem.avg_runtime_minutes / 60)) * (effectiveItem.days_per_month || 30)
      }
    }
    
    // ========================================
    // Step 2: Determine product_type_for_pricing (SKU)
    // Matches the SQL view's CASE logic
    // ========================================
    let productType = ''
    const dltEdition = (effectiveItem.dlt_edition || 'CORE').toUpperCase()
    
    switch (effectiveItem.workload_type) {
      case 'JOBS':
        if (effectiveItem.serverless_enabled) {
          productType = 'JOBS_SERVERLESS_COMPUTE'
        } else if (effectiveItem.photon_enabled) {
          productType = 'JOBS_COMPUTE_(PHOTON)'
        } else {
          productType = 'JOBS_COMPUTE'
        }
        break
      
      case 'ALL_PURPOSE':
        if (effectiveItem.serverless_enabled) {
          productType = 'ALL_PURPOSE_SERVERLESS_COMPUTE'
        } else if (effectiveItem.photon_enabled) {
          productType = 'ALL_PURPOSE_COMPUTE_(PHOTON)'
        } else {
          productType = 'ALL_PURPOSE_COMPUTE'
        }
        break
      
      case 'DLT':
        if (effectiveItem.serverless_enabled) {
          // DLT Serverless uses same rate as Jobs Serverless ($0.39)
          productType = 'JOBS_SERVERLESS_COMPUTE'
        } else {
          productType = `DLT_${dltEdition}_COMPUTE`
          if (effectiveItem.photon_enabled) {
            productType += '_(PHOTON)'
          }
        }
        break
      
      case 'DBSQL':
        const warehouseType = (effectiveItem.dbsql_warehouse_type || 'SERVERLESS').toUpperCase()
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
        productType = 'SERVERLESS_REAL_TIME_INFERENCE'
        break
      
      case 'FMAPI_PROPRIETARY':
        // Proprietary models use their provider-specific pricing
        // Note: Provider names must match the bundle keys (ANTHROPIC, OPENAI, GEMINI - not GOOGLE)
        const fmapiProvider = (effectiveItem.fmapi_provider || 'openai').toLowerCase()
        const providerMapping: Record<string, string> = {
          'google': 'GEMINI',  // Google uses GEMINI_MODEL_SERVING in the bundle
          'anthropic': 'ANTHROPIC',
          'openai': 'OPENAI'
        }
        productType = `${providerMapping[fmapiProvider] || fmapiProvider.toUpperCase()}_MODEL_SERVING`
        break
      
      case 'LAKEBASE':
        productType = 'DATABASE_SERVERLESS_COMPUTE'
        break

      case 'DATABRICKS_APPS':
        productType = 'ALL_PURPOSE_SERVERLESS_COMPUTE'
        break

      case 'AI_PARSE':
        productType = 'SERVERLESS_REAL_TIME_INFERENCE'
        break

      case 'AI_EXTRACT':
      case 'AI_CLASSIFY':
      case 'AI_GATEWAY':
      case 'AGENT_EVALUATION':
        productType = 'SERVERLESS_REAL_TIME_INFERENCE'
        break

      case 'SHUTTERSTOCK_IMAGEAI':
        productType = 'SERVERLESS_REAL_TIME_INFERENCE'
        break

      default:
        productType = 'JOBS_COMPUTE'
    }
    
    // Get DBU price for this product type
    // Try pricing bundle first (static data), then runtime dbuRatesMap, then hardcoded fallback
    let dbuPrice = 0.20
    if (
      effectiveItem.workload_type === 'AI_GATEWAY'
      || effectiveItem.workload_type === 'AGENT_EVALUATION'
      || effectiveItem.workload_type === 'AI_RUNTIME'
      || effectiveItem.workload_type === 'GENERAL_STORAGE'
      || effectiveItem.workload_type === 'ZEROBUS'
    ) {
      const exactSku = effectiveItem.workload_type === 'AI_RUNTIME'
        ? 'MODEL_TRAINING'
        : effectiveItem.workload_type === 'GENERAL_STORAGE'
          ? 'DATABRICKS_STORAGE'
          : effectiveItem.workload_type === 'ZEROBUS'
            ? 'JOBS_SERVERLESS_COMPUTE'
            : 'SERVERLESS_REAL_TIME_INFERENCE'
      const exactBundlePrice = isPricingBundleLoaded && formData.tier
        ? getExactRegionalDBUPrice(
            pricingBundle,
            cloud,
            region,
            formData.tier,
            exactSku,
          )
        : null
      dbuPrice = exactBundlePrice ?? dbuRatesMap[exactSku] ?? 0
    } else if (isPricingBundleLoaded && formData.tier) {
      const bundlePrice = getBundleDBUPrice(pricingBundle, cloud, region, formData.tier, productType)
      if (bundlePrice > 0) {
        dbuPrice = bundlePrice
      } else {
        dbuPrice = pricing[productType] || 0.20
      }
    } else {
      dbuPrice = pricing[productType] || 0.20
    }
    let dsuPrice = isPricingBundleLoaded && formData.tier
      ? (
          getExactRegionalDBUPrice(
            pricingBundle,
            cloud,
            region,
            formData.tier,
            'DATABRICKS_STORAGE',
          ) ?? dbuRatesMap.DATABRICKS_STORAGE ?? 0
        )
      : (dbuRatesMap.DATABRICKS_STORAGE ?? 0)
    if (effectiveItem.workload_type === 'GENERAL_STORAGE') {
      dsuPrice = dbuPrice
    }
    
    // ========================================
    // Step 3: Calculate DBU per hour based on workload type
    // Uses fetched instanceTypes for current DBU rates
    // ========================================
    let dbuPerHour = 0
    let monthlyDBUs = 0
    let monthlyDSUs = 0
    let dsuCost = 0
    let vmCost = 0
    let unitsUsed: number | undefined = undefined  // For AI Search
    let storageCost: number | undefined = undefined  // For AI Search and Lakebase
    let storageDetails: CostBreakdown['storageDetails'] = undefined
    
    // Use the legacy fallback only for a selected but unknown instance.
    // An empty node selection contributes no hidden DBUs.
    let driverDBURate = effectiveItem.driver_node_type ? 0.5 : 0
    let workerDBURate = effectiveItem.worker_node_type ? 0.5 : 0
    
    if (isPricingBundleLoaded && effectiveItem.driver_node_type) {
      const bundleDriverRate = getBundleInstanceDBURate(pricingBundle, cloud, effectiveItem.driver_node_type)
      if (bundleDriverRate > 0) driverDBURate = bundleDriverRate
    }
    if (effectiveItem.driver_node_type && driverDBURate === 0.5) {
      const driverInstance = instanceTypes.find(it => it.id === effectiveItem.driver_node_type || it.name === effectiveItem.driver_node_type)
      if (driverInstance?.dbu_rate) driverDBURate = driverInstance.dbu_rate
    }
    
    if (isPricingBundleLoaded && effectiveItem.worker_node_type) {
      const bundleWorkerRate = getBundleInstanceDBURate(pricingBundle, cloud, effectiveItem.worker_node_type)
      if (bundleWorkerRate > 0) workerDBURate = bundleWorkerRate
    }
    if (effectiveItem.worker_node_type && workerDBURate === 0.5) {
      const workerInstance = instanceTypes.find(it => it.id === effectiveItem.worker_node_type || it.name === effectiveItem.worker_node_type)
      if (workerInstance?.dbu_rate) workerDBURate = workerInstance.dbu_rate
    }
    
    // Get photon multiplier - try pricing bundle first, then fetched photonMultipliers
    // NOTE: For serverless workloads, photon is ALWAYS enabled (built-in)
    const getPhotonMultiplierValue = (): number => {
      // For classic workloads, only apply if photon is explicitly enabled
      if (!effectiveItem.serverless_enabled && !effectiveItem.photon_enabled) return 1.0
      
      // For SERVERLESS workloads, use the corresponding CLASSIC SKU type for photon lookup
      // The photon multiplier for serverless is the same as classic (photon is built-in)
      let skuTypeForLookup: string
      if (effectiveItem.serverless_enabled) {
        if (effectiveItem.workload_type === 'JOBS') {
          skuTypeForLookup = 'JOBS_COMPUTE'
        } else if (effectiveItem.workload_type === 'ALL_PURPOSE') {
          skuTypeForLookup = 'ALL_PURPOSE_COMPUTE'
        } else if (effectiveItem.workload_type === 'DLT') {
          // DLT serverless uses JOBS_SERVERLESS_COMPUTE for pricing, but photon from DLT_CORE_COMPUTE
          skuTypeForLookup = 'DLT_CORE_COMPUTE'
        } else {
          skuTypeForLookup = productType.replace('_(PHOTON)', '')
        }
      } else {
        // For classic, strip _(PHOTON) suffix but keep _COMPUTE suffix
        skuTypeForLookup = productType.replace('_(PHOTON)', '')
      }
      
      // Try pricing bundle first
      if (isPricingBundleLoaded) {
        const bundleMultiplier = getBundlePhotonMultiplier(pricingBundle, cloud, skuTypeForLookup)
        if (bundleMultiplier !== 2.0) return bundleMultiplier // 2.0 is the fallback in bundle helper
      }
      
      // Fall back to fetched photonMultipliers
      const multiplierEntry = photonMultipliers.find(pm => 
        pm.sku_type === skuTypeForLookup || 
        pm.sku_type?.toLowerCase() === skuTypeForLookup.toLowerCase() ||
        pm.sku_type?.toLowerCase().includes((item.workload_type || '').toLowerCase())
      )
      return multiplierEntry?.multiplier || 2.0 // Fallback to 2.0 (typical photon multiplier)
    }
    const photonMultiplier = getPhotonMultiplierValue()
    
    // Serverless mode multiplier (performance = 2x, standard = 1x)
    // Note: All-Purpose Serverless ONLY supports Performance mode (always 2x)
    // Jobs/DLT Serverless support both Standard (1x) and Performance (2x)
    const serverlessMultiplier = !effectiveItem.serverless_enabled ? 1 
      : (effectiveItem.workload_type === 'ALL_PURPOSE') ? 2  // All-Purpose Serverless is always Performance (2x)
      : (effectiveItem.serverless_mode === 'performance') ? 2 : 1
    
    // DLT multiplier (varies by edition for classic DLT)
    const getDLTMultiplier = () => {
      if (effectiveItem.workload_type !== 'DLT') return 1.0
      // DLT has edition-based pricing, the multiplier is baked into the DBU price
      return 1.0
    }
    const dltMultiplier = getDLTMultiplier()
    
    switch (effectiveItem.workload_type) {
      case 'ALL_PURPOSE':
      case 'JOBS':
        if (effectiveItem.serverless_enabled) {
          // Serverless: DBU/Hour = base_dbu_rate × photon_multiplier (always on) × serverless_multiplier
          // Photon is ALWAYS enabled in serverless (built-in)
          // serverlessMultiplier: standard=1x, performance=2x
          dbuPerHour = (driverDBURate + (workerDBURate * numWorkers)) * photonMultiplier * serverlessMultiplier
        } else {
          // Classic: DBU/Hour = (driver_dbu_rate + worker_dbu_rate × num_workers) × photon_multiplier
          dbuPerHour = (driverDBURate + (workerDBURate * numWorkers)) * photonMultiplier
          
          // VM costs for classic compute
          const driverPricingTier = effectiveItem.driver_pricing_tier || 'on_demand'
          const driverPaymentOption = effectiveItem.driver_payment_option || 'NA'
          const workerPricingTier = effectiveItem.worker_pricing_tier || 'spot'
          const workerPaymentOption = effectiveItem.worker_payment_option || 'NA'
          
          // Driver VM cost/hour
          const driverVMCostPerHour = getVMPrice(cloud, region, effectiveItem.driver_node_type || '', driverPricingTier, driverPaymentOption)
          
          // Worker VM cost/hour
          const workerVMCostPerHour = getVMPrice(cloud, region, effectiveItem.worker_node_type || '', workerPricingTier, workerPaymentOption)
          
          // VM Cost/Month = VM Cost/Hour × Hours/Month
          const totalVMCostPerHour = driverVMCostPerHour + (workerVMCostPerHour * numWorkers)
          vmCost = totalVMCostPerHour * hoursPerMonth
        }
        // DBU/Month = DBU/Hour × Hours/Month
        monthlyDBUs = dbuPerHour * hoursPerMonth
        break
      
      case 'DLT':
        if (effectiveItem.serverless_enabled) {
          // DLT Serverless: DBU/Hour = base_dbu_rate × photon (always on) × dlt_multiplier × serverless_multiplier
          // Photon is ALWAYS enabled in serverless (built-in)
          dbuPerHour = (driverDBURate + (workerDBURate * numWorkers)) * photonMultiplier * dltMultiplier * serverlessMultiplier
        } else {
          // DLT Classic: DBU/Hour = (driver_dbu + worker_dbu × workers) × photon_multiplier × dlt_multiplier
          dbuPerHour = (driverDBURate + (workerDBURate * numWorkers)) * photonMultiplier * dltMultiplier
          
          // VM costs for classic compute
          const driverPricingTier = effectiveItem.driver_pricing_tier || 'on_demand'
          const driverPaymentOption = effectiveItem.driver_payment_option || 'NA'
          const workerPricingTier = effectiveItem.worker_pricing_tier || 'spot'
          const workerPaymentOption = effectiveItem.worker_payment_option || 'NA'
          
          const driverVMCostPerHour = getVMPrice(cloud, region, effectiveItem.driver_node_type || '', driverPricingTier, driverPaymentOption)
          const workerVMCostPerHour = getVMPrice(cloud, region, effectiveItem.worker_node_type || '', workerPricingTier, workerPaymentOption)
          
          const totalVMCostPerHour = driverVMCostPerHour + (workerVMCostPerHour * numWorkers)
          vmCost = totalVMCostPerHour * hoursPerMonth
        }
        monthlyDBUs = dbuPerHour * hoursPerMonth
        break
      
      case 'DBSQL':
        // DBSQL: lookup DBU per hour from warehouse size
        // Try pricing bundle first, then fetched dbsqlSizes, then hardcoded fallback
        const dbsqlWarehouseType = (effectiveItem.dbsql_warehouse_type || 'SERVERLESS').toUpperCase()
        const warehouseSize = effectiveItem.dbsql_warehouse_size || 'Small'
        const numClusters = effectiveItem.dbsql_num_clusters || 1
        
        let warehouseDBUs = DBSQL_DBU_RATES[warehouseSize] || 12 // Default fallback
        
        // Try pricing bundle for DBSQL rate
        if (isPricingBundleLoaded) {
          const bundleDbsqlRate = getBundleDBSQLRate(pricingBundle, cloud, dbsqlWarehouseType, warehouseSize)
          if (bundleDbsqlRate && bundleDbsqlRate.dbu_per_hour > 0) {
            warehouseDBUs = bundleDbsqlRate.dbu_per_hour
          }
        }
        
        // Fall back to fetched dbsqlSizes
        if (!warehouseDBUs || warehouseDBUs === (DBSQL_DBU_RATES[warehouseSize] || 12)) {
          const dbsqlSize = dbsqlSizes.find(s => s.id === warehouseSize || s.name === warehouseSize)
          if (dbsqlSize?.dbu_per_hour) warehouseDBUs = dbsqlSize.dbu_per_hour
        }
        
        // DBU/Hour = warehouse_dbu_rate × num_clusters
        dbuPerHour = warehouseDBUs * numClusters
        monthlyDBUs = dbuPerHour * hoursPerMonth
        
        // VM costs only for CLASSIC and PRO (not SERVERLESS)
        if (dbsqlWarehouseType !== 'SERVERLESS') {
          // Try to get warehouse config from pricing bundle for VM details
          const warehouseConfig = isPricingBundleLoaded 
            ? getBundleDBSQLWarehouseConfig(pricingBundle, cloud, dbsqlWarehouseType, warehouseSize)
            : null
          
          if (warehouseConfig) {
            // Use config from bundle: driver + workers VM costs
            // DBSQL has separate driver and worker pricing tier selections
            const dbsqlDriverPricingTier = effectiveItem.dbsql_driver_pricing_tier || effectiveItem.driver_pricing_tier || 'on_demand'
            const dbsqlDriverPaymentOption = effectiveItem.dbsql_driver_payment_option || effectiveItem.driver_payment_option || 'NA'
            const dbsqlWorkerPricingTier = effectiveItem.dbsql_worker_pricing_tier || effectiveItem.worker_pricing_tier || 'spot'
            const dbsqlWorkerPaymentOption = effectiveItem.dbsql_worker_payment_option || effectiveItem.worker_payment_option || 'NA'
            
            const driverVMCost = getVMPrice(cloud, region, warehouseConfig.driver_instance_type, dbsqlDriverPricingTier, dbsqlDriverPaymentOption)
            const workerVMCost = getVMPrice(cloud, region, warehouseConfig.worker_instance_type, dbsqlWorkerPricingTier, dbsqlWorkerPaymentOption)
            
            // VM Cost/Hour = (driver_count × driver_vm + worker_count × worker_vm) × num_clusters
            const dbsqlVMCostPerHour = (
              (warehouseConfig.driver_count * driverVMCost) + 
              (warehouseConfig.worker_count * workerVMCost)
            ) * numClusters
            vmCost = dbsqlVMCostPerHour * hoursPerMonth
          } else if (effectiveItem.driver_node_type) {
            // Fallback: use driver/worker node types if specified
            const dbsqlDriverPricingTier = effectiveItem.dbsql_driver_pricing_tier || effectiveItem.driver_pricing_tier || 'on_demand'
            const dbsqlDriverPaymentOption = effectiveItem.dbsql_driver_payment_option || effectiveItem.driver_payment_option || 'NA'
            const dbsqlWorkerPricingTier = effectiveItem.dbsql_worker_pricing_tier || effectiveItem.worker_pricing_tier || 'spot'
            const dbsqlWorkerPaymentOption = effectiveItem.dbsql_worker_payment_option || effectiveItem.worker_payment_option || 'NA'
            
            const dbsqlDriverVMCost = getVMPrice(cloud, region, effectiveItem.driver_node_type, dbsqlDriverPricingTier, dbsqlDriverPaymentOption)
            const dbsqlWorkerVMCost = effectiveItem.worker_node_type 
              ? getVMPrice(cloud, region, effectiveItem.worker_node_type, dbsqlWorkerPricingTier, dbsqlWorkerPaymentOption)
              : 0
            const dbsqlNumWorkers = effectiveItem.num_workers || 0
            
            const dbsqlVMCostPerHour = (dbsqlDriverVMCost + (dbsqlWorkerVMCost * dbsqlNumWorkers)) * numClusters
            vmCost = dbsqlVMCostPerHour * hoursPerMonth
          }
        }
        // SERVERLESS: No VM costs
        break
      
      case 'VECTOR_SEARCH':
        // AI Search: Units = CEILING(vector_capacity / divisor)
        // Standard: 2M vectors per unit, 4.00 DBU/hour per unit
        // Storage Optimized: 64M vectors per unit, 18.29 DBU/hour per unit
        const vectorMode = effectiveItem.vector_search_mode || 'standard'
        const vectorCapacity = effectiveItem.vector_capacity_millions || 1
        
        // Try pricing bundle first, then fetched data, then defaults
        let vectorDivisor = vectorMode === 'storage_optimized' ? 64000000 : 2000000  // Default divisors
        let vectorModeDBURate = vectorMode === 'storage_optimized' ? 18.29 : 4  // Default DBU rates
        
        if (isPricingBundleLoaded) {
          const bundleVectorRate = getBundleVectorSearchRate(pricingBundle, cloud, vectorMode)
          if (bundleVectorRate) {
            vectorDivisor = bundleVectorRate.input_divisor
            vectorModeDBURate = bundleVectorRate.dbu_rate
          }
        } else {
          // Fall back to fetched vectorSearchModes
          const vectorRateData = getVectorSearchRate(vectorMode)
          if (vectorRateData) {
            vectorDivisor = vectorRateData.input_divisor
            vectorModeDBURate = vectorRateData.dbu_per_hour
          }
        }
        
        // Convert vector capacity from millions to total vectors
        const vectorsTotal = vectorCapacity * 1000000
        const vectorUnitsUsed = Math.ceil(vectorsTotal / vectorDivisor)
        unitsUsed = vectorUnitsUsed  // Store for return
        
        // DBU/Hour = units_used × mode_dbu_rate
        dbuPerHour = vectorUnitsUsed * vectorModeDBURate
        monthlyDBUs = (
          dbuPerHour * hoursPerMonth
          + calculateAISearchRerankerUsage(effectiveItem).monthlyDBUs
        )
        
        // Storage calculation for AI Search
        // The first 30 GB of storage is included
        // Billable Storage = MAX(0, storage_gb - free_storage_gb)
        // Storage Cost = billable GB × 10 DSU/GB × exact regional $/DSU.
        const vectorStorageGB = effectiveItem.vector_search_storage_gb || 0
        const vectorFreeStorageGB = vectorUnitsUsed > 0
          ? AI_SEARCH_INCLUDED_STORAGE_GB
          : 0
        const vectorBillableStorageGB = Math.max(0, vectorStorageGB - vectorFreeStorageGB)
        const vectorStorageDSUPerGB = getAISearchStorageDSUPerGB(
          effectiveItem.vector_search_mode,
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
        // Model Serving: DBU/Hour = gpu_type_dbu_rate
        const gpuType = effectiveItem.model_serving_gpu_type || 'cpu'
        
        // Try pricing bundle first, then fetched data, then default
        let gpuDBURate = 2 // Default fallback
        
        if (isPricingBundleLoaded) {
          const bundleGpuRate = getBundleModelServingRate(pricingBundle, cloud, gpuType)
          if (bundleGpuRate && bundleGpuRate.dbu_rate > 0) {
            gpuDBURate = bundleGpuRate.dbu_rate
          }
        }
        
        // Fall back to fetched modelServingGPUTypes
        if (gpuDBURate === 2) {
          const gpuTypeData = modelServingGPUTypes.find(g => g.id === gpuType || g.name === gpuType)
          if (gpuTypeData?.dbu_per_hour) gpuDBURate = gpuTypeData.dbu_per_hour
        }
        
        // GPU rates are per replica (one replica per four concurrency units).
        // CPU rates remain per concurrency unit.
        const msScaleOutCalc = effectiveItem.model_serving_scale_out || 'small'
        const msPresets: Record<string, number> = { small: 4, medium: 12, large: 40 }
        const msConcurrencyCalc = msScaleOutCalc === 'custom'
          ? (effectiveItem.model_serving_concurrency || 4)
          : (msPresets[msScaleOutCalc] || 4)

        dbuPerHour = calculateModelServingDBUPerHour(
          gpuDBURate,
          gpuType,
          msConcurrencyCalc,
        )
        monthlyDBUs = dbuPerHour * hoursPerMonth
        break

      case 'LAKEBASE':
        // LAKEBASE (Managed PostgreSQL)
        // Formula: discounted minimum CU floor + full-price autoscale headroom
        // dbu_per_cu_hour varies by cloud/tier (0.230 for AWS Premium, 0.213 for Enterprise/Azure)
        const lakebaseNodes = effectiveItem.lakebase_ha_nodes || 1  // 1 primary + up to 3 read replicas
        const lakebaseDBURates: Record<string, Record<string, number>> = {
          'aws': { 'PREMIUM': 0.230, 'ENTERPRISE': 0.213 },
          'azure': { 'PREMIUM': 0.213, 'ENTERPRISE': 0.213 },
        }
        const lakebaseCloudRates = lakebaseDBURates[cloud] || lakebaseDBURates['aws']
        const lakebaseDBUPerCU = lakebaseCloudRates[(formData.tier || 'PREMIUM').toUpperCase()] || 0.213

        const lakebaseAutoscaleConfig = resolveLakebaseAutoscaleConfig(effectiveItem)
        const lakebaseComputeUsage = calculateLakebaseComputeUsage(
          lakebaseAutoscaleConfig,
          lakebaseDBUPerCU,
          lakebaseNodes,
        )
        dbuPerHour = lakebaseComputeUsage.equivalentDbuPerHour
        monthlyDBUs = lakebaseComputeUsage.totalBillableDbu
        
        // Storage calculation for Lakebase (DSU-based pricing)
        // Storage: 15x DSU/GB, PITR: 8.7x DSU/GB, Snapshots: 3.91x DSU/GB
        // Cost = GB × DSU multiplier × exact regional $/DSU.
        const lakebaseStorageGB = Math.min(effectiveItem.lakebase_storage_gb || 0, 8192)
        const lakebasePitrGB = effectiveItem.lakebase_pitr_gb || 0
        const lakebaseSnapshotGB = effectiveItem.lakebase_snapshot_gb || 0
        const lakebaseStorageDSU = lakebaseStorageGB * 15
        const lakebasePitrDSU = lakebasePitrGB * 8.7
        const lakebaseSnapshotDSU = lakebaseSnapshotGB * 3.91
        monthlyDSUs = (
          lakebaseStorageDSU
          + lakebasePitrDSU
          + lakebaseSnapshotDSU
        )
        const lakebaseStorageCost = lakebaseStorageDSU * dsuPrice
        const lakebasePitrCost = lakebasePitrDSU * dsuPrice
        const lakebaseSnapshotCost = lakebaseSnapshotDSU * dsuPrice
        const lakebaseTotalStorageCost = lakebaseStorageCost + lakebasePitrCost + lakebaseSnapshotCost

        if (lakebaseTotalStorageCost > 0) {
          dsuCost = lakebaseTotalStorageCost
          storageCost = lakebaseTotalStorageCost
          storageDetails = {
            totalStorageGB: lakebaseStorageGB,
            billableStorageGB: lakebaseStorageGB,
            dsuPerGB: 15,
            totalDSU: monthlyDSUs,
            pricePerDSU: dsuPrice
          }
        }
        break
      
      case 'FMAPI_DATABRICKS':
        // Foundation Models (Databricks) - llama, gpt-oss, gemma, bge, gte, etc.
        const fmapiDbxQuantity = effectiveItem.fmapi_quantity || 0
        const fmapiDbxRateType = effectiveItem.fmapi_rate_type || 'input_token'
        const fmapiDbxIsProvisioned = fmapiDbxRateType.startsWith('provisioned_')
        
        // Try pricing bundle first
        let dbxDbuRate: number | null = null
        
        if (isPricingBundleLoaded && effectiveItem.fmapi_model) {
          const bundleDbxRate = getBundleFMAPIDatabricksRate(
            pricingBundle,
            cloud,
            effectiveItem.fmapi_model,
            fmapiDbxRateType,
            region,
            effectiveItem.fmapi_endpoint_type || 'global',
          )
          if (bundleDbxRate) {
            dbxDbuRate = bundleDbxRate.dbu_rate
          }
        }
        
        // Fall back to store's cached rate
        if (
          dbxDbuRate === null
          && !isPricingBundleLoaded
          && effectiveItem.fmapi_model
        ) {
          const dbxRateData = getFMAPIDatabricksRate(effectiveItem.fmapi_model, fmapiDbxRateType)
          if (dbxRateData) {
            if (fmapiDbxIsProvisioned) {
              dbxDbuRate = dbxRateData.dbu_per_hour || null
            } else {
              dbxDbuRate = dbxRateData.dbu_per_1M_tokens || null
            }
          }
        }
        
        // Unsupported combinations must not silently use another model's rate.
        if (dbxDbuRate === null) dbxDbuRate = 0
        
        monthlyDBUs = fmapiDbxQuantity * dbxDbuRate
        break
      
      case 'FMAPI_PROPRIETARY':
        // Foundation Models (Proprietary) - OpenAI, Anthropic, Google
        const fmapiPropQuantity = effectiveItem.fmapi_quantity || 0
        const fmapiPropRateType = effectiveItem.fmapi_rate_type || 'input_token'
        const fmapiPropIsProvisioned = fmapiPropRateType === 'batch_inference'
        
        // Try pricing bundle first
        let propDbuRate: number | null = null
        
        if (isPricingBundleLoaded && effectiveItem.fmapi_provider && effectiveItem.fmapi_model) {
          // Bundle key format: "cloud:provider:model:endpoint_type:context_length:rate_type"
          // Use defaults for endpoint_type and context_length if not specified
          const endpointType = effectiveItem.fmapi_endpoint_type || 'global'
          const contextLength = effectiveItem.fmapi_context_length || 'long'
          const bundlePropRate = getBundleFMAPIProprietaryRate(
            pricingBundle, cloud, effectiveItem.fmapi_provider, effectiveItem.fmapi_model, 
            endpointType, contextLength, fmapiPropRateType
          )
          if (bundlePropRate) {
            propDbuRate = bundlePropRate.dbu_rate
          }
        }
        
        // Fall back to store's cached rate
        if (
          propDbuRate === null
          && !isPricingBundleLoaded
          && effectiveItem.fmapi_provider
          && effectiveItem.fmapi_model
        ) {
          const propRateData = getFMAPIProprietaryRate(effectiveItem.fmapi_provider, effectiveItem.fmapi_model, fmapiPropRateType)
          if (propRateData) {
            if (fmapiPropIsProvisioned) {
              propDbuRate = propRateData.dbu_per_hour || null
            } else {
              propDbuRate = propRateData.dbu_per_1M_tokens || null
            }
          }
        }
        
        // Unsupported combinations must not silently use another model's rate.
        if (propDbuRate === null) propDbuRate = 0
        
        monthlyDBUs = fmapiPropQuantity * propDbuRate
        break

      case 'DATABRICKS_APPS': {
        const appsSize = (effectiveItem.databricks_apps_size || 'medium').toLowerCase()
        const appsDbuRates: Record<string, number> = { medium: 0.5, large: 1.0 }
        dbuPerHour = appsDbuRates[appsSize] || 0.5
        monthlyDBUs = dbuPerHour * hoursPerMonth
        break
      }

      case 'AI_RUNTIME': {
        const usage = calculateAIRuntimeUsage(
          cloud,
          effectiveItem.ai_runtime_accelerator_type,
          hoursPerMonth,
        )
        dbuPerHour = usage.dbuPerNodeHour
        monthlyDBUs = usage.monthlyDBUs
        break
      }

      case 'GENERAL_STORAGE': {
        const storageGB = getGeneralStorageGB(effectiveItem)
        const usage = calculateGeneralStorageDSU(effectiveItem, cloud)
        monthlyDSUs = usage.totalDSU
        dsuCost = monthlyDSUs * dsuPrice
        storageCost = dsuCost
        storageDetails = {
          totalStorageGB: storageGB,
          billableStorageGB: storageGB,
          dsuPerGB: 1,
          totalDSU: monthlyDSUs,
          pricePerDSU: dsuPrice,
        }
        break
      }

      case 'AI_PARSE': {
        // Pages-based mode: pages(K) × complexity_rate
        const complexityRates: Record<string, number> = {
          'low_text': 12.5, 'low_images': 22.5, 'medium': 62.5, 'high': 87.5
        }
        const complexity = (effectiveItem.ai_parse_complexity || 'medium').toLowerCase()
        const pagesK = effectiveItem.ai_parse_pages_thousands || 0
        monthlyDBUs = pagesK * (complexityRates[complexity] || 62.5)
        break
      }

      case 'AI_EXTRACT': {
        // inputs(K) x document-type rate
        const extractRates: Record<string, number> = {
          short_text: 45,
          invoice: 45,
          complex_reasoning: 562.5,
          deep_nesting: 537.5,
        }
        const docType = (effectiveItem.ai_extract_document_type || 'invoice').toLowerCase()
        const rate = docType === 'custom'
          ? (effectiveItem.ai_extract_dbus_per_thousand || 0)
          : (extractRates[docType] || 45)
        monthlyDBUs = ((effectiveItem.ai_extract_num_inputs || 0) / 1000) * rate
        break
      }

      case 'AI_CLASSIFY': {
        // docs(K) x document-type rate
        const classifyRates: Record<string, number> = {
          short_text: 4.5,
          rental_contract: 50,
        }
        const docType = (effectiveItem.ai_classify_document_type || 'short_text').toLowerCase()
        const rate = docType === 'custom'
          ? (effectiveItem.ai_classify_dbus_per_thousand || 0)
          : (classifyRates[docType] || 4.5)
        monthlyDBUs = ((effectiveItem.ai_classify_num_docs || 0) / 1000) * rate
        break
      }

      case 'AI_GATEWAY': {
        monthlyDBUs = calculateAIGatewayUsage(effectiveItem).monthlyDBUs
        break
      }

      case 'AGENT_EVALUATION': {
        monthlyDBUs = calculateAgentEvaluationUsage(effectiveItem).monthlyDBUs
        break
      }

      case 'ZEROBUS': {
        monthlyDBUs = calculateZerobusUsage(effectiveItem).monthlyDBUs
        break
      }

      case 'SHUTTERSTOCK_IMAGEAI': {
        // 0.857 DBU per image
        const imageCount = effectiveItem.shutterstock_images || 0
        monthlyDBUs = imageCount * 0.857
        break
      }

      default:
        monthlyDBUs = 0
    }
    
    // ========================================
    // Step 4: Calculate final costs (with NaN guards)
    // ========================================
    const safeDbuPrice = isNaN(dbuPrice) || dbuPrice === undefined ? 0 : dbuPrice
    const safeMonthlyDBUs = isNaN(monthlyDBUs) || monthlyDBUs === undefined ? 0 : monthlyDBUs
    const safeMonthlyDSUs = isNaN(monthlyDSUs) || monthlyDSUs === undefined ? 0 : monthlyDSUs
    const safeDSUCost = isNaN(dsuCost) || dsuCost === undefined ? 0 : dsuCost
    const safeVmCost = isNaN(vmCost) || vmCost === undefined ? 0 : vmCost
    const safeStorageCost = storageCost !== undefined && !isNaN(storageCost) ? storageCost : 0
    
    const dbuCost = safeMonthlyDBUs * safeDbuPrice
    const totalCost = dbuCost + safeVmCost + safeDSUCost
    
    return { 
      monthlyDBUs: safeMonthlyDBUs, 
      dbuCost: isNaN(dbuCost) ? 0 : dbuCost, 
      monthlyDSUs: safeMonthlyDSUs,
      dsuCost: safeDSUCost,
      vmCost: safeVmCost, 
      databricksListCost: dbuCost + safeDSUCost,
      totalCost: isNaN(totalCost) ? 0 : totalCost,
      unitsUsed,  // For AI Search
      dbuPerHour, // For display
      dbuPrice: safeDbuPrice,  // $/DBU rate for display
      dsuPrice,
      storageCost: safeStorageCost > 0 ? safeStorageCost : undefined,
      storageDetails
    }
  }
  
  // Calculate total costs
  const totalCosts = useMemo(() => {
    let totalDBUs = 0
    let totalDBUCost = 0
    let totalDSUs = 0
    let totalDSUCost = 0
    let totalVMCost = 0
    let workloadTotalCost = 0
    let productSpendAtList = 0
    
    lineItems.forEach(item => {
      const costs = calculateItemCost(item)
      // Guard against NaN values propagating
      totalDBUs += isNaN(costs.monthlyDBUs) ? 0 : costs.monthlyDBUs
      totalDBUCost += isNaN(costs.dbuCost) ? 0 : costs.dbuCost
      totalDSUs += isNaN(costs.monthlyDSUs) ? 0 : costs.monthlyDSUs
      totalDSUCost += isNaN(costs.dsuCost) ? 0 : costs.dsuCost
      totalVMCost += isNaN(costs.vmCost) ? 0 : costs.vmCost
      workloadTotalCost += isNaN(costs.totalCost) ? 0 : costs.totalCost
      productSpendAtList += isNaN(costs.databricksListCost)
        ? 0
        : costs.databricksListCost
    })

    const selectedAddon = formData.platform_addons[0] ?? null
    const platformAddonDiscountPct = getPlatformAddonDiscountPct(
      currentEstimate?.discount_config,
    )
    const platformAddon = calculatePlatformAddonCost(
      pricingBundle.platformAddons,
      selectedAddon,
      formData.cloud,
      formData.tier,
      productSpendAtList,
      platformAddonDiscountPct,
    )
    const totalPlatformAddonCost = platformAddon?.cost ?? 0
    
    return {
      totalDBUs,
      totalDBUCost,
      totalDSUs,
      totalDSUCost,
      totalVMCost,
      productSpendAtList,
      workloadTotalCost,
      platformAddon,
      totalPlatformAddonCost,
      totalCost: workloadTotalCost + totalPlatformAddonCost,
    }
  }, [lineItems, formData.cloud, formData.region, formData.tier, formData.platform_addons, currentEstimate?.discount_config, workloadTypes, getVMPrice, vmPricingMap, getInstanceDbuRate, instanceDbuRateMap, instanceTypes, photonMultipliers, dbuRatesMap, dbsqlSizes, modelServingGPUTypes, vectorSearchModes, getVectorSearchRate, getFMAPIDatabricksRate, getFMAPIProprietaryRate, pricingBundle, isPricingBundleLoaded])
  
  // Sync local calculated costs to the store for AI Assistant
  useEffect(() => {
    const costs: Record<string, { total: number; dbu: number; dsu: number; vm: number; dbus: number; dsus: number }> = {}
    lineItems.forEach(item => {
      const itemCosts = calculateItemCost(item, pendingFormEdits[item.line_item_id])
      costs[item.line_item_id] = {
        total: isNaN(itemCosts.totalCost) ? 0 : itemCosts.totalCost,
        dbu: isNaN(itemCosts.dbuCost) ? 0 : itemCosts.dbuCost,
        dsu: isNaN(itemCosts.dsuCost) ? 0 : itemCosts.dsuCost,
        vm: isNaN(itemCosts.vmCost) ? 0 : itemCosts.vmCost,
        dbus: isNaN(itemCosts.monthlyDBUs) ? 0 : itemCosts.monthlyDBUs,
        dsus: isNaN(itemCosts.monthlyDSUs) ? 0 : itemCosts.monthlyDSUs,
      }
    })
    setLocalCalculatedCosts(costs)
  }, [lineItems, pendingFormEdits, formData.cloud, formData.region, formData.tier, setLocalCalculatedCosts, getVMPrice, vmPricingMap, getInstanceDbuRate, instanceDbuRateMap, instanceTypes, photonMultipliers, dbuRatesMap, dbsqlSizes, modelServingGPUTypes, vectorSearchModes, getVectorSearchRate, getFMAPIDatabricksRate, getFMAPIProprietaryRate, pricingBundle, isPricingBundleLoaded])
  
  // Sorted line items
  const sortedLineItems = useMemo(() => {
    const items = [...lineItems]
    if (sortField === 'order') {
      items.sort((a, b) => (a.display_order ?? 0) - (b.display_order ?? 0))
    } else if (sortField === 'name') {
      items.sort((a, b) => (a.workload_name || '').localeCompare(b.workload_name || ''))
    } else if (sortField === 'type') {
      items.sort((a, b) => (a.workload_type || '').localeCompare(b.workload_type || ''))
    } else if (sortField === 'cost') {
      items.sort((a, b) => {
        const costA = calculateItemCost(a).totalCost
        const costB = calculateItemCost(b).totalCost
        return costA - costB
      })
    }
    if (sortDirection === 'desc') items.reverse()
    return items
  }, [lineItems, sortField, sortDirection, calculateItemCost])

  const handleSort = (field: 'order' | 'name' | 'type' | 'cost') => {
    if (sortField === field) {
      setSortDirection(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection(field === 'cost' ? 'desc' : 'asc')
    }
  }

  // DnD for workload reordering
  const dndSensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor)
  )
  const isDragEnabled = sortField === 'order'

  const handleDragEnd = useCallback(async (event: DragEndEvent) => {
    const { active, over } = event
    if (!over || active.id === over.id || !id) return

    const oldIndex = sortedLineItems.findIndex(i => i.line_item_id === active.id)
    const newIndex = sortedLineItems.findIndex(i => i.line_item_id === over.id)
    if (oldIndex === -1 || newIndex === -1) return

    // Reorder locally
    const reordered = [...sortedLineItems]
    const [moved] = reordered.splice(oldIndex, 1)
    reordered.splice(newIndex, 0, moved)

    // Update display_order in store
    const { lineItems: storeItems } = useStore.getState()
    const updatedItems = storeItems.map(item => {
      const newOrder = reordered.findIndex(r => r.line_item_id === item.line_item_id)
      return newOrder >= 0 ? { ...item, display_order: newOrder } : item
    })
    useStore.setState({ lineItems: updatedItems })

    // Persist to backend
    try {
      await apiReorderLineItems(id, reordered.map(i => i.line_item_id))
    } catch {
      toast.error('Failed to save reorder')
    }
  }, [sortedLineItems, id])

  const handleSave = async () => {
    if (!formData.estimate_name.trim()) {
      toast.error('Enter an estimate name')
      return
    }
    if (!formData.region) {
      toast.error('Select a region')
      return
    }
    if (!formData.tier) {
      toast.error('Select a Databricks tier')
      return
    }
    
    setIsSaving(true)
    try {
      // Convert cloud and tier to uppercase for database constraints
      const { platform_addons, ...estimateFields } = formData
      const dataToSave = {
        ...estimateFields,
        cloud: formData.cloud.toUpperCase(),
        tier: formData.tier.toUpperCase(),
        discount_config: {
          ...(currentEstimate?.discount_config || {}),
          platform_addons,
        },
      }
      
      if (id && currentEstimate) {
        await updateEstimate(id, dataToSave)
        setHasUnsavedChanges(false)
        toast.success('All changes saved')
      } else {
        const newEstimate = await createEstimate(dataToSave)
        setHasUnsavedChanges(false)
        navigate(`/calculator/${newEstimate.estimate_id}`, { replace: true })
        toast.success('Estimate created')
      }
    } catch {
      toast.error('Failed to save')
    } finally {
      setIsSaving(false)
    }
  }
  
  const handleExport = async () => {
    if (!id) return
    
    setIsExporting(true)
    try {
      const blob = await exportEstimateToExcel(id)
      const filename = `${formData.estimate_name.replace(/\s+/g, '_')}_${new Date().toISOString().split('T')[0]}.xlsx`
      saveAs(blob, filename)
      toast.success('Exported to Excel')
    } catch {
      toast.error('Export failed')
    } finally {
      setIsExporting(false)
    }
  }
  
  const handleDeleteEstimate = async () => {
    if (!id) return
    
    setIsDeleting(true)
    setShowDeleteConfirm(false) // Close modal immediately
    
    try {
      await deleteEstimate(id)
      toast.success('Estimate deleted')
      navigate('/', { replace: true })
    } catch {
      toast.error('Failed to delete estimate')
      setIsDeleting(false)
    }
  }
  
  const handleRefreshData = async () => {
    clearReferenceCache()
    toast.loading('Refreshing pricing data...', { id: 'refresh-data' })
    try {
      await fetchReferenceData(true) // Force refresh
      toast.success('Pricing data refreshed', { id: 'refresh-data' })
    } catch {
      toast.error('Failed to refresh data', { id: 'refresh-data' })
    }
  }
  
  const handleDeleteLineItem = (item: LineItem) => {
    setWorkloadToDelete(item)
    setShowWorkloadDeleteConfirm(true)
  }
  
  const confirmDeleteWorkload = async () => {
    if (!workloadToDelete) return
    
    setIsDeletingWorkload(true)
    try {
      await deleteLineItem(workloadToDelete.line_item_id)
      toast.success('Workload removed')
    } catch {
      toast.error('Failed to delete')
    } finally {
      setIsDeletingWorkload(false)
      setShowWorkloadDeleteConfirm(false)
      setWorkloadToDelete(null)
    }
  }
  
  // Bulk delete handler
  const handleBulkDelete = () => {
    if (selectedItems.size === 0) return
    setShowBulkDeleteConfirm(true)
  }
  
  const confirmBulkDelete = async () => {
    setIsDeletingWorkload(true)
    try {
      let deletedCount = 0
      for (const itemId of selectedItems) {
        await deleteLineItem(itemId)
        deletedCount++
      }
      toast.success(`${deletedCount} workload(s) deleted`)
      setSelectedItems(new Set())
    } catch {
      toast.error('Failed to delete some workloads')
    } finally {
      setIsDeletingWorkload(false)
      setShowBulkDeleteConfirm(false)
    }
  }
  
  // Toggle item selection
  const toggleItemSelection = (itemId: string) => {
    setSelectedItems(prev => {
      const newSet = new Set(prev)
      if (newSet.has(itemId)) {
        newSet.delete(itemId)
      } else {
        newSet.add(itemId)
      }
      return newSet
    })
  }
  
  // Select/deselect all
  const toggleSelectAll = () => {
    if (selectedItems.size === lineItems.length) {
      setSelectedItems(new Set())
    } else {
      setSelectedItems(new Set(lineItems.map(item => item.line_item_id)))
    }
  }
  
  // Exit bulk select mode
  const exitBulkSelectMode = () => {
    setIsBulkSelectMode(false)
    setSelectedItems(new Set())
  }
  
  const handleCloneWorkload = async (e: React.MouseEvent, item: LineItem) => {
    e.stopPropagation()
    try {
      const cloned = await cloneLineItem(item.line_item_id)
      if (cloned) {
        toast.success(`Workload "${item.workload_name}" cloned`)
        // Note: Cloned workload is immediately persisted to DB - no need to mark config as changed
      }
    } catch {
      toast.error('Failed to clone workload')
    }
  }
  
  const handleNavigateBack = () => {
    if (hasUnsavedChanges) {
      setShowUnsavedChangesConfirm(true)
    } else {
      navigate('/')
    }
  }
  
  const confirmLeaveWithoutSaving = () => {
    setShowUnsavedChangesConfirm(false)
    navigate('/')
  }
  
  const toggleExpand = (itemId: string) => {
    const newExpanded = new Set(expandedItems)
    if (newExpanded.has(itemId)) {
      newExpanded.delete(itemId)
    } else {
      newExpanded.add(itemId)
    }
    setExpandedItems(newExpanded)
  }
  
  const toggleFormula = (itemId: string, alsoExpand: boolean = false) => {
    const newVisible = new Set(formulaVisibleItems)
    if (newVisible.has(itemId)) {
      newVisible.delete(itemId)
    } else {
      newVisible.add(itemId)
      // Also expand the item if requested
      if (alsoExpand && !expandedItems.has(itemId)) {
        const newExpanded = new Set(expandedItems)
        newExpanded.add(itemId)
        setExpandedItems(newExpanded)
      }
    }
    setFormulaVisibleItems(newVisible)
  }
  
  // Get usage summary for a workload
  const getUsageSummary = (item: LineItem) => {
    // Quantity-based workloads don't use run/hour usage
    const wt = item.workload_type || ''
    if (['AI_PARSE', 'AI_EXTRACT', 'AI_CLASSIFY', 'AI_GATEWAY', 'AGENT_EVALUATION', 'GENERAL_STORAGE', 'ZEROBUS', 'SHUTTERSTOCK_IMAGEAI', 'DATABRICKS_APPS'].includes(wt)) return null
    if (item.hours_per_month) {
      return `${item.hours_per_month}h/month`
    }
    if (item.runs_per_day) {
      return `${item.runs_per_day} runs/day × ${item.avg_runtime_minutes || 30}min`
    }
    return null
  }
  
  // Get workload-specific summary details
  const getWorkloadSummaryDetails = (item: LineItem): { label: string; value: string }[] => {
    const details: { label: string; value: string }[] = []
    
    // Add serverless mode for compute workloads when serverless is enabled
    if (['JOBS', 'ALL_PURPOSE', 'DLT'].includes(item.workload_type || '') && item.serverless_enabled) {
      details.push({ 
        label: 'Mode', 
        value: item.serverless_mode === 'performance' ? 'Performance' : 'Standard'
      })
    }
    
    switch (item.workload_type) {
      case 'VECTOR_SEARCH':
        if (item.vector_search_mode) {
          details.push({ 
            label: 'Mode', 
            value: item.vector_search_mode === 'storage_optimized' ? 'Storage Optimized' : 'Standard'
          })
        }
        if (item.vector_capacity_millions) {
          details.push({ label: 'Capacity', value: `${item.vector_capacity_millions}M vectors` })
        }
        if (item.ai_search_reranker_enabled) {
          details.push({
            label: 'Reranker',
            value: `${item.ai_search_reranker_requests_thousands || 0}K requests/mo`,
          })
        }
        break
        
      case 'MODEL_SERVING':
        if (item.model_serving_gpu_type) {
          const gpuLabels: Record<string, string> = {
            'cpu': 'CPU',
            'gpu_small_t4': 'GPU Small (T4)',
            'gpu_medium_a10g_1x': 'GPU Medium (A10G)',
            'gpu_large_a10g_4x': 'GPU Large (4x A10G)',
            'gpu_medium_a100_1x': 'GPU A100',
            'gpu_large_a100_2x': 'GPU A100 (2x)',
            'gpu_small': 'GPU Small',
            'gpu_medium': 'GPU Medium',
            'gpu_large': 'GPU Large'
          }
          details.push({ label: 'Endpoint', value: gpuLabels[item.model_serving_gpu_type] || item.model_serving_gpu_type })
        }
        break

      case 'AI_RUNTIME': {
        const usage = calculateAIRuntimeUsage(
          formData.cloud || 'aws',
          item.ai_runtime_accelerator_type,
          0,
        )
        details.push({
          label: 'Accelerator',
          value: usage.accelerator?.label || 'Unavailable',
        })
        break
      }

      case 'GENERAL_STORAGE': {
        const quantity = item.general_storage_quantity ?? 0
        const unit = (item.general_storage_unit ?? 'gb').toUpperCase()
        details.push({
          label: 'Stored Capacity',
          value: `${quantity.toLocaleString()} ${unit}/month`,
        })
        if (unit === 'TB') {
          details.push({
            label: 'Billable Capacity',
            value: `${getGeneralStorageGB(item).toLocaleString()} GB-month`,
          })
        }
        details.push({
          label: 'Tier 1 Operations',
          value: `${(item.general_storage_tier1_operations_thousands ?? 0).toLocaleString()}K/month`,
        })
        details.push({
          label: 'Tier 2 Operations',
          value: `${(item.general_storage_tier2_operations_thousands ?? 0).toLocaleString()}K/month`,
        })
        break
      }

      case 'ZEROBUS': {
        const usage = calculateZerobusUsage(item)
        details.push({
          label: 'Type',
          value: usage.mode === 'otel'
            ? 'Zerobus OTel Ingest'
            : 'Zerobus Ingest',
        })
        details.push({
          label: 'Ingested Data',
          value: `${formatNumber(usage.monthlyIngestedGB, 3)} GB/month`,
        })
        details.push({
          label: 'Metering',
          value: `${usage.dbuPerGB.toFixed(3)} DBU/GB`,
        })
        break
      }
        
      case 'LAKEBASE':
        if (item.lakebase_cu) {
          details.push({ label: 'CU', value: `${item.lakebase_cu}` })
        }
        if (item.lakebase_ha_nodes) {
          details.push({ label: 'Nodes', value: `${item.lakebase_ha_nodes}${item.lakebase_ha_nodes > 1 ? ' (HA)' : ''}` })
        }
        if (item.lakebase_storage_gb && item.lakebase_storage_gb > 0) {
          details.push({ label: 'Storage', value: `${item.lakebase_storage_gb.toLocaleString()} GB` })
        }
        break
        
      case 'FMAPI_DATABRICKS':
        if (item.fmapi_model) {
          details.push({ label: 'Model', value: item.fmapi_model })
        }
        if (item.fmapi_rate_type) {
          const rateLabels: Record<string, string> = {
            'input_token': 'Input Tokens',
            'output_token': 'Output Tokens',
            'provisioned_scaling': 'Provisioned Scaling',
            'provisioned_entry': 'Provisioned Entry',
            'provisioned_scaling_1_month': 'Provisioned Scaling (1 month)',
            'provisioned_scaling_3_month': 'Provisioned Scaling (3 months)',
            'provisioned_entry_1_month': 'Provisioned Entry (1 month)',
            'provisioned_entry_3_month': 'Provisioned Entry (3 months)',
          }
          details.push({ label: 'Rate', value: rateLabels[item.fmapi_rate_type] || item.fmapi_rate_type })
        }
        if (item.fmapi_quantity) {
          const isProvisioned = (item.fmapi_rate_type || '').startsWith('provisioned_')
            || item.fmapi_rate_type === 'batch_inference'
          details.push({ 
            label: isProvisioned ? 'Hours' : 'Quantity', 
            value: isProvisioned ? `${item.fmapi_quantity}h/mo` : `${item.fmapi_quantity}M` 
          })
        }
        break
        
      case 'FMAPI_PROPRIETARY':
        if (item.fmapi_provider && item.fmapi_model) {
          details.push({ label: 'Model', value: `${item.fmapi_provider}/${item.fmapi_model}` })
        }
        if (item.fmapi_rate_type) {
          const rateLabels: Record<string, string> = {
            'input_token': 'Input',
            'output_token': 'Output',
            'cache_read': 'Cache Read',
            'cache_write': 'Cache Write',
            'batch_inference': 'Batch Inference',
          }
          details.push({ label: 'Rate', value: rateLabels[item.fmapi_rate_type] || item.fmapi_rate_type })
        }
        if (item.fmapi_quantity) {
          const isHourly = item.fmapi_rate_type === 'batch_inference'
          details.push({
            label: isHourly ? 'Hours' : 'Quantity',
            value: isHourly
              ? `${item.fmapi_quantity}h/mo`
              : `${item.fmapi_quantity}M tokens`,
          })
        }
        break
        
      case 'DLT':
        if (item.dlt_edition) {
          details.push({ label: 'Edition', value: item.dlt_edition })
        }
        break
        
      case 'DBSQL':
        if (item.dbsql_warehouse_type) {
          details.push({ label: 'Type', value: item.dbsql_warehouse_type })
        }
        if (item.dbsql_warehouse_size) {
          details.push({ label: 'Size', value: item.dbsql_warehouse_size })
        }
        if (item.dbsql_num_clusters && item.dbsql_num_clusters > 1) {
          details.push({ label: 'Clusters', value: `${item.dbsql_num_clusters}` })
        }
        break

      case 'DATABRICKS_APPS':
        details.push({ label: 'Size', value: (item.databricks_apps_size || 'medium').charAt(0).toUpperCase() + (item.databricks_apps_size || 'medium').slice(1) })
        break

      case 'AI_PARSE':
        details.push({ label: 'Complexity', value: item.ai_parse_complexity || 'medium' })
        if (item.ai_parse_pages_thousands) {
          details.push({ label: 'Pages', value: `${item.ai_parse_pages_thousands}K/mo` })
        }
        break

      case 'AI_EXTRACT':
        details.push({ label: 'Type', value: item.ai_extract_document_type || 'invoice' })
        if (item.ai_extract_num_inputs) {
          details.push({ label: 'Inputs', value: `${formatNumber(item.ai_extract_num_inputs / 1000)}K/mo` })
        }
        break

      case 'AI_CLASSIFY':
        details.push({ label: 'Type', value: item.ai_classify_document_type || 'short_text' })
        if (item.ai_classify_num_docs) {
          details.push({ label: 'Docs', value: `${formatNumber(item.ai_classify_num_docs / 1000)}K/mo` })
        }
        break

      case 'AI_GATEWAY': {
        const usage = calculateAIGatewayUsage(item)
        if (usage.inferenceTables.enabled) {
          details.push({
            label: 'Inference Tables',
            value: `${formatNumber(usage.inferenceTables.monthlyPayloadGB, 3)} GB · ${formatNumber(usage.inferenceTables.monthlyDBUs, 3)} DBUs`,
          })
        }
        if (usage.usageTracking.enabled) {
          details.push({
            label: 'Usage Tracking',
            value: `${formatNumber(usage.usageTracking.monthlyPayloadGB, 3)} GB · ${formatNumber(usage.usageTracking.monthlyDBUs, 3)} DBUs`,
          })
        }
        break
      }

      case 'AGENT_EVALUATION': {
        const usage = calculateAgentEvaluationUsage(item)
        if (usage.labelsEnabled) {
          details.push({
            label: 'Evaluation Tokens',
            value: `${formatNumber(usage.inputTokensMillions, 3)}M input + ${formatNumber(usage.outputTokensMillions, 3)}M output · ${formatNumber(usage.evaluationTokenDBUs, 3)} DBUs`,
          })
        }
        if (usage.syntheticDataEnabled) {
          details.push({
            label: 'Synthetic Questions',
            value: `${usage.syntheticQuestions.toLocaleString()}/mo · ${formatNumber(usage.syntheticQuestionDBUs, 3)} DBUs`,
          })
        }
        break
      }

      case 'SHUTTERSTOCK_IMAGEAI':
        if (item.shutterstock_images) {
          details.push({ label: 'Images', value: `${item.shutterstock_images.toLocaleString()}/mo` })
        }
        break
    }

    return details
  }
  
  // Validation: check if all required fields are filled
  const canCreateEstimate = formData.estimate_name.trim() &&
    formData.region &&
    formData.tier

  // Get missing fields for helpful message
  const getMissingFields = () => {
    const missing: string[] = []
    if (!formData.estimate_name.trim()) missing.push('Estimate Name')
    if (!formData.region) missing.push('Region')
    if (!formData.tier) missing.push('Databricks Tier')
    return missing
  }
  
  // Show deleting state when estimate is being deleted
  if (isDeleting) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="flex flex-col items-center justify-center min-h-[50vh] gap-4">
          <div className="w-12 h-12 rounded-full border-4 border-[var(--border-primary)] border-t-red-500 animate-spin"></div>
          <p className="text-sm font-medium text-[var(--text-primary)]">Deleting estimate...</p>
          <p className="text-xs text-[var(--text-muted)]">You will be redirected shortly</p>
        </div>
      </div>
    )
  }
  
  // Show loading state when loading an existing estimate
  if (id && isLoadingEstimate && !currentEstimate) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="flex items-center gap-3 mb-6">
          <button
            onClick={() => navigate('/')}
            className="p-1.5 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)] transition-colors"
          >
            <ArrowLeftIcon className="w-5 h-5" />
          </button>
          <div className="h-7 w-48 bg-[var(--bg-tertiary)] rounded animate-pulse"></div>
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Content Skeleton */}
          <div className="lg:col-span-2 space-y-6">
            {/* Config Card Skeleton */}
            <div className="card p-5">
              <div className="h-5 w-32 bg-[var(--bg-tertiary)] rounded animate-pulse mb-4"></div>
              <div className="grid grid-cols-3 gap-3 mb-6">
                {[1, 2, 3].map(i => (
                  <div key={i} className="h-16 bg-[var(--bg-tertiary)] rounded-xl animate-pulse"></div>
                ))}
              </div>
              <div className="space-y-4">
                {[1, 2, 3].map(i => (
                  <div key={i} className="h-10 bg-[var(--bg-tertiary)] rounded animate-pulse"></div>
                ))}
              </div>
            </div>
            
            {/* Workloads Skeleton */}
            <div className="space-y-4">
              <div className="h-6 w-28 bg-[var(--bg-tertiary)] rounded animate-pulse"></div>
              <div className="card p-8">
                <div className="flex flex-col items-center gap-4">
                  <div className="relative">
                    <div className="w-12 h-12 rounded-full border-4 border-[var(--border-primary)] border-t-lava-600 animate-spin"></div>
                  </div>
                  <div className="text-center">
                    <p className="text-sm font-medium text-[var(--text-primary)]">Loading estimate...</p>
                    <p className="text-xs text-[var(--text-muted)] mt-1">Please wait while we fetch your data</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          {/* Summary Sidebar Skeleton */}
          <div className="lg:col-span-1">
            <div className="card p-5 space-y-4">
              <div className="h-5 w-20 bg-[var(--bg-tertiary)] rounded animate-pulse"></div>
              <div className="h-24 bg-[var(--bg-tertiary)] rounded animate-pulse"></div>
              <div className="h-12 bg-[var(--bg-tertiary)] rounded animate-pulse"></div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <button
            onClick={handleNavigateBack}
            className="p-1.5 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)] transition-colors"
          >
            <ArrowLeftIcon className="w-5 h-5" />
          </button>
          
          <div>
            {isLoadingEstimate && id ? (
              // Loading skeleton for estimate name
              <div className="space-y-1.5">
                <div className="h-7 w-48 bg-[var(--bg-tertiary)] rounded animate-pulse" />
                <div className="h-4 w-20 bg-[var(--bg-tertiary)] rounded animate-pulse" />
              </div>
            ) : (
              <>
                <input
                  type="text"
                  value={formData.estimate_name}
                  onChange={(e) => {
                    setFormData(prev => ({ ...prev, estimate_name: e.target.value }))
                    markAsChanged()
                  }}
                  placeholder="Untitled Estimate"
                  title={formData.estimate_name}
                  className="text-xl font-semibold bg-transparent border-none p-0 focus:ring-0 w-full min-w-[200px] text-[var(--text-primary)] placeholder-[var(--text-muted)]"
                />
                {currentEstimate && (
                  <p className="text-xs mt-0.5 text-[var(--text-muted)]">Version {currentEstimate.version}</p>
                )}
              </>
            )}
          </div>
          
          {hasUnsavedChanges && (
            <span className="flex items-center gap-1 text-xs text-lava-600 font-medium">
              <ExclamationTriangleIcon className="w-3.5 h-3.5" />
              Unsaved
            </span>
          )}
        </div>
        
        <div className="flex items-center gap-2">
          <button
            onClick={handleRefreshData}
            disabled={isLoadingReferenceData}
            title="Refresh pricing data from server"
            className="btn btn-ghost text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
          >
            <ArrowPathIcon className={clsx("w-4 h-4", isLoadingReferenceData && "animate-spin")} />
          </button>
          
          <button
            onClick={handleExport}
            disabled={isExporting || !id}
            className="btn btn-secondary"
          >
            <ArrowDownTrayIcon className="w-4 h-4" />
            <span className="hidden sm:inline">Excel</span>
          </button>
          
          {id && (
            <button
              onClick={() => setShowDeleteConfirm(true)}
              disabled={isDeleting}
              title="Delete this estimate"
              className="btn btn-ghost text-red-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
            >
              <TrashIcon className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
      
      <div className={clsx(
        "grid grid-cols-1 gap-6",
        isCostSummaryCollapsed ? "lg:grid-cols-1" : "lg:grid-cols-4"
      )}>
        {/* Main Content - Expands when sidebar is collapsed */}
        <div className={clsx(
          "space-y-6",
          isCostSummaryCollapsed ? "lg:col-span-1" : "lg:col-span-3"
        )}>
          {/* Configuration Section - Collapsible */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="card"
          >
            {/* Header - Always visible, clickable to expand/collapse */}
            <div 
              className="px-4 py-3 cursor-pointer hover:bg-[var(--bg-tertiary)]/50 transition-colors flex items-center justify-between"
              onClick={() => setIsConfigCollapsed(!isConfigCollapsed)}
            >
              <div className="flex items-center gap-2.5 min-w-0 flex-1">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 bg-lava-600/10">
                  <CpuChipIcon className="w-4 h-4 text-lava-600" />
                </div>
                <div className="min-w-0 flex-1">
                  <h3 className="font-semibold text-sm text-[var(--text-primary)]">Configuration</h3>
                  <p className="text-[11px] text-[var(--text-muted)] truncate" title={`${formData.cloud.toUpperCase()} • ${formData.region || 'No region'} • ${formData.tier ? formData.tier.charAt(0).toUpperCase() + formData.tier.slice(1) : 'No tier'}${formData.customer_name ? ` • ${formData.customer_name}` : ''}`}>
                    {formData.cloud.toUpperCase()} • {formData.region || 'No region'} • {formData.tier ? formData.tier.charAt(0).toUpperCase() + formData.tier.slice(1) : 'No tier'}
                    {formData.customer_name && ` • ${formData.customer_name}`}
                  </p>
                </div>
              </div>
              <button className="p-1 rounded hover:bg-[var(--bg-tertiary)] transition-colors flex-shrink-0 ml-2">
                {isConfigCollapsed ? (
                  <ChevronDownIcon className="w-4 h-4 text-[var(--text-muted)]" />
                ) : (
                  <ChevronUpIcon className="w-4 h-4 text-[var(--text-muted)]" />
                )}
              </button>
            </div>
            
            {/* Collapsible content */}
            {!isConfigCollapsed && (
              <div className="px-4 pb-3 space-y-3 border-t border-[var(--border-primary)]">
                {/* Cloud Selection + Region + Tier */}
                <div className="pt-3 space-y-3">
                  <div>
                    <label className="block text-xs font-medium mb-2 text-[var(--text-secondary)]">Cloud Provider</label>
                    {isLoadingEstimate && id ? (
                      <div className="grid grid-cols-3 gap-3">
                        {[1, 2, 3].map(i => (
                          <div
                            key={i}
                            className="py-2.5 px-3 rounded-lg border-2 border-dashed border-[var(--border-secondary)]"
                          >
                            <div className="h-5 w-14 mx-auto bg-[var(--bg-tertiary)] rounded animate-pulse" />
                          </div>
                        ))}
                      </div>
                    ) : (
                      <>
                        {lineItems.length > 0 && (
                          <div className="mb-2 text-xs text-amber-500 flex items-center gap-1">
                            <ExclamationTriangleIcon className="w-3.5 h-3.5" />
                            Cloud provider locked. Remove all workloads to change.
                          </div>
                        )}
                        <div className="grid grid-cols-3 gap-3">
                          {CLOUD_PROVIDERS.map(cloud => {
                            const isLocked = lineItems.length > 0 && formData.cloud !== cloud.id
                            return (
                              <button
                                key={cloud.id}
                                disabled={isLocked}
                                onClick={(e) => {
                                  e.stopPropagation()
                                  if (isLocked) return
                                  setFormData(prev => ({ 
                                    ...prev, 
                                    cloud: cloud.id, 
                                    region: '',
                                    tier: (cloud.id === 'azure' && prev.tier === 'enterprise') ? '' : prev.tier,
                                    platform_addons: [],
                                  }))
                                  setSelectedCloud(cloud.id)
                                  markAsChanged()
                                }}
                                className={clsx(
                                  'relative py-2.5 px-3 rounded-lg border-2 transition-all text-center',
                                  formData.cloud === cloud.id
                                    ? 'border-lava-600 bg-lava-600/10'
                                    : 'border-dashed border-[var(--border-secondary)]',
                                  isLocked
                                    ? 'opacity-40 cursor-not-allowed'
                                    : formData.cloud !== cloud.id && 'hover:border-lava-600/50 hover:bg-lava-600/5'
                                )}
                                title={isLocked ? 'Remove all workloads to change cloud provider' : undefined}
                              >
                                <div className={clsx(
                                  'text-sm font-semibold',
                                  formData.cloud === cloud.id ? 'text-lava-600' : 'text-[var(--text-primary)]'
                                )}>
                                  {cloud.name}
                                </div>
                                {formData.cloud === cloud.id && (
                                  <div className="absolute top-1.5 right-1.5">
                                    <CheckIcon className="w-3.5 h-3.5 text-lava-600" />
                                  </div>
                                )}
                              </button>
                            )
                          })}
                        </div>
                      </>
                    )}
                  </div>
                  
                  {/* Region and Tier - underneath Cloud Provider */}
                  {isLoadingEstimate && id ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <div className="h-4 w-16 bg-[var(--bg-tertiary)] rounded animate-pulse mb-1.5" />
                        <div className="h-10 w-full bg-[var(--bg-tertiary)] rounded animate-pulse" />
                      </div>
                      <div>
                        <div className="h-4 w-24 bg-[var(--bg-tertiary)] rounded animate-pulse mb-1.5" />
                        <div className="h-10 w-full bg-[var(--bg-tertiary)] rounded animate-pulse" />
                      </div>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4" onClick={(e) => e.stopPropagation()}>
                      <div>
                        <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">
                          Region <span className="text-red-500">*</span>
                        </label>
                        <select
                          value={formData.region}
                          onChange={(e) => {
                            setFormData(prev => ({ ...prev, region: e.target.value }))
                            setSelectedRegion(e.target.value)
                            markAsChanged()
                          }}
                          className={clsx(
                            "w-full text-sm",
                            !formData.region && "border-lava-600/50 ring-1 ring-lava-600/30"
                          )}
                        >
                          <option value="">{isLoadingRegions ? 'Loading regions...' : 'Select region'}</option>
                          {regions.map(region => (
                            <option key={region.region_code} value={region.region_code}>
                              {region.region_code} ({region.sku_region})
                            </option>
                          ))}
                        </select>
                      </div>
                      
                      <div>
                        <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">
                          Databricks Tier <span className="text-red-500">*</span>
                        </label>
                        <select
                          value={formData.tier}
                          onChange={(e) => {
                            const nextTier = e.target.value
                            const selectedAddon = formData.platform_addons[0]
                            const isUnavailable = selectedAddon
                              ? Boolean(getPlatformAddonAvailabilityError(
                                  pricingBundle.platformAddons,
                                  selectedAddon,
                                  formData.cloud,
                                  nextTier,
                                ))
                              : false
                            setFormData(prev => ({
                              ...prev,
                              tier: nextTier,
                              platform_addons: isUnavailable ? [] : prev.platform_addons,
                            }))
                            if (isUnavailable) {
                              toast('Platform add-on cleared because it is unavailable for this tier')
                            }
                            markAsChanged()
                          }}
                          className={clsx(
                            "w-full text-sm",
                            !formData.tier && "border-lava-600/50 ring-1 ring-lava-600/30"
                          )}
                        >
                          <option value="">Select tier</option>
                          <option value="premium">Premium</option>
                          {formData.cloud !== 'azure' && (
                            <option value="enterprise">Enterprise</option>
                          )}
                        </select>
                      </div>
                    </div>
                  )}

                  <div onClick={(e) => e.stopPropagation()}>
                    <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">
                      Platform Add-on
                    </label>
                    <select
                      value={formData.platform_addons[0] || ''}
                      onChange={(e) => {
                        const selection = e.target.value as PlatformAddonType | ''
                        setFormData(prev => ({
                          ...prev,
                          platform_addons: selection ? [selection] : [],
                        }))
                        markAsChanged()
                      }}
                      disabled={!formData.tier || !isPricingBundleLoaded}
                      className="w-full text-sm"
                    >
                      <option value="">None</option>
                      {PLATFORM_ADDON_TYPES.map(addonType => {
                        const definition = getPlatformAddonDefinition(
                          pricingBundle.platformAddons,
                          addonType,
                        )
                        const error = getPlatformAddonAvailabilityError(
                          pricingBundle.platformAddons,
                          addonType,
                          formData.cloud,
                          formData.tier,
                        )
                        return (
                          <option
                            key={addonType}
                            value={addonType}
                            disabled={Boolean(error)}
                          >
                            {definition?.display_name || addonType}
                            {error ? ` — ${error}` : ''}
                          </option>
                        )
                      })}
                    </select>
                    {totalCosts.platformAddon && (
                      <div className="mt-2 rounded-lg border border-amber-500/20 bg-amber-500/5 px-3 py-2 text-[11px] text-[var(--text-secondary)]">
                        <div className="flex items-center justify-between gap-3">
                          <span>Product Spend at List</span>
                          <span className="font-semibold tabular-nums text-[var(--text-primary)]">
                            {formatCurrency(totalCosts.productSpendAtList)}
                          </span>
                        </div>
                        <div className="flex items-center justify-between gap-3 mt-1">
                          <span>
                            {totalCosts.platformAddon.displayName}
                            {' '}({totalCosts.platformAddon.appliedRatePct}%)
                          </span>
                          <span className="font-semibold tabular-nums text-amber-600 dark:text-amber-400">
                            {formatCurrency(totalCosts.totalPlatformAddonCost)}
                          </span>
                        </div>
                        {totalCosts.platformAddon.promotionLabel && (
                          <p className="mt-1 text-[10px] text-[var(--text-muted)]">
                            Regular uplift {totalCosts.platformAddon.standardRatePct}%.{' '}
                            {totalCosts.platformAddon.promotionLabel}.
                          </p>
                        )}
                        {totalCosts.platformAddon.discountPct > 0 && (
                          <p className="mt-1 text-[10px] text-[var(--text-muted)]">
                            Add-on charge before negotiated discount:{' '}
                            {formatCurrency(totalCosts.platformAddon.costBeforeDiscount)}.
                            {' '}{totalCosts.platformAddon.discountPct}% discount applied.
                          </p>
                        )}
                        <p className="mt-1 text-[10px] text-[var(--text-muted)]">
                          Based on Databricks product spend before discounts; cloud VM costs are excluded.
                        </p>
                      </div>
                    )}
                  </div>
                </div>
                
                {/* Save Button */}
                <div className="border-t border-[var(--border-primary)] pt-4 flex items-center justify-between">
                  <div className="text-xs text-[var(--text-muted)]">
                    {hasUnsavedChanges ? (
                      <span className="text-amber-500 flex items-center gap-1">
                        <ExclamationTriangleIcon className="w-3.5 h-3.5" />
                        Unsaved changes
                      </span>
                    ) : id ? (
                      <span className="text-green-500 flex items-center gap-1">
                        <CheckIcon className="w-3.5 h-3.5" />
                        All changes saved
                      </span>
                    ) : null}
                  </div>
                  <button
                    onClick={handleSave}
                    disabled={isSaving || !canCreateEstimate}
                    title={!canCreateEstimate ? `Missing: ${getMissingFields().join(', ')}` : undefined}
                    className={clsx(
                      "btn btn-primary",
                      hasUnsavedChanges && "ring-2 ring-lava-600/50 ring-offset-2 ring-offset-[var(--bg-primary)]"
                    )}
                  >
                    <CheckIcon className="w-4 h-4" />
                    {isSaving ? 'Saving...' : id ? 'Save Configuration' : 'Create Estimate'}
                  </button>
                </div>
              </div>
            )}
          </motion.div>
          
          {/* Workloads List */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="space-y-4"
          >
            <div className="flex items-center justify-between flex-wrap gap-2">
              <h2 className="text-lg font-semibold flex items-center gap-2 text-[var(--text-primary)]">
                <ServerStackIcon className="w-5 h-5 text-lava-600" />
                Workloads
                <span className="ml-1 text-sm font-normal text-[var(--text-muted)]">
                  ({lineItems.length})
                </span>
              </h2>
              
              <div className="flex items-center gap-2">
                {/* Bulk Select Mode Controls */}
                {lineItems.length > 0 && (
                  <>
                    {!isBulkSelectMode ? (
                      <button
                        onClick={() => setIsBulkSelectMode(true)}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)] rounded-lg transition-colors"
                      >
                        Select
                      </button>
                    ) : (
                      <>
                        <span className="text-xs text-[var(--text-muted)]">
                          {selectedItems.size} selected
                        </span>
                        <button
                          onClick={handleBulkDelete}
                          disabled={selectedItems.size === 0}
                          className={clsx(
                            "flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors",
                            selectedItems.size > 0
                              ? "text-red-600 dark:text-red-400 bg-red-500/10 hover:bg-red-500/20"
                              : "text-[var(--text-muted)] bg-[var(--bg-tertiary)] cursor-not-allowed"
                          )}
                        >
                          <TrashIcon className="w-4 h-4" />
                          Delete
                        </button>
                        <button
                          onClick={exitBulkSelectMode}
                          className="p-1.5 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)]"
                          title="Cancel selection"
                        >
                          <XMarkIcon className="w-4 h-4" />
                        </button>
                      </>
                    )}
                  </>
                )}
                
                  {/* View Mode Toggle: Table (default) → Compact Cards → Expanded Cards */}
                  {lineItems.length > 0 && (
                    <div className="flex items-center gap-1 bg-[var(--bg-tertiary)] rounded-lg p-0.5">
                      <button
                        onClick={() => setWorkloadsViewMode('table')}
                        className={clsx(
                          "p-1.5 rounded-md transition-colors",
                          workloadsViewMode === 'table'
                            ? "bg-[var(--bg-primary)] text-lava-600 shadow-sm"
                            : "text-[var(--text-muted)] hover:text-[var(--text-primary)]"
                        )}
                        title="Table view (default)"
                      >
                        <TableCellsIcon className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => setWorkloadsViewMode('cards')}
                        className={clsx(
                          "p-1.5 rounded-md transition-colors",
                          workloadsViewMode === 'cards'
                            ? "bg-[var(--bg-primary)] text-lava-600 shadow-sm"
                            : "text-[var(--text-muted)] hover:text-[var(--text-primary)]"
                        )}
                        title="Compact cards"
                      >
                        <Squares2X2Icon className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => setWorkloadsViewMode('expanded')}
                        className={clsx(
                          "p-1.5 rounded-md transition-colors",
                          workloadsViewMode === 'expanded'
                            ? "bg-[var(--bg-primary)] text-lava-600 shadow-sm"
                            : "text-[var(--text-muted)] hover:text-[var(--text-primary)]"
                        )}
                        title="Expanded cards with details"
                      >
                        <ListBulletIcon className="w-4 h-4" />
                      </button>
                    </div>
                  )}
                
                {/* Add Workload Button - Top CTA */}
                {canAddWorkload && id && (
                  <button
                    onClick={() => setShowAddForm(true)}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-lava-600 hover:bg-lava-700 rounded-lg transition-colors shadow-sm"
                  >
                    <PlusIcon className="w-4 h-4" />
                    Add
                  </button>
                )}
              </div>
            </div>
            
            {!id ? (
              <div className="card p-8 text-center">
                {!canCreateEstimate ? (
                  <>
                    <p className="text-sm mb-2 text-[var(--text-muted)]">Complete required fields to create estimate</p>
                    <p className="text-xs text-lava-600 mb-3">
                      Missing: {getMissingFields().join(', ')}
                    </p>
                  </>
                ) : (
                  <p className="text-sm mb-3 text-[var(--text-muted)]">Save the estimate first to add workloads</p>
                )}
                <button
                  onClick={handleSave}
                  disabled={isSaving || !canCreateEstimate}
                  className="btn btn-primary"
                >
                  <CheckIcon className="w-4 h-4" />
                  Create Estimate
                </button>
              </div>
            ) : isLoadingLineItems && !lineItemsLoaded ? (
              <div className="card p-8 text-center">
                <div className="flex flex-col items-center gap-4">
                  <div className="relative">
                    <div className="w-12 h-12 rounded-full border-4 border-[var(--border-primary)] border-t-lava-600 animate-spin"></div>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-[var(--text-primary)]">Loading workloads...</p>
                    <p className="text-xs text-[var(--text-muted)] mt-1">Fetching line items for this estimate</p>
                  </div>
                </div>
              </div>
            ) : (
              <>
                {/* Table View - Responsive & Mobile-Friendly */}
                {workloadsViewMode === 'table' && lineItems.length > 0 && (
                  <div className="card overflow-hidden divide-y divide-[var(--border-primary)]">
                    {/* Header - Hidden on mobile */}
                    <div className="hidden sm:grid sm:grid-cols-12 gap-2 py-2 px-3 bg-[var(--bg-tertiary)] text-xs font-medium text-[var(--text-muted)]">
                      {isBulkSelectMode && (
                        <div className="col-span-1 flex items-center">
                          <input
                            type="checkbox"
                            checked={selectedItems.size === lineItems.length && lineItems.length > 0}
                            onChange={toggleSelectAll}
                            className="w-3.5 h-3.5 rounded border-[var(--border-primary)] text-lava-600 focus:ring-lava-600"
                          />
                        </div>
                      )}
                      <button onClick={() => handleSort('name')} className={clsx("flex items-center gap-1 cursor-pointer hover:text-[var(--text-primary)] transition-colors", isBulkSelectMode ? "col-span-3" : "col-span-4")}>
                        Workload
                        {sortField === 'name' && (sortDirection === 'asc' ? <BarsArrowUpIcon className="w-3 h-3" /> : <BarsArrowDownIcon className="w-3 h-3" />)}
                      </button>
                      <button onClick={() => handleSort('type')} className={clsx("flex items-center gap-1 cursor-pointer hover:text-[var(--text-primary)] transition-colors", isBulkSelectMode ? "col-span-4" : "col-span-4")}>
                        Configuration
                        {sortField === 'type' && (sortDirection === 'asc' ? <BarsArrowUpIcon className="w-3 h-3" /> : <BarsArrowDownIcon className="w-3 h-3" />)}
                      </button>
                      <button onClick={() => handleSort('cost')} className="col-span-4 flex items-center gap-1 justify-end cursor-pointer hover:text-[var(--text-primary)] transition-colors">
                        Cost
                        {sortField === 'cost' && (sortDirection === 'asc' ? <BarsArrowUpIcon className="w-3 h-3" /> : <BarsArrowDownIcon className="w-3 h-3" />)}
                      </button>
                    </div>
                    
                    {/* Rows */}
                    <DndContext sensors={dndSensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd} modifiers={[restrictToVerticalAxis]}>
                    <SortableContext items={sortedLineItems.map(i => i.line_item_id)} strategy={verticalListSortingStrategy}>
                    {sortedLineItems.map((item) => {
                      // Create effective item that merges saved data with pending edits for real-time preview
                      const pendingEdits = pendingFormEdits[item.line_item_id]
                      const effectiveItem: LineItem = pendingEdits
                        ? { ...item, ...pendingEdits } as LineItem
                        : item
                      
                      const costs = calculateItemCost(item, pendingEdits)
                      const typeConfig = getWorkloadTypeConfig(effectiveItem.workload_type)
                      const TypeIcon = typeConfig.icon
                      const isExpanded = expandedItems.has(item.line_item_id)
                      const isSelected = selectedItems.has(item.line_item_id)
                      const wType = effectiveItem.workload_type || ''
                      const isServerless = effectiveItem.serverless_enabled || (wType === 'DBSQL' && (effectiveItem.dbsql_warehouse_type || '').toUpperCase() === 'SERVERLESS')
                      const typeName = wType === 'VECTOR_SEARCH'
                        ? 'AI Search'
                        : workloadTypes.find(w => w.workload_type === wType)?.display_name || wType
                      const usageSummary = getUsageSummary(effectiveItem)

                      // Build structured config for better display - uses effectiveItem for real-time sync
                      // Simplified color scheme: orange accent for key features, neutral for rest
                      const getStructuredConfig = () => {
                        const config: {
                          driver?: string
                          workers?: { count: number; type: string }
                          badges: { text: string; accent?: boolean }[]
                          details: string[]
                        } = { badges: [], details: [] }
                        
                        // Key feature badges (accent color)
                        if (isServerless) {
                          config.badges.push({ text: 'Serverless', accent: true })
                        }
                        if (effectiveItem.photon_enabled) {
                          config.badges.push({ text: '⚡ Photon', accent: true })
                        }
                        
                        // Workload-specific configuration
                        if (['JOBS', 'ALL_PURPOSE', 'DLT'].includes(wType)) {
                          // Classic compute workloads - show driver and worker config
                          if (!isServerless) {
                            if (effectiveItem.driver_node_type) {
                              config.driver = effectiveItem.driver_node_type
                            }
                            if (effectiveItem.num_workers && effectiveItem.worker_node_type) {
                              config.workers = { count: effectiveItem.num_workers, type: effectiveItem.worker_node_type }
                            }
                          }
                          // DLT Edition as neutral badge
                          if (wType === 'DLT' && effectiveItem.dlt_edition) {
                            config.badges.push({ text: effectiveItem.dlt_edition })
                          }
                        } else if (wType === 'DBSQL') {
                          // DBSQL - warehouse type as badge, size as detail
                          if (effectiveItem.dbsql_warehouse_type && (effectiveItem.dbsql_warehouse_type || '').toUpperCase() !== 'SERVERLESS') {
                            config.badges.push({ text: (effectiveItem.dbsql_warehouse_type || '').toUpperCase() })
                          }
                          if (effectiveItem.dbsql_warehouse_size) {
                            config.details.push(effectiveItem.dbsql_warehouse_size)
                          }
                          if (effectiveItem.dbsql_num_clusters && effectiveItem.dbsql_num_clusters > 1) {
                            config.details.push(`${effectiveItem.dbsql_num_clusters} clusters`)
                          }
                        } else if (wType === 'VECTOR_SEARCH') {
                          // AI Search - mode as badge
                          if (effectiveItem.vector_search_mode) {
                            const modeLabel = effectiveItem.vector_search_mode === 'storage_optimized' ? 'Storage Opt.' : 'Standard'
                            config.badges.push({ text: modeLabel })
                          }
                          if (effectiveItem.vector_capacity_millions) {
                            config.details.push(`${effectiveItem.vector_capacity_millions}M vectors`)
                          }
                        } else if (wType === 'MODEL_SERVING') {
                          // Model Serving - GPU type
                          if (effectiveItem.model_serving_gpu_type) {
                            config.details.push(effectiveItem.model_serving_gpu_type)
                          }
                        } else if (wType === 'FMAPI_DATABRICKS' || wType === 'FMAPI_PROPRIETARY') {
                          // Foundation Model API - check rate_type for provisioned vs token
                          if (effectiveItem.fmapi_rate_type) {
                            const isHourly = effectiveItem.fmapi_rate_type.startsWith('provisioned_')
                              || effectiveItem.fmapi_rate_type === 'batch_inference'
                            config.badges.push({ text: isHourly ? 'Hourly' : 'Token' })
                          }
                          if (effectiveItem.fmapi_provider && wType === 'FMAPI_PROPRIETARY') {
                            config.details.push(effectiveItem.fmapi_provider)
                          }
                          if (effectiveItem.fmapi_model) {
                            config.details.push(effectiveItem.fmapi_model)
                          }
                        } else if (wType === 'LAKEBASE') {
                          // Lakebase
                          if (effectiveItem.lakebase_cu) {
                            config.details.push(`CU ${effectiveItem.lakebase_cu}`)
                          }
                          if (effectiveItem.lakebase_ha_nodes && effectiveItem.lakebase_ha_nodes > 0) {
                            config.badges.push({ text: `HA ×${effectiveItem.lakebase_ha_nodes}` })
                          }
                          if (effectiveItem.lakebase_storage_gb && effectiveItem.lakebase_storage_gb > 0) {
                            config.details.push(`${effectiveItem.lakebase_storage_gb.toLocaleString()} GB`)
                          }
                        } else if (wType === 'AI_GATEWAY') {
                          const gatewayUsage = calculateAIGatewayUsage(effectiveItem)
                          if (gatewayUsage.inferenceTables.enabled) {
                            config.badges.push({ text: 'Inference Tables' })
                            config.details.push(
                              `${formatNumber(gatewayUsage.inferenceTables.monthlyPayloadGB, 3)} GB / ${formatNumber(gatewayUsage.inferenceTables.monthlyDBUs, 3)} DBUs`,
                            )
                          }
                          if (gatewayUsage.usageTracking.enabled) {
                            config.badges.push({ text: 'Usage Tracking' })
                            config.details.push(
                              `${formatNumber(gatewayUsage.usageTracking.monthlyPayloadGB, 3)} GB / ${formatNumber(gatewayUsage.usageTracking.monthlyDBUs, 3)} DBUs`,
                            )
                          }
                        } else if (wType === 'AGENT_EVALUATION') {
                          const evaluationUsage = calculateAgentEvaluationUsage(effectiveItem)
                          if (evaluationUsage.labelsEnabled) {
                            config.badges.push({ text: 'Evaluation Labels' })
                            config.details.push(
                              `${formatNumber(evaluationUsage.inputTokensMillions, 3)}M input + ${formatNumber(evaluationUsage.outputTokensMillions, 3)}M output / ${formatNumber(evaluationUsage.evaluationTokenDBUs, 3)} DBUs`,
                            )
                          }
                          if (evaluationUsage.syntheticDataEnabled) {
                            config.badges.push({ text: 'Synthetic Data' })
                            config.details.push(
                              `${evaluationUsage.syntheticQuestions.toLocaleString()} questions / ${formatNumber(evaluationUsage.syntheticQuestionDBUs, 3)} DBUs`,
                            )
                          }
                        } else if (wType === 'ZEROBUS') {
                          const zerobusUsage = calculateZerobusUsage(effectiveItem)
                          config.badges.push({
                            text: zerobusUsage.mode === 'otel' ? 'OTel' : 'Standard',
                          })
                          config.details.push(
                            `${formatNumber(zerobusUsage.monthlyIngestedGB, 3)} GB / ${formatNumber(zerobusUsage.monthlyDBUs, 3)} DBUs`,
                          )
                        }
                        
                        return config
                      }
                      
                      const structuredConfig = getStructuredConfig()
                      
                      return (
                        <SortableRow key={item.line_item_id} id={item.line_item_id} disabled={!isDragEnabled}>
                        <div
                          ref={(el) => { workloadRefs.current[item.line_item_id] = el }}
                        >
                          {/* Row */}
                          <div 
                            className={clsx(
                              "grid grid-cols-12 gap-2 py-3 px-3 cursor-pointer hover:bg-[var(--bg-hover)] transition-all",
                              isSelected && isBulkSelectMode && "bg-lava-600/5",
                              isExpanded && "bg-[var(--bg-tertiary)]"
                            )}
                            onClick={() => toggleExpand(item.line_item_id)}
                          >
                            {/* Checkbox - Only in bulk select mode */}
                            {isBulkSelectMode && (
                              <div className="col-span-1 flex items-center" onClick={(e) => e.stopPropagation()}>
                                <input
                                  type="checkbox"
                                  checked={isSelected}
                                  onChange={() => toggleItemSelection(item.line_item_id)}
                                  className="w-3.5 h-3.5 rounded border-[var(--border-primary)] text-lava-600 focus:ring-lava-600"
                                />
                              </div>
                            )}
                            
                            {/* Workload Name & Type */}
                            <div className={clsx(
                              "flex items-center gap-3",
                              isBulkSelectMode ? "col-span-4 sm:col-span-3" : "col-span-5 sm:col-span-4"
                            )}>
                              <div className={clsx("w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0", typeConfig.bgColor)}>
                                <TypeIcon className={clsx("w-4 h-4", typeConfig.color)} />
                              </div>
                              <div className="min-w-0">
                                <p className="font-semibold text-[var(--text-primary)] text-sm truncate" title={item.workload_name}>{item.workload_name}</p>
                                <p className="text-xs text-[var(--text-muted)] truncate" title={typeName}>{typeName}</p>
                              </div>
                            </div>
                            
                            {/* Configuration - Clean, minimal design */}
                            <div className="hidden sm:flex col-span-4 items-center gap-2 min-w-0">
                              {/* Badges - only 2 colors: orange accent for key features, gray for rest */}
                              {structuredConfig.badges.length > 0 && (
                                <div className="flex items-center gap-1 shrink-0">
                                  {structuredConfig.badges.map((badge, idx) => (
                                    <span 
                                      key={idx} 
                                      className={clsx(
                                        "px-1.5 py-0.5 rounded text-[10px] font-medium",
                                        badge.accent 
                                          ? "bg-lava-600/10 text-lava-700 dark:text-lava-500" 
                                          : "bg-[var(--bg-tertiary)] text-[var(--text-muted)]"
                                      )}
                                    >
                                      {badge.text}
                                    </span>
                                  ))}
                                </div>
                              )}
                              
                              {/* Compute config - monochrome, handle different driver/worker types */}
                              {(structuredConfig.driver || structuredConfig.workers) && (
                                <span className="text-[11px] text-[var(--text-secondary)] font-mono truncate" title={`Driver: ${structuredConfig.driver || 'N/A'}, Workers: ${structuredConfig.workers?.count || 0}× ${structuredConfig.workers?.type || 'N/A'}`}>
                                  {(() => {
                                    const d = structuredConfig.driver
                                    const w = structuredConfig.workers
                                    if (d && w) {
                                      // Both driver and workers
                                      if (d === w.type) {
                                        // Same type: show combined count (workers + 1 driver)
                                        return `${w.count + 1}× ${w.type}`
                                      } else {
                                        // Different types: show both
                                        return `${d} + ${w.count}× ${w.type}`
                                      }
                                    } else if (w) {
                                      return `${w.count}× ${w.type}`
                                    } else if (d) {
                                      return d
                                    }
                                    return ''
                                  })()}
                                </span>
                              )}
                              
                              {/* Other details - simple text */}
                              {structuredConfig.details.length > 0 && (
                                <span className="text-[11px] text-[var(--text-secondary)] truncate" title={structuredConfig.details.join(' · ')}>
                                  {structuredConfig.details.join(' · ')}
                                </span>
                              )}
                            </div>
                            
                            {/* Cost + Actions - Combined for tighter spacing */}
                            <div className="col-span-7 sm:col-span-4 flex items-center justify-end gap-3">
                              {/* Cost - Using shared component */}
                              <WorkloadCostDisplay 
                                costs={costs} 
                                size="sm"
                                showDBUs={effectiveItem.workload_type !== 'GENERAL_STORAGE'}
                                isLoading={(() => {
                                  const needsVMCosts = (
                                    !effectiveItem.serverless_enabled &&
                                    ['JOBS', 'ALL_PURPOSE', 'DLT'].includes(wType)
                                  ) ||
                                    (wType === 'DBSQL' && (effectiveItem.dbsql_warehouse_type || '').toUpperCase() !== 'SERVERLESS')
                                  return isLoadingVMCosts && needsVMCosts
                                })()}
                              />
                              
                              {/* Actions */}
                              <div className="flex items-center gap-0.5">
                                {/* Calculator button - show/hide calculation */}
                                <button
                                  onClick={(e) => { e.stopPropagation(); toggleFormula(item.line_item_id, true) }}
                                  className={clsx(
                                    "p-1.5 rounded transition-colors",
                                    formulaVisibleItems.has(item.line_item_id)
                                      ? "text-lava-600 bg-lava-500/10"
                                      : "text-[var(--text-muted)] hover:text-lava-600 hover:bg-lava-500/10"
                                  )}
                                  title={formulaVisibleItems.has(item.line_item_id) ? "Hide calculation" : "Show calculation"}
                                >
                                  <CalculatorIcon className="w-4 h-4" />
                                </button>
                                <button
                                  onClick={(e) => handleCloneWorkload(e, item)}
                                  className="p-1.5 rounded text-[var(--text-muted)] hover:text-blue-500 hover:bg-blue-500/10"
                                  title="Clone"
                                >
                                  <DocumentDuplicateIcon className="w-4 h-4" />
                                </button>
                                <button
                                  onClick={(e) => { e.stopPropagation(); handleDeleteLineItem(item) }}
                                  className="p-1.5 rounded text-[var(--text-muted)] hover:text-red-500 hover:bg-red-500/10"
                                  title="Delete"
                                >
                                  <TrashIcon className="w-4 h-4" />
                                </button>
                                {/* Expand indicator */}
                                <div className={clsx(
                                  "p-1 rounded transition-colors",
                                  isExpanded ? "bg-lava-600/10" : "hover:bg-[var(--bg-tertiary)]"
                                )}>
                                  {isExpanded ? (
                                    <ChevronUpIcon className="w-5 h-5 text-lava-600" />
                                  ) : (
                                    <ChevronDownIcon className="w-5 h-5 text-[var(--text-muted)]" />
                                  )}
                                </div>
                              </div>
                            </div>
                          </div>
                          
                          {/* Mobile Config Row - Show on small screens only */}
                          {!isExpanded && (structuredConfig.badges.length > 0 || structuredConfig.driver || structuredConfig.workers || structuredConfig.details.length > 0) && (
                            <div className="sm:hidden px-3 pb-2 flex items-center gap-2 pl-12 flex-wrap">
                              {/* Badges */}
                              {structuredConfig.badges.map((badge, idx) => (
                                <span 
                                  key={idx} 
                                  className={clsx(
                                    "px-1.5 py-0.5 rounded text-[10px] font-medium",
                                    badge.accent 
                                      ? "bg-lava-600/10 text-lava-700 dark:text-lava-500" 
                                      : "bg-[var(--bg-tertiary)] text-[var(--text-muted)]"
                                  )}
                                >
                                  {badge.text}
                                </span>
                              ))}
                              {/* Compute config - handle different driver/worker types */}
                              {(structuredConfig.driver || structuredConfig.workers) && (
                                <span className="text-[11px] text-[var(--text-secondary)] font-mono">
                                  {(() => {
                                    const d = structuredConfig.driver
                                    const w = structuredConfig.workers
                                    if (d && w) {
                                      if (d === w.type) {
                                        return `${w.count + 1}× ${w.type}`
                                      } else {
                                        return `${d} + ${w.count}× ${w.type}`
                                      }
                                    } else if (w) {
                                      return `${w.count}× ${w.type}`
                                    } else if (d) {
                                      return d
                                    }
                                    return ''
                                  })()}
                                </span>
                              )}
                              {/* Details */}
                              {structuredConfig.details.length > 0 && (
                                <span className="text-[11px] text-[var(--text-secondary)]">
                                  {structuredConfig.details.join(' · ')}
                                </span>
                              )}
                            </div>
                          )}
                          
                          {/* Expanded Details Row - Cost breakdown & config (like card view) */}
                          {isExpanded && (
                            <div className="bg-[var(--bg-secondary)] px-4 pt-3 pb-2 border-b border-[var(--border-primary)]">
                              {/* Cost breakdown grid */}
                              <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3 text-xs">
                                <div>
                                  <span className="text-[var(--text-muted)]">DBU Cost</span>
                                  <p className="font-semibold text-[var(--text-primary)]">{formatCurrency(costs.dbuCost)}</p>
                                </div>
                                {costs.dsuCost > 0 && (
                                  <div>
                                    <span className="text-[var(--text-muted)]">DSU Cost</span>
                                    <p className="font-semibold text-purple-600 dark:text-purple-400">{formatCurrency(costs.dsuCost)}</p>
                                  </div>
                                )}
                                {/* Hide VM Cost for serverless workloads */}
                                {!['VECTOR_SEARCH', 'MODEL_SERVING', 'FMAPI_DATABRICKS', 'FMAPI_PROPRIETARY', 'LAKEBASE', 'AI_GATEWAY', 'AGENT_EVALUATION', 'ZEROBUS'].includes(wType) && (
                                  <div>
                                    <span className="text-[var(--text-muted)]">VM Cost</span>
                                    <p className="font-semibold text-[var(--text-primary)]">{formatCurrency(costs.vmCost)}</p>
                                  </div>
                                )}
                                
                                {/* AI Search: Units Used */}
                                {wType === 'VECTOR_SEARCH' && costs.unitsUsed !== undefined && (
                                  <div>
                                    <span className="text-[var(--text-muted)]">Units Used</span>
                                    <p className="font-semibold text-blue-600 dark:text-blue-400">{costs.unitsUsed} unit{costs.unitsUsed !== 1 ? 's' : ''}</p>
                                  </div>
                                )}
                                
                                {/* Compute workloads: show driver/worker nodes - uses effectiveItem for real-time sync */}
                                {['JOBS', 'ALL_PURPOSE', 'DLT'].includes(wType) && !isServerless && (
                                  <>
                                    {effectiveItem.driver_node_type && (
                                      <div>
                                        <span className="text-[var(--text-muted)]">Driver</span>
                                        <p className="font-mono text-[var(--text-primary)] text-[10px]">{effectiveItem.driver_node_type}</p>
                                      </div>
                                    )}
                                    {effectiveItem.worker_node_type && (
                                      <div>
                                        <span className="text-[var(--text-muted)]">Workers</span>
                                        <p className="text-[var(--text-primary)]">{effectiveItem.num_workers}× <span className="font-mono text-[10px]">{effectiveItem.worker_node_type}</span></p>
                                      </div>
                                    )}
                                  </>
                                )}
                                
                                {/* Workload-specific details - uses effectiveItem for real-time sync */}
                                {getWorkloadSummaryDetails(effectiveItem).map((detail, idx) => (
                                  <div key={idx} className="min-w-0">
                                    <span className="text-[var(--text-muted)]">{detail.label}</span>
                                    <p className="text-[var(--text-primary)] break-words">{detail.value}</p>
                                  </div>
                                ))}
                                
                                {/* Usage summary */}
                                {usageSummary && (
                                  <div>
                                    <span className="text-[var(--text-muted)]">Usage</span>
                                    <p className="text-[var(--text-primary)]">{usageSummary}</p>
                                  </div>
                                )}
                              </div>
                              
                              {/* Formula toggle and display */}
                              <div className="mt-2 pt-2 border-t border-dashed border-[var(--border-primary)]">
                                <button 
                                  onClick={(e) => { e.stopPropagation(); toggleFormula(item.line_item_id) }}
                                  className="flex items-center gap-1.5 text-[11px] text-lava-600 hover:text-lava-700 transition-colors group"
                                >
                                  <CalculatorIcon className="w-3.5 h-3.5" />
                                  <span className="font-medium group-hover:underline">
                                    {formulaVisibleItems.has(item.line_item_id) ? 'Hide Cost Calculation' : 'Show Cost Calculation'}
                                  </span>
                                  {formulaVisibleItems.has(item.line_item_id) ? (
                                    <ChevronUpIcon className="w-3 h-3" />
                                  ) : (
                                    <ChevronDownIcon className="w-3 h-3" />
                                  )}
                                </button>
                              {formulaVisibleItems.has(item.line_item_id) && (
                                <div className="mt-2">
                                {(() => {
                                  // Determine if using run-based or direct hours
                                  const isRunBased = effectiveItem.runs_per_day && effectiveItem.avg_runtime_minutes && !effectiveItem.hours_per_month
                                  const runsPerDay = effectiveItem.runs_per_day || 0
                                  const avgRuntimeMin = effectiveItem.avg_runtime_minutes || 30
                                  const daysPerMonth = effectiveItem.days_per_month || 30
                                  const directHours = effectiveItem.hours_per_month || 730
                                  
                                  // Calculate hours - prefer run-based calculation when available
                                  const hoursPerMonth = isRunBased 
                                    ? runsPerDay * (avgRuntimeMin / 60) * daysPerMonth
                                    : directHours
                                  
                                  const dbuPrice = costs.dbuPrice || 0
                                  const dbuPriceDisplay = formatDbuPrice(wType, dbuPrice)
                                  
                                    if (wType === 'AI_GATEWAY') {
                                      return (
                                        <AIGatewayCostFormula
                                          item={effectiveItem}
                                          costs={costs}
                                          dbuPriceDisplay={dbuPriceDisplay}
                                        />
                                      )
                                    }

                                    if (wType === 'AGENT_EVALUATION') {
                                      return (
                                        <AgentEvaluationCostFormula
                                          item={effectiveItem}
                                          costs={costs}
                                          dbuPriceDisplay={dbuPriceDisplay}
                                        />
                                      )
                                    }

                                    if (wType === 'AI_RUNTIME') {
                                      return (
                                        <AIRuntimeCostFormula
                                          item={effectiveItem}
                                          costs={costs}
                                          cloud={formData.cloud || 'aws'}
                                          dbuPriceDisplay={dbuPriceDisplay}
                                        />
                                      )
                                    }

                                    if (wType === 'GENERAL_STORAGE') {
                                      return (
                                        <GeneralStorageCostFormula
                                          item={effectiveItem}
                                          costs={costs}
                                          cloud={formData.cloud || 'aws'}
                                          unitPrice={costs.dsuPrice || 0}
                                        />
                                      )
                                    }

                                    if (wType === 'ZEROBUS') {
                                      return (
                                        <ZerobusCostFormula
                                          item={effectiveItem}
                                          costs={costs}
                                          dbuPriceDisplay={dbuPriceDisplay}
                                        />
                                      )
                                    }

                                    // AI Search formula
                                    if (wType === 'VECTOR_SEARCH') {
                                      return (
                                        <AISearchCostFormula
                                          item={effectiveItem}
                                          costs={costs}
                                          dbuPriceDisplay={dbuPriceDisplay}
                                        />
                                      )
                                    }
                                  
                                  // FMAPI formula
                                  if (wType === 'FMAPI_DATABRICKS' || wType === 'FMAPI_PROPRIETARY') {
                                    const quantity = effectiveItem.fmapi_quantity || 1
                                    const rateType = effectiveItem.fmapi_rate_type || 'input_token'
                                    const isProvisioned = rateType.startsWith('provisioned_')
                                      || rateType === 'batch_inference'
                                    const dbuPerUnit = quantity > 0 ? costs.monthlyDBUs / quantity : 0
                                    const model = effectiveItem.fmapi_model || 'model'
                                    const provider = wType === 'FMAPI_PROPRIETARY'
                                      ? effectiveItem.fmapi_provider || ''
                                      : ''
                                    
                                    return (
                                      <div className="space-y-1">
                                        <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
                                          <span className="text-blue-600 font-semibold">DBU:</span>
                                          {isProvisioned ? (
                                            <>
                                              <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{quantity} hours/mo</span>
                                              <span>×</span>
                                              <span>{dbuPerUnit.toFixed(2)} DBU/hr</span>
                                              <span className="text-[var(--text-muted)]">({model})</span>
                                            </>
                                          ) : (
                                            <>
                                              <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{quantity}M tokens</span>
                                              <span>×</span>
                                              <span>{dbuPerUnit.toFixed(2)} DBU/M</span>
                                              <span className="text-[var(--text-muted)]">({provider ? `${provider}/` : ''}{model})</span>
                                            </>
                                          )}
                                          <span>=</span>
                                          <span>{formatNumber(costs.monthlyDBUs)} DBUs</span>
                                          <span>×</span>
                                          <span>${dbuPriceDisplay}/DBU</span>
                                          <span>=</span>
                                          <span className="font-semibold">{formatCurrency(costs.totalCost)}</span>
                                        </div>
                                      </div>
                                    )
                                  }
                                  
                                  // Lakebase formula
                                  if (wType === 'LAKEBASE') {
                                    const haNodes = effectiveItem.lakebase_ha_nodes || 1
                                    const lbDBURatesFormula: Record<string, Record<string, number>> = {
                                      'aws': { 'PREMIUM': 0.230, 'ENTERPRISE': 0.213 },
                                      'azure': { 'PREMIUM': 0.213, 'ENTERPRISE': 0.213 },
                                    }
                                    const lbCloudRates = lbDBURatesFormula[formData.cloud || 'aws'] || lbDBURatesFormula['aws']
                                    const lbDBUPerCU = lbCloudRates[(formData.tier || 'PREMIUM').toUpperCase()] || 0.213
                                    const storageGB = effectiveItem.lakebase_storage_gb || 0
                                    const pitrGB = effectiveItem.lakebase_pitr_gb || 0
                                    const snapshotGB = effectiveItem.lakebase_snapshot_gb || 0
                                    const pricePerDSU = costs.dsuPrice || 0
                                    const localStorageCost = storageGB * 15 * pricePerDSU
                                    const localPitrCost = pitrGB * 8.7 * pricePerDSU
                                    const localSnapshotCost = snapshotGB * 3.91 * pricePerDSU
                                    const localTotalStorageCost = localStorageCost + localPitrCost + localSnapshotCost
                                    const hasStorageCosts = localTotalStorageCost > 0
                                    const lakebaseConfig = resolveLakebaseAutoscaleConfig(effectiveItem)
                                    const lakebaseUsage = calculateLakebaseComputeUsage(lakebaseConfig, lbDBUPerCU, haNodes)
                                    const baselineCuHourPrice = lakebaseUsage.baselineEffectiveDbuPerCuHour * dbuPrice
                                    const scaleUpCuHourPrice = lakebaseUsage.scaleUpEffectiveDbuPerCuHour * dbuPrice
                                    const baselineCost = lakebaseUsage.billableBaselineDbu * dbuPrice
                                    const scaleUpCost = lakebaseUsage.scaleUpDbu * dbuPrice
                                    const hasScaleUpCost = lakebaseUsage.scaleUpHours > 0 && lakebaseUsage.scaleUpDbu > 0
                                    return (
                                      <div className="space-y-1">
                                        {/* Hours calculation (if run-based) */}
                                        {isRunBased && (
                                          <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
                                            <span className="font-semibold">Hours:</span>
                                            <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{runsPerDay} runs/day</span>
                                            <span>×</span>
                                            <span>(<span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{avgRuntimeMin}min</span> ÷ 60)</span>
                                            <span>×</span>
                                            <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{daysPerMonth} days/mo</span>
                                            <span>=</span>
                                            <span className="font-semibold">{hoursPerMonth.toFixed(1)}h/mo</span>
                                          </div>
                                        )}
                                        <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
                                          <span className="text-blue-600 font-semibold">Min DBU:</span>
                                          <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{lakebaseUsage.baselineEffectiveDbuPerCuHour.toFixed(3)} DBU/CU-hr</span>
                                          <span>×</span>
                                          <span>${dbuPriceDisplay}/DBU</span>
                                          <span>=</span>
                                          <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">${baselineCuHourPrice.toFixed(3)}/CU-hr</span>
                                          <span>×</span>
                                          <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{lakebaseUsage.baselineCu} CU</span>
                                          <span>×</span>
                                          <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{haNodes} nodes</span>
                                          <span>×</span>
                                          <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{lakebaseUsage.baselineHours.toFixed(0)}h</span>
                                          <span className="text-[var(--text-muted)]">
                                            ({lakebaseUsage.baselineDiscountPct > 0 ? `${lakebaseUsage.baselineDiscountPct}% lower DBU/CU-hr` : 'normal DBU/CU-hr'})
                                          </span>
                                          <span>=</span>
                                          <span>{formatNumber(lakebaseUsage.billableBaselineDbu)} DBUs</span>
                                          <span>×</span>
                                          <span>${dbuPriceDisplay}/DBU</span>
                                          <span>=</span>
                                          <span className="text-blue-500 font-semibold">{formatCurrency(baselineCost)}</span>
                                        </div>
                                        {hasScaleUpCost && (
                                          <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
                                            <span className="text-blue-600 font-semibold">Max DBU:</span>
                                            <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{lakebaseUsage.scaleUpEffectiveDbuPerCuHour.toFixed(3)} DBU/CU-hr</span>
                                            <span>×</span>
                                            <span>${dbuPriceDisplay}/DBU</span>
                                            <span>=</span>
                                            <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">${scaleUpCuHourPrice.toFixed(3)}/CU-hr</span>
                                            <span>×</span>
                                            <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{lakebaseUsage.scaleUpCu} CU</span>
                                            <span>×</span>
                                            <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{haNodes} nodes</span>
                                            <span>×</span>
                                            <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{lakebaseUsage.scaleUpHours.toFixed(0)}h</span>
                                            <span>=</span>
                                            <span>{formatNumber(lakebaseUsage.scaleUpDbu)} DBUs</span>
                                            <span>×</span>
                                            <span>${dbuPriceDisplay}/DBU</span>
                                            <span className="text-[var(--text-muted)]">(normal compute SKU)</span>
                                            <span>=</span>
                                            <span className="text-blue-500 font-semibold">{formatCurrency(scaleUpCost)}</span>
                                          </div>
                                        )}
                                        {storageGB > 0 && (
                                          <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
                                            <span className="text-purple-600 font-semibold">Storage:</span>
                                            <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{storageGB} GB</span>
                                            <span>×</span>
                                            <span>15 DSU/GB</span>
                                            <span>=</span>
                                            <span className="font-semibold">{formatNumber(storageGB * 15)} DSU</span>
                                            <span>×</span>
                                            <span>${pricePerDSU}/DSU/mo</span>
                                            <span>=</span>
                                            <span className="text-purple-500 font-semibold">{formatCurrency(localStorageCost)}</span>
                                          </div>
                                        )}
                                        {pitrGB > 0 && (
                                          <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
                                            <span className="text-purple-600 font-semibold">Point-in-Time Restore:</span>
                                            <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{pitrGB} GB</span>
                                            <span>×</span>
                                            <span>8.7 DSU/GB</span>
                                            <span>=</span>
                                            <span className="font-semibold">{formatNumber(pitrGB * 8.7)} DSU</span>
                                            <span>×</span>
                                            <span>${pricePerDSU}/DSU/mo</span>
                                            <span>=</span>
                                            <span className="text-purple-500 font-semibold">{formatCurrency(localPitrCost)}</span>
                                          </div>
                                        )}
                                        {snapshotGB > 0 && (
                                          <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
                                            <span className="text-purple-600 font-semibold">Snapshots:</span>
                                            <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{snapshotGB} GB</span>
                                            <span>×</span>
                                            <span>3.91 DSU/GB</span>
                                            <span>=</span>
                                            <span className="font-semibold">{formatNumber(snapshotGB * 3.91)} DSU</span>
                                            <span>×</span>
                                            <span>${pricePerDSU}/DSU/mo</span>
                                            <span>=</span>
                                            <span className="text-purple-500 font-semibold">{formatCurrency(localSnapshotCost)}</span>
                                          </div>
                                        )}
                                        <div className="flex items-center gap-1 text-[10px] font-mono flex-wrap pt-1 border-t border-dashed border-[var(--border-primary)]">
                                          <span className="text-[var(--text-secondary)] font-semibold">Total:</span>
                                          <span className="text-blue-500">{formatCurrency(costs.dbuCost)}</span>
                                          {hasStorageCosts && (
                                            <>
                                              <span>+</span>
                                              <span className="text-purple-500">{formatCurrency(costs.dsuCost)}</span>
                                            </>
                                          )}
                                          <span>=</span>
                                          <span className="text-[var(--text-primary)] font-medium">{formatCurrency(costs.totalCost)}</span>
                                        </div>
                                      </div>
                                    )
                                  }
                                  
                                  // Model Serving formula
                                  if (wType === 'MODEL_SERVING') {
                                    const gpuType = effectiveItem.model_serving_gpu_type || 'cpu'
                                    const msScaleOutDisp = effectiveItem.model_serving_scale_out || 'small'
                                    const msPresetsDisp: Record<string, number> = { small: 4, medium: 12, large: 40 }
                                    const msConcurrencyDisp = msScaleOutDisp === 'custom'
                                      ? (effectiveItem.model_serving_concurrency || 4)
                                      : (msPresetsDisp[msScaleOutDisp] || 4)
                                    const isGPU = isModelServingGPUType(gpuType)
                                    const billingCapacityUnits = getModelServingBillingCapacityUnits(
                                      gpuType,
                                      msConcurrencyDisp,
                                    )
                                    const baseRate = billingCapacityUnits > 0 && costs.dbuPerHour
                                      ? costs.dbuPerHour / billingCapacityUnits : 2
                                    return (
                                      <div className="space-y-1">
                                        {isRunBased && (
                                          <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
                                            <span className="font-semibold">Hours:</span>
                                            <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{runsPerDay} runs/day</span>
                                            <span>×</span>
                                            <span>(<span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{avgRuntimeMin}min</span> ÷ 60)</span>
                                            <span>×</span>
                                            <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{daysPerMonth} days/mo</span>
                                            <span>=</span>
                                            <span className="font-semibold">{hoursPerMonth.toFixed(1)}h/mo</span>
                                          </div>
                                        )}
                                        {isGPU && (
                                          <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
                                            <span className="text-blue-600 font-semibold">GPU replicas:</span>
                                            <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">
                                              {msConcurrencyDisp} concurrency
                                            </span>
                                            <span>÷</span>
                                            <span>4 concurrency/replica</span>
                                            <span>=</span>
                                            <span className="font-semibold">
                                              {billingCapacityUnits} GPU replica{billingCapacityUnits === 1 ? '' : 's'}
                                            </span>
                                            <span className="text-[var(--text-muted)]">
                                              ({msScaleOutDisp} scale-out)
                                            </span>
                                          </div>
                                        )}
                                        <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
                                          <span className="text-blue-600 font-semibold">DBU:</span>
                                          <span>{baseRate.toFixed(2)} DBU/{isGPU ? 'replica-hr' : 'concurrency-hr'}</span>
                                          <span className="text-[var(--text-muted)]">({gpuType})</span>
                                          <span>×</span>
                                          <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">
                                            {billingCapacityUnits} {isGPU ? `GPU replica${billingCapacityUnits === 1 ? '' : 's'}` : 'concurrency'}
                                          </span>
                                          {!isGPU && (
                                            <span className="text-[var(--text-muted)]">({msScaleOutDisp} scale-out)</span>
                                          )}
                                          <span>×</span>
                                          <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{hoursPerMonth.toFixed(isRunBased ? 1 : 0)}h</span>
                                          <span>=</span>
                                          <span>{formatNumber(costs.monthlyDBUs)} DBUs</span>
                                          <span>×</span>
                                          <span>${dbuPriceDisplay}/DBU</span>
                                          <span>=</span>
                                          <span className="font-semibold">{formatCurrency(costs.totalCost)}</span>
                                        </div>
                                      </div>
                                    )
                                  }
                                  
                                  // DBSQL formula
                                  if (wType === 'DBSQL') {
                                    const warehouseSize = effectiveItem.dbsql_warehouse_size || 'Small'
                                    const numClusters = effectiveItem.dbsql_num_clusters || 1
                                    const warehouseType = (effectiveItem.dbsql_warehouse_type || 'SERVERLESS').toUpperCase()
                                    const dbuPerWarehouse = costs.dbuPerHour ? costs.dbuPerHour / numClusters : 12
                                    const hasVMCost = costs.vmCost > 0
                                    const dbsqlCloud = formData.cloud || 'aws'
                                    const dbsqlRegion = formData.region || ''
                                    const warehouseConfig = isPricingBundleLoaded
                                      ? getBundleDBSQLWarehouseConfig(
                                          pricingBundle,
                                          dbsqlCloud,
                                          warehouseType,
                                          warehouseSize,
                                        )
                                      : null
                                    const driverPricingTier = effectiveItem.dbsql_driver_pricing_tier || effectiveItem.driver_pricing_tier || 'on_demand'
                                    const driverPaymentOption = effectiveItem.dbsql_driver_payment_option || effectiveItem.driver_payment_option || 'NA'
                                    const workerPricingTier = effectiveItem.dbsql_worker_pricing_tier || effectiveItem.worker_pricing_tier || 'spot'
                                    const workerPaymentOption = effectiveItem.dbsql_worker_payment_option || effectiveItem.worker_payment_option || 'NA'
                                    const driverVMRate = warehouseConfig
                                      ? getVMPrice(
                                          dbsqlCloud,
                                          dbsqlRegion,
                                          warehouseConfig.driver_instance_type,
                                          driverPricingTier,
                                          driverPaymentOption,
                                        )
                                      : 0
                                    const workerVMRate = warehouseConfig
                                      ? getVMPrice(
                                          dbsqlCloud,
                                          dbsqlRegion,
                                          warehouseConfig.worker_instance_type,
                                          workerPricingTier,
                                          workerPaymentOption,
                                        )
                                      : 0
                                    const hasMissingVMRate = Boolean(
                                      warehouseConfig && (driverVMRate <= 0 || workerVMRate <= 0)
                                    )
                                    const isVMRatePending = hasMissingVMRate && isLoadingVMCosts
                                    
                                    return (
                                      <div className="space-y-1.5">
                                        {/* Hours calculation (if run-based) */}
                                        {isRunBased && (
                                          <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
                                            <span className="font-semibold">Hours:</span>
                                            <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{runsPerDay} runs/day</span>
                                            <span>×</span>
                                            <span>(<span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{avgRuntimeMin}min</span> ÷ 60)</span>
                                            <span>×</span>
                                            <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{daysPerMonth} days/mo</span>
                                            <span>=</span>
                                            <span className="font-semibold">{hoursPerMonth.toFixed(1)}h/mo</span>
                                          </div>
                                        )}
                                        
                                        {/* DBU Cost Line */}
                                        <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
                                          <span className="text-blue-600 font-semibold">DBU:</span>
                                          <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{warehouseSize}</span>
                                          <span className="text-[var(--text-muted)]">({dbuPerWarehouse.toFixed(1)} DBU/hr)</span>
                                          {numClusters > 1 && (
                                            <>
                                              <span>×</span>
                                              <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{numClusters} clusters</span>
                                            </>
                                          )}
                                          <span>×</span>
                                          <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded" title={isRunBased ? `${runsPerDay} runs × ${avgRuntimeMin}min ÷ 60 × ${daysPerMonth} days` : undefined}>
                                            {hoursPerMonth.toFixed(isRunBased ? 1 : 0)}h
                                          </span>
                                          <span>=</span>
                                          <span>{formatNumber(costs.monthlyDBUs)} DBUs</span>
                                          <span>×</span>
                                          <span>${dbuPriceDisplay}/DBU</span>
                                          <span>=</span>
                                          <span className="text-blue-600 font-semibold">{formatCurrency(costs.dbuCost)}</span>
                                        </div>
                                        
                                        {/* VM Cost Breakdown (only for PRO/Classic) */}
                                        {warehouseType !== 'SERVERLESS' && (
                                          <VMCalculationLine
                                            driverType={warehouseConfig?.driver_instance_type || ''}
                                            driverRate={driverVMRate}
                                            workerType={warehouseConfig?.worker_instance_type || ''}
                                            workerRate={workerVMRate}
                                            workerCount={warehouseConfig?.worker_count || 0}
                                            clusters={numClusters}
                                            hours={Number(hoursPerMonth.toFixed(isRunBased ? 1 : 0))}
                                            total={costs.vmCost}
                                            status={
                                              !warehouseConfig
                                                ? 'Warehouse VM configuration unavailable'
                                                : hasMissingVMRate
                                                  ? (isVMRatePending ? 'Calculating VM rates…' : 'VM rate unavailable')
                                                  : undefined
                                            }
                                          />
                                        )}
                                        
                                        {/* Total Line */}
                                        <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap pt-1 border-t border-dashed border-[var(--border-primary)]">
                                          <span className="font-semibold">Total:</span>
                                          {hasMissingVMRate ? (
                                            <span className="font-medium text-amber-700 dark:text-amber-300">
                                              {isVMRatePending ? 'Calculating VM rates…' : 'VM rate unavailable'}
                                            </span>
                                          ) : (
                                            <>
                                              <span className="text-blue-600">{formatCurrency(costs.dbuCost)}</span>
                                              {hasVMCost && (
                                                <>
                                                  <span>+</span>
                                                  <span className="text-teal-600">{formatCurrency(costs.vmCost)}</span>
                                                </>
                                              )}
                                              <span>=</span>
                                              <span className="font-semibold">{formatCurrency(costs.totalCost)}</span>
                                            </>
                                          )}
                                        </div>
                                      </div>
                                    )
                                  }
                                  
                                  // Databricks Apps formula
                                  if (wType === 'DATABRICKS_APPS') {
                                    const appsSize = (effectiveItem.databricks_apps_size || 'medium').toLowerCase()
                                    const appsDbuRate = appsSize === 'large' ? 1.0 : 0.5
                                    return (
                                      <div className="space-y-1">
                                        <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
                                          <span className="text-blue-600 font-semibold">DBU:</span>
                                          <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{appsSize.charAt(0).toUpperCase() + appsSize.slice(1)}</span>
                                          <span className="text-[var(--text-muted)]">({appsDbuRate} DBU/hr)</span>
                                          <span>×</span>
                                          <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{hoursPerMonth.toFixed(0)}h</span>
                                          <span>=</span>
                                          <span>{formatNumber(costs.monthlyDBUs)} DBUs</span>
                                          <span>×</span>
                                          <span>${dbuPriceDisplay}/DBU</span>
                                          <span>=</span>
                                          <span className="font-semibold">{formatCurrency(costs.totalCost)}</span>
                                        </div>
                                      </div>
                                    )
                                  }

                                  // AI Extract / AI Classify formula
                                  if (wType === 'AI_EXTRACT' || wType === 'AI_CLASSIFY') {
                                    const isExtract = wType === 'AI_EXTRACT'
                                    const presetRates: Record<string, number> = isExtract
                                      ? {
                                          short_text: 45,
                                          invoice: 45,
                                          complex_reasoning: 562.5,
                                          deep_nesting: 537.5,
                                        }
                                      : { short_text: 4.5, rental_contract: 50 }
                                    const docType = ((isExtract ? effectiveItem.ai_extract_document_type : effectiveItem.ai_classify_document_type) || (isExtract ? 'invoice' : 'short_text')).toLowerCase()
                                    const customRate = isExtract ? effectiveItem.ai_extract_dbus_per_thousand : effectiveItem.ai_classify_dbus_per_thousand
                                    const unitRate = docType === 'custom' ? (customRate || 0) : (presetRates[docType] || 0)
                                    const quantity = (isExtract ? effectiveItem.ai_extract_num_inputs : effectiveItem.ai_classify_num_docs) || 0
                                    const quantityThousands = quantity / 1000
                                    return (
                                      <div className="space-y-1">
                                        <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
                                          <span className="text-blue-600 font-semibold">DBU:</span>
                                          <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{formatNumber(quantityThousands)}K {isExtract ? 'inputs' : 'documents'}</span>
                                          <span>×</span>
                                          <span>{unitRate} DBU/1K</span>
                                          <span className="text-[var(--text-muted)]">({docType})</span>
                                          <span>=</span>
                                          <span>{formatNumber(costs.monthlyDBUs)} DBUs</span>
                                          <span>×</span>
                                          <span>${dbuPriceDisplay}/DBU</span>
                                          <span>=</span>
                                          <span className="font-semibold">{formatCurrency(costs.totalCost)}</span>
                                        </div>
                                      </div>
                                    )
                                  }

                                  // AI Parse formula
                                  if (wType === 'AI_PARSE') {
                                    const aiComplexity = (effectiveItem.ai_parse_complexity || 'medium').toLowerCase()
                                    const aiComplexityRates: Record<string, number> = {
                                      'low_text': 12.5, 'low_images': 22.5, 'medium': 62.5, 'high': 87.5
                                    }
                                    const aiRate = aiComplexityRates[aiComplexity] || 62.5
                                    const aiPagesK = effectiveItem.ai_parse_pages_thousands || 0
                                    const complexityLabels: Record<string, string> = {
                                      'low_text': 'Low (Text)', 'low_images': 'Low (Images)', 'medium': 'Medium', 'high': 'High'
                                    }
                                    return (
                                      <div className="space-y-1">
                                        <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
                                          <span className="text-blue-600 font-semibold">DBU:</span>
                                          <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{aiPagesK}K pages</span>
                                          <span>×</span>
                                          <span>{aiRate} DBU/1K</span>
                                          <span className="text-[var(--text-muted)]">({complexityLabels[aiComplexity] || 'Medium'})</span>
                                          <span>=</span>
                                          <span>{formatNumber(costs.monthlyDBUs)} DBUs</span>
                                          <span>×</span>
                                          <span>${dbuPriceDisplay}/DBU</span>
                                          <span>=</span>
                                          <span className="font-semibold">{formatCurrency(costs.totalCost)}</span>
                                        </div>
                                      </div>
                                    )
                                  }

                                  // Shutterstock ImageAI formula
                                  if (wType === 'SHUTTERSTOCK_IMAGEAI') {
                                    const ssImages = effectiveItem.shutterstock_images || 0
                                    return (
                                      <div className="space-y-1">
                                        <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
                                          <span className="text-blue-600 font-semibold">DBU:</span>
                                          <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{ssImages.toLocaleString()} images</span>
                                          <span>×</span>
                                          <span>0.857 DBU/image</span>
                                          <span>=</span>
                                          <span>{formatNumber(costs.monthlyDBUs)} DBUs</span>
                                          <span>×</span>
                                          <span>${dbuPriceDisplay}/DBU</span>
                                          <span>=</span>
                                          <span className="font-semibold">{formatCurrency(costs.totalCost)}</span>
                                        </div>
                                      </div>
                                    )
                                  }

                                  // Compute workloads (JOBS, ALL_PURPOSE, DLT) - verbose formula with actual rates
                                  const numWorkers = effectiveItem.num_workers || 0
                                  const driverNode = effectiveItem.driver_node_type || ''
                                  const workerNode = effectiveItem.worker_node_type || ''
                                  const photonEnabled = effectiveItem.photon_enabled
                                  const hasVMCost = costs.vmCost > 0 && !isServerless

                                  // Look up actual DBU rates - prefer cached API data, fallback to instanceTypes
                                  const cloud = formData.cloud || 'aws'
                                  const region = formData.region || ''
                                  const driverInstance = instanceTypes.find(it => it.id === driverNode || it.name === driverNode)
                                  const workerInstance = instanceTypes.find(it => it.id === workerNode || it.name === workerNode)

                                  // Use getInstanceDbuRate (from dynamic API) with fallback to instanceTypes
                                  const driverDBURate = driverNode
                                    ? getInstanceDbuRate(cloud, driverNode) || driverInstance?.dbu_rate || 0.5
                                    : 0
                                  const workerDBURate = workerNode
                                    ? getInstanceDbuRate(cloud, workerNode) || workerInstance?.dbu_rate || 0.5
                                    : 0

                                  // Get VM costs using getVMPrice (same as cost calculation) - this properly fetches from VM pricing cache
                                  const driverVMCost = region && driverNode
                                    ? getVMPrice(cloud, region, driverNode, effectiveItem.driver_pricing_tier || 'on_demand', effectiveItem.driver_payment_option || 'no_upfront')
                                    : null
                                  const workerVMCost = region && workerNode
                                    ? getVMPrice(cloud, region, workerNode, effectiveItem.worker_pricing_tier || 'spot', effectiveItem.worker_payment_option || 'NA')
                                    : null

                                  const dbuPerHour = costs.dbuPerHour || 0

                                  return (
                                    <div className="space-y-1.5">
                                      {/* Hours calculation (if run-based) */}
                                      {isRunBased && (
                                        <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
                                          <span className="font-semibold">Hours:</span>
                                          <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{runsPerDay} runs/day</span>
                                          <span>×</span>
                                          <span>(<span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{avgRuntimeMin}min</span> ÷ 60)</span>
                                          <span>×</span>
                                          <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{daysPerMonth} days/mo</span>
                                          <span>=</span>
                                          <span className="font-semibold">{hoursPerMonth.toFixed(1)}h/mo</span>
                                        </div>
                                      )}
                                      
                                      {/* DBU Cost Line */}
                                      <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
                                        <span className="text-blue-600 font-semibold">DBU:</span>
                                        {isServerless ? (
                                          <ServerlessComputeDbuBreakdown
                                            workloadType={wType}
                                            serverlessMode={effectiveItem.serverless_mode}
                                            driverNode={driverNode}
                                            workerNode={workerNode}
                                            driverDBURate={driverDBURate}
                                            workerDBURate={workerDBURate}
                                            numWorkers={numWorkers}
                                            dbuPerHour={dbuPerHour}
                                          />
                                        ) : (
                                          <>
                                            <span>(</span>
                                            <span className="font-medium text-[var(--text-primary)]">Driver</span>
                                            <span>{driverNode}</span>
                                            <span className="text-[var(--text-muted)]">({driverDBURate.toFixed(2)} DBU/hr)</span>
                                            {numWorkers > 0 ? (
                                              <>
                                                <span>+</span>
                                                <span className="font-medium text-[var(--text-primary)]">
                                                  {numWorkers} worker{numWorkers !== 1 ? 's' : ''}
                                                </span>
                                                <span>{workerNode}</span>
                                                <span className="text-[var(--text-muted)]">({workerDBURate.toFixed(2)} DBU/hr each)</span>
                                              </>
                                            ) : (
                                              <span className="text-[var(--text-muted)]">Single node — driver only</span>
                                            )}
                                            <span>)</span>
                                            {photonEnabled && (
                                              <>
                                                <span>×</span>
                                                <span className="text-[var(--text-muted)]">Photon</span>
                                              </>
                                            )}
                                            <span>=</span>
                                            <span>{dbuPerHour.toFixed(2)} DBU/hr</span>
                                          </>
                                        )}
                                        <span>×</span>
                                        <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{hoursPerMonth.toFixed(isRunBased ? 1 : 0)}h</span>
                                        <span>=</span>
                                        <span>{formatNumber(costs.monthlyDBUs)} DBUs</span>
                                        <span>×</span>
                                        <span>${dbuPriceDisplay}/DBU</span>
                                        {wType === 'DLT' && (
                                          <span className="text-[var(--text-muted)]">
                                            ({effectiveItem.dlt_edition || 'CORE'} edition)
                                          </span>
                                        )}
                                        <span>=</span>
                                        <span className="text-blue-600 font-semibold">{formatCurrency(costs.dbuCost)}</span>
                                      </div>
                                      
                                      {/* VM Cost Line (only for classic compute) */}
                                      {hasVMCost && (
                                        <VMCalculationLine
                                          driverType={driverNode}
                                          driverRate={driverVMCost || 0}
                                          workerType={workerNode}
                                          workerRate={workerVMCost || 0}
                                          workerCount={numWorkers}
                                          hours={Number(hoursPerMonth.toFixed(isRunBased ? 1 : 0))}
                                          total={costs.vmCost}
                                        />
                                      )}
                                      
                                      {/* Total Line */}
                                      <div className="flex items-center gap-1 text-[10px] font-mono flex-wrap pt-1 border-t border-dashed border-[var(--border-primary)]">
                                        <span className="text-[var(--text-secondary)] font-semibold">Total:</span>
                                        <span className="text-blue-500">{formatCurrency(costs.dbuCost)}</span>
                                        {hasVMCost && (
                                          <>
                                            <span>+</span>
                                            <span className="text-teal-500">{formatCurrency(costs.vmCost)}</span>
                                          </>
                                        )}
                                        <span>=</span>
                                        <span className="text-[var(--text-primary)] font-medium">{formatCurrency(costs.totalCost)}</span>
                                      </div>
                                    </div>
                                  )
                                })()}
                              </div>
                              )}
                            </div>
                            </div>
                          )}
                          
                          {/* Expanded Form */}
                          {isExpanded && (
                            <div className="bg-[var(--bg-secondary)] border-b-2 border-lava-600/20 p-4">
                              <WorkloadErrorBoundary
                                onReset={() => {
                                  setExpandedItems(prev => {
                                    const next = new Set(prev)
                                    next.delete(item.line_item_id)
                                    return next
                                  })
                                }}
                              >
                                <WorkloadForm
                                  estimateId={id}
                                  lineItem={item}
                                  onClose={() => {
                                    setExpandedItems(prev => {
                                      const next = new Set(prev)
                                      next.delete(item.line_item_id)
                                      return next
                                    })
                                    setPendingFormEdits(prev => {
                                      const next = { ...prev }
                                      delete next[item.line_item_id]
                                      return next
                                    })
                                  }}
                                  onSave={() => {
                                    // Workload is already saved to DB by WorkloadForm - just clear pending edits
                                    setPendingFormEdits(prev => {
                                      const next = { ...prev }
                                      delete next[item.line_item_id]
                                      return next
                                    })
                                  }}
                                  onFormChange={(formData) => {
                                    setPendingFormEdits(prev => ({
                                      ...prev,
                                      [item.line_item_id]: formData
                                    }))
                                  }}
                                  inline
                                />
                              </WorkloadErrorBoundary>
                            </div>
                          )}
                        </div>
                        </SortableRow>
                      )
                    })}
                    </SortableContext>
                    </DndContext>
                  </div>
                )}

                {/* Card Views (Compact and Expanded) */}
                {workloadsViewMode !== 'table' && sortedLineItems.map((item, index) => {
                  // Create effective item that merges saved data with pending edits for real-time preview
                  const pendingEdits = pendingFormEdits[item.line_item_id]
                  const effectiveItem: LineItem = pendingEdits 
                    ? { ...item, ...pendingEdits } as LineItem
                    : item
                  
                  const costs = calculateItemCost(item, pendingEdits)
                  const isExpanded = expandedItems.has(item.line_item_id)
                  const usageSummary = getUsageSummary(effectiveItem)
                  const typeConfig = getWorkloadTypeConfig(effectiveItem.workload_type)
                  const TypeIcon = typeConfig.icon
                  const agentEvaluationUsage = effectiveItem.workload_type === 'AGENT_EVALUATION'
                    ? calculateAgentEvaluationUsage(effectiveItem)
                    : null
                  // Show details row only in 'expanded' mode OR when the item is expanded for editing
                  const showDetailsRow = workloadsViewMode === 'expanded' || isExpanded
                  
                  return (
                    <div
                      key={item.line_item_id}
                      ref={(el) => { workloadRefs.current[item.line_item_id] = el }}
                    >
                    <motion.div
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.02 }}
                      className="card overflow-hidden"
                    >
                      {/* Workload Header */}
                      <div 
                        className={clsx(
                          "p-4 cursor-pointer hover:bg-[var(--bg-hover)] transition-colors",
                          workloadsViewMode === 'cards' && !isExpanded && "py-3"
                        )}
                        onClick={() => toggleExpand(item.line_item_id)}
                      >
                        {/* Top row: name, badges, cost, actions */}
                        <div className="flex items-center gap-4">
                          <div className={clsx(
                            "rounded-lg flex items-center justify-center flex-shrink-0",
                            workloadsViewMode === 'cards' && !isExpanded ? "w-8 h-8" : "w-10 h-10",
                            typeConfig.bgColor
                          )}>
                            <TypeIcon className={clsx(
                              typeConfig.color,
                              workloadsViewMode === 'cards' && !isExpanded ? "w-4 h-4" : "w-5 h-5"
                            )} />
                          </div>
                          
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <h4 className={clsx(
                                "font-semibold truncate text-[var(--text-primary)]",
                                workloadsViewMode === 'cards' && !isExpanded && "text-sm"
                              )} title={item.workload_name}>{item.workload_name}</h4>
                              {(item.serverless_enabled || (item.workload_type === 'DBSQL' && (item.dbsql_warehouse_type || '').toUpperCase() === 'SERVERLESS')) && (
                                <span className="badge badge-teal">Serverless</span>
                              )}
                              {item.photon_enabled && (
                                <span className="badge badge-lava">
                                  <BoltIcon className="w-3 h-3 mr-0.5" />
                                  Photon
                                </span>
                              )}
                            </div>
                            <div className="flex items-center gap-2 text-xs text-[var(--text-muted)] mt-0.5">
                              <span>
                                {item.workload_type === 'VECTOR_SEARCH'
                                  ? 'AI Search'
                                  : workloadTypes.find(w => w.workload_type === item.workload_type)?.display_name || item.workload_type}
                              </span>
                            </div>
                            {agentEvaluationUsage && (
                              <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-[10px] text-[var(--text-secondary)] mt-1">
                                {agentEvaluationUsage.labelsEnabled && (
                                  <span>
                                    Evaluation tokens: {formatNumber(agentEvaluationUsage.inputTokensMillions, 3)}M in + {formatNumber(agentEvaluationUsage.outputTokensMillions, 3)}M out · {formatNumber(agentEvaluationUsage.evaluationTokenDBUs, 3)} DBUs
                                  </span>
                                )}
                                {agentEvaluationUsage.syntheticDataEnabled && (
                                  <span>
                                    Synthetic: {agentEvaluationUsage.syntheticQuestions.toLocaleString()} questions · {formatNumber(agentEvaluationUsage.syntheticQuestionDBUs, 3)} DBUs
                                  </span>
                                )}
                              </div>
                            )}
                          </div>
                          
                          {/* Cost - Using shared component */}
                          <WorkloadCostDisplay 
                            costs={costs}
                            size={workloadsViewMode === 'cards' && !isExpanded ? 'md' : 'lg'}
                            showDBUs={effectiveItem.workload_type !== 'GENERAL_STORAGE'}
                            isLoading={(() => {
                              const wType = effectiveItem.workload_type || ''
                              const needsVMCosts = (
                                !effectiveItem.serverless_enabled &&
                                ['JOBS', 'ALL_PURPOSE', 'DLT'].includes(wType)
                              ) ||
                                (wType === 'DBSQL' && (effectiveItem.dbsql_warehouse_type || '').toUpperCase() !== 'SERVERLESS')
                              return isLoadingVMCosts && needsVMCosts
                            })()}
                            className="min-w-[100px]"
                          />
                          
                          {/* Actions */}
                          <div className="flex items-center gap-1">
                            {/* Show calculation button - always visible, also expands row */}
                            <button
                              onClick={(e) => { e.stopPropagation(); toggleFormula(item.line_item_id, true) }}
                              className={clsx(
                                "p-1.5 rounded-md transition-colors",
                                formulaVisibleItems.has(item.line_item_id)
                                  ? "text-lava-600 bg-lava-500/10"
                                  : "text-[var(--text-muted)] hover:text-lava-600 hover:bg-lava-500/10"
                              )}
                              title={formulaVisibleItems.has(item.line_item_id) ? "Hide calculation" : "Show calculation"}
                            >
                              <CalculatorIcon className="w-4 h-4" />
                            </button>
                            <button
                              onClick={(e) => handleCloneWorkload(e, item)}
                              className="p-1.5 rounded-md text-[var(--text-muted)] hover:text-blue-500 hover:bg-blue-500/10"
                              title="Clone workload"
                            >
                              <DocumentDuplicateIcon className="w-4 h-4" />
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation()
                                handleDeleteLineItem(item)
                              }}
                              className="p-1.5 rounded-md text-[var(--text-muted)] hover:text-red-500 hover:bg-red-500/10"
                              title="Delete workload"
                            >
                              <TrashIcon className="w-4 h-4" />
                            </button>
                            {isExpanded ? (
                              <ChevronUpIcon className="w-5 h-5 text-[var(--text-muted)]" />
                            ) : (
                              <ChevronDownIcon className="w-5 h-5 text-[var(--text-muted)]" />
                            )}
                          </div>
                        </div>
                        
                        {/* Bottom row: Cost breakdown & config summary (only in expanded mode or when item is expanded) */}
                        {showDetailsRow && (
                          <>
                            <div className="mt-3 pt-3 border-t border-[var(--border-primary)] grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3 text-xs">
                              <div>
                                <span className="text-[var(--text-muted)]">DBU Cost</span>
                                <p className="font-semibold text-[var(--text-primary)]">{formatCurrency(costs.dbuCost)}</p>
                              </div>
                            {costs.dsuCost > 0 && (
                              <div>
                                <span className="text-[var(--text-muted)]">DSU Cost</span>
                                <p className="font-semibold text-purple-600 dark:text-purple-400">{formatCurrency(costs.dsuCost)}</p>
                              </div>
                            )}
                              {/* Hide VM Cost for serverless workloads */}
                              {!['VECTOR_SEARCH', 'MODEL_SERVING', 'FMAPI_DATABRICKS', 'FMAPI_PROPRIETARY', 'LAKEBASE', 'AI_GATEWAY', 'AGENT_EVALUATION', 'ZEROBUS'].includes(item.workload_type || '') && (
                                <div>
                                  <span className="text-[var(--text-muted)]">VM Cost</span>
                                  <p className="font-semibold text-[var(--text-primary)]">{formatCurrency(costs.vmCost)}</p>
                                </div>
                              )}
                              
                              {/* Lakebase: Storage Cost */}
                              {item.workload_type === 'LAKEBASE' && costs.storageCost !== undefined && costs.storageCost > 0 && (
                                <div>
                                  <span className="text-[var(--text-muted)]">Storage Cost</span>
                                  <p className="font-semibold text-purple-600 dark:text-purple-400">{formatCurrency(costs.storageCost)}</p>
                                </div>
                              )}
                              
                              {/* AI Search: Units Used (prominent) */}
                              {item.workload_type === 'VECTOR_SEARCH' && costs.unitsUsed !== undefined && (
                                <div>
                                  <span className="text-[var(--text-muted)]">Units Used</span>
                                  <p className="font-semibold text-blue-600 dark:text-blue-400">{costs.unitsUsed} unit{costs.unitsUsed !== 1 ? 's' : ''}</p>
                                </div>
                              )}
                              
                              {/* Compute workloads: show driver/worker nodes */}
                              {(item.workload_type === 'JOBS' || item.workload_type === 'ALL_PURPOSE' || item.workload_type === 'DLT') && (
                                <>
                                  {item.driver_node_type && (
                                    <div>
                                      <span className="text-[var(--text-muted)]">Driver</span>
                                      <p className="font-mono text-[var(--text-primary)] text-[10px]">{item.driver_node_type}</p>
                                    </div>
                                  )}
                                  {item.worker_node_type && (
                                    <div>
                                      <span className="text-[var(--text-muted)]">Workers</span>
                                      <p className="text-[var(--text-primary)]">{item.num_workers}× <span className="font-mono text-[10px]">{item.worker_node_type}</span></p>
                                    </div>
                                  )}
                                </>
                              )}
                              
                              {/* Workload-specific details */}
                              {getWorkloadSummaryDetails(item).map((detail, idx) => (
                                <div key={idx} className="min-w-0">
                                  <span className="text-[var(--text-muted)]">{detail.label}</span>
                                  <p className="text-[var(--text-primary)] break-words">{detail.value}</p>
                                </div>
                              ))}
                              
                              {/* Usage summary */}
                              {usageSummary && (
                                <div>
                                  <span className="text-[var(--text-muted)]">Usage</span>
                                  <p className="text-[var(--text-primary)]">{usageSummary}</p>
                                </div>
                              )}
                            </div>
                            
                            {/* Formula toggle and display */}
                            <div className="mt-2 pt-2 border-t border-dashed border-[var(--border-primary)]">
                              <button 
                                onClick={(e) => { e.stopPropagation(); toggleFormula(item.line_item_id) }}
                                className="flex items-center gap-1.5 text-[11px] text-lava-600 hover:text-lava-700 transition-colors group"
                              >
                                <CalculatorIcon className="w-3.5 h-3.5" />
                                <span className="font-medium group-hover:underline">
                                  {formulaVisibleItems.has(item.line_item_id) ? 'Hide Cost Calculation' : 'Show Cost Calculation'}
                                </span>
                                {formulaVisibleItems.has(item.line_item_id) ? (
                                  <ChevronUpIcon className="w-3 h-3" />
                                ) : (
                                  <ChevronDownIcon className="w-3 h-3" />
                                )}
                              </button>
                            {formulaVisibleItems.has(item.line_item_id) && (
                              <div className="mt-2">
                              {(() => {
                                // Use effectiveItem for real-time preview
                                const wType = effectiveItem.workload_type || ''
                                const isServerless = effectiveItem.serverless_enabled || (wType === 'DBSQL' && (effectiveItem.dbsql_warehouse_type || '').toUpperCase() === 'SERVERLESS')
                                
                                // Determine if using run-based or direct hours
                                const isRunBased = effectiveItem.runs_per_day && effectiveItem.avg_runtime_minutes && !effectiveItem.hours_per_month
                                const runsPerDay = effectiveItem.runs_per_day || 0
                                const avgRuntimeMin = effectiveItem.avg_runtime_minutes || 30
                                const daysPerMonth = effectiveItem.days_per_month || 30
                                const directHours = effectiveItem.hours_per_month || 730
                                
                                // Calculate hours
                                const hoursPerMonth = isRunBased 
                                  ? runsPerDay * (avgRuntimeMin / 60) * daysPerMonth
                                  : directHours
                                
                                const dbuPrice = costs.dbuPrice || 0
                                const dbuPriceDisplay = formatDbuPrice(wType, dbuPrice)
                                
                                if (wType === 'AI_GATEWAY') {
                                  return (
                                    <AIGatewayCostFormula
                                      item={effectiveItem}
                                      costs={costs}
                                      dbuPriceDisplay={dbuPriceDisplay}
                                    />
                                  )
                                }

                                if (wType === 'AGENT_EVALUATION') {
                                  return (
                                    <AgentEvaluationCostFormula
                                      item={effectiveItem}
                                      costs={costs}
                                      dbuPriceDisplay={dbuPriceDisplay}
                                    />
                                  )
                                }

                                if (wType === 'AI_RUNTIME') {
                                  return (
                                    <AIRuntimeCostFormula
                                      item={effectiveItem}
                                      costs={costs}
                                      cloud={formData.cloud || 'aws'}
                                      dbuPriceDisplay={dbuPriceDisplay}
                                    />
                                  )
                                }

                                if (wType === 'GENERAL_STORAGE') {
                                  return (
                                    <GeneralStorageCostFormula
                                      item={effectiveItem}
                                      costs={costs}
                                      cloud={formData.cloud || 'aws'}
                                      unitPrice={costs.dsuPrice || 0}
                                    />
                                  )
                                }

                                if (wType === 'ZEROBUS') {
                                  return (
                                    <ZerobusCostFormula
                                      item={effectiveItem}
                                      costs={costs}
                                      dbuPriceDisplay={dbuPriceDisplay}
                                    />
                                  )
                                }

                                // Special workloads
                                // AI Search formula
                                if (wType === 'VECTOR_SEARCH') {
                                  return (
                                    <AISearchCostFormula
                                      item={effectiveItem}
                                      costs={costs}
                                      dbuPriceDisplay={dbuPriceDisplay}
                                    />
                                  )
                                }
                                
                                if (wType === 'FMAPI_DATABRICKS' || wType === 'FMAPI_PROPRIETARY') {
                                  const quantity = effectiveItem.fmapi_quantity || 0
                                  const dbuPerM = costs.monthlyDBUs / (quantity || 1)
                                  return (
                                    <div className="space-y-1">
                                      <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
                                        <span className="text-blue-600 font-semibold">DBU:</span>
                                        <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{quantity}M tokens</span>
                                        <span>×</span>
                                        <span>{dbuPerM.toFixed(2)} DBU/M</span>
                                        <span>=</span>
                                        <span>{formatNumber(costs.monthlyDBUs)} DBUs</span>
                                        <span>×</span>
                                        <span>${dbuPriceDisplay}/DBU</span>
                                        <span>=</span>
                                        <span className="text-blue-600 font-semibold">{formatCurrency(costs.dbuCost)}</span>
                                      </div>
                                      <div className="flex items-center gap-1 text-[10px] font-mono flex-wrap pt-1 border-t border-dashed border-[var(--border-primary)]">
                                        <span className="text-[var(--text-secondary)] font-semibold">Total:</span>
                                        <span className="text-blue-500">{formatCurrency(costs.dbuCost)}</span>
                                        <span>=</span>
                                        <span className="text-[var(--text-primary)] font-medium">{formatCurrency(costs.totalCost)}</span>
                                      </div>
                                    </div>
                                  )
                                }
                                
                                if (wType === 'DBSQL') {
                                  const warehouseSize = effectiveItem.dbsql_warehouse_size || 'Small'
                                  const numClusters = effectiveItem.dbsql_num_clusters || 1
                                  const warehouseType = (effectiveItem.dbsql_warehouse_type || 'SERVERLESS').toUpperCase()
                                  const dbuPerWarehouse = costs.dbuPerHour ? costs.dbuPerHour / numClusters : 12
                                  const dbsqlCloud = formData.cloud || 'aws'
                                  const dbsqlRegion = formData.region || ''
                                  const warehouseConfig = isPricingBundleLoaded
                                    ? getBundleDBSQLWarehouseConfig(
                                        pricingBundle,
                                        dbsqlCloud,
                                        warehouseType,
                                        warehouseSize,
                                      )
                                    : null
                                  const driverPricingTier = effectiveItem.dbsql_driver_pricing_tier || effectiveItem.driver_pricing_tier || 'on_demand'
                                  const driverPaymentOption = effectiveItem.dbsql_driver_payment_option || effectiveItem.driver_payment_option || 'NA'
                                  const workerPricingTier = effectiveItem.dbsql_worker_pricing_tier || effectiveItem.worker_pricing_tier || 'spot'
                                  const workerPaymentOption = effectiveItem.dbsql_worker_payment_option || effectiveItem.worker_payment_option || 'NA'
                                  const driverVMRate = warehouseConfig
                                    ? getVMPrice(
                                        dbsqlCloud,
                                        dbsqlRegion,
                                        warehouseConfig.driver_instance_type,
                                        driverPricingTier,
                                        driverPaymentOption,
                                      )
                                    : 0
                                  const workerVMRate = warehouseConfig
                                    ? getVMPrice(
                                        dbsqlCloud,
                                        dbsqlRegion,
                                        warehouseConfig.worker_instance_type,
                                        workerPricingTier,
                                        workerPaymentOption,
                                      )
                                    : 0
                                  const hasMissingVMRate = Boolean(
                                    warehouseConfig && (driverVMRate <= 0 || workerVMRate <= 0)
                                  )
                                  const isVMRatePending = hasMissingVMRate && isLoadingVMCosts

                                  return (
                                    <div className="space-y-1.5">
                                      {isRunBased && (
                                        <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
                                          <span className="font-semibold">Hours:</span>
                                          <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{runsPerDay} runs/day</span>
                                          <span>×</span>
                                          <span>(<span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{avgRuntimeMin}min</span> ÷ 60)</span>
                                          <span>×</span>
                                          <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{daysPerMonth} days/mo</span>
                                          <span>=</span>
                                          <span className="font-semibold">{hoursPerMonth.toFixed(1)}h/mo</span>
                                        </div>
                                      )}
                                      <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
                                        <span className="text-blue-600 font-semibold">DBU:</span>
                                        <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{warehouseSize}</span>
                                        <span className="text-[var(--text-muted)]">({dbuPerWarehouse.toFixed(1)} DBU/hr)</span>
                                        {numClusters > 1 && (
                                          <>
                                            <span>×</span>
                                            <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{numClusters} clusters</span>
                                          </>
                                        )}
                                        <span>×</span>
                                        <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">
                                          {hoursPerMonth.toFixed(isRunBased ? 1 : 0)}h
                                        </span>
                                        <span>=</span>
                                        <span>{formatNumber(costs.monthlyDBUs)} DBUs</span>
                                        <span>×</span>
                                        <span>${dbuPriceDisplay}/DBU</span>
                                        <span>=</span>
                                        <span className="text-blue-600 font-semibold">{formatCurrency(costs.dbuCost)}</span>
                                      </div>
                                      {warehouseType !== 'SERVERLESS' && (
                                        <VMCalculationLine
                                          driverType={warehouseConfig?.driver_instance_type || ''}
                                          driverRate={driverVMRate}
                                          workerType={warehouseConfig?.worker_instance_type || ''}
                                          workerRate={workerVMRate}
                                          workerCount={warehouseConfig?.worker_count || 0}
                                          clusters={numClusters}
                                          hours={Number(hoursPerMonth.toFixed(isRunBased ? 1 : 0))}
                                          total={costs.vmCost}
                                          status={
                                            !warehouseConfig
                                              ? 'Warehouse VM configuration unavailable'
                                              : hasMissingVMRate
                                                ? (isVMRatePending ? 'Calculating VM rates…' : 'VM rate unavailable')
                                                : undefined
                                          }
                                        />
                                      )}
                                      <div className="flex items-center gap-1 text-[10px] font-mono flex-wrap pt-1 border-t border-dashed border-[var(--border-primary)]">
                                        <span className="text-[var(--text-secondary)] font-semibold">Total:</span>
                                        {hasMissingVMRate ? (
                                          <span className="font-medium text-amber-700 dark:text-amber-300">
                                            {isVMRatePending ? 'Calculating VM rates…' : 'VM rate unavailable'}
                                          </span>
                                        ) : (
                                          <>
                                            <span className="text-blue-500">{formatCurrency(costs.dbuCost)}</span>
                                            {costs.vmCost > 0 && (
                                              <>
                                                <span>+</span>
                                                <span className="text-teal-500">{formatCurrency(costs.vmCost)}</span>
                                              </>
                                            )}
                                            <span>=</span>
                                            <span className="text-[var(--text-primary)] font-medium">{formatCurrency(costs.totalCost)}</span>
                                          </>
                                        )}
                                      </div>
                                    </div>
                                  )
                                }

                                if (wType === 'LAKEBASE') {
                                  const nodes = effectiveItem.lakebase_ha_nodes || 1
                                  const storageGB = effectiveItem.lakebase_storage_gb || 0
                                  const pitrGB = effectiveItem.lakebase_pitr_gb || 0
                                  const snapshotGB = effectiveItem.lakebase_snapshot_gb || 0
                                  const pricePerDSU = costs.dsuPrice || 0
                                  const localStorageCost = storageGB * 15 * pricePerDSU
                                  const localPitrCost = pitrGB * 8.7 * pricePerDSU
                                  const localSnapshotCost = snapshotGB * 3.91 * pricePerDSU
                                  const localTotalStorageCost = localStorageCost + localPitrCost + localSnapshotCost
                                  const hasStorageCosts = localTotalStorageCost > 0
                                  const lbDBURatesCard: Record<string, Record<string, number>> = {
                                    'aws': { 'PREMIUM': 0.230, 'ENTERPRISE': 0.213 },
                                    'azure': { 'PREMIUM': 0.213, 'ENTERPRISE': 0.213 },
                                  }
                                  const lbCloudRatesCard = lbDBURatesCard[formData.cloud || 'aws'] || lbDBURatesCard['aws']
                                  const lbDBUPerCUCard = lbCloudRatesCard[(formData.tier || 'PREMIUM').toUpperCase()] || 0.213
                                  const lakebaseConfig = resolveLakebaseAutoscaleConfig(effectiveItem)
                                  const lakebaseUsage = calculateLakebaseComputeUsage(lakebaseConfig, lbDBUPerCUCard, nodes)
                                  const baselineCuHourPrice = lakebaseUsage.baselineEffectiveDbuPerCuHour * dbuPrice
                                  const scaleUpCuHourPrice = lakebaseUsage.scaleUpEffectiveDbuPerCuHour * dbuPrice
                                  const baselineCost = lakebaseUsage.billableBaselineDbu * dbuPrice
                                  const scaleUpCost = lakebaseUsage.scaleUpDbu * dbuPrice
                                  const hasScaleUpCost = lakebaseUsage.scaleUpHours > 0 && lakebaseUsage.scaleUpDbu > 0
                                  return (
                                    <div className="space-y-1">
                                      <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
                                        <span className="text-blue-600 font-semibold">Min DBU:</span>
                                        <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{lakebaseUsage.baselineEffectiveDbuPerCuHour.toFixed(3)} DBU/CU-hr</span>
                                        <span>×</span>
                                        <span>${dbuPriceDisplay}/DBU</span>
                                        <span>=</span>
                                        <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">${baselineCuHourPrice.toFixed(3)}/CU-hr</span>
                                        <span>×</span>
                                        <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{lakebaseUsage.baselineCu} CU</span>
                                        <span>×</span>
                                        <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{nodes} nodes</span>
                                        <span>×</span>
                                        <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{lakebaseUsage.baselineHours.toFixed(0)}h</span>
                                        <span className="text-[var(--text-muted)]">
                                          ({lakebaseUsage.baselineDiscountPct > 0 ? `${lakebaseUsage.baselineDiscountPct}% lower DBU/CU-hr` : 'normal DBU/CU-hr'})
                                        </span>
                                        <span>=</span>
                                        <span>{formatNumber(lakebaseUsage.billableBaselineDbu)} DBUs</span>
                                        <span>×</span>
                                        <span>${dbuPriceDisplay}/DBU</span>
                                        <span>=</span>
                                        <span className="text-blue-500 font-semibold">{formatCurrency(baselineCost)}</span>
                                      </div>
                                      {hasScaleUpCost && (
                                        <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
                                          <span className="text-blue-600 font-semibold">Max DBU:</span>
                                          <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{lakebaseUsage.scaleUpEffectiveDbuPerCuHour.toFixed(3)} DBU/CU-hr</span>
                                          <span>×</span>
                                          <span>${dbuPriceDisplay}/DBU</span>
                                          <span>=</span>
                                          <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">${scaleUpCuHourPrice.toFixed(3)}/CU-hr</span>
                                          <span>×</span>
                                          <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{lakebaseUsage.scaleUpCu} CU</span>
                                          <span>×</span>
                                          <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{nodes} nodes</span>
                                          <span>×</span>
                                          <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{lakebaseUsage.scaleUpHours.toFixed(0)}h</span>
                                          <span>=</span>
                                          <span>{formatNumber(lakebaseUsage.scaleUpDbu)} DBUs</span>
                                          <span>×</span>
                                          <span>${dbuPriceDisplay}/DBU</span>
                                          <span className="text-[var(--text-muted)]">(normal compute SKU)</span>
                                          <span>=</span>
                                          <span className="text-blue-500 font-semibold">{formatCurrency(scaleUpCost)}</span>
                                        </div>
                                      )}
                                      {storageGB > 0 && (
                                        <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
                                          <span className="text-purple-600 font-semibold">Storage:</span>
                                          <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{storageGB} GB</span>
                                          <span>×</span>
                                          <span>15 DSU/GB</span>
                                          <span>=</span>
                                          <span className="font-semibold">{formatNumber(storageGB * 15)} DSU</span>
                                          <span>×</span>
                                          <span>${pricePerDSU}/DSU/mo</span>
                                          <span>=</span>
                                          <span className="text-purple-500 font-semibold">{formatCurrency(localStorageCost)}</span>
                                        </div>
                                      )}
                                      {pitrGB > 0 && (
                                        <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
                                          <span className="text-purple-600 font-semibold">Point-in-Time Restore:</span>
                                          <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{pitrGB} GB</span>
                                          <span>×</span>
                                          <span>8.7 DSU/GB</span>
                                          <span>=</span>
                                          <span className="font-semibold">{formatNumber(pitrGB * 8.7)} DSU</span>
                                          <span>×</span>
                                          <span>${pricePerDSU}/DSU/mo</span>
                                          <span>=</span>
                                          <span className="text-purple-500 font-semibold">{formatCurrency(localPitrCost)}</span>
                                        </div>
                                      )}
                                      {snapshotGB > 0 && (
                                        <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
                                          <span className="text-purple-600 font-semibold">Snapshots:</span>
                                          <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{snapshotGB} GB</span>
                                          <span>×</span>
                                          <span>3.91 DSU/GB</span>
                                          <span>=</span>
                                          <span className="font-semibold">{formatNumber(snapshotGB * 3.91)} DSU</span>
                                          <span>×</span>
                                          <span>${pricePerDSU}/DSU/mo</span>
                                          <span>=</span>
                                          <span className="text-purple-500 font-semibold">{formatCurrency(localSnapshotCost)}</span>
                                        </div>
                                      )}
                                      <div className="flex items-center gap-1 text-[10px] font-mono flex-wrap pt-1 border-t border-dashed border-[var(--border-primary)]">
                                        <span className="text-[var(--text-secondary)] font-semibold">Total:</span>
                                        <span className="text-blue-500">{formatCurrency(costs.dbuCost)}</span>
                                        {hasStorageCosts && (
                                          <>
                                            <span>+</span>
                                            <span className="text-purple-500">{formatCurrency(localTotalStorageCost)}</span>
                                          </>
                                        )}
                                        <span>=</span>
                                        <span className="text-[var(--text-primary)] font-medium">{formatCurrency(costs.totalCost)}</span>
                                      </div>
                                    </div>
                                  )
                                }
                                
                                if (wType === 'MODEL_SERVING') {
                                  const gpuTypeCard = effectiveItem.model_serving_gpu_type || 'cpu'
                                  const msScaleOutCard = effectiveItem.model_serving_scale_out || 'small'
                                  const msPresetsCard: Record<string, number> = { small: 4, medium: 12, large: 40 }
                                  const msConcurrencyCard = msScaleOutCard === 'custom'
                                    ? (effectiveItem.model_serving_concurrency || 4)
                                    : (msPresetsCard[msScaleOutCard] || 4)
                                  const isGPUCard = isModelServingGPUType(gpuTypeCard)
                                  const billingCapacityUnitsCard = getModelServingBillingCapacityUnits(
                                    gpuTypeCard,
                                    msConcurrencyCard,
                                  )
                                  const baseRateCard = billingCapacityUnitsCard > 0 && costs.dbuPerHour
                                    ? costs.dbuPerHour / billingCapacityUnitsCard : 2
                                  return (
                                    <div className="space-y-1">
                                      {isGPUCard && (
                                        <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
                                          <span className="text-blue-600 font-semibold">GPU replicas:</span>
                                          <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">
                                            {msConcurrencyCard} concurrency
                                          </span>
                                          <span>÷</span>
                                          <span>4 concurrency/replica</span>
                                          <span>=</span>
                                          <span className="font-semibold">
                                            {billingCapacityUnitsCard} GPU replica{billingCapacityUnitsCard === 1 ? '' : 's'}
                                          </span>
                                          <span className="text-[var(--text-muted)]">
                                            ({msScaleOutCard} scale-out)
                                          </span>
                                        </div>
                                      )}
                                      <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
                                        <span className="text-blue-600 font-semibold">DBU:</span>
                                        <span>{baseRateCard.toFixed(2)} DBU/{isGPUCard ? 'replica-hr' : 'concurrency-hr'}</span>
                                        <span>×</span>
                                        <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">
                                          {billingCapacityUnitsCard} {isGPUCard ? `GPU replica${billingCapacityUnitsCard === 1 ? '' : 's'}` : 'concurrency'}
                                        </span>
                                        {!isGPUCard && (
                                          <span className="text-[var(--text-muted)]">({msScaleOutCard} scale-out)</span>
                                        )}
                                        <span>×</span>
                                        <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{hoursPerMonth.toFixed(0)}h</span>
                                        <span>=</span>
                                        <span>{formatNumber(costs.monthlyDBUs)} DBUs</span>
                                        <span>×</span>
                                        <span>${dbuPriceDisplay}/DBU</span>
                                        <span>=</span>
                                        <span className="text-blue-600 font-semibold">{formatCurrency(costs.dbuCost)}</span>
                                      </div>
                                      <div className="flex items-center gap-1 text-[10px] font-mono flex-wrap pt-1 border-t border-dashed border-[var(--border-primary)]">
                                        <span className="text-[var(--text-secondary)] font-semibold">Total:</span>
                                        <span className="text-blue-500">{formatCurrency(costs.dbuCost)}</span>
                                        <span>=</span>
                                        <span className="text-[var(--text-primary)] font-medium">{formatCurrency(costs.totalCost)}</span>
                                      </div>
                                    </div>
                                  )
                                }
                                
                                // Databricks Apps formula (card view)
                                if (wType === 'DATABRICKS_APPS') {
                                  const appsSize = (effectiveItem.databricks_apps_size || 'medium').toLowerCase()
                                  const appsDbuRate = appsSize === 'large' ? 1.0 : 0.5
                                  return (
                                    <div className="space-y-1">
                                      <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
                                        <span className="text-blue-600 font-semibold">DBU:</span>
                                        <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{appsSize.charAt(0).toUpperCase() + appsSize.slice(1)}</span>
                                        <span className="text-[var(--text-muted)]">({appsDbuRate} DBU/hr)</span>
                                        <span>×</span>
                                        <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{hoursPerMonth.toFixed(0)}h</span>
                                        <span>=</span>
                                        <span>{formatNumber(costs.monthlyDBUs)} DBUs</span>
                                        <span>×</span>
                                        <span>${dbuPriceDisplay}/DBU</span>
                                        <span>=</span>
                                        <span className="font-semibold">{formatCurrency(costs.totalCost)}</span>
                                      </div>
                                    </div>
                                  )
                                }

                                // AI Extract / AI Classify formula
                                if (wType === 'AI_EXTRACT' || wType === 'AI_CLASSIFY') {
                                  const isExtract = wType === 'AI_EXTRACT'
                                  const presetRates: Record<string, number> = isExtract
                                    ? {
                                        short_text: 45,
                                        invoice: 45,
                                        complex_reasoning: 562.5,
                                        deep_nesting: 537.5,
                                      }
                                    : { short_text: 4.5, rental_contract: 50 }
                                  const docType = ((isExtract ? effectiveItem.ai_extract_document_type : effectiveItem.ai_classify_document_type) || (isExtract ? 'invoice' : 'short_text')).toLowerCase()
                                  const customRate = isExtract ? effectiveItem.ai_extract_dbus_per_thousand : effectiveItem.ai_classify_dbus_per_thousand
                                  const unitRate = docType === 'custom' ? (customRate || 0) : (presetRates[docType] || 0)
                                  const quantity = (isExtract ? effectiveItem.ai_extract_num_inputs : effectiveItem.ai_classify_num_docs) || 0
                                  const quantityThousands = quantity / 1000
                                  return (
                                    <div className="space-y-1">
                                      <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
                                        <span className="text-blue-600 font-semibold">DBU:</span>
                                        <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{formatNumber(quantityThousands)}K {isExtract ? 'inputs' : 'documents'}</span>
                                        <span>×</span>
                                        <span>{unitRate} DBU/1K</span>
                                        <span className="text-[var(--text-muted)]">({docType})</span>
                                        <span>=</span>
                                        <span>{formatNumber(costs.monthlyDBUs)} DBUs</span>
                                        <span>×</span>
                                        <span>${dbuPriceDisplay}/DBU</span>
                                        <span>=</span>
                                        <span className="font-semibold">{formatCurrency(costs.totalCost)}</span>
                                      </div>
                                    </div>
                                  )
                                }

                                // AI Parse formula (card view)
                                if (wType === 'AI_PARSE') {
                                  const aiComplexity = (effectiveItem.ai_parse_complexity || 'medium').toLowerCase()
                                  const aiComplexityRates: Record<string, number> = {
                                    'low_text': 12.5, 'low_images': 22.5, 'medium': 62.5, 'high': 87.5
                                  }
                                  const aiRate = aiComplexityRates[aiComplexity] || 62.5
                                  const aiPagesK = effectiveItem.ai_parse_pages_thousands || 0
                                  const complexityLabels: Record<string, string> = {
                                    'low_text': 'Low (Text)', 'low_images': 'Low (Images)', 'medium': 'Medium', 'high': 'High'
                                  }
                                  return (
                                    <div className="space-y-1">
                                      <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
                                        <span className="text-blue-600 font-semibold">DBU:</span>
                                        <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{aiPagesK}K pages</span>
                                        <span>×</span>
                                        <span>{aiRate} DBU/1K</span>
                                        <span className="text-[var(--text-muted)]">({complexityLabels[aiComplexity] || 'Medium'})</span>
                                        <span>=</span>
                                        <span>{formatNumber(costs.monthlyDBUs)} DBUs</span>
                                        <span>×</span>
                                        <span>${dbuPriceDisplay}/DBU</span>
                                        <span>=</span>
                                        <span className="font-semibold">{formatCurrency(costs.totalCost)}</span>
                                      </div>
                                    </div>
                                  )
                                }

                                // Shutterstock ImageAI formula (card view)
                                if (wType === 'SHUTTERSTOCK_IMAGEAI') {
                                  const ssImages = effectiveItem.shutterstock_images || 0
                                  return (
                                    <div className="space-y-1">
                                      <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
                                        <span className="text-blue-600 font-semibold">DBU:</span>
                                        <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{ssImages.toLocaleString()} images</span>
                                        <span>×</span>
                                        <span>0.857 DBU/image</span>
                                        <span>=</span>
                                        <span>{formatNumber(costs.monthlyDBUs)} DBUs</span>
                                        <span>×</span>
                                        <span>${dbuPriceDisplay}/DBU</span>
                                        <span>=</span>
                                        <span className="font-semibold">{formatCurrency(costs.totalCost)}</span>
                                      </div>
                                    </div>
                                  )
                                }

                                // Compute workloads (JOBS, ALL_PURPOSE, DLT, DBSQL)
                                const numWorkers = effectiveItem.num_workers || 0
                                const driverNode = effectiveItem.driver_node_type || ''
                                const workerNode = effectiveItem.worker_node_type || ''
                                const photonEnabled = effectiveItem.photon_enabled
                                const hasVMCost = costs.vmCost > 0 && !isServerless

                                // Look up actual DBU rates
                                const cloud = formData.cloud || 'aws'
                                const region = formData.region || ''
                                const driverInstance = instanceTypes.find(it => it.id === driverNode || it.name === driverNode)
                                const workerInstance = instanceTypes.find(it => it.id === workerNode || it.name === workerNode)

                                const driverDBURate = driverNode
                                  ? getInstanceDbuRate(cloud, driverNode) || driverInstance?.dbu_rate || 0.5
                                  : 0
                                const workerDBURate = workerNode
                                  ? getInstanceDbuRate(cloud, workerNode) || workerInstance?.dbu_rate || 0.5
                                  : 0

                                const driverVMCost = region && driverNode
                                  ? getVMPrice(cloud, region, driverNode, effectiveItem.driver_pricing_tier || 'on_demand', effectiveItem.driver_payment_option || 'no_upfront')
                                  : null
                                const workerVMCost = region && workerNode
                                  ? getVMPrice(cloud, region, workerNode, effectiveItem.worker_pricing_tier || 'spot', effectiveItem.worker_payment_option || 'NA')
                                  : null

                                const dbuPerHour = costs.dbuPerHour || 0

                                return (
                                  <div className="space-y-1.5">
                                    {/* Hours calculation (if run-based) */}
                                    {isRunBased && (
                                      <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
                                        <span className="font-semibold">Hours:</span>
                                        <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{runsPerDay} runs/day</span>
                                        <span>×</span>
                                        <span>(<span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{avgRuntimeMin}min</span> ÷ 60)</span>
                                        <span>×</span>
                                        <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{daysPerMonth} days/mo</span>
                                        <span>=</span>
                                        <span className="font-semibold">{hoursPerMonth.toFixed(1)}h/mo</span>
                                      </div>
                                    )}
                                    
                                    {/* DBU Cost Line */}
                                    <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
                                      <span className="text-blue-600 font-semibold">DBU:</span>
                                      {isServerless ? (
                                        <ServerlessComputeDbuBreakdown
                                          workloadType={wType}
                                          serverlessMode={effectiveItem.serverless_mode}
                                          driverNode={driverNode}
                                          workerNode={workerNode}
                                          driverDBURate={driverDBURate}
                                          workerDBURate={workerDBURate}
                                          numWorkers={numWorkers}
                                          dbuPerHour={dbuPerHour}
                                        />
                                      ) : (
                                        <>
                                          <span>(</span>
                                          <span className="font-medium text-[var(--text-primary)]">Driver</span>
                                          <span>{driverNode}</span>
                                          <span className="text-[var(--text-muted)]">({driverDBURate.toFixed(2)} DBU/hr)</span>
                                          {numWorkers > 0 ? (
                                            <>
                                              <span>+</span>
                                              <span className="font-medium text-[var(--text-primary)]">
                                                {numWorkers} worker{numWorkers !== 1 ? 's' : ''}
                                              </span>
                                              <span>{workerNode}</span>
                                              <span className="text-[var(--text-muted)]">({workerDBURate.toFixed(2)} DBU/hr each)</span>
                                            </>
                                          ) : (
                                            <span className="text-[var(--text-muted)]">Single node — driver only</span>
                                          )}
                                          <span>)</span>
                                          {photonEnabled && (
                                            <>
                                              <span>×</span>
                                              <span className="text-[var(--text-muted)]">Photon</span>
                                            </>
                                          )}
                                          <span>=</span>
                                          <span>{dbuPerHour.toFixed(2)} DBU/hr</span>
                                        </>
                                      )}
                                      <span>×</span>
                                      <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{hoursPerMonth.toFixed(isRunBased ? 1 : 0)}h</span>
                                      <span>=</span>
                                      <span>{formatNumber(costs.monthlyDBUs)} DBUs</span>
                                      <span>×</span>
                                      <span>${dbuPriceDisplay}/DBU</span>
                                      {wType === 'DLT' && (
                                        <span className="text-[var(--text-muted)]">
                                          ({effectiveItem.dlt_edition || 'CORE'} edition)
                                        </span>
                                      )}
                                      <span>=</span>
                                      <span className="text-blue-600 font-semibold">{formatCurrency(costs.dbuCost)}</span>
                                    </div>
                                    
                                    {/* VM Cost Line (only for classic compute) */}
                                    {hasVMCost && (
                                      <VMCalculationLine
                                        driverType={driverNode}
                                        driverRate={driverVMCost || 0}
                                        workerType={workerNode}
                                        workerRate={workerVMCost || 0}
                                        workerCount={numWorkers}
                                        hours={Number(hoursPerMonth.toFixed(isRunBased ? 1 : 0))}
                                        total={costs.vmCost}
                                      />
                                    )}
                                    
                                    {/* Total Line */}
                                    <div className="flex items-center gap-1 text-[10px] font-mono flex-wrap pt-1 border-t border-dashed border-[var(--border-primary)]">
                                      <span className="text-[var(--text-secondary)] font-semibold">Total:</span>
                                      <span className="text-blue-500">{formatCurrency(costs.dbuCost)}</span>
                                      {hasVMCost && (
                                        <>
                                          <span>+</span>
                                          <span className="text-teal-500">{formatCurrency(costs.vmCost)}</span>
                                        </>
                                      )}
                                      <span>=</span>
                                      <span className="text-[var(--text-primary)] font-medium">{formatCurrency(costs.totalCost)}</span>
                                    </div>
                                  </div>
                                )
                              })()}
                              </div>
                            )}
                            </div>
                          </>
                        )}
                      </div>
                      
                      {/* Expanded: Edit Form */}
                      {isExpanded && (
                        <div className="border-t border-[var(--border-primary)] p-4 bg-[var(--bg-tertiary)]">
                          <WorkloadErrorBoundary
                            onReset={() => {
                              setExpandedItems(prev => {
                                const next = new Set(prev)
                                next.delete(item.line_item_id)
                                return next
                              })
                            }}
                          >
                            <WorkloadForm
                              estimateId={id}
                              lineItem={item}
                              onClose={() => {
                                setExpandedItems(prev => {
                                  const next = new Set(prev)
                                  next.delete(item.line_item_id)
                                  return next
                                })
                                // Clear pending edits when closing
                                setPendingFormEdits(prev => {
                                  const next = { ...prev }
                                  delete next[item.line_item_id]
                                  return next
                                })
                              }}
                              onSave={() => {
                                // Workload is already saved to DB by WorkloadForm - just clear pending edits
                                setPendingFormEdits(prev => {
                                  const next = { ...prev }
                                  delete next[item.line_item_id]
                                  return next
                                })
                              }}
                              onFormChange={(formData) => {
                                setPendingFormEdits(prev => ({
                                  ...prev,
                                  [item.line_item_id]: formData
                                }))
                              }}
                              inline
                            />
                          </WorkloadErrorBoundary>
                        </div>
                      )}
                    </motion.div>
                    </div>
                  )
                })}
                
                {/* Add New Workload Section */}
                {!canAddWorkload ? (
                  <div className="p-4 rounded-xl border-2 border-dashed border-[var(--border-secondary)] bg-[var(--bg-tertiary)] text-center">
                    <ExclamationTriangleIcon className="w-6 h-6 mx-auto mb-2 text-lava-600" />
                    <p className="text-sm text-[var(--text-muted)]">
                      Please select a <span className="font-semibold text-[var(--text-secondary)]">Region</span> and <span className="font-semibold text-[var(--text-secondary)]">Databricks Tier</span> before adding workloads
                    </p>
                  </div>
                ) : showAddForm ? (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="card p-5"
                  >
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="font-semibold text-[var(--text-primary)]">Add New Workload</h3>
                      <button
                        onClick={() => setShowAddForm(false)}
                        className="text-sm text-[var(--text-muted)] hover:text-[var(--text-primary)]"
                      >
                        Cancel
                      </button>
                    </div>
                    <WorkloadForm
                      estimateId={id}
                      lineItem={null}
                      onClose={() => setShowAddForm(false)}
                      onSave={() => {
                        // Workload is already saved to DB by WorkloadForm - nothing extra needed
                      }}
                      inline
                    />
                  </motion.div>
                ) : (
                  <button
                    onClick={() => setShowAddForm(true)}
                    className="w-full p-4 rounded-xl border-2 border-dashed border-[var(--border-secondary)] hover:border-lava-600/50 hover:bg-lava-600/5 transition-all flex items-center justify-center gap-2 text-[var(--text-muted)] hover:text-lava-600"
                  >
                    <PlusIcon className="w-5 h-5" />
                    Add Workload
                  </button>
                )}
              </>
            )}
          </motion.div>
        </div>
        
        {/* Cost Summary Sidebar - Right column */}
        {!isCostSummaryCollapsed && (
          <div className="lg:col-span-1">
            <div className="card p-5 sticky top-24">
              {/* Header with Minimize Button */}
              <div className="flex items-center justify-between mb-4">
                <h3 className="flex items-center gap-2">
                  <CurrencyDollarIcon className="w-5 h-5 text-lava-600" />
                  <span className="font-semibold text-[var(--text-primary)]">Cost Summary</span>
                  {(isLoadingLineItems && !lineItemsLoaded) && (
                    <div className="w-3 h-3 border-2 border-lava-600/30 border-t-lava-600 rounded-full animate-spin" />
                  )}
                </h3>
                <button
                  onClick={() => setIsCostSummaryCollapsed(true)}
                  className="flex items-center gap-1 px-2 py-1 rounded-md text-[11px] font-medium text-[var(--text-muted)] hover:text-lava-600 hover:bg-lava-600/10 border border-transparent hover:border-lava-600/20"
                  title="Dock to bottom bar"
                >
                  <ChevronDownIcon className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">Dock</span>
                </button>
              </div>
              
              {!canAddWorkload ? (
                <div className="text-center py-8">
                  <ExclamationTriangleIcon className="w-10 h-10 mx-auto mb-3 text-lava-600" />
                  <p className="text-sm text-[var(--text-muted)]">Select region & tier to see estimates</p>
                </div>
              ) : (isLoadingLineItems && !lineItemsLoaded) ? (
                <div className="space-y-3 py-4">
                  <div className="h-10 bg-[var(--bg-tertiary)] rounded animate-pulse" />
                  <div className="h-5 bg-[var(--bg-tertiary)] rounded animate-pulse w-2/3 mx-auto" />
                </div>
              ) : lineItems.length > 0 ? (
                <div className="space-y-4">
                  {/* Monthly Total - Hero */}
                  <div className="text-center py-4 px-3 bg-gradient-to-br from-lava-600/5 to-amber-500/5 rounded-xl border border-lava-600/10">
                    <p className="text-xs text-[var(--text-muted)] mb-1">Monthly Estimate</p>
                    <p className={clsx(
                      "text-3xl font-bold text-lava-600",
                      isLoadingVMCosts && "opacity-60"
                    )}>
                      {formatCurrency(totalCosts.totalCost)}
                    </p>
                    <p className="text-sm text-[var(--text-secondary)] mt-1">
                      {formatCurrency(totalCosts.totalCost * 12)}/year
                    </p>
                  </div>
                  
                  {/* Cost Breakdown Grid */}
                  <div className="grid grid-cols-2 gap-2">
                    <div className="text-center p-2 sm:p-3 rounded-xl bg-gradient-to-br from-blue-500/5 to-blue-500/10 border border-blue-500/20 min-w-0">
                      <p className="text-[10px] text-blue-600 dark:text-blue-400 uppercase tracking-wider font-medium mb-1">DBU Cost</p>
                      <p className="text-xs font-bold text-[var(--text-primary)] tabular-nums truncate" title={formatCurrency(totalCosts.totalDBUCost)}>{formatCurrencyCompact(totalCosts.totalDBUCost)}</p>
                    </div>
                    <div className="text-center p-2 sm:p-3 rounded-xl bg-gradient-to-br from-purple-500/5 to-purple-500/10 border border-purple-500/20 min-w-0">
                      <p className="text-[10px] text-purple-600 dark:text-purple-400 uppercase tracking-wider font-medium mb-1">DSU Cost</p>
                      <p className="text-xs font-bold text-[var(--text-primary)] tabular-nums truncate" title={formatCurrency(totalCosts.totalDSUCost)}>{formatCurrencyCompact(totalCosts.totalDSUCost)}</p>
                    </div>
                    <div className="text-center p-2 sm:p-3 rounded-xl bg-gradient-to-br from-teal-500/5 to-teal-500/10 border border-teal-500/20 min-w-0">
                      <p className="text-[10px] text-teal-600 dark:text-teal-400 uppercase tracking-wider font-medium mb-1">VM Cost</p>
                      <p className="text-xs font-bold text-[var(--text-primary)] tabular-nums truncate" title={isLoadingVMCosts ? 'Loading...' : formatCurrency(totalCosts.totalVMCost)}>{isLoadingVMCosts ? '...' : formatCurrencyCompact(totalCosts.totalVMCost)}</p>
                    </div>
                    <div className="text-center p-2 sm:p-3 rounded-xl bg-gradient-to-br from-amber-500/5 to-amber-500/10 border border-amber-500/20 min-w-0">
                      <p className="text-[10px] text-amber-600 dark:text-amber-400 uppercase tracking-wider font-medium mb-1">Add-on</p>
                      <p className="text-xs font-bold text-[var(--text-primary)] tabular-nums truncate" title={formatCurrency(totalCosts.totalPlatformAddonCost)}>{formatCurrencyCompact(totalCosts.totalPlatformAddonCost)}</p>
                    </div>
                  </div>
                  
                  {/* Workload Breakdown - Click to navigate */}
                  <div className="pt-3 border-t border-[var(--border-primary)]">
                    <p className="text-xs font-medium text-[var(--text-muted)] mb-3 flex items-center justify-between">
                      <span>Workloads ({lineItems.length})</span>
                      <span className="text-[10px] italic">Click to view</span>
                    </p>
                    <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
                      {totalCosts.platformAddon && (
                        <div className="w-full p-2 rounded-lg bg-amber-500/5 border border-amber-500/15">
                          <div className="flex items-center justify-between text-xs gap-2">
                            <span className="flex items-center gap-1.5 text-amber-700 dark:text-amber-300 font-medium truncate">
                              <ShieldCheckIcon className="w-3.5 h-3.5 flex-shrink-0" />
                              {totalCosts.platformAddon.displayName}
                            </span>
                            <span className="font-semibold text-[var(--text-primary)] tabular-nums text-[11px]">
                              {formatCurrency(totalCosts.totalPlatformAddonCost)}
                            </span>
                          </div>
                          <p className="mt-1 text-[10px] text-[var(--text-muted)]">
                            {totalCosts.platformAddon.appliedRatePct}% of {formatCurrency(totalCosts.productSpendAtList)} product spend at list
                            {totalCosts.platformAddon.discountPct > 0
                              ? `, less ${totalCosts.platformAddon.discountPct}% add-on discount`
                              : ''}
                          </p>
                        </div>
                      )}
                      {(() => {
                        const sortedItems = [...lineItems]
                          .map(item => ({ item, costs: calculateItemCost(item) }))
                          .sort((a, b) => b.costs.totalCost - a.costs.totalCost)
                        
                        const barColors = ['bg-lava-600', 'bg-amber-500', 'bg-blue-500', 'bg-emerald-500', 'bg-purple-500', 'bg-pink-500', 'bg-cyan-500', 'bg-indigo-500']
                        
                        return sortedItems.map(({ item, costs }, idx) => {
                          const percent = totalCosts.totalCost > 0 ? (costs.totalCost / totalCosts.totalCost) * 100 : 0
                          const barColor = barColors[idx % barColors.length]
                          return (
                            <button
                              key={item.line_item_id}
                              onClick={() => scrollToWorkload(item.line_item_id)}
                              className="w-full text-left p-2 rounded-lg hover:bg-[var(--bg-tertiary)] transition-colors group cursor-pointer"
                              title={`Click to view "${item.workload_name}"`}
                            >
                              <div className="flex items-center justify-between text-xs mb-1 gap-2">
                                <span className="text-[var(--text-secondary)] truncate flex-1 min-w-0 group-hover:text-lava-600 transition-colors font-medium" title={item.workload_name}>
                                  {item.workload_name}
                                </span>
                                <div className="flex items-center gap-1.5 flex-shrink-0">
                                  <span className="text-[var(--text-muted)] text-[10px] tabular-nums">{percent.toFixed(0)}%</span>
                                  <span className="font-semibold text-[var(--text-primary)] tabular-nums text-[11px]" title={formatCurrency(costs.totalCost)}>{formatCurrency(costs.totalCost)}</span>
                                </div>
                              </div>
                              <div className="h-1.5 bg-[var(--bg-tertiary)] rounded-full overflow-hidden">
                                <div className={clsx("h-full rounded-full transition-all", barColor, "group-hover:brightness-110")} style={{ width: `${Math.max(percent, 2)}%` }} />
                              </div>
                            </button>
                          )
                        })
                      })()}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8">
                  <CurrencyDollarIcon className="w-10 h-10 mx-auto mb-3 text-[var(--text-muted)]" />
                  <p className="text-sm text-[var(--text-muted)]">Add workloads to see estimates</p>
                </div>
              )}
              
              <p className="mt-4 pt-3 border-t border-[var(--border-primary)] text-[10px] text-[var(--text-muted)] text-center">
                Estimates based on published Databricks pricing
              </p>
            </div>
          </div>
        )}
      </div>
      
      {/* Collapsed Cost Summary - Sticky Bottom Bar */}
      {isCostSummaryCollapsed && (
        <div className="fixed bottom-0 left-0 right-0 z-40">
          {/* Expandable Workload Breakdown - Dropdown style */}
          {showCollapsedBreakdown && lineItems.length > 0 && (
            <>
              {/* Backdrop to close on click outside */}
              <div 
                className="fixed inset-0 bg-black/20 z-[-1]" 
                onClick={() => setShowCollapsedBreakdown(false)}
              />
              <div className="bg-[var(--bg-primary)] border border-[var(--border-primary)] rounded-t-xl shadow-[0_-8px_30px_rgba(0,0,0,0.2)] mx-4 sm:mx-8">
                <div className="p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="text-sm font-semibold text-[var(--text-primary)]">
                      All Workloads ({lineItems.length})
                    </h4>
                    <button
                      onClick={() => setShowCollapsedBreakdown(false)}
                      className="text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)] px-2 py-1 rounded hover:bg-[var(--bg-tertiary)]"
                    >
                      Close ✕
                    </button>
                  </div>
                  {/* Scrollable list of ALL workloads */}
                  <div className="max-h-64 overflow-y-auto space-y-1 pr-1">
                    {(() => {
                      const sortedItems = [...lineItems]
                        .map(item => ({ item, costs: calculateItemCost(item) }))
                        .sort((a, b) => b.costs.totalCost - a.costs.totalCost)
                      
                      const barColors = ['bg-lava-600', 'bg-amber-500', 'bg-blue-500', 'bg-emerald-500', 'bg-purple-500', 'bg-pink-500', 'bg-cyan-500', 'bg-indigo-500']
                      
                      return sortedItems.map(({ item, costs }, idx) => {
                        const percent = totalCosts.totalCost > 0 ? (costs.totalCost / totalCosts.totalCost) * 100 : 0
                        const barColor = barColors[idx % barColors.length]
                        return (
                          <button
                            key={item.line_item_id}
                            onClick={() => {
                              setShowCollapsedBreakdown(false)
                              scrollToWorkload(item.line_item_id)
                            }}
                            className="w-full text-left p-2 rounded-lg hover:bg-[var(--bg-tertiary)] transition-colors group"
                          >
                            <div className="flex items-center justify-between text-xs mb-1">
                              <span className="font-medium text-[var(--text-primary)] truncate max-w-[200px] group-hover:text-lava-600" title={item.workload_name}>
                                {item.workload_name}
                              </span>
                              <div className="flex items-center gap-3 flex-shrink-0">
                                <span className="text-[var(--text-muted)] tabular-nums">{percent.toFixed(0)}%</span>
                                <span className="font-semibold text-[var(--text-primary)] tabular-nums w-20 text-right">{formatCurrency(costs.totalCost)}</span>
                              </div>
                            </div>
                            <div className="h-1 bg-[var(--bg-tertiary)] rounded-full overflow-hidden">
                              <div className={clsx("h-full rounded-full", barColor)} style={{ width: `${Math.max(percent, 1)}%` }} />
                            </div>
                          </button>
                        )
                      })
                    })()}
                  </div>
                  <p className="text-[10px] text-[var(--text-muted)] mt-2 text-center">Click any workload to scroll to it</p>
                </div>
              </div>
            </>
          )}
          
          {/* Main Bar */}
          <div className="bg-[var(--bg-primary)] border-t border-[var(--border-primary)] shadow-[0_-4px_20px_rgba(0,0,0,0.1)]">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="flex items-center justify-between h-14">
                {/* Left side - Expand to sidebar panel button */}
                <button
                  onClick={() => setIsCostSummaryCollapsed(false)}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[var(--text-muted)] hover:text-lava-600 hover:bg-lava-600/10 text-sm transition-colors"
                  title="Expand Cost Summary panel"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4 5h4v14H4z" />
                  </svg>
                  <span className="hidden sm:inline">Expand</span>
                </button>
                
                {/* Center - Stats with colored labels */}
                <div className="flex items-center gap-2 sm:gap-4 text-sm flex-shrink min-w-0">
                  {/* Workload count - clearly styled as expandable */}
                  <button
                    onClick={() => setShowCollapsedBreakdown(!showCollapsedBreakdown)}
                    className={clsx(
                      "flex items-center gap-1 sm:gap-1.5 px-2 sm:px-3 py-1.5 rounded-lg border transition-all flex-shrink-0",
                      showCollapsedBreakdown 
                        ? "bg-lava-600/10 border-lava-600/30 text-lava-600" 
                        : "border-[var(--border-primary)] hover:border-lava-600/30 hover:bg-lava-600/5"
                    )}
                  >
                    <ListBulletIcon className="w-4 h-4" />
                    <span className="font-semibold">{lineItems.length}</span>
                    <span className="text-[var(--text-muted)] hidden sm:inline">workloads</span>
                    <ChevronUpIcon className={clsx("w-3 h-3 transition-transform", showCollapsedBreakdown ? "rotate-180" : "")} />
                  </button>
                  
                  <div className="h-4 w-px bg-[var(--border-primary)] hidden md:block" />
                  
                  {/* DBU Cost - blue label, responsive text */}
                  <div className="flex items-center gap-1 min-w-0">
                    <span className="text-blue-600 dark:text-blue-400 font-semibold text-xs sm:text-sm flex-shrink-0">DBU:</span>
                    <span className="font-bold text-[var(--text-primary)] text-xs sm:text-sm md:text-base truncate">{formatCurrency(totalCosts.totalDBUCost)}</span>
                  </div>
                  
                  {/* DSU Cost */}
                  <div className="flex items-center gap-1 min-w-0">
                    <span className="text-purple-600 dark:text-purple-400 font-semibold text-xs sm:text-sm flex-shrink-0">DSU:</span>
                    <span className="font-bold text-[var(--text-primary)] text-xs sm:text-sm md:text-base truncate">{formatCurrency(totalCosts.totalDSUCost)}</span>
                  </div>

                  {/* VM Cost */}
                  <div className="flex items-center gap-1 min-w-0">
                    <span className="text-teal-600 dark:text-teal-400 font-semibold text-xs sm:text-sm flex-shrink-0">VM:</span>
                    <span className="font-bold text-[var(--text-primary)] text-xs sm:text-sm md:text-base truncate">{formatCurrency(totalCosts.totalVMCost)}</span>
                  </div>

                  {totalCosts.totalPlatformAddonCost > 0 && (
                    <div className="flex items-center gap-1 min-w-0">
                      <span className="text-amber-600 dark:text-amber-400 font-semibold text-xs sm:text-sm flex-shrink-0">Add-on:</span>
                      <span className="font-bold text-[var(--text-primary)] text-xs sm:text-sm md:text-base truncate">{formatCurrency(totalCosts.totalPlatformAddonCost)}</span>
                    </div>
                  )}
                </div>
                
                {/* Right side - Total cost */}
                <div className="flex items-center">
                  <div className="text-right px-3 py-1.5 bg-gradient-to-r from-lava-600/10 to-amber-500/10 rounded-lg border border-lava-600/20">
                    <p className="text-lg sm:text-xl font-bold text-lava-600">
                      {formatCurrency(totalCosts.totalCost)}
                      <span className="text-[10px] font-normal text-[var(--text-muted)] ml-1">/mo</span>
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
      
      {/* Floating Bulk Delete Action Bar - Shows when items are selected */}
      {selectedItems.size > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 50 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 50 }}
          className="fixed bottom-6 inset-x-0 mx-auto w-fit z-40 bg-[var(--bg-primary)] border border-[var(--border-primary)] shadow-2xl rounded-full px-5 py-2.5 flex items-center gap-3"
        >
          <span className="text-sm font-medium text-[var(--text-primary)]">
            {selectedItems.size} workload{selectedItems.size !== 1 ? 's' : ''} selected
          </span>
          
          <div className="h-4 w-px bg-[var(--border-primary)]" />
          
          <button
            onClick={handleBulkDelete}
            className="flex items-center gap-1.5 bg-red-600 hover:bg-red-700 text-white text-sm font-medium px-3 py-1.5 rounded-full transition-colors"
          >
            <TrashIcon className="w-4 h-4" />
            Delete
          </button>
          <button
            onClick={exitBulkSelectMode}
            className="flex items-center gap-1.5 text-[var(--text-muted)] hover:text-[var(--text-primary)] text-sm px-2 py-1.5 rounded-full transition-colors"
          >
            <XMarkIcon className="w-4 h-4" />
            Cancel
          </button>
        </motion.div>
      )}
      
      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="bg-[var(--bg-primary)] rounded-xl shadow-xl border border-[var(--border-primary)] p-6 max-w-md w-full mx-4"
          >
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
                <TrashIcon className="w-5 h-5 text-red-600" />
              </div>
              <div>
                <h3 className="font-semibold text-[var(--text-primary)]">Delete Estimate</h3>
                <p className="text-sm text-[var(--text-muted)]">This action cannot be undone</p>
              </div>
            </div>
            
            <p className="text-sm text-[var(--text-secondary)] mb-6">
              Are you sure you want to delete <span className="font-semibold">"{formData.estimate_name || 'this estimate'}"</span>? 
              All {lineItems.length} workload{lineItems.length !== 1 ? 's' : ''} will also be deleted.
            </p>
            
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                disabled={isDeleting}
                className="btn btn-secondary"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteEstimate}
                disabled={isDeleting}
                className="btn bg-red-600 hover:bg-red-700 text-white"
              >
                {isDeleting ? (
                  <>
                    <ArrowPathIcon className="w-4 h-4 animate-spin" />
                    Deleting...
                  </>
                ) : (
                  <>
                    <TrashIcon className="w-4 h-4" />
                    Delete Estimate
                  </>
                )}
              </button>
            </div>
          </motion.div>
        </div>
      )}
      
      {/* Delete Workload Confirmation Modal */}
      {showWorkloadDeleteConfirm && workloadToDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="bg-[var(--bg-primary)] rounded-xl shadow-xl border border-[var(--border-primary)] p-6 max-w-md w-full mx-4"
          >
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
                <TrashIcon className="w-5 h-5 text-red-600" />
              </div>
              <div>
                <h3 className="font-semibold text-[var(--text-primary)]">Delete Workload</h3>
                <p className="text-sm text-[var(--text-muted)]">This action cannot be undone</p>
              </div>
            </div>
            
            <p className="text-sm text-[var(--text-secondary)] mb-6">
              Are you sure you want to delete <span className="font-semibold">"{workloadToDelete.workload_name}"</span>?
            </p>
            
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => {
                  setShowWorkloadDeleteConfirm(false)
                  setWorkloadToDelete(null)
                }}
                disabled={isDeletingWorkload}
                className="btn btn-secondary"
              >
                Cancel
              </button>
              <button
                onClick={confirmDeleteWorkload}
                disabled={isDeletingWorkload}
                className="btn bg-red-600 hover:bg-red-700 text-white"
              >
                {isDeletingWorkload ? (
                  <>
                    <ArrowPathIcon className="w-4 h-4 animate-spin" />
                    Deleting...
                  </>
                ) : (
                  <>
                    <TrashIcon className="w-4 h-4" />
                    Delete
                  </>
                )}
              </button>
            </div>
          </motion.div>
        </div>
      )}
      
      {/* Bulk Delete Workloads Confirmation Modal */}
      {showBulkDeleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="bg-[var(--bg-primary)] rounded-xl shadow-xl border border-[var(--border-primary)] p-6 max-w-md w-full mx-4"
          >
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
                <TrashIcon className="w-5 h-5 text-red-600" />
              </div>
              <div>
                <h3 className="font-semibold text-[var(--text-primary)]">Delete {selectedItems.size} Workload{selectedItems.size !== 1 ? 's' : ''}</h3>
                <p className="text-sm text-[var(--text-muted)]">This action cannot be undone</p>
              </div>
            </div>
            
            <div className="text-sm text-[var(--text-secondary)] mb-6">
              <p className="mb-2">The following workloads will be deleted:</p>
              <div className="max-h-32 overflow-y-auto bg-[var(--bg-tertiary)] rounded-lg p-2">
                {lineItems
                  .filter(item => selectedItems.has(item.line_item_id))
                  .map(item => (
                    <div key={item.line_item_id} className="text-xs py-0.5 text-[var(--text-muted)]">
                      • {item.workload_name}
                    </div>
                  ))}
              </div>
            </div>
            
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowBulkDeleteConfirm(false)}
                disabled={isDeletingWorkload}
                className="btn btn-secondary"
              >
                Cancel
              </button>
              <button
                onClick={confirmBulkDelete}
                disabled={isDeletingWorkload}
                className="btn bg-red-600 hover:bg-red-700 text-white"
              >
                {isDeletingWorkload ? (
                  <>
                    <ArrowPathIcon className="w-4 h-4 animate-spin" />
                    Deleting...
                  </>
                ) : (
                  <>
                    <TrashIcon className="w-4 h-4" />
                    Delete All
                  </>
                )}
              </button>
            </div>
          </motion.div>
        </div>
      )}
      
      {/* Unsaved Changes Confirmation Modal */}
      {showUnsavedChangesConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="bg-[var(--bg-primary)] rounded-xl shadow-xl border border-[var(--border-primary)] p-6 max-w-md w-full mx-4"
          >
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
                <ExclamationTriangleIcon className="w-5 h-5 text-amber-600" />
              </div>
              <div>
                <h3 className="font-semibold text-[var(--text-primary)]">Unsaved Changes</h3>
                <p className="text-sm text-[var(--text-muted)]">You have unsaved configuration changes</p>
              </div>
            </div>
            
            <p className="text-sm text-[var(--text-secondary)] mb-6">
              Are you sure you want to leave? Your unsaved changes will be lost.
            </p>
            
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowUnsavedChangesConfirm(false)}
                className="btn btn-secondary"
              >
                Stay
              </button>
              <button
                onClick={confirmLeaveWithoutSaving}
                className="btn bg-amber-600 hover:bg-amber-700 text-white"
              >
                Leave Anyway
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  )
}
