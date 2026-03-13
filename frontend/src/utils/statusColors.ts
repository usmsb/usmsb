// Status color utilities - centralized status-to-color mapping
// Used across multiple pages for consistency

// Agent status colors
export type AgentStatus = 'online' | 'active' | 'offline' | 'inactive' | 'busy'

// Matching opportunity status colors
export type OpportunityStatus =
  | 'discovered'
  | 'contacted'
  | 'negotiating'
  | 'accepted'
  | 'rejected'
  | 'expired'
  | 'pending'
  | 'in_progress'
  | 'agreed'
  | 'timeout'

// Collaboration status colors
export type CollaborationStatus =
  | 'analyzing'
  | 'organizing'
  | 'executing'
  | 'integrating'
  | 'completed'
  | 'failed'
  | 'pending'
  | 'assigned'

// Governance proposal status colors
export type GovernanceStatus = 'passed' | 'rejected' | 'active' | 'voting'

// Simulation status colors
export type SimulationStatus = 'completed' | 'failed' | 'cancelled' | 'running' | 'paused'

// Generic status type
export type Status = AgentStatus | OpportunityStatus | CollaborationStatus | GovernanceStatus | SimulationStatus

// Base color configuration
interface StatusColorConfig {
  bgClass: string
  textClass: string
  darkBgClass: string
  darkTextClass: string
}

// All status color configurations
const statusColorMap: Record<string, StatusColorConfig> = {
  // Agent statuses
  online: {
    bgClass: 'bg-green-100',
    textClass: 'text-green-700',
    darkBgClass: 'dark:bg-green-900/30',
    darkTextClass: 'dark:text-green-400',
  },
  active: {
    bgClass: 'bg-green-100',
    textClass: 'text-green-700',
    darkBgClass: 'dark:bg-green-900/30',
    darkTextClass: 'dark:text-green-400',
  },
  offline: {
    bgClass: 'bg-gray-100',
    textClass: 'text-gray-700',
    darkBgClass: 'dark:bg-secondary-800',
    darkTextClass: 'dark:text-gray-400',
  },
  inactive: {
    bgClass: 'bg-gray-100',
    textClass: 'text-gray-700',
    darkBgClass: 'dark:bg-secondary-800',
    darkTextClass: 'dark:text-gray-400',
  },
  busy: {
    bgClass: 'bg-yellow-100',
    textClass: 'text-yellow-700',
    darkBgClass: 'dark:bg-yellow-900/30',
    darkTextClass: 'dark:text-yellow-400',
  },
  // Opportunity statuses
  discovered: {
    bgClass: 'bg-blue-100',
    textClass: 'text-blue-700',
    darkBgClass: 'dark:bg-blue-900/30',
    darkTextClass: 'dark:text-blue-400',
  },
  contacted: {
    bgClass: 'bg-yellow-100',
    textClass: 'text-yellow-700',
    darkBgClass: 'dark:bg-yellow-900/30',
    darkTextClass: 'dark:text-yellow-400',
  },
  negotiating: {
    bgClass: 'bg-purple-100',
    textClass: 'text-purple-700',
    darkBgClass: 'dark:bg-purple-900/30',
    darkTextClass: 'dark:text-purple-400',
  },
  accepted: {
    bgClass: 'bg-green-100',
    textClass: 'text-green-700',
    darkBgClass: 'dark:bg-green-900/30',
    darkTextClass: 'dark:text-green-400',
  },
  rejected: {
    bgClass: 'bg-red-100',
    textClass: 'text-red-700',
    darkBgClass: 'dark:bg-red-900/30',
    darkTextClass: 'dark:text-red-400',
  },
  expired: {
    bgClass: 'bg-gray-100',
    textClass: 'text-gray-700',
    darkBgClass: 'dark:bg-secondary-800',
    darkTextClass: 'dark:text-gray-400',
  },
  pending: {
    bgClass: 'bg-yellow-100',
    textClass: 'text-yellow-700',
    darkBgClass: 'dark:bg-yellow-900/30',
    darkTextClass: 'dark:text-yellow-400',
  },
  in_progress: {
    bgClass: 'bg-blue-100',
    textClass: 'text-blue-700',
    darkBgClass: 'dark:bg-blue-900/30',
    darkTextClass: 'dark:text-blue-400',
  },
  agreed: {
    bgClass: 'bg-green-100',
    textClass: 'text-green-700',
    darkBgClass: 'dark:bg-green-900/30',
    darkTextClass: 'dark:text-green-400',
  },
  timeout: {
    bgClass: 'bg-red-100',
    textClass: 'text-red-700',
    darkBgClass: 'dark:bg-red-900/30',
    darkTextClass: 'dark:text-red-400',
  },
  // Collaboration statuses
  analyzing: {
    bgClass: 'bg-blue-100',
    textClass: 'text-blue-700',
    darkBgClass: 'dark:bg-blue-900/30',
    darkTextClass: 'dark:text-blue-400',
  },
  organizing: {
    bgClass: 'bg-indigo-100',
    textClass: 'text-indigo-700',
    darkBgClass: 'dark:bg-indigo-900/30',
    darkTextClass: 'dark:text-indigo-400',
  },
  executing: {
    bgClass: 'bg-purple-100',
    textClass: 'text-purple-700',
    darkBgClass: 'dark:bg-purple-900/30',
    darkTextClass: 'dark:text-purple-400',
  },
  integrating: {
    bgClass: 'bg-cyan-100',
    textClass: 'text-cyan-700',
    darkBgClass: 'dark:bg-cyan-900/30',
    darkTextClass: 'dark:text-cyan-400',
  },
  completed: {
    bgClass: 'bg-green-100',
    textClass: 'text-green-700',
    darkBgClass: 'dark:bg-green-900/30',
    darkTextClass: 'dark:text-green-400',
  },
  failed: {
    bgClass: 'bg-red-100',
    textClass: 'text-red-700',
    darkBgClass: 'dark:bg-red-900/30',
    darkTextClass: 'dark:text-red-400',
  },
  assigned: {
    bgClass: 'bg-blue-100',
    textClass: 'text-blue-700',
    darkBgClass: 'dark:bg-blue-900/30',
    darkTextClass: 'dark:text-blue-400',
  },
  // Governance statuses
  passed: {
    bgClass: 'bg-green-100',
    textClass: 'text-green-700',
    darkBgClass: 'dark:bg-green-900/30',
    darkTextClass: 'dark:text-green-400',
  },
  voting: {
    bgClass: 'bg-purple-100',
    textClass: 'text-purple-700',
    darkBgClass: 'dark:bg-purple-900/30',
    darkTextClass: 'dark:text-purple-400',
  },
  // Simulation statuses
  running: {
    bgClass: 'bg-blue-100',
    textClass: 'text-blue-700',
    darkBgClass: 'dark:bg-blue-900/30',
    darkTextClass: 'dark:text-blue-400',
  },
  cancelled: {
    bgClass: 'bg-gray-100',
    textClass: 'text-gray-700',
    darkBgClass: 'dark:bg-secondary-800',
    darkTextClass: 'dark:text-gray-400',
  },
  paused: {
    bgClass: 'bg-yellow-100',
    textClass: 'text-yellow-700',
    darkBgClass: 'dark:bg-yellow-900/30',
    darkTextClass: 'dark:text-yellow-400',
  },
}

