// ConfirmDangerousModal.tsx - 危险操作二次确认弹窗
import { ReactNode } from 'react'
import { AlertTriangle, X } from 'lucide-react'

interface ConfirmDangerousModalProps {
  isOpen: boolean
  title: string
  description?: string
  confirmText?: string
  cancelText?: string
  confirmLoading?: boolean
  onConfirm: () => void
  onCancel: () => void
  children?: ReactNode
}

export default function ConfirmDangerousModal({
  isOpen,
  title,
  description,
  confirmText = '确认执行',
  cancelText = '取消',
  confirmLoading,
  onConfirm,
  onCancel,
  children,
}: ConfirmDangerousModalProps) {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onCancel}
      />

      {/* Modal */}
      <div className="relative bg-bg-secondary border border-danger/30 rounded-2xl shadow-2xl w-full max-w-md mx-4 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border-primary">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-danger/10 flex items-center justify-center">
              <AlertTriangle className="w-5 h-5 text-danger" />
            </div>
            <h2 className="text-lg font-bold text-text-primary font-rajdhani">{title}</h2>
          </div>
          <button
            onClick={onCancel}
            className="text-text-muted hover:text-text-primary transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-4 space-y-3">
          {description && (
            <p className="text-text-secondary text-sm">{description}</p>
          )}
          {children && <div>{children}</div>}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-border-primary bg-bg-tertiary/50">
          <button
            onClick={onCancel}
            className="px-4 py-2 rounded-lg bg-bg-tertiary text-text-secondary hover:text-text-primary text-sm transition-colors"
          >
            {cancelText}
          </button>
          <button
            onClick={onConfirm}
            disabled={confirmLoading}
            className="px-4 py-2 rounded-lg bg-danger text-white text-sm font-medium hover:bg-danger/90 disabled:opacity-50 transition-colors"
          >
            {confirmLoading ? '处理中...' : confirmText}
          </button>
        </div>
      </div>
    </div>
  )
}
