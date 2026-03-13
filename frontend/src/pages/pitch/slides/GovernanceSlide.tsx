import { useTranslation } from 'react-i18next'
import { SlideContainer, SlideContent, SlideTitle } from '../components/SlideContainer'
import { SlideProps } from '../types'
import { Scale, Coins, Award, Users } from 'lucide-react'

export function GovernanceSlide({ isActive, direction }: SlideProps) {
  const { t } = useTranslation()

  const layers = [
    {
      icon: <Coins className="w-8 h-8" />,
      title: t('pitch.gov.layer1Title', '资本权重层'),
      desc: t('pitch.gov.layer1Desc', '基于质押金额，单地址最大 10%'),
      power: '40%',
      color: 'from-primary-500 to-purple-500'
    },
    {
      icon: <Award className="w-8 h-8" />,
      title: t('pitch.gov.layer2Title', '生产权重层'),
      desc: t('pitch.gov.layer2Desc', '基于贡献积分，单地址最大 15%'),
      power: '30%',
      color: 'from-purple-500 to-cyan-500'
    },
    {
      icon: <Users className="w-8 h-8" />,
      title: t('pitch.gov.layer3Title', '社区共识层'),
      desc: t('pitch.gov.layer3Desc', '一人一票，占总投票权 10%'),
      power: '30%',
      color: 'from-cyan-500 to-green-500'
    }
  ]

  return (
    <SlideContainer isActive={isActive} direction={direction}>
      <SlideContent>
        <SlideTitle
          subtitle={t('pitch.gov.subtitle', '三层治理结构，平衡资本、贡献与社区')}
        >
          {t('pitch.gov.title', '治理机制')}
        </SlideTitle>

        <div className="flex justify-center mb-8">
          <div className="relative w-48 h-48">
            <div className="absolute inset-0 rounded-full border-4 border-primary-500/30 animate-pulse" />
            <div className="absolute inset-4 rounded-full border-4 border-purple-500/30 animate-pulse" style={{ animationDelay: '0.5s' }} />
            <div className="absolute inset-8 rounded-full border-4 border-cyan-500/30 animate-pulse" style={{ animationDelay: '1s' }} />
            <div className="absolute inset-0 flex items-center justify-center">
              <Scale className="w-12 h-12 text-primary-400" />
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {layers.map((layer, index) => (
            <div
              key={index}
              className="p-6 rounded-2xl bg-white/5 border border-white/10 hover:border-primary-400/30 transition-all"
            >
              <div className={`w-14 h-14 rounded-xl bg-gradient-to-br ${layer.color} flex items-center justify-center text-white mb-4`}>
                {layer.icon}
              </div>
              <h3 className="font-semibold mb-2">{layer.title}</h3>
              <p className="text-slate-400 text-sm mb-4">{layer.desc}</p>
              <div className="flex items-center justify-between">
                <span className="text-slate-500 text-sm">{t('pitch.gov.votingPower', '投票权重')}</span>
                <span className="text-2xl font-bold text-primary-400 font-['Orbitron']">{layer.power}</span>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-8 p-6 rounded-2xl bg-gradient-to-br from-primary-500/10 to-purple-500/10 border border-primary-400/20">
          <h4 className="font-semibold mb-4 text-center">{t('pitch.gov.processTitle', '治理流程')}</h4>
          <div className="flex flex-wrap items-center justify-center gap-3 text-sm">
            <span className="px-4 py-2 rounded-lg bg-white/5">{t('pitch.gov.step1', '发起提案')}</span>
            <span className="text-slate-500">→</span>
            <span className="px-4 py-2 rounded-lg bg-white/5">{t('pitch.gov.step2', '社区讨论')}</span>
            <span className="text-slate-500">→</span>
            <span className="px-4 py-2 rounded-lg bg-white/5">{t('pitch.gov.step3', '投票决策')}</span>
            <span className="text-slate-500">→</span>
            <span className="px-4 py-2 rounded-lg bg-white/5">{t('pitch.gov.step4', '执行结果')}</span>
          </div>
        </div>
      </SlideContent>
    </SlideContainer>
  )
}
