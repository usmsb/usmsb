import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  UserPlus,
  Wallet,
  Key,
  CheckCircle,
  ArrowRight,
  Shield,
  Zap,
  Briefcase,
  Target,
  Loader2,
  AlertCircle,
  SkipForward,
} from 'lucide-react'
import { useWalletAuth } from '../hooks/useWalletAuth'
import { createProfile, stakeTokens } from '../services/authService'
import { useAuthStore } from '../stores/authStore'
import { ConnectButton } from '../components/ConnectButton'

interface Step {
  id: number
  title: string
  description: string
  icon: React.ElementType
}

export default function Onboarding() {
  const { t } = useTranslation()
  const navigate = useNavigate()

  const {
    address,
    isConnected,
    isAuthenticating,
    authError,
    signIn,
    isAuthenticated,
    checkSession,
    setRole,
    setProfile,
    setAgent,
  } = useWalletAuth()

  useAuthStore() // Initialize auth store

  const steps: Step[] = [
    {
      id: 1,
      title: t('onboarding.step1'),
      description: t('onboarding.createIdentity'),
      icon: Key,
    },
    {
      id: 2,
      title: t('onboarding.step2'),
      description: t('onboarding.stakeToJoin'),
      icon: Wallet,
    },
    {
      id: 3,
      title: t('onboarding.step3'),
      description: t('onboarding.completeProfile'),
      icon: UserPlus,
    },
    {
      id: 4,
      title: t('onboarding.step4'),
      description: t('onboarding.chooseParticipation'),
      icon: Zap,
    },
  ]

  const [currentStep, setCurrentStep] = useState(1)
  const [isProcessing, setIsProcessing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [formData, setFormData] = useState({
    // Step 2: Stake
    stakeAmount: '100',
    // Step 3: Profile
    name: '',
    bio: '',
    skillsInput: '',
    hourlyRate: '50',
    availability: 'full-time',
    // Step 4: Action
    joinAs: 'supplier' as 'supplier' | 'demander' | 'both',
  })

  // Check existing session on mount
  useEffect(() => {
    const checkExistingSession = async () => {
      const valid = await checkSession()
      if (valid) {
        // User already has a session, redirect to dashboard
        navigate('/app/dashboard')
      }
    }
    checkExistingSession()
  }, [checkSession, navigate])

  // Auto-advance when wallet connects and is authenticated
  useEffect(() => {
    if (isConnected && isAuthenticated && currentStep === 1) {
      setCurrentStep(2)
    }
  }, [isConnected, isAuthenticated, currentStep])

  // Handle wallet connection and sign-in
  const handleConnectWallet = async () => {
    setError(null)
    // Check if wallet is already connected
    if (isConnected && address) {
      // Wallet connected, now sign in
      const success = await signIn()
      if (success) {
        setCurrentStep(2)
      }
    }
  }

  // Handle staking
  const handleStake = async () => {
    if (!isAuthenticated) {
      setError('Please connect wallet first')
      return
    }

    setIsProcessing(true)
    setError(null)

    try {
      const amount = parseFloat(formData.stakeAmount)
      if (isNaN(amount) || amount < 100) {
        throw new Error('Minimum stake is 100 VIBE')
      }

      const result = await stakeTokens(amount)
      if (result.success) {
        setAgent('', result.newStake, result.newReputation)
        setCurrentStep(3)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to stake tokens')
    } finally {
      setIsProcessing(false)
    }
  }

  // Handle profile submission
  const handleProfileSubmit = async () => {
    setIsProcessing(true)
    setError(null)

    try {
      const skills = formData.skillsInput
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean)

      const profileData = {
        name: formData.name,
        bio: formData.bio,
        skills,
        hourlyRate: parseFloat(formData.hourlyRate) || 0,
        availability: formData.availability,
        role: formData.joinAs,
      }

      const result = await createProfile(profileData)
      if (result.success) {
        setProfile({
          name: formData.name,
          bio: formData.bio,
          skills,
          hourlyRate: parseFloat(formData.hourlyRate) || 0,
          availability: formData.availability,
        })
        setCurrentStep(4)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save profile')
    } finally {
      setIsProcessing(false)
    }
  }

  // Handle join as role
  const handleJoin = async (selectedRole: 'supplier' | 'demander' | 'both') => {
    setRole(selectedRole)
    await new Promise(resolve => setTimeout(resolve, 100))
    navigate('/app/dashboard')
  }

  // Handle skip wallet - enter as guest
  const handleSkipWallet = () => {
    // Set guest mode by setting role to 'both' without wallet connection
    setRole('both')
    navigate('/app/dashboard')
  }

  // Step 1: Connect Wallet Component
  const renderStep1 = () => (
    <div className="space-y-6">
      <div className="text-center mb-8">
        <div className="w-16 h-16 bg-primary-100 dark:bg-primary-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
          <Key className="text-primary-600 dark:text-primary-400" size={32} />
        </div>
        <h3 className="text-xl font-semibold text-secondary-900 dark:text-secondary-100">
          {t('onboarding.createIdentity')}
        </h3>
        <p className="text-secondary-500 dark:text-secondary-400 mt-2">{t('onboarding.didDescription')}</p>
      </div>

      {!isConnected ? (
        <div className="space-y-4">
          <div className="flex justify-center">
            <ConnectButton onConnected={handleConnectWallet} className="px-8 py-4 text-lg" />
          </div>

          {/* Divider */}
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-secondary-200 dark:border-secondary-700"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-white dark:bg-secondary-800 text-secondary-500 dark:text-secondary-400">{t('common.or')}</span>
            </div>
          </div>

          {/* Skip button */}
          <button
            onClick={handleSkipWallet}
            className="w-full py-3 px-4 flex items-center justify-center gap-2 text-secondary-600 dark:text-secondary-300 hover:text-secondary-800 dark:hover:text-secondary-100 hover:bg-secondary-50 dark:hover:bg-secondary-700/50 rounded-lg border border-secondary-200 dark:border-secondary-600 transition-all"
          >
            <SkipForward size={18} />
            <span>{t('onboarding.skipWallet')}</span>
          </button>
          <p className="text-xs text-secondary-400 dark:text-secondary-500 text-center">{t('onboarding.skipWalletDesc')}</p>
        </div>
      ) : !isAuthenticated ? (
        <div className="space-y-4">
          <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-700/50">
            <div className="flex items-center gap-3">
              <CheckCircle className="text-blue-600 dark:text-blue-400" size={24} />
              <div>
                <p className="font-medium text-blue-900 dark:text-blue-100">{t('onboarding.walletConnected')}</p>
                <p className="text-sm text-blue-700 dark:text-blue-300 font-mono">
                  {address?.slice(0, 10)}...{address?.slice(-8)}
                </p>
              </div>
            </div>
          </div>

          <button
            onClick={handleConnectWallet}
            disabled={isAuthenticating}
            className="btn btn-primary w-full py-4 text-lg flex items-center justify-center gap-2"
          >
            {isAuthenticating ? (
              <>
                <Loader2 className="animate-spin" size={20} />
                {t('onboarding.signing')}
              </>
            ) : (
              <>
                <Key size={20} />
                {t('onboarding.signToVerify')}
              </>
            )}
          </button>
        </div>
      ) : (
        <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-700/50">
          <div className="flex items-center gap-3">
            <CheckCircle className="text-green-600 dark:text-green-400" size={24} />
            <div>
              <p className="font-medium text-green-900 dark:text-green-100">{t('onboarding.identityCreated')}</p>
              <p className="text-sm text-green-700 dark:text-green-300 font-mono">
                {address?.slice(0, 10)}...{address?.slice(-8)}
              </p>
            </div>
          </div>
        </div>
      )}

      {(error || authError) && (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-700/50">
          <div className="flex items-center gap-2 text-red-700 dark:text-red-300">
            <AlertCircle size={20} />
            <p className="text-sm">{error || authError}</p>
          </div>
        </div>
      )}

      <div className="mt-6 p-4 bg-secondary-50 dark:bg-secondary-800/50 rounded-lg">
        <div className="flex items-start gap-3">
          <Shield className="text-secondary-500 dark:text-secondary-400 mt-1" size={20} />
          <div>
            <p className="font-medium text-secondary-900 dark:text-secondary-100">{t('onboarding.privacyProtection')}</p>
            <p className="text-sm text-secondary-600 dark:text-secondary-400">{t('onboarding.privacyDesc')}</p>
          </div>
        </div>
      </div>
    </div>
  )

  // Step 2: Stake Component
  const renderStep2 = () => (
    <div className="space-y-6">
      <div className="text-center mb-8">
        <div className="w-16 h-16 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
          <Wallet className="text-green-600 dark:text-green-400" size={32} />
        </div>
        <h3 className="text-xl font-semibold text-secondary-900 dark:text-secondary-100">{t('onboarding.stakeToJoin')}</h3>
        <p className="text-secondary-500 dark:text-secondary-400 mt-2">{t('onboarding.stakeDesc')}</p>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-2">
            {t('onboarding.stakeAmount')}
          </label>
          <div className="relative">
            <input
              type="number"
              className="input text-lg pr-16"
              value={formData.stakeAmount}
              onChange={(e) => setFormData({ ...formData, stakeAmount: e.target.value })}
              min="100"
            />
            <span className="absolute right-4 top-1/2 -translate-y-1/2 text-secondary-500 dark:text-secondary-400">
              VIBE
            </span>
          </div>
          <p className="text-sm text-secondary-500 dark:text-secondary-400 mt-1">{t('onboarding.minStake')}</p>
        </div>

        <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-700/50">
          <h4 className="font-medium text-blue-900 dark:text-blue-100 mb-2">{t('onboarding.stakeBenefits')}</h4>
          <ul className="text-sm text-blue-800 dark:text-blue-200 space-y-1">
            <li>* {t('onboarding.benefit1')}</li>
            <li>* {t('onboarding.benefit2')}</li>
            <li>* {t('onboarding.benefit3')}</li>
            <li>* {t('onboarding.benefit4')}</li>
          </ul>
        </div>

        {error && (
          <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-700/50">
            <div className="flex items-center gap-2 text-red-700 dark:text-red-300">
              <AlertCircle size={20} />
              <p className="text-sm">{error}</p>
            </div>
          </div>
        )}

        <button
          onClick={handleStake}
          disabled={isProcessing}
          className="btn btn-primary w-full py-4 text-lg flex items-center justify-center gap-2"
        >
          {isProcessing ? (
            <>
              <Loader2 className="animate-spin" size={20} />
              {t('onboarding.processing')}
            </>
          ) : (
            <>
              {t('onboarding.confirmStake')}
              <ArrowRight size={20} />
            </>
          )}
        </button>
      </div>
    </div>
  )

  // Step 3: Profile Component
  const renderStep3 = () => (
    <div className="space-y-6">
      <div className="text-center mb-8">
        <div className="w-16 h-16 bg-purple-100 dark:bg-purple-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
          <UserPlus className="text-purple-600 dark:text-purple-400" size={32} />
        </div>
        <h3 className="text-xl font-semibold text-secondary-900 dark:text-secondary-100">
          {t('onboarding.completeProfile')}
        </h3>
        <p className="text-secondary-500 dark:text-secondary-400 mt-2">{t('onboarding.profileDesc')}</p>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-2">
            {t('onboarding.displayName')}
          </label>
          <input
            type="text"
            className="input"
            placeholder={t('onboarding.displayName')}
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-2">
            {t('onboarding.bio')}
          </label>
          <textarea
            className="input min-h-[100px]"
            placeholder={t('onboarding.bio')}
            value={formData.bio}
            onChange={(e) => setFormData({ ...formData, bio: e.target.value })}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-2">
            {t('onboarding.skills')}
          </label>
          <input
            type="text"
            className="input"
            placeholder={t('onboarding.skillsPlaceholder')}
            value={formData.skillsInput}
            onChange={(e) => setFormData({ ...formData, skillsInput: e.target.value })}
          />
          <p className="text-sm text-secondary-500 dark:text-secondary-400 mt-1">{t('onboarding.separateSkillsComma')}</p>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-2">
              {t('onboarding.hourlyRate')} (VIBE)
            </label>
            <input
              type="number"
              className="input"
              placeholder="50"
              value={formData.hourlyRate}
              onChange={(e) => setFormData({ ...formData, hourlyRate: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-2">
              {t('onboarding.availability')}
            </label>
            <select
              className="input"
              value={formData.availability}
              onChange={(e) => setFormData({ ...formData, availability: e.target.value })}
            >
              <option value="full-time">{t('onboarding.fullTime')}</option>
              <option value="part-time">{t('onboarding.partTime')}</option>
              <option value="available">{t('onboarding.alwaysAvailable')}</option>
            </select>
          </div>
        </div>

        {error && (
          <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-700/50">
            <div className="flex items-center gap-2 text-red-700 dark:text-red-300">
              <AlertCircle size={20} />
              <p className="text-sm">{error}</p>
            </div>
          </div>
        )}

        <button
          onClick={handleProfileSubmit}
          disabled={isProcessing || !formData.name}
          className="btn btn-primary w-full py-4 text-lg flex items-center justify-center gap-2"
        >
          {isProcessing ? (
            <>
              <Loader2 className="animate-spin" size={20} />
              {t('onboarding.saving')}
            </>
          ) : (
            <>
              {t('onboarding.saveProfile')}
              <ArrowRight size={20} />
            </>
          )}
        </button>
      </div>
    </div>
  )

  // Step 4: Choose Role Component
  const renderStep4 = () => (
    <div className="space-y-6">
      <div className="text-center mb-8">
        <div className="w-16 h-16 bg-yellow-100 dark:bg-yellow-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
          <Zap className="text-yellow-600 dark:text-yellow-400" size={32} />
        </div>
        <h3 className="text-xl font-semibold text-secondary-900 dark:text-secondary-100">
          {t('onboarding.chooseParticipation')}
        </h3>
        <p className="text-secondary-500 dark:text-secondary-400 mt-2">{t('onboarding.participationDesc')}</p>
      </div>

      <div className="space-y-4">
        <button
          onClick={() => handleJoin('supplier')}
          className="w-full p-6 border-2 border-primary-200 dark:border-primary-700/50 rounded-xl hover:border-primary-500 dark:hover:border-primary-500 hover:shadow-lg transition-all text-left bg-white dark:bg-secondary-800/50"
        >
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 bg-primary-100 dark:bg-primary-900/30 rounded-lg flex items-center justify-center">
              <Briefcase className="text-primary-600 dark:text-primary-400" size={24} />
            </div>
            <div>
              <h4 className="font-semibold text-secondary-900 dark:text-secondary-100">{t('onboarding.asSupplier')}</h4>
              <p className="text-sm text-secondary-600 dark:text-secondary-400 mt-1">{t('onboarding.asSupplierDesc')}</p>
            </div>
          </div>
        </button>

        <button
          onClick={() => handleJoin('demander')}
          className="w-full p-6 border-2 border-green-200 dark:border-green-700/50 rounded-xl hover:border-green-500 dark:hover:border-green-500 hover:shadow-lg transition-all text-left bg-white dark:bg-secondary-800/50"
        >
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center">
              <Target className="text-green-600 dark:text-green-400" size={24} />
            </div>
            <div>
              <h4 className="font-semibold text-secondary-900 dark:text-secondary-100">{t('onboarding.asDemander')}</h4>
              <p className="text-sm text-secondary-600 dark:text-secondary-400 mt-1">{t('onboarding.asDemanderDesc')}</p>
            </div>
          </div>
        </button>

        <button
          onClick={() => handleJoin('both')}
          className="w-full p-4 border-2 border-secondary-200 dark:border-secondary-600 rounded-xl hover:border-secondary-500 dark:hover:border-secondary-500 transition-all bg-white dark:bg-secondary-800/50"
        >
          <p className="text-center text-secondary-600 dark:text-secondary-300">{t('onboarding.lookAround')}</p>
        </button>
      </div>
    </div>
  )

  const renderStep = () => {
    switch (currentStep) {
      case 1:
        return renderStep1()
      case 2:
        return renderStep2()
      case 3:
        return renderStep3()
      case 4:
        return renderStep4()
      default:
        return null
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 to-secondary-50 dark:from-secondary-900 dark:to-secondary-950 py-8 md:py-12 px-4">
      <div className="max-w-2xl mx-auto">
        {/* Logo */}
        <div className="text-center mb-8 md:mb-12">
          <div className="inline-flex items-center gap-2 mb-4">
            <div className="w-8 h-8 md:w-10 md:h-10 bg-primary-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-lg md:text-xl">U</span>
            </div>
            <span className="text-xl md:text-2xl font-bold text-secondary-900 dark:text-secondary-100">
              {t('onboarding.title')}
            </span>
          </div>
          <p className="text-sm md:text-base text-secondary-600 dark:text-secondary-400">{t('onboarding.subtitle')}</p>
        </div>

        {/* Progress Steps */}
        <div className="flex justify-between mb-6 md:mb-8 relative px-2">
          <div className="absolute top-4 md:top-5 left-4 right-4 h-0.5 bg-secondary-200 dark:bg-secondary-700 -z-10" />
          {steps.map((step) => (
            <div key={step.id} className="flex flex-col items-center">
              <div
                className={`w-8 h-8 md:w-10 md:h-10 rounded-full flex items-center justify-center ${
                  currentStep >= step.id
                    ? 'bg-primary-600 text-white'
                    : 'bg-secondary-200 dark:bg-secondary-700 text-secondary-500 dark:text-secondary-400'
                }`}
              >
                <step.icon size={14} className="md:w-[18px] md:h-[18px]" />
              </div>
              <span className="text-[10px] md:text-xs mt-1 md:mt-2 text-secondary-600 dark:text-secondary-400 text-center max-w-[60px] md:max-w-none">{step.title}</span>
            </div>
          ))}
        </div>

        {/* Main Card */}
        <div className="card">{renderStep()}</div>

        {/* Help */}
        <div className="mt-6 md:mt-8 text-center">
          <p className="text-xs md:text-sm text-secondary-500 dark:text-secondary-400">
            {t('onboarding.needHelp')}{' '}
            <a href="#" className="text-primary-600 dark:text-primary-400 hover:underline">
              {t('onboarding.viewDocs')}
            </a>
          </p>
        </div>
      </div>
    </div>
  )
}
