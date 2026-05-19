/**
 * Admin 侧边导航栏
 */
import { NavLink, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  Server,
  Bot,
  Users,
  ArrowLeftRight,
  ClipboardList,
  GitMerge,
  Dna,
  Brain,
  Vote,
  Hexagon,
  Settings,
  Shield,
  Monitor,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  Coins,
  VoteIcon,
  ScrollText,
} from 'lucide-react'
import { useState } from 'react'
import clsx from 'clsx'
import { useAuthStore } from '@/stores/authStore'

interface NavItem {
  key: string
  label: string
  icon: React.ComponentType<{ className?: string }>
  path: string
  badge?: number | null
  children?: { label: string; path: string; superadminOnly?: boolean }[]
  superadminOnly?: boolean
}

const navItems: NavItem[] = [
  { key: 'dashboard', label: '运营总览', icon: LayoutDashboard, path: '/admin/dashboard' },
  { key: 'nodes', label: '节点管理', icon: Server, path: '/admin/nodes' },
  { key: 'agents', label: 'Agent 管理', icon: Bot, path: '/admin/agents' },
  { key: 'users', label: '用户管理', icon: Users, path: '/admin/users' },
  { key: 'transactions', label: '交易流水', icon: ArrowLeftRight, path: '/admin/transactions' },
  { key: 'orders', label: '订单管理', icon: ClipboardList, path: '/admin/orders' },
  { key: 'matching', label: '匹配分析', icon: GitMerge, path: '/admin/matching' },
  { key: 'gene-capsules', label: 'Gene Capsule', icon: Dna, path: '/admin/gene-capsules' },
  { key: 'intelligence', label: 'AI 能力', icon: Brain, path: '/admin/intelligence' },
  { key: 'governance', label: '治理投票', icon: VoteIcon, path: '/admin/governance' },
  {
    key: 'contracts',
    label: '区块链合约',
    icon: Hexagon,
    path: '/admin/contracts',
    children: [
      { label: '总览', path: '/admin/contracts' },
      { label: '质押生态', path: '/admin/contracts/staking' },
      { label: '奖励分发', path: '/admin/contracts/rewards' },
      { label: '治理合约', path: '/admin/contracts/governance' },
      { label: '市场数据', path: '/admin/contracts/market' },
      { label: '订单协作', path: '/admin/contracts/orders' },
    ]
  },
  {
    key: 'system',
    label: '系统管理',
    icon: Settings,
    path: '/admin/system',
    children: [
      { label: '健康状态', path: '/admin/system/health', superadminOnly: true },
      { label: '运行时配置', path: '/admin/system/config', superadminOnly: true },
      { label: '日志查看', path: '/admin/system/logs', superadminOnly: true },
    ]
  },
  { key: 'permissions', label: '权限管理', icon: Shield, path: '/admin/permissions', superadminOnly: true },
  { key: 'command-center', label: '指挥中心', icon: Monitor, path: '/admin/command-center' },
]

export default function AdminSidebar({
  collapsed,
  onToggle,
}: {
  collapsed: boolean
  onToggle: () => void
}) {
  const userRole = useAuthStore(s => s.userRole)
  const location = useLocation()
  const isSuperadmin = userRole === 'superadmin'
  const isAdmin = userRole === 'node_admin' || isSuperadmin

  return (
    <aside className={clsx(
      'fixed top-16 left-0 h-[calc(100vh-64px)] bg-bg-secondary border-r border-border-primary',
      'transition-all duration-300 z-30 flex flex-col',
      collapsed ? 'w-16' : 'w-64',
    )}>
      {/* 导航列表 */}
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {navItems
          .filter(item => !item.superadminOnly || isSuperadmin)
          .map(item => (
            <NavItem
              key={item.key}
              item={item}
              collapsed={collapsed}
              isActive={location.pathname.startsWith(item.path)}
              isSuperadmin={isSuperadmin}
            />
          ))
        }
      </nav>

      {/* 折叠按钮 */}
      <div className="p-3 border-t border-border-primary">
        <button
          onClick={onToggle}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-text-muted hover:text-text-primary hover:bg-bg-tertiary transition-colors"
        >
          {collapsed ? (
            <ChevronRight className="w-5 h-5" />
          ) : (
            <>
              <ChevronLeft className="w-5 h-5" />
              <span className="text-sm">收起</span>
            </>
          )}
        </button>
      </div>
    </aside>
  )
}

function NavItem({
  item,
  collapsed,
  isActive,
  isSuperadmin,
}: {
  item: NavItem
  collapsed: boolean
  isActive: boolean
  isSuperadmin: boolean
}) {
  const [expanded, setExpanded] = useState(isActive)

  if (item.children) {
    return (
      <div>
        <button
          onClick={() => setExpanded(!expanded)}
          className={clsx(
            'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors',
            isActive ? 'bg-primary-muted text-primary border border-primary/30' : 'text-text-secondary hover:bg-bg-tertiary',
          )}
        >
          <item.icon className="w-5 h-5 shrink-0" />
          {!collapsed && (
            <>
              <span className="flex-1 text-left font-rajdhani font-medium text-sm">{item.label}</span>
              <ChevronDown className={clsx('w-4 h-4 transition-transform', expanded && 'rotate-180')} />
            </>
          )}
        </button>

        {!collapsed && expanded && (
          <div className="ml-4 mt-1 space-y-0.5">
            {item.children
              .filter(child => !child.superadminOnly || isSuperadmin)
              .map(child => (
                <NavLink
                  key={child.path}
                  to={child.path}
                  end={child.path === '/admin/contracts'}
                  className={clsx(
                    'flex items-center px-3 py-2 rounded-lg text-sm transition-colors',
                    'text-text-secondary hover:bg-bg-tertiary hover:text-text-primary',
                  )}
                >
                  <span>{child.label}</span>
                </NavLink>
              ))
            }
          </div>
        )}
      </div>
    )
  }

  return (
    <NavLink
      to={item.path}
      className={clsx(
        'flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors',
        isActive
          ? 'bg-primary-muted text-primary border border-primary/30'
          : 'text-text-secondary hover:bg-bg-tertiary hover:text-text-primary',
      )}
    >
      <item.icon className="w-5 h-5 shrink-0" />
      {!collapsed && (
        <span className="font-rajdhani font-medium text-sm">{item.label}</span>
      )}
      {!collapsed && item.badge && (
        <span className="ml-auto px-2 py-0.5 rounded-full bg-danger text-white text-xs">
          {item.badge}
        </span>
      )}
    </NavLink>
  )
}
