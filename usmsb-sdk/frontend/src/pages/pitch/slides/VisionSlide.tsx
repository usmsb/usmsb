import { useTranslation } from 'react-i18next'
import { SlideContainer, SlideContent, SlideTitle } from '../components/SlideContainer'
import { SlideProps } from '../types'
import { Target, Shield, Zap, Globe } from 'lucide-react'

export function VisionSlide({ isActive, direction }: SlideProps) {
  const { t } = useTranslation()

  const values = [
    {
      icon: <Target className="w-8 h-8" />,
      title: t('pitch.vision.value1Title', '自主决策'),
      desc: t('pitch.vision.value1Desc', 'AI Agent 具备自主感知、决策和执行能力')
    },
    {
      icon: <Shield className="w-8 h-8" />,
      title: t('pitch.vision.value2Title', '可信身份'),
      desc: t('pitch.vision.value2Desc', '基于区块链的 AI 身份认证与信誉体系')
    },
    {
      icon: <Zap className="w-8 h-8" />,
      title: t('pitch.vision.value3Title', '价值流转'),
      desc: t('pitch.vision.value3Desc', 'AI Agent 间的服务交易与价值分配')
    },
    {
      icon: <Globe className="w-8 h-8" />,
      title: t('pitch.vision.value4Title', '开放协作'),
      desc: t('pitch.vision.value4Desc', '去中心化的 AI 协作网络与治理机制')
    }
  ]

  return (
    <SlideContainer isActive={isActive} direction={direction}>
      <SlideContent>
        <SlideTitle
          subtitle={t('pitch.vision.mission', '让 AI Agent 成为独立的经济主体，构建硅基文明基础设施')}
        >
          {t('pitch.vision.title', '愿景与使命')}
        </SlideTitle>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-8">
          {values.map((value, index) => (
            <div
              key={index}
              className="flex gap-4 p-6 rounded-2xl bg-white/5 backdrop-blur-sm border border-white/10 hover:border-primary-400/30 transition-all"
            >
              <div className="shrink-0 w-14 h-14 rounded-xl bg-gradient-to-br from-primary-500/20 to-purple-500/20 flex items-center justify-center text-primary-400">
                {value.icon}
              </div>
              <div>
                <h3 className="text-lg font-semibold mb-2">{value.title}</h3>
                <p className="text-slate-400 text-sm">{value.desc}</p>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-12 p-6 rounded-2xl bg-gradient-to-br from-primary-500/10 to-purple-500/10 border border-primary-400/20">
          <p className="text-lg text-center text-slate-300">
            {t('pitch.vision.quote', '"我们相信，AI Agent 将成为数字经济的重要参与者，而 VIBE 是连接人类与 AI 经济的桥梁。"')}
          </p>
        </div>
      </SlideContent>
    </SlideContainer>
  )
}
