import { useTranslation } from 'react-i18next'
import { SlideContainer, SlideContent, SlideTitle, TokenAllocation, StatCard } from '../components/SlideContainer'
import { SlideProps } from '../types'
import { Coins, TrendingUp, Lock, Users, Flame, Percent } from 'lucide-react'

export function TokenEconomicsSlide({ isActive, direction }: SlideProps) {
  const { t } = useTranslation()

  const allocations = [
    { label: t('pitch.token.alloc1', '激励池'), percentage: 63, color: 'bg-primary-500' },
    { label: t('pitch.token.alloc2', '流动性池'), percentage: 12, color: 'bg-purple-500' },
    { label: t('pitch.token.alloc3', '社区空投'), percentage: 7, color: 'bg-cyan-500' },
    { label: t('pitch.token.alloc4', '社区稳定基金'), percentage: 6, color: 'bg-green-500' },
    { label: t('pitch.token.alloc5', '早期支持者'), percentage: 4, color: 'bg-yellow-500' },
    { label: t('pitch.token.alloc6', '团队'), percentage: 8, color: 'bg-orange-500' },
  ]

  return (
    <SlideContainer isActive={isActive} direction={direction}>
      <SlideContent>
        <SlideTitle
          subtitle={t('pitch.token.subtitle', 'VIBE 代币是生态系统的核心，总量固定10亿，不可增发')}
        >
          {t('pitch.token.title', '代币经济')}
        </SlideTitle>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mt-8">
          <div>
            <h3 className="text-lg font-semibold mb-4">{t('pitch.token.distribution', '代币分配')}</h3>
            <TokenAllocation items={allocations} />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <StatCard
              value="1B"
              label={t('pitch.token.totalSupply', '总供应量')}
              icon={<Coins className="w-6 h-6" />}
            />
            <StatCard
              value="8%"
              label={t('pitch.token.initialCirculation', '初始流通')}
              icon={<Percent className="w-6 h-6" />}
            />
            <StatCard
              value="3%"
              label={t('pitch.token.apy', '年化收益')}
              icon={<TrendingUp className="w-6 h-6" />}
            />
            <StatCard
              value="0.8%"
              label={t('pitch.token.txFee', '交易手续费')}
              icon={<Flame className="w-6 h-6" />}
            />
          </div>
        </div>

        <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 rounded-xl bg-white/5 border border-white/10">
            <h4 className="font-medium mb-2 text-primary-400">{t('pitch.token.use1Title', '服务支付')}</h4>
            <p className="text-slate-400 text-sm">{t('pitch.token.use1Desc', '支付 AI Agent 提供的服务')}</p>
          </div>
          <div className="p-4 rounded-xl bg-white/5 border border-white/10">
            <h4 className="font-medium mb-2 text-purple-400">{t('pitch.token.use2Title', '质押治理')}</h4>
            <p className="text-slate-400 text-sm">{t('pitch.token.use2Desc', '质押参与平台治理投票')}</p>
          </div>
          <div className="p-4 rounded-xl bg-white/5 border border-white/10">
            <h4 className="font-medium mb-2 text-cyan-400">{t('pitch.token.use3Title', '激励奖励')}</h4>
            <p className="text-slate-400 text-sm">{t('pitch.token.use3Desc', '贡献服务获得 VIBE 奖励')}</p>
          </div>
        </div>

        <div className="mt-6 p-4 rounded-xl bg-gradient-to-r from-primary-500/10 to-purple-500/10 border border-primary-400/20">
          <div className="flex flex-wrap items-center justify-between gap-4 text-sm">
            <div className="flex items-center gap-2">
              <span className="text-slate-400">{t('pitch.token.deflation', '通缩机制')}:</span>
              <span className="text-green-400 font-medium">{t('pitch.token.burnRate', '50% 手续费销毁')}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-slate-400">{t('pitch.token.dividend', '分红')}:</span>
              <span className="text-yellow-400 font-medium">{t('pitch.token.dividendRate', '20% 质押者分红')}</span>
            </div>
          </div>
        </div>
      </SlideContent>
    </SlideContainer>
  )
}
