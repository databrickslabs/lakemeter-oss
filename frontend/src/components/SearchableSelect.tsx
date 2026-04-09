import { useState, useRef, useEffect, useMemo } from 'react'
import clsx from 'clsx'
import { ChevronDownIcon, XMarkIcon, MagnifyingGlassIcon } from '@heroicons/react/24/outline'

interface Option {
  value: string
  label: string
  group?: string  // Optional group for categorization
}

interface SearchableSelectProps {
  options: Option[]
  value: string
  onChange: (value: string) => void
  onSearchChange?: (search: string) => void
  onOpen?: () => void  // Called when dropdown opens (for lazy loading)
  placeholder?: string
  searchPlaceholder?: string
  isLoading?: boolean
  disabled?: boolean
  required?: boolean
  className?: string
  grouped?: boolean  // Enable grouped display
}

export default function SearchableSelect({
  options,
  value,
  onChange,
  onSearchChange,
  onOpen,
  placeholder = 'Select...',
  searchPlaceholder = 'Search...',
  isLoading = false,
  disabled = false,
  required = false,
  className,
  grouped = false
}: SearchableSelectProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [search, setSearch] = useState('')
  const containerRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Find the selected option label
  const selectedOption = options.find(o => o.value === value)
  
  // Filter options based on search
  const filteredOptions = search
    ? options.filter(o => 
        o.label.toLowerCase().includes(search.toLowerCase()) ||
        o.group?.toLowerCase().includes(search.toLowerCase())
      )
    : options

  // Group options by their group property
  const groupedOptions = useMemo(() => {
    if (!grouped) return null
    
    const groups: { [key: string]: Option[] } = {}
    filteredOptions.forEach(option => {
      const groupName = option.group || 'Other'
      if (!groups[groupName]) {
        groups[groupName] = []
      }
      groups[groupName].push(option)
    })
    
    // Sort groups alphabetically, but put "General Purpose" first if it exists
    const sortedGroupNames = Object.keys(groups).sort((a, b) => {
      if (a === 'General Purpose') return -1
      if (b === 'General Purpose') return 1
      return a.localeCompare(b)
    })
    
    return sortedGroupNames.map(name => ({
      name,
      options: groups[name]
    }))
  }, [filteredOptions, grouped])

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false)
        setSearch('')
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Notify parent of search changes (for API filtering)
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      onSearchChange?.(search)
    }, 300)
    return () => clearTimeout(timeoutId)
  }, [search, onSearchChange])

  const handleSelect = (optionValue: string) => {
    onChange(optionValue)
    setIsOpen(false)
    setSearch('')
  }

  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation()
    onChange('')
    setSearch('')
  }

  return (
    <div ref={containerRef} className={clsx("relative", className)}>
      {/* Main button/display */}
      <div
        onClick={() => {
          if (!disabled) {
            const wasOpen = isOpen
            setIsOpen(!isOpen)
            if (!wasOpen) {
              // Opening the dropdown
              onOpen?.()  // Trigger lazy loading callback
              setTimeout(() => inputRef.current?.focus(), 0)
            }
          }
        }}
        className={clsx(
          "w-full flex items-center gap-1.5 px-2.5 py-1.5 rounded-md border text-sm cursor-pointer transition-colors",
          "bg-[var(--bg-secondary)] border-[var(--border-primary)]",
          "hover:border-[var(--border-secondary)]",
          isOpen && "border-lava-600 ring-1 ring-lava-600/30",
          !value && required && !isOpen && "border-lava-600/50 ring-1 ring-lava-600/30",
          disabled && "opacity-50 cursor-not-allowed"
        )}
      >
        <MagnifyingGlassIcon className="w-4 h-4 text-[var(--text-muted)] flex-shrink-0" />
        
        {isOpen ? (
          <input
            ref={inputRef}
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={searchPlaceholder}
            className="flex-1 bg-transparent border-none p-0 focus:ring-0 focus:outline-none text-[var(--text-primary)] placeholder-[var(--text-muted)]"
            onClick={(e) => e.stopPropagation()}
          />
        ) : isLoading ? (
          <span className="flex-1 truncate text-[var(--text-muted)] flex items-center gap-2">
            <svg className="animate-spin h-3 w-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Loading...
          </span>
        ) : (
          <span 
            className={clsx(
              "flex-1 truncate",
              value ? "text-[var(--text-primary)]" : "text-[var(--text-muted)]"
            )}
            title={selectedOption?.label || placeholder}
          >
            {selectedOption?.label || placeholder}
          </span>
        )}
        
        {value && !isOpen && (
          <button
            onClick={handleClear}
            className="p-0.5 hover:bg-[var(--bg-tertiary)] rounded"
          >
            <XMarkIcon className="w-4 h-4 text-[var(--text-muted)]" />
          </button>
        )}
        
        <ChevronDownIcon className={clsx(
          "w-4 h-4 text-[var(--text-muted)] transition-transform flex-shrink-0",
          isOpen && "rotate-180"
        )} />
      </div>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute z-50 w-full mt-1 bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-md shadow-lg max-h-64 overflow-auto">
          {isLoading ? (
            <div className="px-2.5 py-1.5 text-sm text-[var(--text-muted)]">Loading...</div>
          ) : filteredOptions.length === 0 ? (
            <div className="px-2.5 py-1.5 text-sm text-[var(--text-muted)]">
              {search ? 'No results found' : 'No options available'}
            </div>
          ) : grouped && groupedOptions ? (
            <>
              <div className="px-2.5 py-1 text-xs text-[var(--text-muted)] border-b border-[var(--border-primary)]">
                {filteredOptions.length} result{filteredOptions.length !== 1 ? 's' : ''}
              </div>
              {groupedOptions.map((group) => (
                <div key={group.name}>
                  <div className="px-2.5 py-1 text-xs font-semibold text-[var(--text-secondary)] bg-[var(--bg-tertiary)] sticky top-0 border-b border-[var(--border-primary)]">
                    {group.name}
                  </div>
                  {group.options.map((option) => (
                    <div
                      key={option.value}
                      onClick={() => handleSelect(option.value)}
                      className={clsx(
                        "px-2.5 py-1.5 text-sm cursor-pointer transition-colors",
                        option.value === value
                          ? "bg-lava-600/10 text-lava-600"
                          : "text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)]"
                      )}
                    >
                      {option.label}
                    </div>
                  ))}
                </div>
              ))}
            </>
          ) : (
            <>
              <div className="px-2.5 py-1 text-xs text-[var(--text-muted)] border-b border-[var(--border-primary)]">
                {filteredOptions.length} result{filteredOptions.length !== 1 ? 's' : ''}
              </div>
              {filteredOptions.map((option) => (
                <div
                  key={option.value}
                  onClick={() => handleSelect(option.value)}
                  className={clsx(
                    "px-2.5 py-1.5 text-sm cursor-pointer transition-colors",
                    option.value === value
                      ? "bg-lava-600/10 text-lava-600"
                      : "text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)]"
                  )}
                >
                  {option.label}
                </div>
              ))}
            </>
          )}
        </div>
      )}
    </div>
  )
}

