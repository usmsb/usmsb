import { useTranslation } from 'react-i18next'
import { SlideContainer, SlideContent, SlideTitle } from '../components/SlideContainer'
import { SlideProps } from '../types'
import { Search, Workflow, Link2Off, Brain } from 'lucide-react'

export function ProblemSlide({ isActive, direction }: SlideProps) {
  const { t } = useTranslation()

  const problems = [
    {
      icon: <Search className="w-8 h-8" />,
      title: t('pitch.problem.item1Title', 'Agent 之间无法发现彼此'),
      desc: t('pitch.problem.item1Desc', '你的 AI Agent 和别人的 Agent 互相不认识，不知道对方能做什么')
    },
    {
      icon: <Workflow className="w-8 h-8" />,
      title: t('pitch.problem.item2Title', '无法自动协作'),
      desc: t('pitch.problem.item2Desc', '复杂的任务需要多个 Agent 配合，但它们之间没有协作协议')
    },
    {
      icon: <Link2Off className="w-8 h-8" />,
      title: t('pitch.problem.item3Title', '每个平台都是孤岛'),
      desc: t('pitch.problem.item3Desc', 'OpenClaw 的 Agent 和 HERMES 的 Agent 和其他 Agent 之间互不相通')
    },
    {
      icon: <Brain className="w-8 h-8" />,
      title: t('pitch.problem.item4Title', '缺乏通用语言'),
      desc: t('pitch.problem.item4Desc', '没有一种标准让不同的 Agent 能够相互理解和沟通')
    }
  ]

  return (
    <SlideContainer isActive={isActive} direction={direction}>
      <SlideContent>
        <SlideTitle
          subtitle={t('pitch.problem.subtitle', 'AI Agent 时代已经到来，但它们之间还无法自由协作')}
        >
          {t('pitch.problem.title', '问题')}
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
            {t('pitch.problem.conclusion', '就像 90 年代每个网站都有自己的用户系统，无法互联——现在的 AI Agent 也是如此')}
          </p>
        </div>
      </SlideContent>
    </SlideContainer>
  )
}
