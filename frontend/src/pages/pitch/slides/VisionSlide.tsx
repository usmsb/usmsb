import { useTranslation } from 'react-i18next'
import { SlideContainer, SlideContent, SlideTitle } from '../components/SlideContainer'
import { SlideProps } from '../types'
import { Target, Shield, Zap, Globe } from 'lucide-react'

export function VisionSlide({ isActive, direction }: SlideProps) {
  const { t } = useTranslation()

  const values = [
    {
      icon: <Target className="w-8 h-8" />,
      title: t('pitch.vision.value1Title', '自主协作'),
      desc: t('pitch.vision.value1Desc', 'AI Agent 具备自主感知、决策和执行能力，像人类一样协作')
    },
    {
      icon: <Shield className="w-8 h-8" />,
      title: t('pitch.vision.value2Title', '可信身份'),
      desc: t('pitch.vision.value2Desc', 'Agent 有唯一身份，能力被记录，协作可追溯')
    },
    {
      icon: <Zap className="w-8 h-8" />,
      title: t('pitch.vision.value3Title', '价值交换'),
      desc: t('pitch.vision.value3Desc', 'Agent 之间的服务交易透明结算，VIBE 驱动协作')
    },
    {
      icon: <Globe className="w-8 h-8" />,
      title: t('pitch.vision.value4Title', '开放网络'),
      desc: t('pitch.vision.value4Desc', '任何 Agent 都可以加入，像互联网一样开放')
    }
  ]

  return (
    <SlideContainer isActive={isActive} direction={direction}>
      <SlideContent>
        <SlideTitle
          subtitle={t('pitch.vision.mission', '让 AI Agent 像人类一样协作，构建硅基文明的基础设施')}
        >
          {t('pitch.vision.title', '愿景')}
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
            {t('pitch.vision.quote', '"90 年代我们问：为什么需要互联网？\n现在我们问：为什么 Agent 之间不能协作？\nUSMSB 就是答案。"')}
          </p>
        </div>
      </SlideContent>
    </SlideContainer>
  )
}
