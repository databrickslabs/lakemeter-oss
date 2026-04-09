import React from 'react'
import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { Bars3Icon } from '@heroicons/react/24/outline'

interface SortableItemProps {
  id: string
  children: React.ReactNode
  disabled?: boolean
}

export function SortableItem({ id, children, disabled }: SortableItemProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id, disabled })

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
    position: 'relative' as const,
    zIndex: isDragging ? 50 : undefined,
  }

  return (
    <div ref={setNodeRef} style={style} {...attributes}>
      <div className="flex items-center">
        {!disabled && (
          <div
            {...listeners}
            className="flex-shrink-0 cursor-grab active:cursor-grabbing p-1 -ml-1 mr-1 text-[var(--text-muted)] hover:text-[var(--text-secondary)] touch-none"
            title="Drag to reorder"
          >
            <Bars3Icon className="w-4 h-4" />
          </div>
        )}
        <div className="flex-1 min-w-0">{children}</div>
      </div>
    </div>
  )
}
