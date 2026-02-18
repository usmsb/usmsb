import { useToastStore } from '@/stores/toastStore'
import { X, CheckCircle, AlertCircle, AlertTriangle, Info } from 'lucide-react'
import clsx from 'clsx'

export default function ToastContainer() {
  const { toasts, removeToast } = useToastStore()

  if (toasts.length === 0) return null

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2" role="region" aria-label="Notifications">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          role="alert"
          className={clsx(
            'flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg min-w-[300px] max-w-[400px] animate-slide-in',
            {
              'bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 text-green-800 dark:text-green-200': toast.type === 'success',
              'bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-800 dark:text-red-200': toast.type === 'error',
              'bg-yellow-50 dark:bg-yellow-900/30 border border-yellow-200 dark:border-yellow-800 text-yellow-800 dark:text-yellow-200': toast.type === 'warning',
              'bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 text-blue-800 dark:text-blue-200': toast.type === 'info',
            }
          )}
        >
          {toast.type === 'success' && <CheckCircle size={20} className="text-green-500 dark:text-green-400 flex-shrink-0" />}
          {toast.type === 'error' && <AlertCircle size={20} className="text-red-500 dark:text-red-400 flex-shrink-0" />}
          {toast.type === 'warning' && <AlertTriangle size={20} className="text-yellow-500 dark:text-yellow-400 flex-shrink-0" />}
          {toast.type === 'info' && <Info size={20} className="text-blue-500 dark:text-blue-400 flex-shrink-0" />}
          <span className="flex-1 text-sm">{toast.message}</span>
          <button
            onClick={() => removeToast(toast.id)}
            aria-label="Dismiss notification"
            className="flex-shrink-0 p-1 rounded hover:bg-black/10 dark:hover:bg-white/10"
          >
            <X size={16} />
          </button>
        </div>
      ))}
    </div>
  )
}
