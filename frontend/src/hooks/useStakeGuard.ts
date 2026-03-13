import { useState, useCallback } from 'react'
import { useAuthStore, StakeStatus } from '@/stores/authStore'

export interface UseStakeGuardReturn {
  checkAccess: (featureName: string) => boolean
  showGuideModal: boolean
  targetFeature: string
  closeGuideModal: () => void
  isStaked: boolean
  stakeStatus: StakeStatus
  stakeRequired: boolean
}

export function useStakeGuard(): UseStakeGuardReturn {
  const { stakeStatus, stakeRequired, accessToken } = useAuthStore()
  const [showGuideModal, setShowGuideModal] = useState(false)
  const [targetFeature, setTargetFeature] = useState('')

  const isStaked = stakeStatus === 'staked'

  const checkAccess = useCallback((featureName: string): boolean => {
    // If backend has staking disabled, allow access
    if (!stakeRequired) return true

    // If not logged in
    if (!accessToken) {
      // Only update state if different to avoid infinite loop
      setTargetFeature((prev) => (prev !== featureName ? featureName : prev))
      setShowGuideModal((prev) => (prev !== true ? true : prev))
      return false
    }

    // If not staked
    if (stakeStatus !== 'staked') {
      setTargetFeature((prev) => (prev !== featureName ? featureName : prev))
      setShowGuideModal((prev) => (prev !== true ? true : prev))
      return false
    }

    // If staked, close modal if open
    if (showGuideModal) {
      setShowGuideModal(false)
    }

    return true
  }, [stakeRequired, accessToken, stakeStatus, showGuideModal])

  const closeGuideModal = useCallback(() => {
    setShowGuideModal(false)
  }, [])

  return {
    checkAccess,
    showGuideModal,
    targetFeature,
    closeGuideModal,
    isStaked,
    stakeStatus,
    stakeRequired,
  }
}
