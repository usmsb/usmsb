import { useState } from 'react'
import { useAccount, useReadContract, useWriteContract, useWaitForTransactionReceipt } from 'wagmi'
import { Scale, ThumbsUp, ThumbsDown, Clock, CheckCircle, XCircle, Loader2, RefreshCw } from 'lucide-react'
import { VIBGOVERNANCE_ABI, VIBGOVERNANCE_ADDRESS } from '@/data/contracts'
import { useAppStore } from '@/store'
import clsx from 'clsx'

interface ProposalInfo {
  id: number
  proposer: `0x${string}`
  title: string
  description: string
  forVotes: bigint
  againstVotes: bigint
  startTime: bigint
  endTime: bigint
  executed: boolean
  cancelled: boolean
}

export function GovernancePanel() {
  const { address, isConnected } = useAccount()
  const { theme } = useAppStore()
  const isDark = theme === 'dark'

  const [selectedProposalId, setSelectedProposalId] = useState<number | null>(null)
  const [isVoting, setIsVoting] = useState(false)

  // Read total proposal count via getProposalCount() (proposalCount is a per-address mapping)
  const { data: proposalCount, isLoading: isCountLoading, refetch: refetchCount } = useReadContract({
    address: VIBGOVERNANCE_ADDRESS,
    abi: VIBGOVERNANCE_ABI,
    functionName: 'getProposalCount',
  })

  // Read user's voting power
  const { data: votingPower } = useReadContract({
    address: VIBGOVERNANCE_ADDRESS,
    abi: VIBGOVERNANCE_ABI,
    functionName: 'getVotes',
    args: [address!],
    query: { enabled: isConnected && !!address },
  })

  // Write contract for voting
  const { data: writeData, writeContract, isPending: isWritePending } = useWriteContract()
  const { isLoading: isConfirming, isSuccess: isConfirmed } = useWaitForTransactionReceipt({
    hash: writeData,
  })

  // Get proposals (last 5)
  const proposals: ProposalInfo[] = []
  const count = Number(proposalCount ?? 0)
  for (let i = Math.max(1, count - 4); i <= count; i++) {
    // We'll read each proposal individually via hook
    proposals.push({ id: i } as ProposalInfo)
  }

  // Read a specific proposal
  const readProposal = (proposalId: number) => {
    return useReadContract({
      address: VIBGOVERNANCE_ADDRESS,
      abi: VIBGOVERNANCE_ABI,
      functionName: 'getProposal',
      args: [BigInt(proposalId)],
      query: { enabled: proposalId > 0 && proposalId <= count },
    })
  }

  // Vote function
  const handleVote = async (proposalId: number, support: boolean) => {
    try {
      setIsVoting(true)
      writeContract({
        address: VIBGOVERNANCE_ADDRESS,
        abi: VIBGOVERNANCE_ABI,
        functionName: 'castVote',
        args: [BigInt(proposalId), support],
      })
    } catch (err) {
      console.error('Failed to vote:', err)
    } finally {
      setIsVoting(false)
    }
  }

  const formatVotes = (votes: bigint) => {
    const num = Number(votes) / 1e18
    if (num >= 1e6) return `${(num / 1e6).toFixed(1)}M`
    if (num >= 1e3) return `${(num / 1e3).toFixed(1)}K`
    return num.toFixed(0)
  }

  const getStatusIcon = (proposal: ProposalInfo) => {
    if (proposal.executed) return <CheckCircle className="text-green-500" size={16} />
    if (proposal.cancelled) return <XCircle className="text-red-500" size={16} />
    const now = BigInt(Math.floor(Date.now() / 1000))
    if (now < proposal.endTime) return <Clock className="text-blue-500" size={16} />
    return <CheckCircle className="text-green-500" size={16} />
  }

  const getStatusText = (proposal: ProposalInfo) => {
    if (proposal.executed) return 'Passed'
    if (proposal.cancelled) return 'Rejected'
    const now = BigInt(Math.floor(Date.now() / 1000))
    if (now < proposal.endTime) return 'Active'
    return 'Ended'
  }

  const getVotingPower = () => {
    if (!votingPower) return '0'
    return formatVotes(votingPower as bigint)
  }

  if (!isConnected) {
    return (
      <div className={clsx(
        'card',
        isDark && 'border-neon-blue/20'
      )}>
        <div className="flex items-center gap-3 mb-4">
          <div className={clsx(
            'w-10 h-10 rounded-lg flex items-center justify-center',
            isDark ? 'bg-purple-900/30' : 'bg-purple-50'
          )}>
            <Scale size={20} className={isDark ? 'text-purple-400' : 'text-purple-500'} />
          </div>
          <div>
            <h3 className={clsx(
              'font-semibold',
              isDark ? 'text-gray-100' : 'text-gray-900'
            )}>Governance</h3>
            <p className={clsx(
              'text-sm',
              isDark ? 'text-gray-400' : 'text-gray-500'
            )}>Connect wallet to view proposals</p>
          </div>
        </div>
        <div className={clsx(
          'flex items-center justify-center py-6 rounded-lg',
          isDark ? 'bg-cyber-dark/50 border border-gray-700' : 'bg-gray-50 border border-gray-200'
        )}>
          <p className={clsx(
            'text-sm',
            isDark ? 'text-gray-400' : 'text-gray-500'
          )}>Connect wallet to participate in governance</p>
        </div>
      </div>
    )
  }

  return (
    <div className={clsx(
      'card',
      isDark && 'border-neon-purple/20'
    )}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className={clsx(
            'w-10 h-10 rounded-lg flex items-center justify-center',
            isDark ? 'bg-purple-900/30' : 'bg-purple-50'
          )}>
            <Scale size={20} className={isDark ? 'text-purple-400' : 'text-purple-500'} />
          </div>
          <div>
            <h3 className={clsx(
              'font-semibold',
              isDark ? 'text-gray-100' : 'text-gray-900'
            )}>Governance</h3>
            <p className={clsx(
              'text-sm',
              isDark ? 'text-gray-400' : 'text-gray-500'
            )}>Vote on proposals</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className={clsx(
            'text-sm',
            isDark ? 'text-neon-purple' : 'text-purple-600'
          )}>
            {getVotingPower()} VP
          </span>
          <button
            onClick={() => refetchCount()}
            className={clsx(
              'p-1.5 rounded-lg transition-colors',
              isDark ? 'hover:bg-neon-purple/10 text-gray-400' : 'hover:bg-purple-50 text-gray-500'
            )}
          >
            <RefreshCw size={14} />
          </button>
        </div>
      </div>

      {/* Proposals list */}
      {isCountLoading ? (
        <div className="flex items-center justify-center py-6">
          <Loader2 className={clsx(
            'w-5 h-5 animate-spin',
            isDark ? 'text-neon-purple' : 'text-purple-500'
          )} />
        </div>
      ) : count === 0 ? (
        <div className={clsx(
          'flex items-center justify-center py-6 rounded-lg',
          isDark ? 'bg-cyber-dark/50' : 'bg-gray-50'
        )}>
          <p className={clsx(
            'text-sm',
            isDark ? 'text-gray-400' : 'text-gray-500'
          )}>No proposals yet</p>
        </div>
      ) : (
        <div className="space-y-3">
          {proposals.map((p) => {
            const { data: proposal } = readProposal(p.id)
            if (!proposal) return null
            const [proposer, title, description, forVotes, againstVotes, startTime, endTime, executed, cancelled] = proposal as any

            const totalVotes = forVotes + againstVotes
            const forPercent = totalVotes > 0 ? (Number(forVotes) / Number(totalVotes)) * 100 : 0
            const isActive = !executed && !cancelled && BigInt(Math.floor(Date.now() / 1000)) < endTime

            return (
              <div
                key={p.id}
                className={clsx(
                  'p-3 rounded-lg border transition-colors',
                  isDark
                    ? 'bg-cyber-dark/30 border-gray-700 hover:border-neon-purple/30'
                    : 'bg-gray-50 border-gray-200 hover:border-purple-200'
                )}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    {getStatusIcon({ executed, cancelled, startTime, endTime } as ProposalInfo)}
                    <span className={clsx(
                      'text-sm font-medium',
                      isDark ? 'text-gray-200' : 'text-gray-800'
                    )}>
                      #{p.id} {String(title || 'Proposal').slice(0, 40)}
                    </span>
                  </div>
                  <span className={clsx(
                    'px-2 py-0.5 rounded-full text-xs font-medium',
                    isDark
                      ? executed
                        ? 'bg-green-900/30 text-green-400'
                        : cancelled
                          ? 'bg-red-900/30 text-red-400'
                          : 'bg-blue-900/30 text-blue-400'
                      : executed
                        ? 'bg-green-100 text-green-700'
                        : cancelled
                          ? 'bg-red-100 text-red-700'
                          : 'bg-blue-100 text-blue-700'
                  )}>
                    {getStatusText({ executed, cancelled, startTime, endTime } as ProposalInfo)}
                  </span>
                </div>

                {/* Vote bar */}
                <div className="mb-2">
                  <div className={clsx(
                    'w-full rounded-full h-1.5 overflow-hidden',
                    isDark ? 'bg-gray-700' : 'bg-gray-200'
                  )}>
                    <div
                      className="h-full bg-green-500 rounded-full transition-all"
                      style={{ width: `${forPercent}%` }}
                    />
                  </div>
                  <div className="flex justify-between mt-1 text-xs">
                    <span className={clsx(
                      'flex items-center gap-1',
                      isDark ? 'text-green-400' : 'text-green-600'
                    )}>
                      <ThumbsUp size={10} />
                      {formatVotes(forVotes)}
                    </span>
                    <span className={clsx(
                      'flex items-center gap-1',
                      isDark ? 'text-red-400' : 'text-red-600'
                    )}>
                      <ThumbsDown size={10} />
                      {formatVotes(againstVotes)}
                    </span>
                  </div>
                </div>

                {/* Vote buttons */}
                {isActive && (
                  <div className="flex gap-2 mt-2">
                    <button
                      onClick={() => handleVote(p.id, true)}
                      disabled={isVoting || isWritePending}
                      className={clsx(
                        'flex-1 flex items-center justify-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium transition-all',
                        'bg-green-500/10 text-green-600 hover:bg-green-500/20',
                        isDark && 'hover:shadow-[0_0_10px_rgba(34,197,94,0.3)]',
                        (isVoting || isWritePending) && 'opacity-50 cursor-not-allowed'
                      )}
                    >
                      {isVoting ? <Loader2 size={12} className="animate-spin" /> : <ThumbsUp size={12} />}
                      For
                    </button>
                    <button
                      onClick={() => handleVote(p.id, false)}
                      disabled={isVoting || isWritePending}
                      className={clsx(
                        'flex-1 flex items-center justify-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium transition-all',
                        'bg-red-500/10 text-red-600 hover:bg-red-500/20',
                        isDark && 'hover:shadow-[0_0_10px_rgba(239,68,68,0.3)]',
                        (isVoting || isWritePending) && 'opacity-50 cursor-not-allowed'
                      )}
                    >
                      {isVoting ? <Loader2 size={12} className="animate-spin" /> : <ThumbsDown size={12} />}
                      Against
                    </button>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* Confirmation status */}
      {isConfirmed && (
        <div className={clsx(
          'mt-3 p-2 rounded-lg text-sm text-center',
          isDark ? 'bg-green-900/20 text-green-400' : 'bg-green-50 text-green-700'
        )}>
          Vote confirmed!
        </div>
      )}
    </div>
  )
}

export default GovernancePanel
