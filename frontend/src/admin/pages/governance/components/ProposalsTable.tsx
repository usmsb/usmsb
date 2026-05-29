// ProposalsTable.tsx - 提案列表组件
import { useState } from 'react'
import { CheckCircle, Clock, XCircle, ChevronDown, ChevronUp } from 'lucide-react'
import VoteBar from '../../../components/charts/VoteBar'
import AddressDisplay from '../../../components/shared/AddressDisplay'

export interface Proposal {
  id: number
  title?: string
  description: string
  proposer: string
  for_votes: number
  against_votes: number
  deadline: number
  executed: boolean
  canceled?: boolean
  quorum?: number
}

interface ProposalsTableProps {
  proposals: Proposal[]
  isLoading?: boolean
  onSelect?: (proposal: Proposal) => void
  selectedId?: number | null
  className?: string
}

function ProposalStatus({ proposal }: { proposal: Proposal }) {
  if (proposal.executed) return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-neon-green/10 text-neon-green text-xs border border-neon-green/30">
      <CheckCircle className="w-3 h-3" /> 已执行
    </span>
  )
  if (proposal.canceled) return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-gray-500/10 text-gray-500 text-xs border border-gray-500/30">
      <XCircle className="w-3 h-3" /> 已取消
    </span>
  )
  if (proposal.deadline * 1000 < Date.now()) return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-neon-red/10 text-neon-red text-xs border border-neon-red/30">
      已过期
    </span>
  )
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-neon-yellow/10 text-neon-yellow text-xs border border-neon-yellow/30">
      <Clock className="w-3 h-3" /> 进行中
    </span>
  )
}

export default function ProposalsTable({
  proposals,
  isLoading,
  onSelect,
  selectedId,
  className = '',
}: ProposalsTableProps) {
  const [expanded, setExpanded] = useState<number | null>(null)

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-16 bg-cyber-dark rounded-lg animate-pulse" />
        ))}
      </div>
    )
  }

  if (!proposals.length) {
    return (
      <div className="text-center text-gray-500 py-12">
        暂无提案数据
      </div>
    )
  }

  return (
    <div className={`space-y-2 ${className}`}>
      {proposals.map((proposal) => {
        const isExpanded = expanded === proposal.id
        const forVotes = Number(proposal.for_votes)
        const againstVotes = Number(proposal.against_votes)

        return (
          <div
            key={proposal.id}
            className={`bg-cyber-dark/50 rounded-xl border transition-colors overflow-hidden cursor-pointer ${
              selectedId === proposal.id ? 'border-neon-blue/50' : 'border-neon-blue/20 hover:border-neon-blue/40'
            }`}
            onClick={() => {
              setExpanded(isExpanded ? null : proposal.id)
              onSelect?.(proposal)
            }}
          >
            <div className="flex items-start gap-3 p-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-mono text-gray-500">#{proposal.id}</span>
                  <ProposalStatus proposal={proposal} />
                </div>
                <p className="text-gray-200 text-sm font-medium line-clamp-1">
                  {proposal.title || proposal.description}
                </p>
                <div className="flex items-center gap-3 mt-1.5">
                  <AddressDisplay address={proposal.proposer} textClassName="text-[10px]" />
                  <span className="text-xs text-gray-500">
                    赞成 {forVotes.toLocaleString()} / 反对 {againstVotes.toLocaleString()}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="text-right hidden sm:block">
                  <div className="text-xs text-neon-green">+{forVotes.toLocaleString()}</div>
                  <div className="text-xs text-neon-red">-{againstVotes.toLocaleString()}</div>
                </div>
                <button className="p-1 text-gray-500">
                  {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {isExpanded && (
              <div className="px-4 pb-4 border-t border-neon-blue/20 pt-3 space-y-3">
                <p className="text-gray-400 text-sm">{proposal.description}</p>
                <VoteBar forVotes={forVotes} againstVotes={againstVotes} />
                {proposal.deadline > 0 && (
                  <p className="text-xs text-gray-500">
                    截止时间: {new Date(proposal.deadline * 1000).toLocaleString('zh-CN')}
                  </p>
                )}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
