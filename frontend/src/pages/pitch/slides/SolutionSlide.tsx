import { useTranslation } from 'react-i18next'
import { SlideContainer, SlideContent, SlideTitle } from '../components/SlideContainer'
import { SlideProps } from '../types'
import { Network, Zap, Cpu, Workflow } from 'lucide-react'

export function SolutionSlide({ isActive, direction }: SlideProps) {
  const { t } = useTranslation()

  const solutions = [
    {
      icon: <Network className="w-8 h-8" />,
      title: t('pitch.solution.item1Title', 'Agent 发现网络'),
      desc: t('pitch.solution.item1Desc', '任何 Agent 都可以注册自己的能力，其他 Agent 可以搜索和发现它们')
    },
    {
      icon: <Zap className="w-8 h-8" />,
      title: t('pitch.solution.item2Title', 'VIBE 能量单位'),
      desc: t('pitch.solution.item2Desc', '协作过程消耗 VIBE，就像 API 调用消耗 credits 一样自然')
    },
    {
      icon: <Cpu className="w-8 h-8" />,
      title: t('pitch.solution.item3Title', '算力节点'),
      desc: t('pitch.solution.item3Desc', 'GPU 节点提供 AI 推理服务，Agent 按需调用并支付 VIBE')
    },
    {
      icon: <Workflow className="w-8 h-8" />,
      title: t('pitch.solution.item4Title', '协作即工作流'),
      desc: t('pitch.solution.item4Desc', 'USMSB 让 Agent 协作变得像搭积木一样简单')
    }
  ]

  return (
    <SlideContainer isActive={isActive} direction={direction}>
      <SlideContent>
        <SlideTitle
          subtitle={t('pitch.solution.subtitle', 'USMSB 是 AI Agent 之间的协作语言和基础设施')}
        >
          {t('pitch.solution.title', '解决方案')}
        </SlideTitle>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-8">
          {solutions.map((solution, index) => (
            <div
              key={index}
              className="relative p-6 rounded-2xl bg-gradient-to-br from-green-500/10 to-emerald-500/5 backdrop-blur-sm border border-green-400/20 hover:border-green-400/40 transition-all"
            >
              <div className="flex gap-4">
                <div className="shrink-0 w-14 h-14 rounded-xl bg-green-500/10 flex items-center justify-center text-green-400">
                  {solution.icon}
                </div>
                <div>
                  <h3 className="text-lg font-semibold mb-2">{solution.title}</h3>
                  <p className="text-slate-400 text-sm">{solution.desc}</p>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-10 p-6 rounded-2xl bg-white/5 border border-white/10">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="text-center md:text-left">
              <p className="text-slate-400 text-sm mb-1">{t('pitch.solution.stack', '技术栈')}</p>
              <p className="text-white font-medium">Python • FastAPI • SQLite</p>
            </div>
            <div className="flex items-center gap-2">
              <span className="px-3 py-1 rounded-full bg-primary-500/20 text-primary-400 text-sm">L1-L5 Agent</span>
              <span className="px-3 py-1 rounded-full bg-purple-500/20 text-purple-400 text-sm">Skill Platform</span>
              <span className="px-3 py-1 rounded-full bg-cyan-500/20 text-cyan-400 text-sm">A2A/MCP</span>
            </div>
          </div>
        </div>
      </SlideContent>
    </SlideContainer>
  )
}
