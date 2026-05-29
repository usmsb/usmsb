/**
 * Admin 顶部导航栏
 */
import { Link, useLocation } from 'react-router-dom'
import {
  Bell,
  ChevronDown,
  LogOut,
} from 'lucide-react'
import { useAuthStore } from '@/stores/authStore'
import { useState, useRef, useEffect } from 'react'

// Logo SVG
function AdminLogo() {
  return (
    <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
      <rect width="32" height="32" rx="8" fill="url(#adminLogoGrad)" />
      <path d="M8 16L16 8L24 16L16 24L8 16Z" fill="white" fillOpacity="0.9" />
      <path d="M12 16L16 12L20 16L16 20L12 16Z" fill="url(#adminLogoGrad)" />
      <defs>
        <linearGradient id="adminLogoGrad" x1="0" y1="0" x2="32" y2="32">
          <stop offset="0%" stopColor="#00f5ff" />
          <stop offset="100%" stopColor="#bf00ff" />
        </linearGradient>
      </defs>
    </svg>
  )
}

function NotificationBell() {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="relative p-2 rounded-lg hover:bg-cyber-card border border-transparent hover:border-neon-blue/30 transition-all"
      >
        <Bell className="w-5 h-5 text-neon-blue" />
        <span className="absolute top-1 right-1 w-2 h-2 bg-neon-red rounded-full animate-pulse" />
      </button>
      {open && (
        <div className="absolute right-0 top-full mt-2 w-80 bg-cyber-card border border-neon-blue/30 rounded-xl shadow-lg z-50">
          <div className="p-4 border-b border-neon-blue/20">
            <p className="text-neon-blue font-cyber font-medium">通知</p>
          </div>
          <div className="p-4 text-center text-gray-500 text-sm">
            暂无新通知
          </div>
        </div>
      )}
    </div>
  )
}

function UserMenu() {
  const logout = useAuthStore(s => s.logout)
  const address = useAuthStore(s => s.address)
  const userRole = useAuthStore(s => s.userRole)
  const isConnected = useAuthStore(s => s.isConnected)
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  if (!isConnected || !address) return null

  const displayRole = userRole === 'node_admin' ? '节点管理员' : userRole === 'superadmin' ? '超级管理员' : userRole || ''

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 p-2 rounded-lg hover:bg-cyber-card border border-transparent hover:border-neon-blue/30 transition-all"
      >
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-neon-blue to-neon-purple flex items-center justify-center">
          <span className="text-white text-sm font-medium">
            {address?.slice(2, 4).toUpperCase() || 'AD'}
          </span>
        </div>
        <div className="text-left hidden sm:block">
          <p className="text-gray-200 text-sm font-medium font-cyber">
            {displayRole}
          </p>
          <p className="text-gray-500 text-xs font-mono">
            {address?.slice(0, 6)}...{address?.slice(-4)}
          </p>
        </div>
        <ChevronDown className="w-4 h-4 text-gray-500" />
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-56 bg-cyber-card border border-neon-blue/30 rounded-xl shadow-lg z-50">
          <div className="p-3 border-b border-neon-blue/20">
            <p className="text-neon-blue text-sm font-medium">{userRole}</p>
            <p className="text-gray-500 text-xs font-mono mt-0.5">{address}</p>
          </div>
          <div className="p-2">
            <button
              onClick={logout}
              className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-neon-red hover:bg-neon-red/10 transition-colors text-sm"
            >
              <LogOut className="w-4 h-4" />
              退出登录
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function ConnectionStatus() {
  const [status, setStatus] = useState<'connected' | 'connecting' | 'disconnected'>('connecting')

  useEffect(() => {
    const timer = setTimeout(() => setStatus('connected'), 1500)
    return () => clearTimeout(timer)
  }, [])

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-cyber-card border border-neon-blue/20">
      <div className={`w-2 h-2 rounded-full ${
        status === 'connected' ? 'bg-neon-green animate-pulse' :
        status === 'connecting' ? 'bg-neon-yellow animate-pulse' : 'bg-neon-red'
      }`}
        style={{ boxShadow: status === 'connected' ? '0 0 10px #00ff88' : status === 'connecting' ? '0 0 10px #ffff00' : '0 0 10px #ff0040' }}
      />
      <span className="text-gray-400 text-xs font-cyber">
        {status === 'connected' ? '实时已连接' :
         status === 'connecting' ? '连接中...' : '已断开'}
      </span>
    </div>
  )
}

export default function AdminHeader() {
  const location = useLocation()

  // 生成面包屑
  const segments = location.pathname.replace('/admin/', '').split('/').filter(Boolean)
  const breadcrumbs = [
    { label: '首页', path: '/admin/dashboard' },
    ...segments.map((seg, i) => ({
      label:
        seg === 'dashboard' ? '运营总览' :
        seg === 'nodes' ? '节点管理' :
        seg === 'agents' ? 'Agent 管理' :
        seg === 'users' ? '用户管理' :
        seg === 'transactions' ? '交易流水' :
        seg === 'orders' ? '订单管理' :
        seg === 'matching' ? '匹配分析' :
        seg === 'gene-capsules' ? 'Gene Capsule' :
        seg === 'intelligence' ? 'AI 能力' :
        seg === 'governance' ? '治理投票' :
        seg === 'contracts' ? '区块链合约' :
        seg === 'system' ? '系统管理' :
        seg === 'permissions' ? '权限管理' :
        seg === 'command-center' ? '指挥中心' :
        seg === 'staking' ? '质押生态' :
        seg === 'rewards' ? '奖励分发' :
        seg === 'market' ? '市场数据' :
        seg === 'health' ? '健康状态' :
        seg === 'config' ? '运行时配置' :
        seg === 'logs' ? '日志查看' :
        seg,
      path: '/admin/' + segments.slice(0, i + 1).join('/'),
    }))
  ]

  return (
    <header className="fixed top-0 left-0 right-0 z-40 h-16 bg-cyber-card border-b border-neon-blue/20 flex items-center px-6 gap-4"
      style={{ boxShadow: '0 0 20px rgba(0, 245, 255, 0.1)' }}>
      {/* Logo */}
      <Link to="/admin/dashboard" className="flex items-center gap-3 shrink-0">
        <AdminLogo />
        <span className="font-cyber text-base font-bold text-transparent bg-clip-text bg-gradient-to-r from-neon-blue to-neon-purple hidden md:block">
          USMSB Admin
        </span>
      </Link>

      {/* 面包屑 */}
      <nav className="hidden lg:flex items-center gap-1 text-sm">
        {breadcrumbs.map((crumb, i) => (
          <span key={crumb.path} className="flex items-center gap-1">
            {i > 0 && <span className="text-gray-600">/</span>}
            {i < breadcrumbs.length - 1 ? (
              <Link to={crumb.path} className="text-gray-400 hover:text-neon-blue transition-colors">
                {crumb.label}
              </Link>
            ) : (
              <span className="text-neon-blue font-medium">{crumb.label}</span>
            )}
          </span>
        ))}
      </nav>

      {/* 右侧 */}
      <div className="ml-auto flex items-center gap-3">
        <ConnectionStatus />
        <NotificationBell />
        <UserMenu />
      </div>
    </header>
  )
}
