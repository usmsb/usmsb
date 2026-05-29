/**
 * StatusBadge - 状态徽章
 * 通用状态显示组件
 */
import clsx from 'clsx'

type StatusValue =
  | 'online' | 'busy' | 'offline' | 'idle'
  | 'pending' | 'in_progress' | 'delivered' | 'completed' | 'cancelled' | 'disputed'
  | 'active' | 'passed' | 'rejected' | 'expired'
  | 'staked' | 'unstaking' | 'unlocked' | 'none'
  | 'ok' | 'degraded' | 'down' | 'warning' | 'critical' | 'maintenance'
  | 'public' | 'private' | 'negotiable'
  | 'ai' | 'human' | 'system'
  | string

const statusConfig: Record<string, { label: string; color: string; bg: string }> = {
  // Agent/连接状态
  online:     { label: '在线',  color: 'text-neon-green', bg: 'bg-neon-green/10 border-neon-green/30' },
  busy:      { label: '忙碌',  color: 'text-neon-yellow', bg: 'bg-neon-yellow/10 border-neon-yellow/30' },
  offline:   { label: '离线',  color: 'text-gray-500',  bg: 'bg-gray-500/10 border-gray-500/30' },
  idle:      { label: '空闲',  color: 'text-gray-400',   bg: 'bg-gray-400/10 border-gray-400/30' },

  // 订单/任务状态
  pending:    { label: '待处理', color: 'text-neon-yellow', bg: 'bg-neon-yellow/10 border-neon-yellow/30' },
  in_progress:{ label: '进行中', color: 'text-neon-purple',    bg: 'bg-neon-purple/10 border-neon-purple/30' },
  delivered:  { label: '已交付', color: 'text-neon-blue', bg: 'bg-neon-blue/10 border-neon-blue/30' },
  completed:  { label: '已完成', color: 'text-neon-green', bg: 'bg-neon-green/10 border-neon-green/30' },
  cancelled:  { label: '已取消', color: 'text-gray-500',   bg: 'bg-gray-500/10 border-gray-500/30' },
  disputed:   { label: '争议中', color: 'text-neon-red',  bg: 'bg-neon-red/10 border-neon-red/30' },

  // 提案状态
  active:    { label: '进行中', color: 'text-neon-green', bg: 'bg-neon-green/10 border-neon-green/30' },
  passed:    { label: '已通过', color: 'text-neon-green', bg: 'bg-neon-green/10 border-neon-green/30' },
  rejected:  { label: '已否决', color: 'text-neon-red',  bg: 'bg-neon-red/10 border-neon-red/30' },
  expired:   { label: '已过期', color: 'text-gray-500',   bg: 'bg-gray-500/10 border-gray-500/30' },

  // Stake 状态
  staked:    { label: '已质押', color: 'text-neon-green', bg: 'bg-neon-green/10 border-neon-green/30' },
  unstaking: { label: '解质押中', color: 'text-neon-yellow', bg: 'bg-neon-yellow/10 border-neon-yellow/30' },
  unlocked:  { label: '已解锁', color: 'text-gray-500',   bg: 'bg-gray-500/10 border-gray-500/30' },
  none:      { label: '无',     color: 'text-gray-500',   bg: 'bg-gray-500/10 border-gray-500/30' },

  // 服务健康
  ok:        { label: '正常', color: 'text-neon-green', bg: 'bg-neon-green/10 border-neon-green/30' },
  degraded:  { label: '降级', color: 'text-neon-yellow', bg: 'bg-neon-yellow/10 border-neon-yellow/30' },
  down:      { label: '宕机', color: 'text-neon-red',  bg: 'bg-neon-red/10 border-neon-red/30' },
  warning:   { label: '警告', color: 'text-neon-yellow', bg: 'bg-neon-yellow/10 border-neon-yellow/30' },
  critical:  { label: '危险', color: 'text-neon-red',  bg: 'bg-neon-red/10 border-neon-red/30' },
  maintenance:{ label: '维护', color: 'text-neon-purple',    bg: 'bg-neon-purple/10 border-neon-purple/30' },

  // Gene Capsule 可视性
  public:    { label: '公开', color: 'text-neon-green', bg: 'bg-neon-green/10 border-neon-green/30' },
  private:   { label: '私有', color: 'text-neon-yellow', bg: 'bg-neon-yellow/10 border-neon-yellow/30' },
  negotiable:{ label: '谈判', color: 'text-neon-purple',    bg: 'bg-neon-purple/10 border-neon-purple/30' },

  // Agent 类型
  ai:        { label: 'AI Agent', color: 'text-neon-blue', bg: 'bg-neon-blue/10 border-neon-blue/30' },
  human:     { label: 'Human',    color: 'text-neon-green', bg: 'bg-neon-green/10 border-neon-green/30' },
  system:    { label: 'System',   color: 'text-gray-500',   bg: 'bg-gray-500/10 border-gray-500/30' },
}

interface StatusBadgeProps {
  status: StatusValue
  label?: string
  size?: 'sm' | 'md'
  pulse?: boolean
  className?: string
}

export default function StatusBadge({
  status,
  label,
  size = 'md',
  pulse = false,
  className = '',
}: StatusBadgeProps) {
  const config = statusConfig[status] || {
    label: label || status,
    color: 'text-gray-400',
    bg: 'bg-gray-400/10 border-gray-400/30',
  }

  return (
    <span className={clsx(
      'inline-flex items-center gap-1.5 rounded-full border font-rajdhani font-medium',
      config.color,
      config.bg,
      size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs',
      pulse && 'animate-pulse',
      className,
    )}>
      <span className={clsx(
        'w-1.5 h-1.5 rounded-full',
        config.color.replace('text-', 'bg-'),
        pulse && 'animate-ping',
      )} />
      {config.label}
    </span>
  )
}
