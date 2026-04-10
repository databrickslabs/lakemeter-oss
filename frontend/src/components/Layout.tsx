import { Link, Outlet, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Squares2X2Icon, 
  PlusCircleIcon,
  SunIcon,
  MoonIcon,
  ComputerDesktopIcon,
  ChevronDownIcon,
  UserCircleIcon,
  ExclamationTriangleIcon,
  ArrowPathIcon,
  QuestionMarkCircleIcon,
  DocumentTextIcon,
  CurrencyDollarIcon,
} from '@heroicons/react/24/outline'
import clsx from 'clsx'
import { useState, useRef, useEffect, useCallback } from 'react'
import { useTheme, Theme } from '../hooks/useTheme'
import { useStore } from '../store/useStore'
import { ChatPanel } from './ChatPanel'
import toast from 'react-hot-toast'
import { SESSION_EXPIRED_EVENT, resetSessionExpiredFlag } from '../api/client'

// Sparkles Icon for AI Assistant
function SparklesIcon({ className }: { className?: string }) {
  return (
    <svg 
      xmlns="http://www.w3.org/2000/svg" 
      fill="none" 
      viewBox="0 0 24 24" 
      strokeWidth={1.5} 
      stroke="currentColor" 
      className={className}
    >
      <path 
        strokeLinecap="round" 
        strokeLinejoin="round" 
        d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z" 
      />
    </svg>
  )
}

const navigation = [
  { name: 'Estimates', href: '/', icon: Squares2X2Icon },
  { name: 'New Estimate', href: '/calculator', icon: PlusCircleIcon },
]

// Lakemeter logo - White icon on Databricks Lava background
const LakemeterLogo = () => (
  <svg viewBox="0 0 24 24" fill="none" className="w-7 h-7">
    {/* Databricks Lava 600 background */}
    <rect x="0" y="0" width="24" height="24" rx="5" fill="#FF3621" />
    {/* Roof line */}
    <path d="M5 9l7-4 7 4" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    {/* Gauge arc */}
    <path d="M7 15a5 5 0 0 1 10 0" stroke="white" strokeWidth="2" strokeLinecap="round" />
    {/* Needle */}
    <path d="M12 15l2-3" stroke="white" strokeWidth="2" strokeLinecap="round" />
    {/* Center dot */}
    <circle cx="12" cy="15" r="1.3" fill="white" />
    {/* Wave */}
    <path d="M5 20q3.5-1.5 7 0t7 0" stroke="white" strokeWidth="1.5" strokeLinecap="round" opacity="0.9" />
  </svg>
)

const themeOptions: { value: Theme; label: string; icon: typeof SunIcon }[] = [
  { value: 'light', label: 'Light', icon: SunIcon },
  { value: 'dark', label: 'Dark', icon: MoonIcon },
  { value: 'system', label: 'System', icon: ComputerDesktopIcon },
]

// LocalStorage keys for first-time user experience
const STORAGE_KEYS = {
  AI_ASSISTANT_OPENED: 'lakemeter_ai_assistant_opened',
  HELP_ICON_CLICKED: 'lakemeter_help_icon_clicked'
}

