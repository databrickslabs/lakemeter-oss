/**
 * AI Chat Panel Component
 * 
 * Provides a conversational interface for the AI assistant to help users
 * create and manage estimates.
 */
import { useState, useRef, useEffect, useCallback, useMemo } from 'react'
import clsx from 'clsx'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  PaperAirplaneIcon,
  XMarkIcon,
  SparklesIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  ArrowPathIcon,
  DocumentPlusIcon,
  TrashIcon,
  MinusIcon,
  ChevronUpIcon,
  ChevronDownIcon,
  StopIcon,
  PencilIcon,
  CheckIcon,
  ClipboardIcon,
  ClipboardDocumentCheckIcon
} from '@heroicons/react/24/outline'
// AI Chat Panel uses fetch directly - no store needed

interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
  toolResults?: ToolResult[]
  isStreaming?: boolean
  isThinking?: boolean
  isEdited?: boolean
}

interface ToolResult {
  tool: string
  result: any
}

interface DraftEstimate {
  draft_id: string
  name: string
  cloud: string
  region: string
  description?: string
  status: 'draft'
}

interface DraftWorkload {
  draft_id: string
  workload_type: string
  workload_name: string
  estimated_cost: number
  [key: string]: any
}

interface ProposedWorkload {
  proposal_id: string
  workload_type: string
  workload_name: string
  reason: string
  [key: string]: any
}

interface ChatPanelProps {
  isOpen: boolean
  onClose: () => void
  onEstimateCreated?: (estimateId: string) => void
  onWorkloadConfirmed?: (workloadConfig: any) => Promise<void>  // Called when user confirms a proposed workload
  currentEstimate?: any
  currentWorkloads?: any[]
  // Calculated costs for each workload (keyed by item_id)
  itemCosts?: Record<string, { total: number; dbu: number; vm: number }>
  // Controlled panel width for push layout
  panelWidth?: number
  onWidthChange?: (width: number) => void
  // Mode: 'estimate' for full features, 'home' for Q&A only
  mode?: 'estimate' | 'home'
}

