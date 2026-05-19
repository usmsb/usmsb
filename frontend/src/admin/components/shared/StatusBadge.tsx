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
  online:     { label: '在线',  color: 'text-success', bg: 'bg-success/10 border-success/20' },
  busy:      { label: '忙碌',  color: 'text-warning', bg: 'bg-warning/10 border-warning/20' },
  offline:   { label: '离线',  color: 'text-danger',  bg: 'bg-danger/10 border-danger/20' },
  idle:      { label: '空闲',  color: 'text-muted',   bg: 'bg-muted/10 border-muted/20' },

  // 订单/任务状态
  pending:    { label: '待处理', color: 'text-warning', bg: 'bg-warning/10 border-warning/20' },
  in_progress:{ label: '进行中', color: 'text-info',    bg: 'bg-info/10 border-info/20' },
  delivered:  { label: '已交付', color: 'text-primary', bg: 'bg-primary/10 border-primary/20' },
  completed:  { label: '已完成', color: 'text-success', bg: 'bg-success/10 border-success/20' },
  cancelled:  { label: '已取消', color: 'text-muted',   bg: 'bg-muted/10 border-muted/20' },
  disputed:   { label: '争议中', color: 'text-danger',  bg: 'bg-danger/10 border-danger/20' },

  // 提案状态
  active:    { label: '进行中', color: 'text-success', bg: 'bg-success/10 border-success/20' },
  passed:    { label: '已通过', color: 'text-success', bg: 'bg-success/10 border-success/20' },
  rejected:  { label: '已否决', color: 'text-danger',  bg: 'bg-danger/10 border-danger/20' },
  expired:   { label: '已过期', color: 'text-muted',   bg: 'bg-muted/10 border-muted/20' },

  // Stake 状态
  staked:    { label: '已质押', color: 'text-success', bg: 'bg-success/10 border-success/20' },
  unstaking: { label: '解质押中', color: 'text-warning', bg: 'bg-warning/10 border-warning/20' },
  unlocked:  { label: '已解锁', color: 'text-muted',   bg: 'bg-muted/10 border-muted/20' },
  none:      { label: '无',     color: 'text-muted',   bg: 'bg-muted/10 border-muted/20' },

  // 服务健康
  ok:        { label: '正常', color: 'text-success', bg: 'bg-success/10 border-success/20' },
  degraded:  { label: '降级', color: 'text-warning', bg: 'bg-warning/10 border-warning/20' },
  down:      { label: '宕机', color: 'text-danger',  bg: 'bg-danger/10 border-danger/20' },
  warning:   { label: '警告', color: 'text-warning', bg: 'bg-warning/10 border-warning/20' },
  critical:  { label: '危险', color: 'text-danger',  bg: 'bg-danger/10 border-danger/20' },
  maintenance:{ label: '维护', color: 'text-info',    bg: 'bg-info/10 border-info/20' },

  // Gene Capsule 可视性
  public:    { label: '公开', color: 'text-success', bg: 'bg-success/10 border-success/20' },
  private:   { label: '私有', color: 'text-warning', bg: 'bg-warning/10 border-warning/20' },
  negotiable:{ label: '谈判', color: 'text-info',    bg: 'bg-info/10 border-info/20' },

  // Agent 类型
  ai:        { label: 'AI Agent', color: 'text-primary', bg: 'bg-primary/10 border-primary/20' },
  human:     { label: 'Human',    color: 'text-success', bg: 'bg-success/10 border-success/20' },
  system:    { label: 'System',   color: 'text-muted',   bg: 'bg-muted/10 border-muted/20' },
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
    color: 'text-text-secondary',
    bg: 'bg-bg-tertiary border-border-primary',
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