export default function Layout() {
  const location = useLocation()
  const { theme, setTheme } = useTheme()
  const [isOpen, setIsOpen] = useState(false)
  const [isHelpOpen, setIsHelpOpen] = useState(false)
  const [isChatOpen, setIsChatOpen] = useState(false)
  const [chatPanelWidth, setChatPanelWidth] = useState(380)
  const [showSessionExpired, setShowSessionExpired] = useState(false)
  const [sessionExpiredMessage, setSessionExpiredMessage] = useState('')
  const [hasUsedAIAssistant, setHasUsedAIAssistant] = useState(() => {
    return localStorage.getItem(STORAGE_KEYS.AI_ASSISTANT_OPENED) === 'true'
  })
  const [hasClickedHelp, setHasClickedHelp] = useState(() => {
    return localStorage.getItem(STORAGE_KEYS.HELP_ICON_CLICKED) === 'true'
  })
  const dropdownRef = useRef<HTMLDivElement>(null)
  const helpDropdownRef = useRef<HTMLDivElement>(null)
  
  const { 
    currentUser, 
    isAuthenticated, 
    authError, 
    fetchCurrentUser,
    currentEstimate,
    lineItems,
    localCalculatedCosts,
    createLineItem,
    calculateAllWorkloadCosts,
    setSessionExpired,
    // Reference data loading (moved to app startup for faster page loads)
    fetchReferenceData,
    loadPricingBundle,
    isReferenceDataLoaded,
    isPricingBundleLoaded
  } = useStore()
  
  // Determine page type for AI assistant mode
  const isEstimateDetailPage = location.pathname.startsWith('/calculator/') && location.pathname !== '/calculator'
  const isHomePage = location.pathname === '/'
  const showAIAssistant = isEstimateDetailPage || isHomePage
  
  // Handle page refresh
  const handleRefreshPage = useCallback(() => {
    resetSessionExpiredFlag()
    setSessionExpired(false)
    setShowSessionExpired(false)
    window.location.reload()
  }, [setSessionExpired])
  
  // Listen for session expiration events
  useEffect(() => {
    const handleSessionExpired = (event: CustomEvent) => {
      console.log('Session expired event received:', event.detail)
      setSessionExpiredMessage(event.detail?.message || 'Your session has expired')
      setShowSessionExpired(true)
      setSessionExpired(true)
    }
    
    window.addEventListener(SESSION_EXPIRED_EVENT, handleSessionExpired as EventListener)
    return () => {
      window.removeEventListener(SESSION_EXPIRED_EVENT, handleSessionExpired as EventListener)
    }
  }, [setSessionExpired])
  
  // Smart first-time AI Assistant: Open by default for first-time users
  useEffect(() => {
    if (showAIAssistant && !hasUsedAIAssistant) {
      // First time seeing AI assistant - open it
      setIsChatOpen(true)
    }
  }, [showAIAssistant, hasUsedAIAssistant])
  
  // Track when user interacts with AI assistant
  const handleToggleChat = useCallback(() => {
    const newState = !isChatOpen
    setIsChatOpen(newState)
    
    // Mark as "used" once they've interacted (opened or closed)
    if (!hasUsedAIAssistant) {
      localStorage.setItem(STORAGE_KEYS.AI_ASSISTANT_OPENED, 'true')
      setHasUsedAIAssistant(true)
    }
  }, [isChatOpen, hasUsedAIAssistant])
  
  // Track when user clicks help icon
  const handleOpenHelp = useCallback(() => {
    setIsHelpOpen(!isHelpOpen)
    
    if (!hasClickedHelp) {
      localStorage.setItem(STORAGE_KEYS.HELP_ICON_CLICKED, 'true')
      setHasClickedHelp(true)
    }
  }, [isHelpOpen, hasClickedHelp])
  
  // Close chat when navigating away from pages with AI assistant
  useEffect(() => {
    if (!showAIAssistant && isChatOpen) {
      setIsChatOpen(false)
    }
  }, [showAIAssistant, isChatOpen])
  
  // Fetch current user on mount
  useEffect(() => {
    fetchCurrentUser()
  }, [fetchCurrentUser])
  
  // Pre-load reference data and pricing bundle at app startup
  // This speeds up Calculator page load significantly
  useEffect(() => {
    // Start loading in parallel (non-blocking)
    if (!isReferenceDataLoaded) {
      fetchReferenceData()
    }
    if (!isPricingBundleLoaded) {
      loadPricingBundle()
    }
  }, [fetchReferenceData, loadPricingBundle, isReferenceDataLoaded, isPricingBundleLoaded])
  
  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
      if (helpDropdownRef.current && !helpDropdownRef.current.contains(event.target as Node)) {
        setIsHelpOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])
  
  const currentTheme = themeOptions.find(t => t.value === theme) || themeOptions[2]
  const CurrentIcon = currentTheme.icon
  
  // Show auth error screen if not authenticated
  if (authError) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center p-8" style={{ backgroundColor: 'var(--bg-primary)' }}>
        <div 
          className="max-w-md w-full p-8 rounded-xl border text-center"
          style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-primary)' }}
        >
          <div className="w-16 h-16 mx-auto mb-6 rounded-full flex items-center justify-center bg-lava-600/10">
            <LakemeterLogo />
          </div>
          <h1 className="text-2xl font-bold mb-2" style={{ color: 'var(--text-primary)' }}>
            Authentication Required
          </h1>
          <p className="mb-6" style={{ color: 'var(--text-secondary)' }}>
            {authError}
          </p>
          <div 
            className="p-4 rounded-lg text-sm text-left"
            style={{ backgroundColor: 'var(--bg-tertiary)', color: 'var(--text-muted)' }}
          >
            <p className="font-medium mb-2" style={{ color: 'var(--text-primary)' }}>For local development:</p>
            <p className="mb-2">Set the <code className="px-1.5 py-0.5 rounded bg-black/20">LOCAL_DEV_EMAIL</code> environment variable:</p>
            <code className="block p-2 rounded bg-black/30 text-lava-500 text-xs">
              LOCAL_DEV_EMAIL=your.email@databricks.com
            </code>
          </div>
        </div>
      </div>
    )
  }
  
  return (
    <div className="min-h-screen flex flex-col transition-colors duration-200" style={{ backgroundColor: 'var(--bg-primary)' }}>
      {/* Top Navigation */}
      <header 
        className="sticky top-0 z-50 backdrop-blur-xl border-b transition-colors"
        style={{ 
          backgroundColor: 'var(--bg-secondary)', 
          borderColor: 'var(--border-primary)' 
        }}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-14">
            {/* Logo */}
            <Link to="/" className="flex items-center gap-3 group">
              <div 
                className="w-10 h-10 rounded-lg flex items-center justify-center border group-hover:border-lava-600/50 transition-colors"
                style={{ backgroundColor: 'var(--bg-tertiary)', borderColor: 'var(--border-primary)' }}
              >
                <LakemeterLogo />
              </div>
              <div>
                <span className="text-xl font-semibold" style={{ color: 'var(--text-primary)' }}>
                  Lakemeter
                </span>
                <span className="hidden sm:inline text-xs ml-2 uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
                  Pricing Calculator
                </span>
              </div>
            </Link>
            
            {/* Navigation */}
            <div className="flex items-center gap-3">
              <nav className="flex items-center gap-1">
                {navigation.map((item) => {
                  const isActive = location.pathname === item.href || 
                    (item.href !== '/' && location.pathname.startsWith(item.href))
                  
                  return (
                    <Link
                      key={item.name}
                      to={item.href}
                      className={clsx(
                        'flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-200',
                        isActive && 'border'
                      )}
                      style={isActive ? {
                        backgroundColor: 'rgba(255, 54, 33, 0.1)',
                        color: 'var(--databricks-red)',
                        borderColor: 'rgba(255, 54, 33, 0.2)'
                      } : {
                        color: 'var(--text-secondary)'
                      }}
                    >
                      <item.icon className="w-4 h-4" />
                      <span className="hidden sm:inline">{item.name}</span>
                    </Link>
                  )
                })}
              </nav>
              
              {/* User Info */}
              {isAuthenticated && currentUser && (
                <div 
                  className="flex items-center gap-2 px-3 py-1.5 rounded-lg border"
                  style={{ 
                    backgroundColor: 'var(--bg-tertiary)', 
                    borderColor: 'var(--border-primary)',
                    color: 'var(--text-secondary)'
                  }}
                >
                  <UserCircleIcon className="w-4 h-4" />
                  <span className="text-sm hidden md:inline max-w-[150px] truncate" title={currentUser.full_name || currentUser.email}>
                    {currentUser.full_name || currentUser.email.split('@')[0]}
                  </span>
                </div>
              )}
              
              {/* Theme Dropdown */}
              <div className="relative" ref={dropdownRef}>
                <button
                  onClick={() => setIsOpen(!isOpen)}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg transition-colors border border-transparent hover:border-current"
                  style={{ color: 'var(--text-secondary)' }}
                >
                  <CurrentIcon className="w-4 h-4" />
                  <span className="text-sm hidden sm:inline">{currentTheme.label}</span>
                  <ChevronDownIcon className={clsx('w-3 h-3 transition-transform', isOpen && 'rotate-180')} />
                </button>
                
                {isOpen && (
                  <div 
                    className="absolute right-0 mt-1 w-36 rounded-lg shadow-lg py-1 z-50 border"
                    style={{ 
                      backgroundColor: 'var(--bg-secondary)', 
                      borderColor: 'var(--border-primary)' 
                    }}
                  >
                    {themeOptions.map((option) => {
                      const Icon = option.icon
                      const isSelected = theme === option.value
                      return (
                        <button
                          key={option.value}
                          onClick={() => {
                            setTheme(option.value)
                            setIsOpen(false)
                          }}
                          className="w-full flex items-center gap-2 px-3 py-2 text-sm transition-colors"
                          style={isSelected ? {
                            backgroundColor: 'rgba(255, 54, 33, 0.1)',
                            color: 'var(--databricks-red)'
                          } : {
                            color: 'var(--text-secondary)'
                          }}
                        >
                          <Icon className="w-4 h-4" />
                          <span>{option.label}</span>
                        </button>
                      )
                    })}
                  </div>
                )}
              </div>
              
              {/* Help Center Dropdown */}
              <div className="relative" ref={helpDropdownRef}>
                <button
                  onClick={handleOpenHelp}
                  className={clsx(
                    "relative flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg transition-colors text-sm border border-transparent hover:border-current",
                    isHelpOpen
                      ? "text-lava-600 border-lava-600"
                      : "text-[var(--text-secondary)] hover:text-lava-600"
                  )}
                  title="Help & Feedback"
                >
                  <QuestionMarkCircleIcon className="w-4 h-4" />
                  <span className="hidden sm:inline">Help</span>
                  {/* Pulsing badge for first-time users */}
                  {!hasClickedHelp && (
                    <span className="absolute -top-0.5 -right-0.5 flex h-3 w-3">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-lava-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-3 w-3 bg-lava-500"></span>
                    </span>
                  )}
                </button>
                
                <AnimatePresence>
                  {isHelpOpen && (
                    <motion.div 
                      initial={{ opacity: 0, y: -8, scale: 0.95 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, y: -8, scale: 0.95 }}
                      transition={{ duration: 0.15 }}
                      className="absolute right-0 mt-2 w-56 rounded-xl shadow-lg py-2 z-50 border overflow-hidden"
                      style={{ 
                        backgroundColor: 'var(--bg-secondary)', 
                        borderColor: 'var(--border-primary)' 
                      }}
                    >
                      <div className="px-3 py-1.5 mb-1">
                        <p className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider">Help & Resources</p>
                      </div>
                      
                      <a
                        href="https://cheeyutan.github.io/lakemeter-opensource/"
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={() => setIsHelpOpen(false)}
                        className="flex items-center gap-3 px-3 py-2.5 text-sm transition-colors hover:bg-[var(--bg-tertiary)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                      >
                        <DocumentTextIcon className="w-4 h-4 text-blue-500" />
                        <div>
                          <p className="font-medium">Documentation</p>
                          <p className="text-xs text-[var(--text-muted)]">User guides & reference</p>
                        </div>
                      </a>

                      <a
                        href="https://www.databricks.com/product/pricing"
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={() => setIsHelpOpen(false)}
                        className="flex items-center gap-3 px-3 py-2.5 text-sm transition-colors hover:bg-[var(--bg-tertiary)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                      >
                        <CurrencyDollarIcon className="w-4 h-4 text-purple-500" />
                        <div>
                          <p className="font-medium">Official Pricing</p>
                          <p className="text-xs text-[var(--text-muted)]">Databricks pricing page</p>
                        </div>
                      </a>

                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
              
            </div>
          </div>
        </div>
      </header>
      
      {/* Main content - shifts left when chat is open */}
      <main 
        className="flex-1"
        style={isChatOpen && showAIAssistant ? { marginRight: `${chatPanelWidth}px` } : undefined}
      >
        <motion.div
          key={location.pathname}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2, ease: 'easeOut' }}
        >
          <Outlet />
        </motion.div>
      </main>
      
      {/* Footer - shifts left when chat is open */}
      <footer 
        className="border-t py-4 mt-auto"
        style={{ 
          borderColor: 'var(--border-primary)',
          ...(isChatOpen && showAIAssistant ? { marginRight: `${chatPanelWidth}px` } : {})
        }}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col sm:flex-row items-center justify-center gap-2 sm:gap-4">
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
              <span className="text-lava-600">Databricks</span> Pricing Calculator • Powered by Apps & Lakebase
            </p>
            <span className="hidden sm:inline text-[var(--text-muted)]">•</span>
            <div className="flex items-center gap-3 text-xs">
              <a
                href="/docs/"
                target="_blank"
                rel="noopener noreferrer"
                className="text-lava-600 hover:text-lava-700 transition-colors hover:underline"
              >
                Docs
              </a>
              <a
                href="https://www.databricks.com/product/pricing"
                target="_blank"
                rel="noopener noreferrer"
                className="text-lava-600 hover:text-lava-700 transition-colors hover:underline"
              >
                Pricing
              </a>
            </div>
          </div>
        </div>
      </footer>
      
      {/* AI Chat Panel - Available on home page (Q&A mode) and estimate detail pages (full mode) */}
      {showAIAssistant && (
        <ChatPanel
          isOpen={isChatOpen}
          onClose={() => setIsChatOpen(false)}
          currentEstimate={isEstimateDetailPage ? currentEstimate : undefined}
          currentWorkloads={isEstimateDetailPage ? lineItems : undefined}
          itemCosts={isEstimateDetailPage ? localCalculatedCosts : undefined}
          mode={isHomePage ? 'home' : 'estimate'}
          onWorkloadConfirmed={isEstimateDetailPage ? async (workloadConfig) => {
            if (currentEstimate?.estimate_id) {
              try {
                await createLineItem({
                  estimate_id: currentEstimate.estimate_id,
                  ...workloadConfig
                })
                calculateAllWorkloadCosts(currentEstimate.estimate_id)
                toast.success(`Workload "${workloadConfig.workload_name}" added!`)
              } catch (err: any) {
                toast.error(err.message || 'Failed to add workload')
                throw err  // Re-throw so ChatPanel can show error
              }
            }
          } : undefined}
          onWidthChange={setChatPanelWidth}
          panelWidth={chatPanelWidth}
        />
      )}
      
      {/* Floating AI Assistant Button - Shows when chat is closed for discovery */}
      {showAIAssistant && !isChatOpen && (
        <button
          onClick={handleToggleChat}
          className="fixed bottom-6 right-6 z-40 flex items-center gap-2.5 pl-4 pr-5 py-3 rounded-full text-white shadow-lg transition-all duration-200 hover:shadow-xl bg-gradient-to-r from-lava-600 via-amber-500 to-yellow-500 shadow-lava-600/25 hover:shadow-lava-600/35"
          title="Open AI Assistant"
        >
          {/* Icon */}
          <SparklesIcon className="w-5 h-5" />
          {/* Label */}
          <span className="text-sm font-semibold whitespace-nowrap">AI Assistant</span>
          {/* Subtle pulse ring for attention (only for first-time users) */}
          {!hasUsedAIAssistant && (
            <span className="absolute inset-0 rounded-full bg-gradient-to-r from-lava-500 to-amber-400 animate-ping opacity-20" />
          )}
        </button>
      )}
      
      {/* Session Expired Modal */}
      <AnimatePresence>
        {showSessionExpired && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[100] flex items-center justify-center p-4"
            style={{ backgroundColor: 'rgba(0, 0, 0, 0.6)' }}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="max-w-md w-full rounded-2xl shadow-2xl overflow-hidden"
              style={{ backgroundColor: 'var(--bg-primary)' }}
            >
              {/* Header with warning icon */}
              <div className="bg-gradient-to-r from-amber-500 to-lava-600 px-6 py-8 text-center">
                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-white/20 flex items-center justify-center">
                  <ExclamationTriangleIcon className="w-10 h-10 text-white" />
                </div>
                <h2 className="text-2xl font-bold text-white">Session Expired</h2>
              </div>
              
              {/* Content */}
              <div className="px-6 py-6">
                <p className="text-center mb-6" style={{ color: 'var(--text-secondary)' }}>
                  {sessionExpiredMessage || 'Your session has expired due to inactivity or token expiration.'}
                </p>
                
                <div 
                  className="p-4 rounded-lg mb-6 text-sm"
                  style={{ backgroundColor: 'var(--bg-tertiary)', color: 'var(--text-muted)' }}
                >
                  <p className="font-medium mb-2" style={{ color: 'var(--text-primary)' }}>
                    What happened?
                  </p>
                  <ul className="list-disc list-inside space-y-1">
                    <li>Your authentication token has expired</li>
                    <li>This can happen after extended inactivity</li>
                    <li>Your data is safe - just refresh to continue</li>
                  </ul>
                </div>
                
                <button
                  onClick={handleRefreshPage}
                  className="w-full flex items-center justify-center gap-2 px-6 py-3 rounded-xl font-semibold text-white bg-gradient-to-r from-lava-600 to-amber-500 hover:from-lava-700 hover:to-amber-600 transition-all duration-200 shadow-lg hover:shadow-xl"
                >
                  <ArrowPathIcon className="w-5 h-5" />
                  Refresh Page
                </button>
                
                <p className="text-center text-xs mt-4" style={{ color: 'var(--text-muted)' }}>
                  You'll be redirected to log in again
                </p>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