// Default fallback colors
const defaultColor: StatusColorConfig = {
  bgClass: 'bg-gray-100',
  textClass: 'text-gray-700',
  darkBgClass: 'dark:bg-secondary-800',
  darkTextClass: 'dark:text-gray-400',
}

/**
 * Get Tailwind CSS classes for a given status
 * @param status - The status string to look up
 * @returns Combined Tailwind CSS class string
 */
export function getStatusColor(status: string): string {
  const config = statusColorMap[status] || defaultColor
  return `${config.bgClass} ${config.textClass} ${config.darkBgClass} ${config.darkTextClass}`
}

/**
 * Get background color class only
 */
export function getStatusBgColor(status: string): string {
  const config = statusColorMap[status] || defaultColor
  return `${config.bgClass} ${config.darkBgClass}`
}

/**
 * Get text color class only
 */
export function getStatusTextColor(status: string): string {
  const config = statusColorMap[status] || defaultColor
  return `${config.textClass} ${config.darkTextClass}`
}

/**
 * Get status color config object
 */
export function getStatusColorConfig(status: string): StatusColorConfig {
  return statusColorMap[status] || defaultColor
}

/**
 * Get match score color based on score value (0-1)
 * @param score - Score between 0 and 1
 * @returns Color class string
 */
export function getMatchScoreColor(score: number): string {
  if (score >= 0.8) {
    return 'text-green-500 dark:text-green-400'
  }
  if (score >= 0.6) {
    return 'text-blue-500 dark:text-blue-400'
  }
  if (score >= 0.4) {
    return 'text-yellow-500 dark:text-yellow-400'
  }
  return 'text-red-500 dark:text-red-400'
}

/**
 * Get match score background color
 */
export function getMatchScoreBgColor(score: number): string {
  if (score >= 0.8) {
    return 'bg-green-500/20 dark:bg-green-500/10'
  }
  if (score >= 0.6) {
    return 'bg-blue-500/20 dark:bg-blue-500/10'
  }
  if (score >= 0.4) {
    return 'bg-yellow-500/20 dark:bg-yellow-500/10'
  }
  return 'bg-red-500/20 dark:bg-red-500/10'
}

/**
 * Get reputation color based on value (0-100)
 * @param reputation - Reputation score between 0 and 100
 * @returns Color class string
 */
export function getReputationColor(reputation: number): string {
  if (reputation >= 80) {
    return 'text-green-500 dark:text-green-400'
  }
  if (reputation >= 60) {
    return 'text-blue-500 dark:text-blue-400'
  }
  if (reputation >= 40) {
    return 'text-yellow-500 dark:text-yellow-400'
  }
  return 'text-red-500 dark:text-red-400'
}
