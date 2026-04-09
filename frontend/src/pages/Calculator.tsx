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
  Bars3Icon
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
import type { LineItem } from '../types'
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
  getAvailableRegionsFromBundle
} from '../utils/pricingBundle'

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
    label: 'VS'
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
  vmCost: number
  monthlyDBUs: number
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
    'SERVERLESS_REAL_TIME_INFERENCE': 0.07,  // Vector Search, Model Serving, FMAPI Databricks
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
    'SERVERLESS_REAL_TIME_INFERENCE': 0.07,  // Vector Search, Model Serving, FMAPI Databricks
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
    'SERVERLESS_REAL_TIME_INFERENCE': 0.07,  // Vector Search, Model Serving, FMAPI Databricks
    'DATABASE_SERVERLESS_COMPUTE': 0.48  // Lakebase
  }
}

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
  vmCost: number
  totalCost: number
  // Optional fields for specific workload types
  unitsUsed?: number  // Vector Search units
  dbuPerHour?: number // DBU per hour for display
  dbuPrice?: number   // $/DBU rate for display
  // Storage costs for Vector Search and Lakebase
  storageCost?: number
  storageDetails?: {
    totalStorageGB: number
    freeStorageGB?: number  // Vector Search only
    billableStorageGB: number
    pricePerGB?: number     // Vector Search
    dsuPerGB?: number       // Lakebase
    totalDSU?: number       // Lakebase
    pricePerDSU?: number    // Lakebase
  }
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
    // Vector Search modes for DBU rates
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
    tier: ''  // No default - must be selected
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
      // Skip serverless workloads (no VM costs)
      if (item.serverless_enabled) return
      
      // Handle DBSQL Classic/Pro warehouses - get instance types from warehouse config
      if (item.workload_type === 'DBSQL' && (item.dbsql_warehouse_type || '').toUpperCase() !== 'SERVERLESS') {
        const warehouseConfig = getBundleDBSQLWarehouseConfig(
          pricingBundle,
          formData.cloud,
          (item.dbsql_warehouse_type || 'PRO').toUpperCase(),
          item.dbsql_warehouse_size || 'Small'
        )
        
        if (warehouseConfig) {
          // Fetch driver instance type VM cost
          const driverTier = item.dbsql_driver_pricing_tier || item.driver_pricing_tier || 'on_demand'
          const driverPayment = item.dbsql_driver_payment_option || item.driver_payment_option || 'NA'
          fetchConfigs.add(`${warehouseConfig.driver_instance_type}:${driverTier}:${driverPayment}`)
          
          // Fetch worker instance type VM cost
          const workerTier = item.dbsql_worker_pricing_tier || item.worker_pricing_tier || 'on_demand'
          const workerPayment = item.dbsql_worker_payment_option || item.worker_payment_option || 'NA'
          fetchConfigs.add(`${warehouseConfig.worker_instance_type}:${workerTier}:${workerPayment}`)
        }
        return // Don't process driver_node_type/worker_node_type for DBSQL
      }
      
      // Driver pricing (for non-DBSQL workloads)
      if (item.driver_node_type) {
        const driverTier = item.driver_pricing_tier || 'on_demand'
        const driverPayment = item.driver_payment_option || 'NA'
        fetchConfigs.add(`${item.driver_node_type}:${driverTier}:${driverPayment}`)
      }
      
      // Worker pricing (for non-DBSQL workloads)
      if (item.worker_node_type) {
        const workerTier = item.worker_pricing_tier || 'spot'
        const workerPayment = item.worker_payment_option || 'NA'
        fetchConfigs.add(`${item.worker_node_type}:${workerTier}:${workerPayment}`)
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
  }, [formData.cloud, formData.region, lineItems, lineItemsLoaded, fetchVMCostForInstance, pricingBundle])
  
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
    tier: ''
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
        tier: (currentEstimate.tier || '').toLowerCase()
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
      return { monthlyDBUs: 0, dbuCost: 0, vmCost: 0, totalCost: 0 }
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
        // Vector Search uses SERVERLESS_REAL_TIME_INFERENCE pricing ($0.07/DBU)
        productType = 'SERVERLESS_REAL_TIME_INFERENCE'
        break
      
      case 'MODEL_SERVING':
        productType = 'SERVERLESS_REAL_TIME_INFERENCE'
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

      case 'SHUTTERSTOCK_IMAGEAI':
        productType = 'SERVERLESS_REAL_TIME_INFERENCE'
        break

      default:
        productType = 'JOBS_COMPUTE'
    }
    
    // Get DBU price for this product type
    // Try pricing bundle first (static data), then runtime dbuRatesMap, then hardcoded fallback
    let dbuPrice = 0.20
    if (isPricingBundleLoaded && formData.tier) {
      const bundlePrice = getBundleDBUPrice(pricingBundle, cloud, region, formData.tier, productType)
      if (bundlePrice > 0) {
        dbuPrice = bundlePrice
      } else {
        dbuPrice = pricing[productType] || 0.20
      }
    } else {
      dbuPrice = pricing[productType] || 0.20
    }
    
    // ========================================
    // Step 3: Calculate DBU per hour based on workload type
    // Uses fetched instanceTypes for accurate DBU rates
    // ========================================
    let dbuPerHour = 0
    let monthlyDBUs = 0
    let vmCost = 0
    let unitsUsed: number | undefined = undefined  // For Vector Search
    let storageCost: number | undefined = undefined  // For Vector Search and Lakebase
    let storageDetails: CostBreakdown['storageDetails'] = undefined
    
    // Get instance DBU rates - try pricing bundle first, then fetched instanceTypes
    let driverDBURate = 0.5 // Fallback
    let workerDBURate = 0.5
    
    if (isPricingBundleLoaded && effectiveItem.driver_node_type) {
      const bundleDriverRate = getBundleInstanceDBURate(pricingBundle, cloud, effectiveItem.driver_node_type)
      if (bundleDriverRate > 0) driverDBURate = bundleDriverRate
    }
    if (!driverDBURate || driverDBURate === 0.5) {
      const driverInstance = instanceTypes.find(it => it.id === effectiveItem.driver_node_type || it.name === effectiveItem.driver_node_type)
      if (driverInstance?.dbu_rate) driverDBURate = driverInstance.dbu_rate
    }
    
    if (isPricingBundleLoaded && effectiveItem.worker_node_type) {
      const bundleWorkerRate = getBundleInstanceDBURate(pricingBundle, cloud, effectiveItem.worker_node_type)
      if (bundleWorkerRate > 0) workerDBURate = bundleWorkerRate
    }
    if (!workerDBURate || workerDBURate === 0.5) {
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
        // Vector Search: Units = CEILING(vector_capacity / divisor)
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
        monthlyDBUs = dbuPerHour * hoursPerMonth
        
        // Storage calculation for Vector Search
        // Free Storage = units_used × 20 GB
        // Billable Storage = MAX(0, storage_gb - free_storage_gb)
        // Storage Cost = billable_storage_gb × price_per_gb_per_month ($0.023/GB/month)
        const vectorStorageGB = effectiveItem.vector_search_storage_gb || 0
        const vectorFreeStorageGB = vectorUnitsUsed * 20
        const vectorBillableStorageGB = Math.max(0, vectorStorageGB - vectorFreeStorageGB)
        const vectorStoragePricePerGB = 0.023  // $0.023 per GB per month
        const vectorStorageCost = vectorBillableStorageGB * vectorStoragePricePerGB

        if (vectorStorageGB > 0) {
          storageCost = vectorStorageCost
          storageDetails = {
            totalStorageGB: vectorStorageGB,
            freeStorageGB: vectorFreeStorageGB,
            billableStorageGB: vectorBillableStorageGB,
            pricePerGB: vectorStoragePricePerGB
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
        
        // Apply concurrency multiplier
        const msScaleOutCalc = effectiveItem.model_serving_scale_out || 'small'
        const msPresets: Record<string, number> = { small: 4, medium: 12, large: 40 }
        const msConcurrencyCalc = msScaleOutCalc === 'custom'
          ? (effectiveItem.model_serving_concurrency || 4)
          : (msPresets[msScaleOutCalc] || 4)

        // Total Cost = DBU/Hour × concurrency × hours_per_month × dbu_price
        dbuPerHour = gpuDBURate * msConcurrencyCalc
        monthlyDBUs = dbuPerHour * hoursPerMonth
        break

      case 'LAKEBASE':
        // LAKEBASE (Managed PostgreSQL)
        // Formula: DBU/Hour = cu_size × dbu_per_cu_hour × num_nodes
        // dbu_per_cu_hour varies by cloud/tier (0.230 for AWS Premium, 0.213 for Enterprise/Azure)
        const lakebaseCU = effectiveItem.lakebase_cu || 1
        const lakebaseNodes = effectiveItem.lakebase_ha_nodes || 1  // 1-3 nodes for HA
        const lakebaseDBURates: Record<string, Record<string, number>> = {
          'aws': { 'PREMIUM': 0.230, 'ENTERPRISE': 0.213 },
          'azure': { 'PREMIUM': 0.213, 'ENTERPRISE': 0.213 },
        }
        const lakebaseCloudRates = lakebaseDBURates[cloud] || lakebaseDBURates['aws']
        const lakebaseDBUPerCU = lakebaseCloudRates[(formData.tier || 'PREMIUM').toUpperCase()] || 0.213

        dbuPerHour = lakebaseCU * lakebaseDBUPerCU * lakebaseNodes
        monthlyDBUs = dbuPerHour * hoursPerMonth
        
        // Storage calculation for Lakebase (DSU-based pricing)
        // Storage: 15x DSU/GB, PITR: 8.7x DSU/GB, Snapshots: 3.91x DSU/GB
        // Cost = GB × DSU_multiplier × $/DSU ($0.023/DSU/month)
        const lakebaseStorageGB = Math.min(effectiveItem.lakebase_storage_gb || 0, 8192)
        const lakebasePitrGB = effectiveItem.lakebase_pitr_gb || 0
        const lakebaseSnapshotGB = effectiveItem.lakebase_snapshot_gb || 0
        const lakebasePricePerDSU = 0.023
        const lakebaseStorageCost = lakebaseStorageGB * 15 * lakebasePricePerDSU
        const lakebasePitrCost = lakebasePitrGB * 8.7 * lakebasePricePerDSU
        const lakebaseSnapshotCost = lakebaseSnapshotGB * 3.91 * lakebasePricePerDSU
        const lakebaseTotalStorageCost = lakebaseStorageCost + lakebasePitrCost + lakebaseSnapshotCost

        if (lakebaseTotalStorageCost > 0) {
          storageCost = lakebaseTotalStorageCost
          storageDetails = {
            totalStorageGB: lakebaseStorageGB,
            billableStorageGB: lakebaseStorageGB,
            dsuPerGB: 15,
            totalDSU: lakebaseStorageGB * 15,
            pricePerDSU: lakebasePricePerDSU
          }
        }
        break
      
      case 'FMAPI_DATABRICKS':
        // Foundation Models (Databricks) - llama, gpt-oss, gemma, bge, gte, etc.
        const fmapiDbxQuantity = effectiveItem.fmapi_quantity || 0
        const fmapiDbxRateType = effectiveItem.fmapi_rate_type || 'input_token'
        const fmapiDbxIsProvisioned = ['provisioned_scaling', 'provisioned_entry'].includes(fmapiDbxRateType)
        
        // Try pricing bundle first
        let dbxDbuRate: number | null = null
        
        if (isPricingBundleLoaded && effectiveItem.fmapi_model) {
          const bundleDbxRate = getBundleFMAPIDatabricksRate(pricingBundle, cloud, effectiveItem.fmapi_model, fmapiDbxRateType)
          if (bundleDbxRate) {
            dbxDbuRate = bundleDbxRate.dbu_rate
          }
        }
        
        // Fall back to store's cached rate
        if (dbxDbuRate === null && effectiveItem.fmapi_model) {
          const dbxRateData = getFMAPIDatabricksRate(effectiveItem.fmapi_model, fmapiDbxRateType)
          if (dbxRateData) {
            if (fmapiDbxIsProvisioned) {
              dbxDbuRate = dbxRateData.dbu_per_hour || null
            } else {
              dbxDbuRate = dbxRateData.dbu_per_1M_tokens || null
            }
          }
        }
        
        // Apply defaults if still no rate found
        if (dbxDbuRate === null) {
          if (fmapiDbxIsProvisioned) {
            dbxDbuRate = fmapiDbxRateType === 'provisioned_scaling' ? 200 : 50
          } else {
            dbxDbuRate = fmapiDbxRateType === 'output_token' ? 3.0 : 1.0
          }
        }
        
        monthlyDBUs = fmapiDbxQuantity * dbxDbuRate
        break
      
      case 'FMAPI_PROPRIETARY':
        // Foundation Models (Proprietary) - OpenAI, Anthropic, Google
        const fmapiPropQuantity = effectiveItem.fmapi_quantity || 0
        const fmapiPropRateType = effectiveItem.fmapi_rate_type || 'input_token'
        const fmapiPropIsProvisioned = fmapiPropRateType === 'provisioned_scaling'
        
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
        if (propDbuRate === null && effectiveItem.fmapi_provider && effectiveItem.fmapi_model) {
          const propRateData = getFMAPIProprietaryRate(effectiveItem.fmapi_provider, effectiveItem.fmapi_model, fmapiPropRateType)
          if (propRateData) {
            if (fmapiPropIsProvisioned) {
              propDbuRate = propRateData.dbu_per_hour || null
            } else {
              propDbuRate = propRateData.dbu_per_1M_tokens || null
            }
          }
        }
        
        // Apply defaults if still no rate found
        if (propDbuRate === null) {
          if (fmapiPropIsProvisioned) {
            propDbuRate = 150
          } else {
            switch (fmapiPropRateType) {
              case 'output_token': propDbuRate = 6.0; break
              case 'cache_read': propDbuRate = 0.5; break
              case 'cache_write': propDbuRate = 1.0; break
              default: propDbuRate = 2.0 // input_token
            }
          }
        }
        
        monthlyDBUs = fmapiPropQuantity * propDbuRate
        break

      case 'DATABRICKS_APPS': {
        const appsSize = (effectiveItem.databricks_apps_size || 'medium').toLowerCase()
        const appsDbuRates: Record<string, number> = { medium: 0.5, large: 1.0 }
        dbuPerHour = appsDbuRates[appsSize] || 0.5
        monthlyDBUs = dbuPerHour * hoursPerMonth
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
    const safeVmCost = isNaN(vmCost) || vmCost === undefined ? 0 : vmCost
    const safeStorageCost = storageCost !== undefined && !isNaN(storageCost) ? storageCost : 0
    
    const dbuCost = safeMonthlyDBUs * safeDbuPrice
    const totalCost = dbuCost + safeVmCost + safeStorageCost
    
    return { 
      monthlyDBUs: safeMonthlyDBUs, 
      dbuCost: isNaN(dbuCost) ? 0 : dbuCost, 
      vmCost: safeVmCost, 
      totalCost: isNaN(totalCost) ? 0 : totalCost,
      unitsUsed,  // For Vector Search
      dbuPerHour, // For display
      dbuPrice: safeDbuPrice,  // $/DBU rate for display
      storageCost: safeStorageCost > 0 ? safeStorageCost : undefined,
      storageDetails
    }
  }
  
  // Calculate total costs
  const totalCosts = useMemo(() => {
    let totalDBUs = 0
    let totalDBUCost = 0
    let totalVMCost = 0
    let totalCost = 0
    
    lineItems.forEach(item => {
      const costs = calculateItemCost(item)
      // Guard against NaN values propagating
      totalDBUs += isNaN(costs.monthlyDBUs) ? 0 : costs.monthlyDBUs
      totalDBUCost += isNaN(costs.dbuCost) ? 0 : costs.dbuCost
      totalVMCost += isNaN(costs.vmCost) ? 0 : costs.vmCost
      totalCost += isNaN(costs.totalCost) ? 0 : costs.totalCost
    })
    
    return { totalDBUs, totalDBUCost, totalVMCost, totalCost }
  }, [lineItems, formData.cloud, formData.region, formData.tier, workloadTypes, getVMPrice, vmPricingMap, getInstanceDbuRate, instanceDbuRateMap, instanceTypes, photonMultipliers, dbuRatesMap, dbsqlSizes, modelServingGPUTypes, vectorSearchModes, getVectorSearchRate, getFMAPIDatabricksRate, getFMAPIProprietaryRate, pricingBundle, isPricingBundleLoaded])
  
  // Sync local calculated costs to the store for AI Assistant
  useEffect(() => {
    const costs: Record<string, { total: number; dbu: number; vm: number; dbus: number }> = {}
    lineItems.forEach(item => {
      const itemCosts = calculateItemCost(item, pendingFormEdits[item.line_item_id])
      costs[item.line_item_id] = {
        total: isNaN(itemCosts.totalCost) ? 0 : itemCosts.totalCost,
        dbu: isNaN(itemCosts.dbuCost) ? 0 : itemCosts.dbuCost,
        vm: isNaN(itemCosts.vmCost) ? 0 : itemCosts.vmCost,
        dbus: isNaN(itemCosts.monthlyDBUs) ? 0 : itemCosts.monthlyDBUs
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
      const dataToSave = {
        ...formData,
        cloud: formData.cloud.toUpperCase(),
        tier: formData.tier.toUpperCase()
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
    if (['AI_PARSE', 'SHUTTERSTOCK_IMAGEAI', 'DATABRICKS_APPS'].includes(wt)) return null
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
            'provisioned_entry': 'Provisioned Entry'
          }
          details.push({ label: 'Rate', value: rateLabels[item.fmapi_rate_type] || item.fmapi_rate_type })
        }
        if (item.fmapi_quantity) {
          const isProvisioned = ['provisioned_scaling', 'provisioned_entry'].includes(item.fmapi_rate_type || '')
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
            'cache_write': 'Cache Write'
          }
          details.push({ label: 'Rate', value: rateLabels[item.fmapi_rate_type] || item.fmapi_rate_type })
        }
        if (item.fmapi_quantity) {
          details.push({ label: 'Quantity', value: `${item.fmapi_quantity}M tokens` })
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
                                    tier: (cloud.id === 'azure' && prev.tier === 'enterprise') ? '' : prev.tier
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
                            setFormData(prev => ({ ...prev, tier: e.target.value }))
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
                      const typeName = workloadTypes.find(w => w.workload_type === wType)?.display_name || wType
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
                          // Vector Search - mode as badge
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
                            const isProvisioned = ['provisioned_scaling', 'provisioned_entry'].includes(effectiveItem.fmapi_rate_type)
                            config.badges.push({ text: isProvisioned ? 'Provisioned' : 'Token' })
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
                                isLoading={(() => {
                                  const needsVMCosts = !effectiveItem.serverless_enabled && 
                                    ['JOBS', 'ALL_PURPOSE', 'DLT'].includes(wType) ||
                                    (wType === 'DBSQL' && (effectiveItem.dbsql_warehouse_type || '').toUpperCase() !== 'SERVERLESS')
                                  return isLoadingVMCosts && needsVMCosts && costs.vmCost === 0
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
                                {/* Hide VM Cost for serverless workloads */}
                                {!['VECTOR_SEARCH', 'MODEL_SERVING', 'FMAPI_DATABRICKS', 'FMAPI_PROPRIETARY', 'LAKEBASE'].includes(wType) && (
                                  <div>
                                    <span className="text-[var(--text-muted)]">VM Cost</span>
                                    <p className="font-semibold text-[var(--text-primary)]">{formatCurrency(costs.vmCost)}</p>
                                  </div>
                                )}
                                
                                {/* Lakebase: Storage Cost */}
                                {wType === 'LAKEBASE' && costs.storageCost !== undefined && costs.storageCost > 0 && (
                                  <div>
                                    <span className="text-[var(--text-muted)]">Storage Cost</span>
                                    <p className="font-semibold text-purple-600 dark:text-purple-400">{formatCurrency(costs.storageCost)}</p>
                                  </div>
                                )}
                                
                                {/* Vector Search: Units Used */}
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
                                  const dbuPriceDisplay = dbuPrice.toFixed(2)
                                  
                                    // Vector Search formula (with storage)
                                    if (wType === 'VECTOR_SEARCH') {
                                      const capacity = effectiveItem.vector_capacity_millions || 1
                                      const mode = effectiveItem.vector_search_mode || 'standard'
                                      const divisor = mode === 'storage_optimized' ? 64 : 2
                                      const unitsUsed = Math.ceil(capacity / divisor)
                                      const dbuPerUnit = mode === 'storage_optimized' ? 18.29 : 4
                                      const vsStorageGB = effectiveItem.vector_search_storage_gb || 0
                                      const vsFreeStorageGB = unitsUsed * 20
                                      const vsBillableStorageGB = Math.max(0, vsStorageGB - vsFreeStorageGB)
                                      const vsStorageCost = vsBillableStorageGB * 0.023
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
                                            <span className="text-blue-600 font-semibold">DBU:</span>
                                            <span>⌈<span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{capacity}M</span> vectors ÷ {divisor}M⌉</span>
                                            <span>=</span>
                                            <span className="font-semibold">{unitsUsed} unit{unitsUsed !== 1 ? 's' : ''}</span>
                                            <span>×</span>
                                            <span>{dbuPerUnit.toFixed(2)} DBU/hr/unit</span>
                                            <span>×</span>
                                            <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{hoursPerMonth.toFixed(isRunBased ? 1 : 0)}h</span>
                                            <span>=</span>
                                            <span>{formatNumber(costs.monthlyDBUs)} DBUs</span>
                                            <span>×</span>
                                            <span>${dbuPriceDisplay}/DBU</span>
                                            <span>=</span>
                                            <span className="text-blue-500 font-semibold">{formatCurrency(costs.dbuCost)}</span>
                                          </div>
                                          {vsStorageGB > 0 && (
                                            <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
                                              <span className="text-purple-600 font-semibold">Storage:</span>
                                              <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{vsStorageGB} GB</span>
                                              <span>−</span>
                                              <span>{vsFreeStorageGB} GB free</span>
                                              <span className="text-[var(--text-muted)]">({unitsUsed} units × 20GB)</span>
                                              <span>=</span>
                                              <span className="font-semibold">{vsBillableStorageGB} GB</span>
                                              <span>×</span>
                                              <span>$0.023/GB</span>
                                              <span>=</span>
                                              <span className="text-purple-500 font-semibold">{formatCurrency(vsStorageCost)}</span>
                                            </div>
                                          )}
                                          <div className="flex items-center gap-1 text-[10px] font-mono flex-wrap pt-1 border-t border-dashed border-[var(--border-primary)]">
                                            <span className="text-[var(--text-secondary)] font-semibold">Total:</span>
                                            <span className="text-blue-500">{formatCurrency(costs.dbuCost)}</span>
                                            {vsStorageGB > 0 && (
                                              <>
                                                <span>+</span>
                                                <span className="text-purple-500">{formatCurrency(vsStorageCost)}</span>
                                              </>
                                            )}
                                            <span>=</span>
                                            <span className="text-[var(--text-primary)] font-medium">{formatCurrency(costs.totalCost)}</span>
                                          </div>
                                        </div>
                                      )
                                    }
                                  
                                  // FMAPI formula
                                  if (wType === 'FMAPI_DATABRICKS' || wType === 'FMAPI_PROPRIETARY') {
                                    const quantity = effectiveItem.fmapi_quantity || 1
                                    const rateType = effectiveItem.fmapi_rate_type || 'input_token'
                                    const isProvisioned = ['provisioned_scaling', 'provisioned_entry'].includes(rateType)
                                    const dbuPerUnit = quantity > 0 ? costs.monthlyDBUs / quantity : 0
                                    const model = effectiveItem.fmapi_model || 'model'
                                    const provider = effectiveItem.fmapi_provider || ''
                                    
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
                                    const cu = effectiveItem.lakebase_cu || 1
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
                                    const pricePerDSU = 0.023
                                    const localStorageCost = storageGB * 15 * pricePerDSU
                                    const localPitrCost = pitrGB * 8.7 * pricePerDSU
                                    const localSnapshotCost = snapshotGB * 3.91 * pricePerDSU
                                    const localTotalStorageCost = localStorageCost + localPitrCost + localSnapshotCost
                                    const hasStorageCosts = localTotalStorageCost > 0
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
                                          <span className="text-blue-600 font-semibold">DBU:</span>
                                          <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{cu} CU</span>
                                          <span>×</span>
                                          <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{lbDBUPerCU} DBU/CU-hr</span>
                                          <span>×</span>
                                          <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{haNodes} nodes</span>
                                          <span>×</span>
                                          <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{hoursPerMonth.toFixed(isRunBased ? 1 : 0)}h</span>
                                          <span>=</span>
                                          <span>{formatNumber(costs.monthlyDBUs)} DBUs</span>
                                          <span>×</span>
                                          <span>${dbuPriceDisplay}/DBU</span>
                                          <span>=</span>
                                          <span className="text-blue-500 font-semibold">{formatCurrency(costs.dbuCost)}</span>
                                        </div>
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
                                  
                                  // Model Serving formula
                                  if (wType === 'MODEL_SERVING') {
                                    const gpuType = effectiveItem.model_serving_gpu_type || 'cpu'
                                    const msScaleOutDisp = effectiveItem.model_serving_scale_out || 'small'
                                    const msPresetsDisp: Record<string, number> = { small: 4, medium: 12, large: 40 }
                                    const msConcurrencyDisp = msScaleOutDisp === 'custom'
                                      ? (effectiveItem.model_serving_concurrency || 4)
                                      : (msPresetsDisp[msScaleOutDisp] || 4)
                                    const gpuBaseRate = msConcurrencyDisp > 0 && costs.dbuPerHour
                                      ? costs.dbuPerHour / msConcurrencyDisp : 2
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
                                        <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
                                          <span className="text-blue-600 font-semibold">DBU:</span>
                                          <span>{gpuBaseRate.toFixed(2)} DBU/hr</span>
                                          <span className="text-[var(--text-muted)]">({gpuType})</span>
                                          <span>×</span>
                                          <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{msConcurrencyDisp} concurrency</span>
                                          <span className="text-[var(--text-muted)]">({msScaleOutDisp})</span>
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
                                        
                                        {/* VM Cost Line (only for PRO/Classic) */}
                                        {hasVMCost && (
                                          <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
                                            <span className="text-teal-600 font-semibold">VM:</span>
                                            <span>{warehouseType} warehouse VM costs</span>
                                            <span>×</span>
                                            <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{hoursPerMonth.toFixed(isRunBased ? 1 : 0)}h</span>
                                            <span>=</span>
                                            <span className="text-teal-600 font-semibold">{formatCurrency(costs.vmCost)}</span>
                                          </div>
                                        )}
                                        
                                        {/* Total Line */}
                                        <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap pt-1 border-t border-dashed border-[var(--border-primary)]">
                                          <span className="font-semibold">Total:</span>
                                          <span className="text-blue-600">{formatCurrency(costs.dbuCost)}</span>
                                          {hasVMCost && (
                                            <>
                                              <span>+</span>
                                              <span className="text-teal-600">{formatCurrency(costs.vmCost)}</span>
                                            </>
                                          )}
                                          <span>=</span>
                                          <span className="font-semibold">{formatCurrency(costs.totalCost)}</span>
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
                                  const driverDBURate = getInstanceDbuRate(cloud, driverNode) || driverInstance?.dbu_rate || 0
                                  const workerDBURate = getInstanceDbuRate(cloud, workerNode) || workerInstance?.dbu_rate || 0

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
                                          <>
                                            <span>{dbuPerHour.toFixed(2)} DBU/hr</span>
                                            <span className="text-[var(--text-muted)] text-[9px]">(Serverless{photonEnabled ? ' + Photon' : ''})</span>
                                          </>
                                        ) : (
                                          <>
                                            <span>(</span>
                                            <span title={driverNode}>{driverDBURate.toFixed(2)}</span>
                                            <span>+</span>
                                            <span title={workerNode}>{workerDBURate.toFixed(2)}</span>
                                            <span>×</span>
                                            <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{numWorkers}</span>
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
                                        <span>=</span>
                                        <span className="text-blue-600 font-semibold">{formatCurrency(costs.dbuCost)}</span>
                                      </div>
                                      
                                      {/* VM Cost Line (only for classic compute) */}
                                      {hasVMCost && (
                                        <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
                                          <span className="text-teal-600 font-semibold">VM:</span>
                                          <span>(</span>
                                          <span title={driverNode}>${driverVMCost?.toFixed(4) || '0'}</span>
                                          <span>+</span>
                                          <span title={workerNode}>${workerVMCost?.toFixed(4) || '0'}</span>
                                          <span>×</span>
                                          <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{numWorkers}</span>
                                          <span>)</span>
                                          <span>×</span>
                                          <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{hoursPerMonth.toFixed(isRunBased ? 1 : 0)}h</span>
                                          <span>=</span>
                                          <span className="text-teal-600 font-semibold">{formatCurrency(costs.vmCost)}</span>
                                        </div>
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
                              <span>{workloadTypes.find(w => w.workload_type === item.workload_type)?.display_name || item.workload_type}</span>
                            </div>
                          </div>
                          
                          {/* Cost - Using shared component */}
                          <WorkloadCostDisplay 
                            costs={costs}
                            size={workloadsViewMode === 'cards' && !isExpanded ? 'md' : 'lg'}
                            isLoading={(() => {
                              const wType = item.workload_type || ''
                              const needsVMCosts = !item.serverless_enabled && 
                                ['JOBS', 'ALL_PURPOSE', 'DLT'].includes(wType) ||
                                (wType === 'DBSQL' && (item.dbsql_warehouse_type || '').toUpperCase() !== 'SERVERLESS')
                              return isLoadingVMCosts && needsVMCosts && costs.vmCost === 0
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
                              {/* Hide VM Cost for serverless workloads */}
                              {!['VECTOR_SEARCH', 'MODEL_SERVING', 'FMAPI_DATABRICKS', 'FMAPI_PROPRIETARY', 'LAKEBASE'].includes(item.workload_type || '') && (
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
                              
                              {/* Vector Search: Units Used (prominent) */}
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
                                const dbuPriceDisplay = dbuPrice.toFixed(2)
                                
                                // Special workloads
                                // Vector Search formula (with storage)
                                if (wType === 'VECTOR_SEARCH') {
                                  const capacity = effectiveItem.vector_capacity_millions || 1
                                  const mode = effectiveItem.vector_search_mode || 'standard'
                                  const divisor = mode === 'storage_optimized' ? 64 : 2
                                  const unitsUsed = Math.ceil(capacity / divisor)
                                  const dbuPerUnit = mode === 'storage_optimized' ? 18.29 : 4
                                  const vsStorageGB = effectiveItem.vector_search_storage_gb || 0
                                  const vsFreeStorageGB = unitsUsed * 20
                                  const vsBillableStorageGB = Math.max(0, vsStorageGB - vsFreeStorageGB)
                                  const vsStorageCost = vsBillableStorageGB * 0.023
                                  return (
                                    <div className="space-y-1">
                                      <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
                                        <span className="text-blue-600 font-semibold">DBU:</span>
                                        <span>⌈<span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{capacity}M vectors</span> ÷ {divisor}⌉</span>
                                        <span>= {unitsUsed} units ×</span>
                                        <span>{dbuPerUnit} DBU/unit/hr ×</span>
                                        <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{hoursPerMonth.toFixed(0)}h</span>
                                        <span>=</span>
                                        <span>{formatNumber(costs.monthlyDBUs)} DBUs × ${dbuPriceDisplay}</span>
                                        <span>=</span>
                                        <span className="text-blue-500 font-semibold">{formatCurrency(costs.dbuCost)}</span>
                                      </div>
                                      {vsStorageGB > 0 && (
                                        <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
                                          <span className="text-purple-600 font-semibold">Storage:</span>
                                          <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{vsStorageGB} GB</span>
                                          <span>−</span>
                                          <span>{vsFreeStorageGB} GB free</span>
                                          <span className="text-[var(--text-muted)]">({unitsUsed} units × 20GB)</span>
                                          <span>=</span>
                                          <span className="font-semibold">{vsBillableStorageGB} GB</span>
                                          <span>×</span>
                                          <span>$0.023/GB</span>
                                          <span>=</span>
                                          <span className="text-purple-500 font-semibold">{formatCurrency(vsStorageCost)}</span>
                                        </div>
                                      )}
                                      <div className="flex items-center gap-1 text-[10px] font-mono flex-wrap pt-1 border-t border-dashed border-[var(--border-primary)]">
                                        <span className="text-[var(--text-secondary)] font-semibold">Total:</span>
                                        <span className="text-blue-500">{formatCurrency(costs.dbuCost)}</span>
                                        {vsStorageGB > 0 && (
                                          <>
                                            <span>+</span>
                                            <span className="text-purple-500">{formatCurrency(vsStorageCost)}</span>
                                          </>
                                        )}
                                        <span>=</span>
                                        <span className="text-[var(--text-primary)] font-medium">{formatCurrency(costs.totalCost)}</span>
                                      </div>
                                    </div>
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
                                
                                if (wType === 'LAKEBASE') {
                                  const cu = effectiveItem.lakebase_cu || 1
                                  const nodes = effectiveItem.lakebase_ha_nodes || 1
                                  const storageGB = effectiveItem.lakebase_storage_gb || 0
                                  const pitrGB = effectiveItem.lakebase_pitr_gb || 0
                                  const snapshotGB = effectiveItem.lakebase_snapshot_gb || 0
                                  const pricePerDSU = 0.023
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
                                  return (
                                    <div className="space-y-1">
                                      <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
                                        <span className="text-blue-600 font-semibold">DBU:</span>
                                        <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{cu} CU</span>
                                        <span>×</span>
                                        <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{lbDBUPerCUCard} DBU/CU-hr</span>
                                        <span>×</span>
                                        <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{nodes} nodes</span>
                                        <span>×</span>
                                        <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{hoursPerMonth.toFixed(0)}h</span>
                                        <span>=</span>
                                        <span>{formatNumber(costs.monthlyDBUs)} DBUs</span>
                                        <span>×</span>
                                        <span>${dbuPriceDisplay}/DBU</span>
                                        <span>=</span>
                                        <span className="text-blue-500 font-semibold">{formatCurrency(costs.dbuCost)}</span>
                                      </div>
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
                                  const msScaleOutCard = effectiveItem.model_serving_scale_out || 'small'
                                  const msPresetsCard: Record<string, number> = { small: 4, medium: 12, large: 40 }
                                  const msConcurrencyCard = msScaleOutCard === 'custom'
                                    ? (effectiveItem.model_serving_concurrency || 4)
                                    : (msPresetsCard[msScaleOutCard] || 4)
                                  const gpuBaseRateCard = msConcurrencyCard > 0 && costs.dbuPerHour
                                    ? costs.dbuPerHour / msConcurrencyCard : 2
                                  return (
                                    <div className="space-y-1">
                                      <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
                                        <span className="text-blue-600 font-semibold">DBU:</span>
                                        <span>{gpuBaseRateCard.toFixed(2)} DBU/hr</span>
                                        <span>×</span>
                                        <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{msConcurrencyCard} concurrency</span>
                                        <span className="text-[var(--text-muted)]">({msScaleOutCard})</span>
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

                                const driverDBURate = getInstanceDbuRate(cloud, driverNode) || driverInstance?.dbu_rate || 0
                                const workerDBURate = getInstanceDbuRate(cloud, workerNode) || workerInstance?.dbu_rate || 0

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
                                        <>
                                          <span>{dbuPerHour.toFixed(2)} DBU/hr</span>
                                          <span className="text-[var(--text-muted)] text-[9px]">(Serverless{photonEnabled ? ' + Photon' : ''})</span>
                                        </>
                                      ) : (
                                        <>
                                          <span>(</span>
                                          <span title={driverNode}>{driverDBURate.toFixed(2)}</span>
                                          <span>+</span>
                                          <span title={workerNode}>{workerDBURate.toFixed(2)}</span>
                                          <span>×</span>
                                          <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{numWorkers}</span>
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
                                      <span>=</span>
                                      <span className="text-blue-600 font-semibold">{formatCurrency(costs.dbuCost)}</span>
                                    </div>
                                    
                                    {/* VM Cost Line (only for classic compute) */}
                                    {hasVMCost && (
                                      <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] flex-wrap">
                                        <span className="text-teal-600 font-semibold">VM:</span>
                                        <span>(</span>
                                        <span title={driverNode}>${driverVMCost?.toFixed(4) || '0'}</span>
                                        <span>+</span>
                                        <span title={workerNode}>${workerVMCost?.toFixed(4) || '0'}</span>
                                        <span>×</span>
                                        <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{numWorkers}</span>
                                        <span>)</span>
                                        <span>×</span>
                                        <span className="font-medium bg-amber-50 dark:bg-amber-900/20 px-0.5 rounded">{hoursPerMonth.toFixed(isRunBased ? 1 : 0)}h</span>
                                        <span>=</span>
                                        <span className="text-teal-600 font-semibold">{formatCurrency(costs.vmCost)}</span>
                                      </div>
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
                  
                  {/* Cost Breakdown Grid - DBU + VM only */}
                  <div className="grid grid-cols-2 gap-2">
                    <div className="text-center p-2 sm:p-3 rounded-xl bg-gradient-to-br from-blue-500/5 to-blue-500/10 border border-blue-500/20 min-w-0">
                      <p className="text-[10px] text-blue-600 dark:text-blue-400 uppercase tracking-wider font-medium mb-1">DBU Cost</p>
                      <p className="text-xs font-bold text-[var(--text-primary)] tabular-nums truncate" title={formatCurrency(totalCosts.totalDBUCost)}>{formatCurrencyCompact(totalCosts.totalDBUCost)}</p>
                    </div>
                    <div className="text-center p-2 sm:p-3 rounded-xl bg-gradient-to-br from-purple-500/5 to-purple-500/10 border border-purple-500/20 min-w-0">
                      <p className="text-[10px] text-purple-600 dark:text-purple-400 uppercase tracking-wider font-medium mb-1">VM Cost</p>
                      <p className="text-xs font-bold text-[var(--text-primary)] tabular-nums truncate" title={isLoadingVMCosts ? 'Loading...' : formatCurrency(totalCosts.totalVMCost)}>{isLoadingVMCosts ? '...' : formatCurrencyCompact(totalCosts.totalVMCost)}</p>
                    </div>
                  </div>
                  
                  {/* Workload Breakdown - Click to navigate */}
                  <div className="pt-3 border-t border-[var(--border-primary)]">
                    <p className="text-xs font-medium text-[var(--text-muted)] mb-3 flex items-center justify-between">
                      <span>Workloads ({lineItems.length})</span>
                      <span className="text-[10px] italic">Click to view</span>
                    </p>
                    <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
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
                  
                  {/* VM Cost - purple label, responsive text */}
                  <div className="flex items-center gap-1 min-w-0">
                    <span className="text-purple-600 dark:text-purple-400 font-semibold text-xs sm:text-sm flex-shrink-0">VM:</span>
                    <span className="font-bold text-[var(--text-primary)] text-xs sm:text-sm md:text-base truncate">{formatCurrency(totalCosts.totalVMCost)}</span>
                  </div>
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
