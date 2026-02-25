import { useTranslation } from 'react-i18next'
import { SlideContainer, SlideContent, SlideTitle } from '../components/SlideContainer'
import { SlideProps } from '../types'
import { CheckCircle, Clock, Zap } from 'lucide-react'

export function RoadmapSlide({ isActive, direction }: SlideProps) {
  const { t } = useTranslation()

  const milestones = [
    {
      quarter: 'Q1 2025',
      title: t('pitch.roadmap.q1Title', '主网上线'),
      items: [
        t('pitch.roadmap.q1Item1', 'VIBE 代币发布'),
        t('pitch.roadmap.q1Item2', 'Agent 钱包上线'),
        t('pitch.roadmap.q1Item3', '基础质押功能'),
      ],
      status: 'completed'
    },
    {
      quarter: 'Q2 2025',
      title: t('pitch.roadmap.q2Title', '生态扩展'),
      items: [
        t('pitch.roadmap.q2Item1', 'Agent 注册协议'),
        t('pitch.roadmap.q2Item2', '供需匹配市场'),
        t('pitch.roadmap.q2Item3', '协作网络'),
      ],
      status: 'active'
    },
    {
      quarter: 'Q3 2025',
      title: t('pitch.roadmap.q3Title', '跨链集成'),
      items: [
        t('pitch.roadmap.q3Item1', '多链资产桥接'),
        t('pitch.roadmap.q3Item2', '跨链消息传递'),
        t('pitch.roadmap.q3Item3', '统一身份认证'),
      ],
      status: 'pending'
    },
    {
      quarter: 'Q4 2025',
      title: t('pitch.roadmap.q4Title', 'DAO 治理'),
      items: [
        t('pitch.roadmap.q4Item1', '完全去中心化'),
        t('pitch.roadmap.q4Item2', '社区自治'),
        t('pitch.roadmap.q4Item3', '协议升级投票'),
      ],
      status: 'pending'
    }
  ]

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-400" />
      case 'active':
        return <Zap className="w-5 h-5 text-primary-400" />
      default:
        return <Clock className="w-5 h-5 text-slate-400" />
    }
  }

  return (
    <SlideContainer isActive={isActive} direction={direction}>
      <SlideContent>
        <SlideTitle
          subtitle={t('pitch.roadmap.subtitle', '清晰的路线图，稳步推进生态建设')}
        >
          {t('pitch.roadmap.title', '发展路线')}
        </SlideTitle>

        <div className="relative mt-8">
          <div className="absolute left-4 md:left-1/2 top-0 bottom-0 w-0.5 bg-gradient-to-b from-primary-500 via-purple-500 to-cyan-500 md:-translate-x-1/2" />

          <div className="space-y-8">
            {milestones.map((milestone, index) => (
              <div
                key={index}
                className={`relative flex items-start gap-6 ${index % 2 === 0 ? 'md:flex-row' : 'md:flex-row-reverse'}`}
              >
                <div className="absolute left-4 md:left-1/2 w-4 h-4 rounded-full bg-primary-500 md:-translate-x-1/2 mt-6 z-10" />
                
                <div className={`flex-1 ml-12 md:ml-0 ${index % 2 === 0 ? 'md:pr-12' : 'md:pl-12'}`}>
                  <div className={`p-5 rounded-2xl bg-white/5 border border-white/10 ${
                    milestone.status === 'active' ? 'border-primary-400/30 bg-primary-500/5' : ''
                  }`}>
                    <div className="flex items-center gap-3 mb-3">
                      {getStatusIcon(milestone.status)}
                      <span className="text-sm text-primary-400 font-mono">{milestone.quarter}</span>
                    </div>
                    <h3 className="text-lg font-semibold mb-3">{milestone.title}</h3>
                    <ul className="space-y-2">
                      {milestone.items.map((item, i) => (
                        <li key={i} className="flex items-center gap-2 text-slate-400 text-sm">
                          <div className="w-1.5 h-1.5 rounded-full bg-primary-400" />
                          {item}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                <div className="hidden md:block flex-1" />
              </div>
            ))}
          </div>
        </div>

        <div className="mt-8 flex justify-center">
          <div className="flex items-center gap-6 text-sm">
            <div className="flex items-center gap-2">
              <CheckCircle className="w-4 h-4 text-green-400" />
              <span className="text-slate-400">{t('pitch.roadmap.completed', '已完成')}</span>
            </div>
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4 text-primary-400" />
              <span className="text-slate-400">{t('pitch.roadmap.inProgress', '进行中')}</span>
            </div>
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-slate-400" />
              <span className="text-slate-400">{t('pitch.roadmap.planned', '计划中')}</span>
            </div>
          </div>
        </div>
      </SlideContent>
    </SlideContainer>
  )
}
