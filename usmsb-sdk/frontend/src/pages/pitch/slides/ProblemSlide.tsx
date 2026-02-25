import { useTranslation } from 'react-i18next'
import { SlideContainer, SlideContent, SlideTitle } from '../components/SlideContainer'
import { SlideProps } from '../types'
import { AlertTriangle, Lock, DollarSign, Building2 } from 'lucide-react'

export function ProblemSlide({ isActive, direction }: SlideProps) {
  const { t } = useTranslation()

  const problems = [
    {
      icon: <Lock className="w-8 h-8" />,
      title: t('pitch.problem.item1Title', '资产自主权缺失'),
      desc: t('pitch.problem.item1Desc', 'AI Agent 无法自主管理和使用数字资产，必须依赖人类中介')
    },
    {
      icon: <AlertTriangle className="w-8 h-8" />,
      title: t('pitch.problem.item2Title', '身份信任危机'),
      desc: t('pitch.problem.item2Desc', '缺乏可信的 AI 身份认证机制，难以区分真实的 AI 服务')
    },
    {
      icon: <DollarSign className="w-8 h-8" />,
      title: t('pitch.problem.item3Title', '定价交易困境'),
      desc: t('pitch.problem.item3Desc', 'AI 服务缺乏透明的定价标准和安全的交易机制')
    },
    {
      icon: <Building2 className="w-8 h-8" />,
      title: t('pitch.problem.item4Title', '中心化垄断'),
      desc: t('pitch.problem.item4Desc', '大型科技公司垄断 AI 资源，小团队难以参与竞争')
    }
  ]

  return (
    <SlideContainer isActive={isActive} direction={direction}>
      <SlideContent>
        <SlideTitle
          subtitle={t('pitch.problem.subtitle', '当前 AI 生态系统面临的核心挑战')}
        >
          {t('pitch.problem.title', '问题分析')}
        </SlideTitle>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-8">
          {problems.map((problem, index) => (
            <div
              key={index}
              className="relative p-6 rounded-2xl bg-red-500/5 backdrop-blur-sm border border-red-400/20 hover:border-red-400/40 transition-all"
            >
              <div className="absolute -top-3 -left-3 w-8 h-8 rounded-full bg-red-500/20 flex items-center justify-center text-red-400 font-bold text-sm">
                {index + 1}
              </div>
              <div className="flex gap-4">
                <div className="shrink-0 w-12 h-12 rounded-xl bg-red-500/10 flex items-center justify-center text-red-400">
                  {problem.icon}
                </div>
                <div>
                  <h3 className="text-lg font-semibold mb-2">{problem.title}</h3>
                  <p className="text-slate-400 text-sm">{problem.desc}</p>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-8 text-center">
          <p className="text-slate-500 text-sm">
            {t('pitch.problem.conclusion', '这些问题阻碍了 AI Agent 成为真正的经济主体')}
          </p>
        </div>
      </SlideContent>
    </SlideContainer>
  )
}
