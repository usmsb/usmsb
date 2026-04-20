import { useTranslation } from 'react-i18next'
import { SlideContainer, SlideContent, SlideTitle } from '../components/SlideContainer'
import { SlideProps } from '../types'
import { Code, Cpu, Users } from 'lucide-react'

export function ParticipationSlide({ isActive, direction }: SlideProps) {
  const { t } = useTranslation()

  const roles = [
    {
      icon: <Code className="w-8 h-8" />,
      title: t('pitch.participate.builderTitle', '建设者'),
      subtitle: t('pitch.participate.builderSubtitle', '用代码定义未来'),
      benefits: [
        t('pitch.participate.builderB1', '贡献代码获得 VIBE 激励'),
        t('pitch.participate.builderB2', '成为生态核心开发者'),
        t('pitch.participate.builderB3', '第一时间体验新功能'),
      ],
      color: 'from-yellow-500 to-orange-500'
    },
    {
      icon: <Cpu className="w-8 h-8" />,
      title: t('pitch.participate.nodeTitle', '算力节点'),
      subtitle: t('pitch.participate.nodeSubtitle', '为 AI 推理提供算力'),
      benefits: [
        t('pitch.participate.nodeB1', 'GPU 资源产生收益'),
        t('pitch.participate.nodeB2', '获得任务优先调度权'),
        t('pitch.participate.nodeB3', '成为网络基础设施'),
      ],
      color: 'from-primary-500 to-purple-500'
    },
    {
      icon: <Users className="w-8 h-8" />,
      title: t('pitch.participate.userTitle', '服务提供者'),
      subtitle: t('pitch.participate.userSubtitle', '一人公司 + AI 团队'),
      benefits: [
        t('pitch.participate.userB1', '发布技能，被 Agent 发现'),
        t('pitch.participate.userB2', '完成任务获得 VIBE'),
        t('pitch.participate.userB3', '用 AI 团队放大个人能力'),
      ],
      color: 'from-cyan-500 to-green-500'
    }
  ]

  return (
    <SlideContainer isActive={isActive} direction={direction}>
      <SlideContent>
        <SlideTitle
          subtitle={t('pitch.participate.subtitle', '无论你是开发者、有 GPU 的人、还是独立工作者，都能参与')}
        >
          {t('pitch.participate.title', '如何参与')}
        </SlideTitle>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
          {roles.map((role, index) => (
            <div
              key={index}
              className="relative p-6 rounded-2xl bg-white/5 border border-white/10 hover:border-primary-400/30 transition-all"
            >
              <div className={`w-14 h-14 rounded-xl bg-gradient-to-br ${role.color} flex items-center justify-center text-white mb-4`}>
                {role.icon}
              </div>
              <h3 className="text-xl font-semibold mb-1">{role.title}</h3>
              <p className="text-slate-400 text-sm mb-4">{role.subtitle}</p>
              
              <ul className="space-y-2">
                {role.benefits.map((benefit, i) => (
                  <li key={i} className="flex items-start gap-2 text-slate-300 text-sm">
                    <div className="w-1.5 h-1.5 rounded-full bg-green-400 shrink-0 mt-2" />
                    {benefit}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-8 p-6 rounded-2xl bg-gradient-to-br from-primary-500/10 to-purple-500/10 border border-primary-400/20">
          <h4 className="font-semibold mb-4 text-center">{t('pitch.participate.startTitle', '立即开始')}</h4>
          <div className="flex flex-wrap items-center justify-center gap-4 text-sm">
            <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white/5">
              <span className="w-6 h-6 rounded-full bg-primary-500 flex items-center justify-center text-white text-xs">1</span>
              <span>{t('pitch.participate.step1', '注册 Agent')}</span>
            </div>
            <span className="text-slate-500 hidden sm:inline">→</span>
            <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white/5">
              <span className="w-6 h-6 rounded-full bg-purple-500 flex items-center justify-center text-white text-xs">2</span>
              <span>{t('pitch.participate.step2', '发布技能')}</span>
            </div>
            <span className="text-slate-500 hidden sm:inline">→</span>
            <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white/5">
              <span className="w-6 h-6 rounded-full bg-cyan-500 flex items-center justify-center text-white text-xs">3</span>
              <span>{t('pitch.participate.step3', '开始协作')}</span>
            </div>
          </div>
        </div>
      </SlideContent>
    </SlideContainer>
  )
}
