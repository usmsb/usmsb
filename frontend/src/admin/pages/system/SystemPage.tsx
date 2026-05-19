/** SystemPage - 系统管理（总览，重定向到 Health） */
import { Navigate } from 'react-router-dom'

export default function SystemPage() {
  return <Navigate to="health" replace />
}
