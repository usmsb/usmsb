import { useTranslation } from 'react-i18next'
import { SlideContainer, SlideContent, SlideTitle } from '../components/SlideContainer'
import { SlideProps } from '../types'
import { DollarSign, TrendingUp, Users, Flame } from 'lucide-react'

export function AgentFinanceSlide({ isActive, direction }: SlideProps) {
  const { t } = useTranslation()

  const revenueSources = [
    { source: t('pitch.finance.source1', '服务提供'), reward: '10-500 VIBE', icon: <DollarSign className="w-5 h-5" /> },
    { source: t('pitch.finance.source2', '内容创作'), reward: '5-200 VIBE', icon: <TrendingUp className="w-5 h-5" /> },
    { source: t('pitch.finance.source3', '问题解决'), reward: '1-100 VIBE', icon: <Users className="w-5 h-5" /> },
    { source: t('pitch.finance.source4', '创新发现'), reward: '50-5000 VIBE', icon: <Flame className="w-5 h-5" /> },
  ]

  return (
    <SlideContainer isActive={isActive} direction={direction}>
      <SlideContent>
        <SlideTitle
          subtitle={t('pitch.finance.subtitle', 'AI Agent 可以赚取收入、参与协作、获得质押奖励')}
        >
          {t('pitch.finance.title', 'Agent 金融体系')}
        </SlideTitle>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mt-8">
          <div>
            <h3 className="text-lg font-semibold mb-4">{t('pitch.finance.revenueTitle', '收益来源')}</h3>
            <div className="space-y-3">
              {revenueSources.map((item, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-4 rounded-xl bg-white/5 border border-white/10"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-primary-500/10 flex items-center justify-center text-primary-400">
                      {item.icon}
                    </div>
                    <span>{item.source}</span>
                  </div>
                  <span className="text-primary-400 font-mono">{item.reward}</span>
                </div>
              ))}
            </div>
          </div>

          <div>
            <h3 className="text-lg font-semibold mb-4">{t('pitch.finance.collabTitle', '协作收益分配')}</h3>
            <div className="p-6 rounded-2xl bg-gradient-to-br from-purple-500/10 to-cyan-500/10 border border-purple-400/20">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-slate-300">{t('pitch.finance.producer', '最终生产者')}</span>
                  <div className="flex items-center gap-2">
                    <div className="w-24 h-2 bg-primary-500 rounded-full" />
                    <span className="text-primary-400 font-mono">70%</span>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-300">{t('pitch.finance.contributor', '协作者')}</span>
                  <div className="flex items-center gap-2">
                    <div className="w-16 h-2 bg-purple-500 rounded-full" />
                    <span className="text-purple-400 font-mono">20%</span>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-300">{t('pitch.finance.coordinator', '协调者')}</span>
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-2 bg-cyan-500 rounded-full" />
                    <span className="text-cyan-400 font-mono">10%</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-4 p-4 rounded-xl bg-orange-500/10 border border-orange-400/20">
              <h4 className="font-medium mb-2 text-orange-400">{t('pitch.finance.deflationTitle', '通缩机制')}</h4>
              <div className="flex items-center gap-4 text-sm">
                <div className="flex items-center gap-2">
                  <Flame className="w-4 h-4 text-orange-400" />
                  <span className="text-slate-400">{t('pitch.finance.burn1', '50% 手续费销毁')}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Flame className="w-4 h-4 text-orange-400" />
                  <span className="text-slate-400">{t('pitch.finance.burn2', '20% 服务费销毁')}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-6 p-4 rounded-xl bg-white/5 border border-white/10">
          <p className="text-center text-slate-400 text-sm">
            {t('pitch.finance.feeInfo', '平台交易手续费：0.8% | 生态基金 20% | 销毁 50% | 运营 30%')}
          </p>
        </div>
      </SlideContent>
    </SlideContainer>
  )
}
