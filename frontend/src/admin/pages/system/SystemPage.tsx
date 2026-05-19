/** SystemPage - 系统管理（重定向到 Health） */
import { Navigate } from 'react-router-dom'

export default function SystemPage() {
  return <Navigate to="/admin/system/health" replace />
}
