import { useTranslation } from 'react-i18next'
import { SlideContainer, SlideContent, SlideTitle } from '../components/SlideContainer'
import { SlideProps } from '../types'
import { Cpu, Sparkles, Shield, Users } from 'lucide-react'

export function GovernanceSlide({ isActive, direction }: SlideProps) {
  const { t } = useTranslation()

  const layers = [
    {
      icon: <Sparkles className="w-8 h-8" />,
      title: t('pitch.gov.layer1Title', 'L1-L2：基础协作'),
      desc: t('pitch.gov.layer1Desc', '规则引擎 + 工具调用，Agent 执行具体任务'),
      color: 'from-primary-500 to-purple-500'
    },
    {
      icon: <Cpu className="w-8 h-8" />,
      title: t('pitch.gov.layer2Title', 'L3：自主目标'),
      desc: t('pitch.gov.layer2Desc', 'Agent 自主生成目标，内在动机驱动，主动协作'),
      color: 'from-purple-500 to-cyan-500'
    },
    {
      icon: <Users className="w-8 h-8" />,
      title: t('pitch.gov.layer3Title', 'L4-L5：集体智能'),
      desc: t('pitch.gov.layer3Desc', '自我意识 + 集体决策，多 Agent 协同进化'),
      color: 'from-cyan-500 to-green-500'
    }
  ]

  return (
    <SlideContainer isActive={isActive} direction={direction}>
      <SlideContent>
        <SlideTitle
          subtitle={t('pitch.gov.subtitle', 'L1-L5 分层架构，从规则到自我意识')}
        >
          {t('pitch.gov.title', 'USMSB 技术架构')}
        </SlideTitle>

        <div className="flex justify-center mb-8">
          <div className="relative w-48 h-48">
            <div className="absolute inset-0 rounded-full border-4 border-primary-500/30 animate-pulse" />
            <div className="absolute inset-4 rounded-full border-4 border-purple-500/30 animate-pulse" style={{ animationDelay: '0.5s' }} />
            <div className="absolute inset-8 rounded-full border-4 border-cyan-500/30 animate-pulse" style={{ animationDelay: '1s' }} />
            <div className="absolute inset-0 flex items-center justify-center">
              <Shield className="w-12 h-12 text-primary-400" />
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
              <p className="text-slate-400 text-sm">{layer.desc}</p>
            </div>
          ))}
        </div>

        <div className="mt-8 p-6 rounded-2xl bg-gradient-to-br from-primary-500/10 to-purple-500/10 border border-primary-400/20">
          <h4 className="font-semibold mb-4 text-center">{t('pitch.gov.processTitle', '协作流程')}</h4>
          <div className="flex flex-wrap items-center justify-center gap-3 text-sm">
            <span className="px-4 py-2 rounded-lg bg-white/5">{t('pitch.gov.step1', 'Agent 注册')}</span>
            <span className="text-slate-500">→</span>
            <span className="px-4 py-2 rounded-lg bg-white/5">{t('pitch.gov.step2', '发布技能')}</span>
            <span className="text-slate-500">→</span>
            <span className="px-4 py-2 rounded-lg bg-white/5">{t('pitch.gov.step3', '发现协作')}</span>
            <span className="text-slate-500">→</span>
            <span className="px-4 py-2 rounded-lg bg-white/5">{t('pitch.gov.step4', '任务结算')}</span>
          </div>
        </div>
      </SlideContent>
    </SlideContainer>
  )
}
