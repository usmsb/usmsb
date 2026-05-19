/**
 * Dashboard - 运营总览页面
 * Phase 1 核心交付物
 */
import { useQuery } from '@tanstack/react-query'
import {
  Bot,
  Users,
  Activity,
  DollarSign,
  TrendingUp,
  TrendingDown,
  Server,
  ArrowLeftRight,
  ClipboardList,
  Target,
  Coins,
  Zap,
  RefreshCw,
} from 'lucide-react'
import {
  fetchDashboardStats,
  fetchNodes,
  fetchTransactions,
  fetchOrders,
  fetchAgents,
} from '../../api/adminApi'
import StatCard from '../../components/shared/StatCard'
import StatusBadge from '../../components/shared/StatusBadge'
import AgentTrendChart from './components/AgentTrendChart'
import TransactionChart from './components/TransactionChart'
import StakeDistributionChart from './components/StakeDistributionChart'
import NodeHealthTable from './components/NodeHealthTable'
import RecentTransactionsTable from './components/RecentTransactionsTable'
import LiveFeed from './components/LiveFeed'
import { useState } from 'react'

function TimeRangeSelector({
  value,
  onChange,
}: {
  value: '7d' | '30d' | '90d'
  onChange: (v: '7d' | '30d' | '90d') => void
}) {
  return (
    <div className="flex gap-1 bg-bg-tertiary rounded-lg p-1">
      {(['7d', '30d', '90d'] as const).map(range => (
        <button
          key={range}
          onClick={() => onChange(range)}
          className={`px-3 py-1 rounded-md text-sm font-rajdhani font-medium transition-all ${
            value === range
              ? 'bg-primary text-white'
              : 'text-text-secondary hover:text-text-primary'
          }`}
        >
          {range === '7d' ? '7天' : range === '30d' ? '30天' : '90天'}
        </button>
      ))}
    </div>
  )
}

function RefreshButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-bg-tertiary hover:bg-bg-elevated text-text-secondary hover:text-text-primary transition-colors text-sm"
    >
      <RefreshCw className="w-4 h-4" />
      刷新
    </button>
  )
}