export function ChatPanel({
  isOpen,
  onClose,
  onEstimateCreated: _onEstimateCreated, // Reserved for future use
  onWorkloadConfirmed,
  currentEstimate,
  currentWorkloads,
  itemCosts,
  panelWidth: controlledWidth,
  onWidthChange,
  mode = 'estimate'
}: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [draftEstimate, setDraftEstimate] = useState<DraftEstimate | null>(null)
  const [draftWorkloads, setDraftWorkloads] = useState<DraftWorkload[]>([])
  const [proposedWorkloads, setProposedWorkloads] = useState<ProposedWorkload[]>([])
  const [processingProposals, setProcessingProposals] = useState<Set<string>>(new Set())
  const [proposalsCollapsed, setProposalsCollapsed] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isMinimized, setIsMinimized] = useState(false)
  const [localPanelWidth, setLocalPanelWidth] = useState(380)
  const [isResizing, setIsResizing] = useState(false)
  const [showQuickActions, setShowQuickActions] = useState(true) // Visible by default
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null)
  const [editingContent, setEditingContent] = useState('')
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null)
  
  // Use controlled width if provided, otherwise use local state
  const panelWidth = controlledWidth ?? localPanelWidth
  const setPanelWidth = onWidthChange ?? setLocalPanelWidth
  
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const messagesContainerRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const abortControllerRef = useRef<AbortController | null>(null)
  const panelRef = useRef<HTMLDivElement>(null)
  const userScrolledRef = useRef(false) // Track if user manually scrolled
  
  // Calculate total cost from itemCosts - memoized for real-time updates
  const totalCost = useMemo(() => {
    if (!itemCosts || !currentWorkloads) return 0
    let total = 0
    currentWorkloads.forEach(w => {
      const itemId = w.item_id || w.line_item_id
      const costs = itemCosts[itemId]
      if (costs?.total) {
        total += costs.total
      }
    })
    return total
  }, [itemCosts, currentWorkloads])
  
  // Handle resize drag
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    setIsResizing(true)
  }, [])
  
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing) return
      const newWidth = window.innerWidth - e.clientX
      // Min 320px, max 90% of viewport width for maximum flexibility
      const maxWidth = Math.floor(window.innerWidth * 0.9)
      setPanelWidth(Math.min(Math.max(320, newWidth), maxWidth))
    }
    
    const handleMouseUp = () => {
      setIsResizing(false)
    }
    
    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = 'ew-resize'
      document.body.style.userSelect = 'none'
    }
    
    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
  }, [isResizing])
  
  // Auto-resize textarea as user types
  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputValue(e.target.value)
    // Auto-resize
    const textarea = e.target
    textarea.style.height = 'auto'
    textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px'
  }, [])
  
  // Quick action chips - context-aware suggestions with explicit tool-triggering prompts
  const quickActions = useMemo(() => {
    // Home page mode - Q&A focused actions
    if (mode === 'home') {
      return [
        { label: '📚 Workload types', action: 'Explain the different Databricks workload types and when to use each one.' },
        { label: '💰 Pricing guide', action: 'How does Databricks pricing work? Explain DBUs, compute costs, and key pricing factors.' },
        { label: '🏗️ Architecture help', action: 'I need help planning a data architecture. What questions should I consider?' },
        { label: '💡 Best practices', action: 'What are the best practices for optimizing Databricks costs?' },
      ]
    }
    
    // Estimate page mode - full actions
    const hasWorkloads = (currentWorkloads?.length || 0) > 0
    if (!hasWorkloads) {
      return [
        { label: '💡 Optimize', action: 'Analyze my workloads and suggest specific optimizations to reduce costs.' },
        { label: '📊 Summary', action: 'Give me a summary of my current estimate with cost breakdown by workload type.' },
        { label: '➕ Add workload', action: 'Propose a new workload for my existing estimate. Ask me what type I need.' },
        { label: '❓ Pricing', action: 'Explain how Databricks pricing works for the workload types I have.' },
      ]
    }
    return [
      { label: '💡 Optimize', action: 'Analyze my workloads and suggest specific optimizations to reduce costs.' },
      { label: '📊 Summary', action: 'Give me a summary of my current estimate with cost breakdown by workload type.' },
      { label: '➕ Add workload', action: 'Propose a new workload for my existing estimate. Ask me what type I need.' },
      { label: '❓ Pricing', action: 'Explain how Databricks pricing works for the workload types I have.' },
    ]
  }, [currentWorkloads, mode])

  // Scroll to bottom when messages change - but only if user hasn't manually scrolled up
  useEffect(() => {
    if (!userScrolledRef.current) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages])
  
  // Reset scroll tracking when loading starts (new message being sent)
  useEffect(() => {
    if (isLoading) {
      userScrolledRef.current = false
    }
  }, [isLoading])
  
  // Handle manual scroll - detect if user scrolled up
  const handleScroll = useCallback(() => {
    const container = messagesContainerRef.current
    if (!container) return
    
    // Check if user is at the bottom (within 100px)
    const isAtBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 100
    userScrolledRef.current = !isAtBottom
  }, [])

  // Focus input when panel opens
  useEffect(() => {
    if (isOpen) {
      inputRef.current?.focus()
    }
  }, [isOpen])

  // Build welcome message content based on context
  const buildWelcomeContent = useCallback(() => {
    // Home page mode - Q&A only (advisory mode)
    if (mode === 'home') {
      return `**👋 Welcome! I'm your Databricks pricing advisor.**

I'm here to help you **learn and plan** before you dive in:

- 📚 **Explore** workload types (Jobs, SQL, ML, GenAI, etc.)
- 💰 **Understand** pricing factors and DBU costs
- 🏗️ **Get guidance** on architecture decisions
- 💡 **Learn** cost optimization best practices

---

**Ready to build an estimate?**
Click **"+ New Estimate"** above to create one, then I can help you add workloads and calculate costs!

---

📖 **Help & Resources**
- [Documentation](https://cheeyutan.github.io/lakemeter-opensource/) - User guides & reference
- [Official Pricing](https://www.databricks.com/product/pricing) - Databricks pricing page

*Ask me anything using the quick actions below* 👇`
    }
    
    // Estimate page mode - full features
    if (currentEstimate) {
      return `**How can I help you today?**

I can assist you with:

- 📊 **Analyze** your workloads and costs
- 💡 **Optimize** spending with smart recommendations  
- ➕ **Add workloads** based on your requirements
- ❓ **Answer questions** about Databricks pricing

---

📖 **Help & Resources**
- [Documentation](https://cheeyutan.github.io/lakemeter-opensource/) - User guides & reference
- [Official Pricing](https://www.databricks.com/product/pricing) - Databricks pricing page

*Try the quick actions below or ask me anything!*`
    } else {
      return `**Hi! I'm your Databricks pricing assistant.**

*Loading estimate details...*`
    }
  }, [currentEstimate, mode])
  
  // Stop/cancel generation
  const stopGeneration = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
      setIsLoading(false)
      
      // Update the last message to indicate it was stopped
      setMessages(prev => {
        const newMessages = [...prev]
        const lastIdx = newMessages.length - 1
        if (lastIdx >= 0 && newMessages[lastIdx].isStreaming) {
          newMessages[lastIdx] = {
            ...newMessages[lastIdx],
            isStreaming: false,
            isThinking: false,
            content: newMessages[lastIdx].content + '\n\n*[Generation stopped]*'
          }
        }
        return newMessages
      })
    }
  }, [])
  
  // Edit message handler
  const startEditMessage = useCallback((messageId: string, content: string) => {
    setEditingMessageId(messageId)
    setEditingContent(content)
  }, [])
  
  const cancelEditMessage = useCallback(() => {
    setEditingMessageId(null)
    setEditingContent('')
  }, [])
  
  // Copy message to clipboard
  const copyMessageToClipboard = useCallback(async (messageId: string, content: string) => {
    try {
      await navigator.clipboard.writeText(content)
      setCopiedMessageId(messageId)
      // Reset copied state after 2 seconds
      setTimeout(() => setCopiedMessageId(null), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }, [])
  
  // State for pending edit message - will be sent after state reset
  const [pendingEditMessage, setPendingEditMessage] = useState<string | null>(null)
  const [pendingMessageIsEdited, setPendingMessageIsEdited] = useState(false)
  
  const saveEditMessage = useCallback(async (messageId: string) => {
    if (!editingContent.trim()) return
    
    // Find the index of the message being edited
    const messageIndex = messages.findIndex(m => m.id === messageId)
    if (messageIndex === -1) return
    
    const editedContent = editingContent.trim()
    
    // Clear proposed workloads since they may have been created after this message
    setProposedWorkloads([])
    
    setEditingMessageId(null)
    setEditingContent('')
    
    // Clear the backend conversation to start fresh from the edit point
    if (conversationId) {
      try {
        await fetch(`/api/v1/chat/${conversationId}`, { method: 'DELETE' })
      } catch {
        // Ignore errors - we'll start a new conversation anyway
      }
    }
    
    // Reset conversation state
    setConversationId(null)
    
    // Keep only the welcome message
    const welcomeMessage: Message = {
      id: 'welcome',
      role: 'assistant',
      content: buildWelcomeContent(),
      timestamp: new Date()
    }
    setMessages([welcomeMessage])
    
    // Set pending edit message to be sent after state reset
    setPendingEditMessage(editedContent)
    setPendingMessageIsEdited(true)
  }, [editingContent, messages, conversationId, buildWelcomeContent])
  
  
  // Add welcome message on first open
  useEffect(() => {
    if (isOpen && messages.length === 0) {
      const welcomeMessage: Message = {
        id: 'welcome',
        role: 'assistant',
        content: buildWelcomeContent(),
        timestamp: new Date()
      }
      setMessages([welcomeMessage])
    }
  }, [isOpen, buildWelcomeContent])
  
  // Update welcome message when estimate data or costs change (only if no conversation has started)
  useEffect(() => {
    if (isOpen && messages.length === 1 && messages[0].id === 'welcome' && currentEstimate) {
      // Update the welcome message with fresh data including synced costs
      setMessages([{
        id: 'welcome',
        role: 'assistant',
        content: buildWelcomeContent(),
        timestamp: new Date()
      }])
    }
  }, [isOpen, currentEstimate, currentWorkloads, totalCost, buildWelcomeContent])

  const sendMessage = useCallback(async (directMessage?: string, isEdited?: boolean) => {
    const messageToSend = directMessage || inputValue.trim()
    if (!messageToSend || isLoading) return

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: messageToSend,
      timestamp: new Date(),
      isEdited: isEdited || false
    }

    setMessages(prev => [...prev, userMessage])
    setInputValue('')
    setIsLoading(true)
    setError(null)

    // Create placeholder for assistant response with thinking indicator
    const assistantMessageId = `assistant-${Date.now()}`
    setMessages(prev => [...prev, {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      isStreaming: true,
      isThinking: true  // Show thinking indicator until content starts
    }])

    try {
      abortControllerRef.current = new AbortController()
      
      // Build enriched workloads context with actual calculated costs
      const enrichedWorkloads = (currentWorkloads || draftWorkloads || []).map(w => {
        // lineItems use line_item_id, drafts use draft_id
        const itemId = w.line_item_id || w.item_id || w.draft_id
        const costs = itemCosts?.[itemId]
        return {
          ...w,
          total_cost: costs?.total || w.total_cost || 0,
          dbu_cost: costs?.dbu || w.dbu_cost || 0,
          vm_cost: costs?.vm || w.vm_cost || 0
        }
      })
      
      const response = await fetch('/api/v1/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          message: userMessage.content,
          conversation_id: conversationId,
          estimate_context: mode === 'home' ? null : (currentEstimate || draftEstimate),
          workloads_context: mode === 'home' ? [] : enrichedWorkloads,
          mode: mode,
          stream: true
        }),
        signal: abortControllerRef.current.signal
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const reader = response.body?.getReader()
      if (!reader) throw new Error('No response body')

      const decoder = new TextDecoder()
      let buffer = ''
      let fullContent = ''
      let toolResults: ToolResult[] = []

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (data === '[DONE]') continue

            try {
              const chunk = JSON.parse(data)
              
              if (chunk.type === 'start') {
                setConversationId(chunk.conversation_id)
              } else if (chunk.type === 'content') {
                fullContent += chunk.content
                setMessages(prev => prev.map(m => 
                  m.id === assistantMessageId 
                    ? { ...m, content: fullContent, isThinking: false }
                    : m
                ))
              } else if (chunk.type === 'tool_result') {
                toolResults.push({
                  tool: chunk.tool,
                  result: chunk.result
                })
              } else if (chunk.type === 'proposal') {
                // AI proposed a workload - add to pending proposals (deduplicate by proposal_id)
                if (chunk.workload && chunk.workload.proposal_id) {
                  setProposedWorkloads(prev => {
                    // Check if this proposal already exists
                    const exists = prev.some(p => p.proposal_id === chunk.workload.proposal_id)
                    if (exists) return prev
                    return [...prev, chunk.workload]
                  })
                }
              } else if (chunk.type === 'done') {
                // Only update proposals if there wasn't an error in the content
                // (Don't show stale proposals when AI service errors occur)
                const hasError = fullContent.includes('Error getting response') || fullContent.includes('AI service error')
                
                if (!hasError) {
                  // Update draft state from final response
                  if (chunk.estimate) {
                    setDraftEstimate(chunk.estimate)
                  }
                  if (chunk.workloads) {
                    setDraftWorkloads(chunk.workloads)
                  }
                  if (chunk.proposed_workloads && chunk.proposed_workloads.length > 0) {
                    setProposedWorkloads(chunk.proposed_workloads)
                  }
                }
              } else if (chunk.type === 'error') {
                throw new Error(chunk.content)
              }
            } catch (e) {
              // Ignore parse errors for incomplete chunks
            }
          }
        }
      }

      // Finalize the assistant message
      setMessages(prev => prev.map(m => 
        m.id === assistantMessageId 
          ? { ...m, content: fullContent, isStreaming: false, toolResults }
          : m
      ))

    } catch (err: any) {
      if (err.name === 'AbortError') return
      
      console.error('Chat error:', err)
      setError(err.message || 'Failed to get response')
      
      // Remove the streaming message on error
      setMessages(prev => prev.filter(m => m.id !== assistantMessageId))
    } finally {
      setIsLoading(false)
      abortControllerRef.current = null
    }
  }, [inputValue, isLoading, conversationId, currentEstimate, currentWorkloads, draftEstimate, draftWorkloads, itemCosts])

  // Effect to send pending edit message after state reset
  useEffect(() => {
    if (pendingEditMessage && !isLoading) {
      sendMessage(pendingEditMessage, pendingMessageIsEdited)
      setPendingEditMessage(null)
      setPendingMessageIsEdited(false)
    }
  }, [pendingEditMessage, pendingMessageIsEdited, isLoading, sendMessage])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const clearConversation = async () => {
    if (conversationId) {
      try {
        await fetch(`/api/v1/chat/${conversationId}`, { method: 'DELETE' })
      } catch (e) {
        // Ignore errors
      }
    }
    // Clear all state
    setConversationId(null)
    setDraftEstimate(null)
    setDraftWorkloads([])
    setProposedWorkloads([])
    setError(null)
    
    // Restore welcome message with fresh context
    const welcomeMessage: Message = {
      id: 'welcome',
      role: 'assistant',
      content: buildWelcomeContent(),
      timestamp: new Date()
    }
    setMessages([welcomeMessage])
  }
  
  const handleConfirmWorkload = async (proposalId: string) => {
    if (!conversationId) return
    
    // Immediately show processing state
    setProcessingProposals(prev => new Set(prev).add(proposalId))
    
    try {
      const response = await fetch(`/api/v1/chat/${conversationId}/confirm-workload`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ proposal_id: proposalId, confirmed: true })
      })
      
      if (!response.ok) throw new Error('Failed to confirm workload')
      
      const result = await response.json()
      
      // Remove from pending proposals
      setProposedWorkloads(prev => prev.filter(p => p.proposal_id !== proposalId))
      
      // Call the parent callback with the workload config and AWAIT the result
      if (onWorkloadConfirmed && result.workload_config) {
        try {
          await onWorkloadConfirmed(result.workload_config)
          
          // Only show success message AFTER the workload is actually created
          setMessages(prev => [...prev, {
            id: `system-${Date.now()}`,
            role: 'system',
            content: `✅ Workload "${result.workload_config?.workload_name}" added to estimate.`,
            timestamp: new Date()
          }])
        } catch (createErr: any) {
          // Show error if creation failed
          setMessages(prev => [...prev, {
            id: `system-${Date.now()}`,
            role: 'system',
            content: `❌ Failed to add workload: ${createErr.message || 'Database error'}. Please try again.`,
            timestamp: new Date()
          }])
          setError(createErr.message || 'Failed to add workload to database')
        }
      }
      
    } catch (err: any) {
      setError(err.message || 'Failed to confirm workload')
    } finally {
      // Clear processing state
      setProcessingProposals(prev => {
        const next = new Set(prev)
        next.delete(proposalId)
        return next
      })
    }
  }
  
  const handleRejectWorkload = async (proposalId: string) => {
    if (!conversationId) return
    
    // Immediately show processing state
    setProcessingProposals(prev => new Set(prev).add(proposalId))
    
    try {
      const response = await fetch(`/api/v1/chat/${conversationId}/confirm-workload`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ proposal_id: proposalId, confirmed: false })
      })
      
      if (!response.ok) throw new Error('Failed to reject workload')
      
      // Remove from pending proposals
      const rejected = proposedWorkloads.find(p => p.proposal_id === proposalId)
      setProposedWorkloads(prev => prev.filter(p => p.proposal_id !== proposalId))
      
      // Add info message
      setMessages(prev => [...prev, {
        id: `system-${Date.now()}`,
        role: 'system',
        content: `❌ Workload "${rejected?.workload_name}" proposal rejected.`,
        timestamp: new Date()
      }])
      
    } catch (err: any) {
      setError(err.message || 'Failed to reject workload')
    } finally {
      // Clear processing state
      setProcessingProposals(prev => {
        const next = new Set(prev)
        next.delete(proposalId)
        return next
      })
    }
  }
  
  // Batch accept all proposals
  const handleAcceptAll = async () => {
    for (const proposal of proposedWorkloads) {
      await handleConfirmWorkload(proposal.proposal_id)
    }
  }
  
  // Batch reject all proposals
  const handleRejectAll = async () => {
    for (const proposal of proposedWorkloads) {
      await handleRejectWorkload(proposal.proposal_id)
    }
  }

  if (!isOpen) return null
  
  return (
    <>
      {/* Minimized Dock */}
      {isMinimized ? (
        <div className="fixed bottom-4 right-4 z-50">
          <button
            onClick={() => setIsMinimized(false)}
            className="flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-lava-600 to-amber-500 text-white rounded-full shadow-lg hover:shadow-xl"
          >
            <SparklesIcon className="w-5 h-5" />
            <span className="font-medium text-sm">AI Assistant</span>
            <ChevronUpIcon className="w-4 h-4" />
          </button>
        </div>
      ) : (
        <div 
          ref={panelRef}
          className="fixed top-14 bottom-0 right-0 bg-[var(--bg-primary)] border-l border-[var(--border-primary)] shadow-2xl z-40 flex flex-col"
          style={{ width: `min(100vw, ${panelWidth}px)` }}
        >
          {/* Resize Handle */}
          <div
            onMouseDown={handleMouseDown}
            className={clsx(
              "absolute left-0 top-0 bottom-0 w-1.5 cursor-ew-resize hover:bg-lava-600/30 transition-colors z-10",
              isResizing && "bg-lava-600/50"
            )}
          >
            <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-12 rounded-full bg-[var(--border-secondary)] opacity-0 hover:opacity-100 transition-opacity" />
          </div>
          
      {/* Header - Slim */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-[var(--border-primary)] bg-[var(--bg-secondary)]">
        <div className="flex items-center gap-2">
          <h2 className="font-semibold text-sm text-[var(--text-primary)]">AI Assistant</h2>
          {conversationId && (
            <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" title="Active session" />
          )}
          {/* Info tooltip for AI disclaimer */}
          <div className="relative group">
            <button
              className="p-1 rounded hover:bg-[var(--bg-tertiary)] text-[var(--text-muted)] hover:text-[var(--text-secondary)] transition-colors"
              title="AI-generated estimates are for planning purposes only. Always review and validate configurations before deployment."
            >
              <InformationCircleIcon className="w-4 h-4" />
            </button>
            <div className="absolute left-0 top-full mt-1 w-64 p-2.5 text-[11px] leading-relaxed bg-[var(--bg-primary)] border border-[var(--border-primary)] rounded-lg shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50">
              <div className="flex items-start gap-2">
                <ExclamationTriangleIcon className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
                <span className="text-[var(--text-secondary)]">AI-generated estimates are for planning purposes only. Always review and validate configurations before deployment.</span>
              </div>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={clearConversation}
            className="p-2 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 text-[var(--text-secondary)] hover:text-red-600 dark:hover:text-red-400 transition-colors"
            title="Clear conversation"
          >
            <TrashIcon className="w-4 h-4" />
          </button>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-[var(--bg-tertiary)] text-[var(--text-secondary)] transition-colors"
            title="Minimize"
          >
            <MinusIcon className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Current Estimate Context - Shows the estimate being worked on (only in estimate mode) */}
      {mode === 'estimate' && currentEstimate && (
        <div className="px-4 py-2.5 bg-gradient-to-r from-slate-50 to-slate-100 dark:from-slate-800/50 dark:to-slate-900/50 border-b border-[var(--border-primary)]">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 min-w-0 flex-1">
              <div className="w-7 h-7 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center flex-shrink-0">
                <DocumentPlusIcon className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="font-medium text-sm text-[var(--text-primary)] truncate" title={currentEstimate.estimate_name || currentEstimate.name || 'Estimate'}>
                  {currentEstimate.estimate_name || currentEstimate.name || 'Estimate'}
                </div>
                <div className="flex items-center gap-1 text-[10px] text-[var(--text-muted)] flex-wrap">
                  <span className="px-1 py-0.5 rounded bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 font-medium">
                    {(currentEstimate.cloud || 'AWS').toUpperCase()}
                  </span>
                  <span className="truncate">{currentEstimate.region || 'N/A'}</span>
                  <span>•</span>
                  <span>{currentEstimate.tier || 'PREMIUM'}</span>
                </div>
              </div>
            </div>
            <div className="text-right flex-shrink-0">
              <div className="text-[10px] text-[var(--text-muted)]">
                {currentWorkloads?.length || 0} workloads
              </div>
              <div className="font-bold text-sm text-[var(--text-primary)]">
                {totalCost > 0 ? (
                  <span className="text-green-600 dark:text-green-400">
                    ${totalCost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </span>
                ) : (
                  <span className="text-[var(--text-muted)]">—</span>
                )}
                <span className="text-[10px] font-normal text-[var(--text-muted)]">/mo</span>
              </div>
            </div>
          </div>
        </div>
      )}
      
      {/* Proposed Workloads - Awaiting Confirmation */}
      {proposedWorkloads.length > 0 && (
        <div className="px-4 py-2 bg-amber-50 dark:bg-amber-900/20 border-b border-amber-200 dark:border-amber-800">
          {/* Collapsible header */}
          <button
            onClick={() => setProposalsCollapsed(!proposalsCollapsed)}
            className="w-full flex items-center justify-between py-1"
          >
            <div className="flex items-center gap-2">
              <ExclamationCircleIcon className="w-4 h-4 text-amber-600" />
              <span className="text-sm font-medium text-amber-700 dark:text-amber-300">
                {proposedWorkloads.length} Proposed Workload{proposedWorkloads.length !== 1 ? 's' : ''} - Confirm to Add
              </span>
            </div>
            {proposalsCollapsed ? (
              <ChevronDownIcon className="w-4 h-4 text-amber-600" />
            ) : (
              <ChevronUpIcon className="w-4 h-4 text-amber-600" />
            )}
          </button>
          
          {/* Collapsible content */}
          {!proposalsCollapsed && (
            <>
              {/* Batch action buttons */}
              <div className="flex items-center gap-2 mt-2 mb-3">
                <button
                  onClick={handleAcceptAll}
                  disabled={processingProposals.size > 0}
                  className="text-xs px-2.5 py-1 bg-green-600 hover:bg-green-700 disabled:bg-green-400 text-white rounded transition-colors"
                >
                  Accept All ({proposedWorkloads.length})
                </button>
                <button
                  onClick={handleRejectAll}
                  disabled={processingProposals.size > 0}
                  className="text-xs px-2.5 py-1 bg-gray-200 hover:bg-gray-300 disabled:bg-gray-100 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded transition-colors"
                >
                  Reject All
                </button>
              </div>
              
              {/* Proposals list with max height */}
              <div className="space-y-2 max-h-[280px] overflow-y-auto pr-1">
                {proposedWorkloads.map((proposal) => {
                  const isProcessing = processingProposals.has(proposal.proposal_id)
                  
                  return (
                    <div 
                      key={proposal.proposal_id}
                      className={clsx(
                        "bg-white dark:bg-gray-800 rounded-lg p-3 border border-amber-200 dark:border-amber-700 transition-opacity",
                        isProcessing && "opacity-50"
                      )}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1 flex-wrap">
                            <span className="font-medium text-sm text-gray-900 dark:text-gray-100">
                              {proposal.workload_name}
                            </span>
                            <span className="text-[10px] px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded">
                              {proposal.workload_type}
                            </span>
                          </div>
                          {proposal.reason && (
                            <p className="text-xs text-gray-600 dark:text-gray-400 line-clamp-2 mb-1.5">
                              {proposal.reason}
                            </p>
                          )}
                          {/* Enhanced config details */}
                          <div className="flex flex-wrap gap-x-2 gap-y-1 text-[11px] text-gray-500 dark:text-gray-400">
                            {proposal.serverless_enabled && (
                              <span className="px-1.5 py-0.5 bg-teal-100 dark:bg-teal-900/30 text-teal-700 dark:text-teal-300 rounded">Serverless</span>
                            )}
                            {proposal.photon_enabled && (
                              <span className="px-1.5 py-0.5 bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300 rounded">Photon</span>
                            )}
                            {proposal.num_workers && <span>{proposal.num_workers} workers</span>}
                            {proposal.worker_node_type && (
                              <span className="font-mono text-[10px]">{proposal.worker_node_type}</span>
                            )}
                            {proposal.dbsql_warehouse_size && <span>{proposal.dbsql_warehouse_size}</span>}
                            {proposal.hours_per_month && <span>{proposal.hours_per_month}h/mo</span>}
                            {(proposal.runs_per_day && proposal.avg_runtime_minutes) && (
                              <span>{proposal.runs_per_day}×{proposal.avg_runtime_minutes}min</span>
                            )}
                            {proposal.dlt_edition && <span>{proposal.dlt_edition}</span>}
                          </div>
                        </div>
                        <div className="flex items-center gap-1 flex-shrink-0">
                          {isProcessing ? (
                            <div className="w-8 h-8 flex items-center justify-center">
                              <svg className="animate-spin h-4 w-4 text-amber-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                              </svg>
                            </div>
                          ) : (
                            <>
                              <button
                                onClick={() => handleConfirmWorkload(proposal.proposal_id)}
                                className="p-1.5 rounded-full bg-green-100 hover:bg-green-200 dark:bg-green-900/30 dark:hover:bg-green-800/50 text-green-700 dark:text-green-400 transition-colors"
                                title="Confirm & Add"
                              >
                                <CheckCircleIcon className="w-4 h-4" />
                              </button>
                              <button
                                onClick={() => handleRejectWorkload(proposal.proposal_id)}
                                className="p-1.5 rounded-full bg-red-100 hover:bg-red-200 dark:bg-red-900/30 dark:hover:bg-red-800/50 text-red-700 dark:text-red-400 transition-colors"
                                title="Reject"
                              >
                                <XMarkIcon className="w-4 h-4" />
                              </button>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </>
          )}
        </div>
      )}

      {/* Messages */}
      <div 
        ref={messagesContainerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto p-4 space-y-5"
      >
        {messages.map((message) => (
          <div
            key={message.id}
            className={clsx(
              'flex gap-3 group',
              message.role === 'user' ? 'flex-row-reverse' : 'flex-row'
            )}
          >
            {/* Message Content - No avatar or label needed, position indicates role */}
            <div className={clsx(
              'flex-1 min-w-0',
              message.role === 'user' ? 'text-right' : 'text-left'
            )}>
              {/* User message editing */}
              {message.role === 'user' && editingMessageId === message.id ? (
                <div className="inline-block max-w-[85%] text-left">
                  <textarea
                    value={editingContent}
                    onChange={(e) => setEditingContent(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault()
                        saveEditMessage(message.id)
                      }
                    }}
                    className="w-full min-w-[200px] p-3 text-[13px] rounded-xl border border-blue-300 bg-[#d7edfe] dark:bg-blue-900/20 focus:outline-none focus:ring-2 focus:ring-blue-400 text-[var(--text-primary)]"
                    rows={3}
                    placeholder="Press Enter to save, Shift+Enter for new line"
                  />
                  <div className="flex gap-2 mt-2 justify-end items-center">
                    <span className="text-[10px] text-[var(--text-muted)]">Enter to save · Shift+Enter for new line</span>
                    <button
                      onClick={cancelEditMessage}
                      className="px-3 py-1.5 text-xs rounded-lg border border-[var(--border-primary)] text-[var(--text-secondary)] hover:bg-[var(--bg-secondary)]"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={() => saveEditMessage(message.id)}
                      className="px-3 py-1.5 text-xs rounded-lg bg-blue-600 text-white hover:bg-blue-700 flex items-center gap-1"
                    >
                      <CheckIcon className="w-3 h-3" />
                      Save
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <div className={clsx(
                    'inline-block text-[13px] leading-[1.7]',
                    message.role === 'user'
                      ? 'bg-[#d7edfe] text-[var(--text-primary)] px-4 py-2.5 rounded-2xl rounded-tr-md max-w-[85%] whitespace-pre-wrap text-left shadow-sm'
                      : message.role === 'system'
                      ? 'bg-green-50 dark:bg-green-900/20 text-green-800 dark:text-green-200 px-4 py-2.5 rounded-xl border border-green-200 dark:border-green-800'
                      : 'text-[var(--text-primary)] max-w-full'
                  )}>
                    {(message.isStreaming || message.isThinking) && !message.content ? (
                      <div className="flex items-center gap-2 px-2 py-2">
                        <div className="flex gap-1">
                          <span className="w-2 h-2 bg-lava-600 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                          <span className="w-2 h-2 bg-lava-600 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                          <span className="w-2 h-2 bg-lava-600 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                        </div>
                      </div>
                    ) : message.role === 'user' ? (
                      // User messages - plain text with preserved whitespace
                      <span className="whitespace-pre-wrap">{message.content}</span>
                    ) : (
                      // AI/System messages - enhanced markdown rendering
                      <div className="ai-message-content">
                        <ReactMarkdown 
                          remarkPlugins={[remarkGfm]}
                          components={{
                            // Enhanced heading styles
                            h1: ({children}) => <h1 className="text-base font-bold text-[var(--text-primary)] mt-3 mb-2 pb-1 border-b border-[var(--border-primary)]">{children}</h1>,
                            h2: ({children}) => <h2 className="text-[14px] font-bold text-[var(--text-primary)] mt-3 mb-1.5">{children}</h2>,
                            h3: ({children}) => <h3 className="text-[13px] font-semibold text-[var(--text-primary)] mt-2 mb-1">{children}</h3>,
                            // Paragraphs with proper spacing
                            p: ({children}) => <p className="my-2 text-[var(--text-primary)] leading-relaxed">{children}</p>,
                            // Simple list styles
                            ul: ({children}) => <ul className="my-2 ml-4 space-y-1 list-disc">{children}</ul>,
                            ol: ({children}) => <ol className="my-2 ml-4 space-y-1 list-decimal">{children}</ol>,
                            li: ({children}) => <li className="text-[var(--text-primary)]">{children}</li>,
                            // Bold text
                            strong: ({children}) => <strong className="font-semibold text-[var(--text-primary)]">{children}</strong>,
                            // Italic
                            em: ({children}) => <em className="text-[var(--text-secondary)] italic">{children}</em>,
                            // Inline code
                            code: ({className, children}) => {
                              const isBlock = className?.includes('language-')
                              if (isBlock) {
                                return (
                                  <code className="block bg-slate-900 dark:bg-slate-950 text-slate-100 p-3 rounded-lg text-xs font-mono overflow-x-auto my-3 border border-slate-700">
                                    {children}
                                  </code>
                                )
                              }
                              return (
                                <code className="px-1.5 py-0.5 bg-lava-600/10 dark:bg-lava-600/30 text-lava-700 dark:text-lava-400 rounded text-[12px] font-mono">
                                  {children}
                                </code>
                              )
                            },
                            // Code blocks
                            pre: ({children}) => <pre className="my-3 overflow-hidden rounded-lg">{children}</pre>,
                            // Blockquotes
                            blockquote: ({children}) => (
                              <blockquote className="my-3 pl-3 border-l-3 border-lava-500 bg-lava-600/5 dark:bg-lava-600/10 py-2 pr-3 rounded-r-lg text-[var(--text-secondary)] italic">
                                {children}
                              </blockquote>
                            ),
                            // Horizontal rule
                            hr: () => <hr className="my-4 border-[var(--border-primary)]" />,
                            // Links
                            a: ({href, children}) => (
                              <a href={href} className="text-lava-700 dark:text-lava-500 hover:underline font-medium" target="_blank" rel="noopener noreferrer">
                                {children}
                              </a>
                            ),
                          }}
                        >
                          {message.content}
                        </ReactMarkdown>
                      </div>
                    )}
                  </div>

                  {/* Tool Results - More prominent styling */}
                  {message.toolResults && message.toolResults.length > 0 && (
                    <div className="mt-2.5 flex flex-wrap gap-2">
                      {message.toolResults.map((tr, idx) => (
                        <div
                          key={idx}
                          className="text-[11px] px-2.5 py-1.5 bg-slate-100 dark:bg-slate-800 rounded-lg flex items-center gap-1.5"
                        >
                          {tr.result?.success ? (
                            <CheckCircleIcon className="w-3.5 h-3.5 text-green-500" />
                          ) : (
                            <ArrowPathIcon className="w-3.5 h-3.5 text-lava-600" />
                          )}
                          <span className="font-medium text-slate-600 dark:text-slate-300">
                            {tr.tool.replace(/_/g, ' ')}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Timestamp, Edited tag, and Action Buttons */}
                  <div className={clsx(
                    'flex items-center gap-2 mt-1.5',
                    message.role === 'user' ? 'justify-end' : 'justify-start'
                  )}>
                    {/* Edited tag */}
                    {message.isEdited && (
                      <span className="text-[9px] text-[var(--text-muted)] italic">(edited)</span>
                    )}
                    <span className="text-[10px] text-[var(--text-muted)]">
                      {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                    {/* Copy button for user and assistant messages */}
                    {(message.role === 'user' || message.role === 'assistant') && message.id !== 'welcome' && message.content && (
                      <button
                        onClick={() => copyMessageToClipboard(message.id, message.content)}
                        className={clsx(
                          "p-1 rounded transition-colors",
                          copiedMessageId === message.id
                            ? "text-green-500"
                            : "text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-secondary)]"
                        )}
                        title={copiedMessageId === message.id ? "Copied!" : "Copy message"}
                      >
                        {copiedMessageId === message.id ? (
                          <ClipboardDocumentCheckIcon className="w-3.5 h-3.5" />
                        ) : (
                          <ClipboardIcon className="w-3.5 h-3.5" />
                        )}
                      </button>
                    )}
                    {/* Edit button for user messages - always visible */}
                    {message.role === 'user' && message.id !== 'welcome' && !isLoading && (
                      <button
                        onClick={() => startEditMessage(message.id, message.content)}
                        className="p-1 rounded hover:bg-blue-100 dark:hover:bg-blue-900/30 text-blue-400 hover:text-blue-600 transition-colors"
                        title="Edit message"
                      >
                        <PencilIcon className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </>
              )}
            </div>
          </div>
        ))}

        {/* Error Message */}
        {error && (
          <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl">
            <div className="flex items-start gap-2 text-sm text-red-700 dark:text-red-300">
              <ExclamationCircleIcon className="w-5 h-5 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium">{error.includes('400') ? 'Request failed' : 'Error'}</p>
                <p className="text-xs mt-1 opacity-80">
                  {error.includes('400') 
                    ? 'The conversation may be too long. Try clearing the chat and starting fresh.'
                    : error.includes('429')
                    ? 'Rate limited. Please wait a moment and try again.'
                    : error}
                </p>
                {error.includes('400') && (
                  <button
                    onClick={clearConversation}
                    className="mt-2 text-xs px-3 py-1.5 bg-red-100 dark:bg-red-800/50 rounded-lg hover:bg-red-200 dark:hover:bg-red-700/50 transition-colors font-medium"
                  >
                    Clear & restart
                  </button>
                )}
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 border-t border-[var(--border-primary)] bg-gradient-to-t from-[var(--bg-secondary)] to-[var(--bg-primary)]">
        {/* Quick Actions Toggle */}
        {!isLoading && (
          <div className="mb-2">
            <button
              onClick={() => setShowQuickActions(!showQuickActions)}
              className="text-[10px] text-[var(--text-muted)] hover:text-lava-700 dark:hover:text-lava-500 flex items-center gap-1 transition-colors"
            >
              {showQuickActions ? (
                <ChevronDownIcon className="w-3 h-3" />
              ) : (
                <ChevronUpIcon className="w-3 h-3" />
              )}
              {showQuickActions ? "Hide Quick Actions" : "Show Quick Actions"}
            </button>
            
            {/* Quick Action Buttons - 2x2 on mobile, single row on larger */}
            {showQuickActions && (
              <div className="mt-2 grid grid-cols-2 sm:flex sm:justify-center gap-1.5">
                {quickActions.map((action: { label: string; action: string }, idx: number) => (
                  <button
                    key={idx}
                    onClick={() => sendMessage(action.action)}
                    className="text-[10px] px-2.5 py-1.5 rounded-full border border-[var(--border-primary)] bg-[var(--bg-primary)] hover:bg-lava-50 dark:hover:bg-lava-900/20 hover:border-lava-400 hover:text-lava-700 dark:hover:text-lava-400 text-[var(--text-secondary)] transition-all text-center"
                  >
                    {action.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
        
        {/* Text Input with Auto-expand - Submit button inside */}
        <div className="relative flex items-end">
          <textarea
            ref={inputRef}
            value={inputValue}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder="Ask about pricing, workloads, or optimization..."
            rows={1}
            className="w-full resize-none rounded-xl border border-[var(--border-primary)] bg-[var(--bg-primary)] pl-4 pr-12 py-3 text-[13px] leading-relaxed focus:outline-none focus:ring-0 focus:border-lava-500 dark:focus:border-lava-600 placeholder:text-[var(--text-muted)] shadow-sm transition-colors"
            style={{ 
              minHeight: '44px', 
              maxHeight: '150px',
              height: 'auto',
              overflow: inputValue.length > 100 ? 'auto' : 'hidden'
            }}
          />
          
          {/* Submit/Stop Button - Aligned to bottom of textarea */}
          <button
            onClick={isLoading ? stopGeneration : () => sendMessage()}
            disabled={!isLoading && !inputValue.trim()}
            className={clsx(
              "absolute right-2 w-8 h-8 rounded-lg flex items-center justify-center transition-all duration-150",
              "bottom-[6px]", // Align with text baseline
              isLoading 
                ? "bg-red-500 hover:bg-red-600 text-white"
                : inputValue.trim()
                  ? "bg-lava-600 hover:bg-lava-700 text-white"
                  : "bg-[var(--bg-tertiary)] text-[var(--text-muted)] cursor-not-allowed"
            )}
            title={isLoading ? "Stop generation" : "Send message"}
          >
            {isLoading ? (
              <StopIcon className="w-4 h-4" />
            ) : (
              <PaperAirplaneIcon className="w-4 h-4" />
            )}
          </button>
          
          {/* Character count for long messages */}
          {inputValue.length > 100 && (
            <span className="absolute right-12 bottom-[10px] text-[9px] text-[var(--text-muted)] bg-[var(--bg-secondary)] px-1.5 py-0.5 rounded">
              {inputValue.length}
            </span>
          )}
        </div>
        
        <div className="flex items-center justify-between mt-2 text-[9px] text-[var(--text-muted)]">
          <span>Shift+Enter for new line</span>
          <span>Powered by Claude Opus 4.5</span>
        </div>
      </div>
        </div>
      )}
    </>
  )
}

/**
 * Custom Sparkles Icon - Matches the provided SVG path
 */
function SparklesAnimatedIcon({ className }: { className?: string }) {
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

/**
 * AI Assistant Toggle Button
 * 
 * Fixed button in top right corner to open the chat panel.
 */
export function ChatToggleButton({ onClick, hasActiveConversation }: { onClick: () => void, hasActiveConversation?: boolean }) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        "fixed top-4 right-4 w-10 h-10 rounded-lg shadow-lg flex items-center justify-center transition-all hover:scale-105 z-40",
        hasActiveConversation
          ? "bg-teal-600 hover:bg-teal-700"
          : "bg-gradient-to-br from-lava-600 to-amber-600 hover:from-lava-700 hover:to-amber-700"
      )}
      title="AI Assistant"
    >
      <SparklesAnimatedIcon className="w-5 h-5 text-white" />
      {hasActiveConversation && (
        <span className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full border-2 border-white" />
      )}
    </button>
  )
}

