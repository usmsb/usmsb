import { useTranslation } from 'react-i18next'
import { SlideContainer, SlideContent, SlideTitle } from '../components/SlideContainer'
import { SlideProps } from '../types'
import { Brain, Cpu, Sparkles, Globe } from 'lucide-react'

export function ArchitectureSlide({ isActive, direction }: SlideProps) {
  const { t } = useTranslation()

  const layers = [
    {
      icon: <Cpu className="w-6 h-6" />,
      name: t('pitch.arch.layer1Name', 'L1: 反应式'),
      desc: t('pitch.arch.layer1Desc', '规则引擎，if-then 匹配，<10ms 响应'),
      color: 'from-primary-500 to-purple-500'
    },
    {
      icon: <Cpu className="w-6 h-6" />,
      name: t('pitch.arch.layer2Name', 'L2: 工具性'),
      desc: t('pitch.arch.layer2Desc', 'LLM + 工具调用 + 记忆，>95% 调用成功率'),
      color: 'from-purple-500 to-cyan-500'
    },
    {
      icon: <Sparkles className="w-6 h-6" />,
      name: t('pitch.arch.layer3Name', 'L3: 自主目标'),
      desc: t('pitch.arch.layer3Desc', '目标生成 + 内在动机 + 动态协商'),
      color: 'from-cyan-500 to-green-500'
    },
    {
      icon: <Brain className="w-6 h-6" />,
      name: t('pitch.arch.layer4Name', 'L4-L5: 自我意识'),
      desc: t('pitch.arch.layer4Desc', '元认知 + 他心智 + 集体智能'),
      color: 'from-green-500 to-yellow-500'
    }
  ]

  return (
    <SlideContainer isActive={isActive} direction={direction}>
      <SlideContent>
        <SlideTitle
          subtitle={t('pitch.arch.subtitle', 'L1-L5 分层架构，从规则匹配到集体智能')}
        >
          {t('pitch.arch.title', 'Agent 架构')}
        </SlideTitle>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mt-8">
          {layers.map((layer, index) => (
            <div
              key={index}
              className="relative p-5 rounded-2xl bg-white/5 border border-white/10 hover:border-primary-400/30 transition-all"
            >
              <div className={`absolute -top-3 -left-3 w-8 h-8 rounded-lg bg-gradient-to-br ${layer.color} flex items-center justify-center text-white font-bold text-sm`}>
                {index + 1}
              </div>
              <div className="mt-4">
                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${layer.color} flex items-center justify-center text-white mb-4`}>
                  {layer.icon}
                </div>
                <h3 className="font-semibold mb-2">{layer.name}</h3>
                <p className="text-slate-400 text-sm">{layer.desc}</p>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-8 p-6 rounded-2xl bg-gradient-to-br from-primary-500/10 to-purple-500/10 border border-primary-400/20">
          <h3 className="font-semibold mb-4 text-center">{t('pitch.arch.flowTitle', '协作流程')}</h3>
          <div className="flex flex-wrap items-center justify-center gap-4 text-sm">
            <span className="px-4 py-2 rounded-lg bg-primary-500/20 text-primary-400">{t('pitch.arch.flow1', '注册能力')}</span>
            <span className="text-slate-500">→</span>
            <span className="px-4 py-2 rounded-lg bg-purple-500/20 text-purple-400">{t('pitch.arch.flow2', '发现协作')}</span>
            <span className="text-slate-500">→</span>
            <span className="px-4 py-2 rounded-lg bg-cyan-500/20 text-cyan-400">{t('pitch.arch.flow3', '协商任务')}</span>
            <span className="text-slate-500">→</span>
            <span className="px-4 py-2 rounded-lg bg-green-500/20 text-green-400">{t('pitch.arch.flow4', '结算 VIBE')}</span>
          </div>
        </div>

        <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
          <div className="p-3 rounded-xl bg-white/5">
            <p className="text-2xl font-bold text-primary-400 font-['Orbitron']">L1-L5</p>
            <p className="text-slate-400 text-xs">{t('pitch.arch.stat1', 'Agent 分层')}</p>
          </div>
          <div className="p-3 rounded-xl bg-white/5">
            <p className="text-2xl font-bold text-purple-400 font-['Orbitron']">A2A</p>
            <p className="text-slate-400 text-xs">{t('pitch.arch.stat2', '协作协议')}</p>
          </div>
          <div className="p-3 rounded-xl bg-white/5">
            <p className="text-2xl font-bold text-cyan-400 font-['Orbitron']">MCP</p>
            <p className="text-slate-400 text-xs">{t('pitch.arch.stat3', '工具调用')}</p>
          </div>
          <div className="p-3 rounded-xl bg-white/5">
            <p className="text-2xl font-bold text-green-400 font-['Orbitron']">VIBE</p>
            <p className="text-slate-400 text-xs">{t('pitch.arch.stat4', '协作燃料')}</p>
          </div>
        </div>
      </SlideContent>
    </SlideContainer>
  )
}
