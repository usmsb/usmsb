import { useTranslation } from 'react-i18next'
import { X, Lock, Briefcase, Target, Vote, Shield, ArrowRight } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useAppStore } from '@/store'
import clsx from 'clsx'

interface StakeGuideModalProps {
  isOpen: boolean
  onClose: () => void
  featureName: string
  requiredStake?: number
}

export function StakeGuideModal({
  isOpen,
  onClose,
  featureName,
  requiredStake = 100,
}: StakeGuideModalProps) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { theme } = useAppStore()
  const isDark = theme === 'dark'

  if (!isOpen) return null

  const handleStakeNow = () => {
    onClose()
    navigate('/app/onboarding')
  }

  const benefits = [
    {
      icon: Briefcase,
      title: t('stake.benefit1Title'),
      desc: t('stake.benefit1Desc'),
    },
    {
      icon: Target,
      title: t('stake.benefit2Title'),
      desc: t('stake.benefit2Desc'),
    },
    {
      icon: Shield,
      title: t('stake.benefit3Title'),
      desc: t('stake.benefit3Desc'),
    },
    {
      icon: Vote,
      title: t('stake.benefit4Title'),
      desc: t('stake.benefit4Desc'),
    },
  ]

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div
        className={clsx(
          'relative rounded-2xl shadow-xl max-w-md w-full overflow-hidden',
          // Background - Light/Dark mode (must be mutually exclusive)
          isDark
            ? 'bg-cyber-card border border-neon-blue/30'
            : 'bg-white border border-gray-200'
        )}
      >
        {/* Header */}
        <div
          className={clsx(
            'relative px-6 py-8',
            // Gradient background - Light/Dark mode (must be mutually exclusive)
            isDark
              ? 'bg-gradient-to-r from-neon-blue/20 to-neon-purple/20'
              : 'bg-gradient-to-r from-blue-500 to-blue-600'
          )}
        >
          {/* Cyberpunk border effect */}
          {isDark && (
            <div className="absolute inset-0 border border-neon-blue/30 rounded-t-2xl" />
          )}
          <button
            onClick={onClose}
            className={clsx(
              'absolute top-4 right-4 p-1 rounded-full transition-colors',
              isDark
                ? 'bg-neon-blue/20 text-neon-blue hover:bg-neon-blue/30'
                : 'bg-white/20 text-white hover:bg-white/30'
            )}
          >
            <X size={20} />
          </button>
          <div className="flex items-center gap-3 mb-2">
            <div
              className={clsx(
                'w-12 h-12 rounded-full flex items-center justify-center',
                isDark ? 'bg-neon-blue/20' : 'bg-white/20'
              )}
            >
              <Lock
                size={24}
                className={isDark ? 'text-neon-blue' : 'text-white'}
              />
            </div>
            <div>
              <h2
                className={clsx(
                  'text-xl font-bold',
                  isDark ? 'text-neon-blue font-cyber' : 'text-white'
                )}
              >
                {t('stake.required')}
              </h2>
              <p
                className={clsx(
                  'text-sm',
                  isDark ? 'text-gray-400' : 'text-white/80'
                )}
              >
                {t('stake.toAccess')} {featureName}
              </p>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="px-6 py-6">
          <p
            className={clsx(
              'mb-4',
              isDark ? 'text-gray-300' : 'text-gray-600'
            )}
          >
            {t('stake.description')}
          </p>

          <div
            className={clsx(
              'rounded-lg p-4 mb-6',
              isDark
                ? 'bg-neon-blue/10 border border-neon-blue/30'
                : 'bg-blue-50'
            )}
          >
            <p
              className={clsx(
                'text-sm',
                isDark ? 'text-neon-blue' : 'text-blue-700'
              )}
            >
              {t('stake.minimumRequired')}:
              <span className="font-bold ml-2">{requiredStake} VIBE</span>
            </p>
          </div>

          <h3
            className={clsx(
              'font-semibold mb-3',
              isDark ? 'text-white font-cyber' : 'text-gray-900'
            )}
          >
            {t('stake.benefits')}
          </h3>
          <div className="space-y-3 mb-6">
            {benefits.map((benefit, index) => (
              <div key={index} className="flex items-start gap-3">
                <div
                  className={clsx(
                    'w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0',
                    isDark
                      ? 'bg-neon-purple/20'
                      : 'bg-gray-100'
                  )}
                >
                  <benefit.icon
                    size={16}
                    className={isDark ? 'text-neon-purple' : 'text-gray-600'}
                  />
                </div>
                <div>
                  <p
                    className={clsx(
                      'font-medium text-sm',
                      isDark ? 'text-white' : 'text-gray-900'
                    )}
                  >
                    {benefit.title}
                  </p>
                  <p
                    className={clsx(
                      'text-xs',
                      isDark ? 'text-gray-400' : 'text-gray-500'
                    )}
                  >
                    {benefit.desc}
                  </p>
                </div>
              </div>
            ))}
          </div>

          {/* Actions */}
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className={clsx(
                'flex-1 py-3 px-4 rounded-lg border-2 transition-all',
                isDark
                  ? 'border-neon-blue/30 text-neon-blue hover:bg-neon-blue/10'
                  : 'border-gray-200 text-gray-600 hover:bg-gray-50'
              )}
            >
              {t('stake.later')}
            </button>
            <button
              onClick={handleStakeNow}
              className={clsx(
                'flex-1 py-3 px-4 rounded-lg transition-all flex items-center justify-center gap-2',
                isDark
                  ? 'bg-neon-blue text-black hover:bg-neon-blue/90 font-cyber'
                  : 'bg-blue-600 text-white hover:bg-blue-700'
              )}
            >
              {t('stake.stakeNow')}
              <ArrowRight size={18} />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