export default function DashboardPage() {
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d'>('7d')

  // 并行请求所有数据
  const { data: stats, isLoading: statsLoading, refetch: refetchStats } = useQuery({
    queryKey: ['admin', 'dashboard', 'stats'],
    queryFn: fetchDashboardStats,
    refetchInterval: 60000, // 60s
  })

  const { data: nodesData, isLoading: nodesLoading, refetch: refetchNodes } = useQuery({
    queryKey: ['admin', 'nodes'],
    queryFn: () => fetchNodes({ pageSize: 100 }),
    refetchInterval: 30000,
  })

  const { data: agentsData, isLoading: agentsLoading, refetch: refetchAgents } = useQuery({
    queryKey: ['admin', 'agents'],
    queryFn: () => fetchAgents({ pageSize: 5 }),
    refetchInterval: 30000,
  })

  const { data: txData, isLoading: txLoading, refetch: refetchTx } = useQuery({
    queryKey: ['admin', 'transactions'],
    queryFn: () => fetchTransactions({ pageSize: 10 }),
    refetchInterval: 30000,
  })

  const { data: ordersData, isLoading: ordersLoading, refetch: refetchOrders } = useQuery({
    queryKey: ['admin', 'orders'],
    queryFn: () => fetchOrders({ pageSize: 100 }),
    refetchInterval: 30000,
  })

  const handleRefresh = () => {
    refetchStats()
    refetchNodes()
    refetchAgents()
    refetchTx()
    refetchOrders()
  }

  // 计算实时变化
  const onlineRate = stats
    ? ((stats.onlineAgents / stats.totalAgents) * 100).toFixed(1)
    : '0'

  return (
    <div className="space-y-6">
      {/* 页面标题栏 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary font-rajdhani">运营总览</h1>
          <p className="text-text-muted text-sm mt-1">
            实时监控 USMSB 平台全局运营状态
          </p>
        </div>
        <div className="flex items-center gap-3">
          <TimeRangeSelector value={timeRange} onChange={setTimeRange} />
          <RefreshButton onClick={handleRefresh} />
        </div>
      </div>

      {/* ===== 第一行：12 个统计卡片 ===== */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-6 gap-4">
        {/* Agent 统计 */}
        <StatCard
          title="总 Agent"
          value={stats?.totalAgents ?? 0}
          icon={Bot}
          color="primary"
          loading={statsLoading}
          sparklineData={stats?.agentTrend?.map(t => t.online + t.busy + t.offline)}
        />
        <StatCard
          title="在线 Agent"
          value={stats?.onlineAgents ?? 0}
          icon={Activity}
          color="success"
          loading={statsLoading}
          change={parseFloat(onlineRate) - 70}
          changeLabel="在线率"
        />
        <StatCard
          title="忙碌 Agent"
          value={stats?.busyAgents ?? 0}
          icon={Zap}
          color="warning"
          loading={statsLoading}
        />
        <StatCard
          title="离线 Agent"
          value={stats?.offlineAgents ?? 0}
          icon={Activity}
          color="danger"
          loading={statsLoading}
        />

        {/* 用户统计 */}
        <StatCard
          title="总用户"
          value={stats?.totalUsers ?? 0}
          icon={Users}
          color="info"
          loading={statsLoading}
        />
        <StatCard
          title="今日新增用户"
          value={stats?.newUsersToday ?? 0}
          icon={Users}
          color="success"
          loading={statsLoading}
        />

        {/* 质押统计 */}
        <StatCard
          title="总质押量"
          value={stats?.totalStake ?? '0'}
          icon={Coins}
          color="primary"
          suffix="VIBE"
          loading={statsLoading}
        />
        <StatCard
          title="质押估值"
          value={stats?.totalStakeUsd ?? 0}
          prefix="$"
          color="info"
          decimals={2}
          loading={statsLoading}
        />
        <StatCard
          title="VIBE 价格"
          value={stats?.vibePriceUsd ?? 0}
          prefix="$"
          color="success"
          decimals={4}
          loading={statsLoading}
        />

        {/* 业务统计 */}
        <StatCard
          title="活跃需求"
          value={stats?.activeDemands ?? 0}
          icon={Target}
          color="warning"
          loading={statsLoading}
        />
        <StatCard
          title="活跃服务"
          value={stats?.activeServices ?? 0}
          icon={Server}
          color="info"
          loading={statsLoading}
        />
        <StatCard
          title="活跃订单"
          value={stats?.activeOrders ?? 0}
          icon={ClipboardList}
          color="primary"
          loading={statsLoading}
        />
      </div>

      {/* ===== 第二行：交易统计 + 实时动态 ===== */}
      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
        {/* 交易统计（3/4 宽度） */}
        <div className="xl:col-span-3 space-y-6">
          {/* 交易金额 + 笔数 */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard
              title="今日交易额"
              value={stats?.todayTransactionVolume ?? '0'}
              icon={DollarSign}
              color="success"
              suffix="VIBE"
              loading={statsLoading}
            />
            <StatCard
              title="今日交易笔数"
              value={stats?.todayTransactionCount ?? 0}
              icon={ArrowLeftRight}
              color="primary"
              loading={statsLoading}
            />
            <StatCard
              title="平台总收入"
              value={stats?.platformRevenue ?? '0'}
              icon={Coins}
              color="warning"
              suffix="VIBE"
              loading={statsLoading}
            />
            <StatCard
              title="总交易数"
              value={stats?.totalTransactions ?? 0}
              icon={ArrowLeftRight}
              color="info"
              loading={statsLoading}
            />
          </div>

          {/* 趋势图表 */}
          <div className="bg-bg-secondary rounded-xl border border-border-primary p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-text-primary font-rajdhani font-medium">趋势分析</h3>
              <TimeRangeSelector value={timeRange} onChange={setTimeRange} />
            </div>
            <AgentTrendChart
              data={stats?.agentTrend ?? []}
              timeRange={timeRange}
              className="h-64"
            />
          </div>

          {/* 交易趋势 + Stake 分布 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-bg-secondary rounded-xl border border-border-primary p-5">
              <h3 className="text-text-primary font-rajdhani font-medium mb-4">交易趋势</h3>
              <TransactionChart className="h-56" />
            </div>
            <div className="bg-bg-secondary rounded-xl border border-border-primary p-5">
              <h3 className="text-text-primary font-rajdhani font-medium mb-4">Stake 分布</h3>
              <StakeDistributionChart
                data={stats?.stakeDistribution}
                loading={statsLoading}
                className="h-56"
              />
            </div>
          </div>
        </div>

        {/* 实时动态（1/4 宽度） */}
        <div className="xl:col-span-1">
          <LiveFeed
            agents={agentsData?.agents?.slice(0, 5) ?? []}
            transactions={txData?.transactions?.slice(0, 5) ?? []}
            loading={agentsLoading || txLoading}
          />
        </div>
      </div>

      {/* ===== 第三行：节点健康 + 最新交易 ===== */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="bg-bg-secondary rounded-xl border border-border-primary p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-text-primary font-rajdhani font-medium">节点健康</h3>
            <a href="/admin/nodes" className="text-primary text-sm hover:underline">查看全部 →</a>
          </div>
          <NodeHealthTable
            nodes={nodesData?.nodes ?? []}
            loading={nodesLoading}
          />
        </div>

        <div className="bg-bg-secondary rounded-xl border border-border-primary p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-text-primary font-rajdhani font-medium">最新交易</h3>
            <a href="/admin/transactions" className="text-primary text-sm hover:underline">查看全部 →</a>
          </div>
          <RecentTransactionsTable
            transactions={txData?.transactions ?? []}
            loading={txLoading}
          />
        </div>
      </div>

      {/* ===== 底部：质押等级分布 + 实时数据 ===== */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[
          { label: '无 Stake', value: stats?.stakeDistribution?.none ?? 0, color: 'muted' as const },
          { label: 'Bronze', value: stats?.stakeDistribution?.bronze ?? 0, color: 'warning' as const },
          { label: 'Silver', value: stats?.stakeDistribution?.silver ?? 0, color: 'info' as const },
          { label: 'Gold', value: stats?.stakeDistribution?.gold ?? 0, color: 'primary' as const },
          { label: 'Platinum', value: stats?.stakeDistribution?.platinum ?? 0, color: 'success' as const },
        ].map(item => (
          <div key={item.label} className="bg-bg-secondary rounded-xl border border-border-primary p-4 flex items-center gap-4">
            <div className={`w-10 h-10 rounded-lg bg-${item.color}/10 flex items-center justify-center`}>
              <Coins className={`w-5 h-5 text-${item.color}`} />
            </div>
            <div>
              <p className="text-text-muted text-xs">{item.label}</p>
              <p className="text-text-primary font-orbitron text-lg">{item.value.toLocaleString()}</p>
            </div>
          </div>
        ))}
      </div>

      {/* 实时连接状态 */}
      <div className="flex items-center gap-2 text-text-muted text-xs">
        <div className="w-2 h-2 rounded-full bg-success animate-pulse" />
        <span>数据每 30-60 秒自动刷新 · 最后更新：{new Date().toLocaleTimeString('zh-CN')}</span>
      </div>
    </div>
  )
}
