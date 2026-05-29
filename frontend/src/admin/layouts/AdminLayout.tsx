/**
 * Admin 主 Layout
 * 复用 frontend 样式体系：Tailwind CSS + Cyberpunk 暗色主题 + Rajdhani 字体
 */
import { ReactNode } from 'react'
import { useState } from 'react'
import AdminHeader from './AdminHeader'
import AdminSidebar from './AdminSidebar'
import ToastContainer from '@/components/Toast'

export default function AdminLayout({ children }: { children: ReactNode }) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  return (
    <div className="min-h-screen bg-cyber-dark dark">
      {/* 顶部导航栏 */}
      <AdminHeader />

      <div className="flex">
        {/* 侧边栏 */}
        <AdminSidebar
          collapsed={sidebarCollapsed}
          onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
        />

        {/* 主内容区 */}
        <main className={`flex-1 overflow-auto transition-all duration-300
          ${sidebarCollapsed ? 'ml-16' : 'ml-64'}
          min-h-[calc(100vh-64px)]`}>
          <div className="p-6 pt-16">
            {children}
          </div>
        </main>
      </div>

      {/* 全局 Toast */}
      <ToastContainer />
    </div>
  )
}
