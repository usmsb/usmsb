import { useTranslation } from 'react-i18next'
import { X, Lock, Briefcase, Target, Vote, Shield, ArrowRight } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
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

  if (!isOpen) return null

  const handleStakeNow = () => {
    onClose()
    navigate('/app/onboarding')
  }

  const benefits = [
    {
      icon: Briefcase,
      title: t('stake.benefit1Title', '发布服务'),
      desc: t('stake.benefit1Desc', '向市场提供您的专业技能'),
    },
    {
      icon: Target,
      title: t('stake.benefit2Title', '发布需求'),
      desc: t('stake.benefit2Desc', '发布任务需求找到合适的服务商'),
    },
    {
      icon: Shield,
      title: t('stake.benefit3Title', '注册 Agent'),
      desc: t('stake.benefit3Desc', '注册您的 AI Agent 参与网络协作'),
    },
    {
      icon: Vote,
      title: t('stake.benefit4Title', '治理投票'),
      desc: t('stake.benefit4Desc', '参与平台治理决策'),
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
      <div className="relative bg-white dark:bg-secondary-800 rounded-2xl shadow-xl max-w-md w-full overflow-hidden">
        {/* Header */}
        <div className="relative bg-gradient-to-r from-primary-500 to-primary-600 px-6 py-8 text-white">
          <button
            onClick={onClose}
            className="absolute top-4 right-4 p-1 rounded-full bg-white/20 hover:bg-white/30 transition-colors"
          >
            <X size={20} />
          </button>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-12 h-12 rounded-full bg-white/20 flex items-center justify-center">
              <Lock size={24} />
            </div>
            <div>
              <h2 className="text-xl font-bold">
                {t('stake.required', '需要质押')}
              </h2>
              <p className="text-white/80 text-sm">
                {t('stake.toAccess', '访问')} {featureName}
              </p>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="px-6 py-6">
          <p className="text-secondary-600 dark:text-secondary-300 mb-4">
            {t('stake.description', '质押 VIBE 代币以解锁平台全部功能。质押不仅是参与门槛，更是对网络安全的承诺。')}
          </p>

          <div className="bg-primary-50 dark:bg-primary-900/20 rounded-lg p-4 mb-6">
            <p className="text-sm text-primary-700 dark:text-primary-300">
              {t('stake.minimumRequired', '最低质押金额')}:
              <span className="font-bold ml-2">{requiredStake} VIBE</span>
            </p>
          </div>

          <h3 className="font-semibold text-secondary-900 dark:text-secondary-100 mb-3">
            {t('stake.benefits', '质押权益')}
          </h3>
          <div className="space-y-3 mb-6">
            {benefits.map((benefit, index) => (
              <div key={index} className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-secondary-100 dark:bg-secondary-700 flex items-center justify-center flex-shrink-0">
                  <benefit.icon size={16} className="text-primary-600 dark:text-primary-400" />
                </div>
                <div>
                  <p className="font-medium text-secondary-900 dark:text-secondary-100 text-sm">
                    {benefit.title}
                  </p>
                  <p className="text-xs text-secondary-500 dark:text-secondary-400">
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
                'border-secondary-200 dark:border-secondary-600',
                'text-secondary-600 dark:text-secondary-300',
                'hover:bg-secondary-50 dark:hover:bg-secondary-700'
              )}
            >
              {t('common.later', '稍后再说')}
            </button>
            <button
              onClick={handleStakeNow}
              className={clsx(
                'flex-1 py-3 px-4 rounded-lg transition-all',
                'bg-primary-600 text-white',
                'hover:bg-primary-700',
                'flex items-center justify-center gap-2'
              )}
            >
              {t('stake.stakeNow', '立即质押')}
              <ArrowRight size={18} />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
