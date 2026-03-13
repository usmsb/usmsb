import { useTranslation } from 'react-i18next'
import { SlideContainer, SlideContent, SlideTitle } from '../components/SlideContainer'
import { SlideProps } from '../types'
import { Wallet, Shield, Clock, CheckCircle, ArrowRight } from 'lucide-react'

export function AgentWalletSlide({ isActive, direction }: SlideProps) {
  const { t } = useTranslation()

  const features = [
    {
      icon: <Shield className="w-6 h-6" />,
      title: t('pitch.wallet.feat1Title', '限额控制'),
      desc: t('pitch.wallet.feat1Desc', '单笔最大 500 VIBE，每日限额 1000 VIBE')
    },
    {
      icon: <CheckCircle className="w-6 h-6" />,
      title: t('pitch.wallet.feat2Title', '白名单机制'),
      desc: t('pitch.wallet.feat2Desc', '仅可向白名单或已注册 Agent 转账')
    },
    {
      icon: <Clock className="w-6 h-6" />,
      title: t('pitch.wallet.feat3Title', '审批流程'),
      desc: t('pitch.wallet.feat3Desc', '大额转账需人类主人审批')
    }
  ]

  return (
    <SlideContainer isActive={isActive} direction={direction}>
      <SlideContent>
        <SlideTitle
          subtitle={t('pitch.wallet.subtitle', '专为 AI Agent 设计的智能合约钱包，安全、可控、人机协同')}
        >
          {t('pitch.wallet.title', 'Agent 智能钱包')}
        </SlideTitle>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mt-8">
          <div>
            <div className="p-6 rounded-2xl bg-gradient-to-br from-primary-500/10 to-purple-500/10 border border-primary-400/20">
              <div className="flex items-center gap-4 mb-6">
                <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-primary-500 to-purple-600 flex items-center justify-center">
                  <Wallet className="w-7 h-7 text-white" />
                </div>
                <div>
                  <h3 className="font-semibold text-lg">{t('pitch.wallet.archTitle', '智能合约钱包架构')}</h3>
                  <p className="text-slate-400 text-sm">{t('pitch.wallet.archDesc', '基于 Solidity 的安全钱包')}</p>
                </div>
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between p-3 rounded-lg bg-white/5">
                  <span className="text-slate-400">{t('pitch.wallet.owner', '主人 (人类)')}</span>
                  <span className="text-primary-400">MetaMask</span>
                </div>
                <div className="flex justify-center">
                  <ArrowRight className="w-5 h-5 text-slate-500 rotate-90" />
                </div>
                <div className="flex items-center justify-between p-3 rounded-lg bg-white/5">
                  <span className="text-slate-400">{t('pitch.wallet.agent', 'Agent')}</span>
                  <span className="text-purple-400">Backend Service</span>
                </div>
                <div className="flex justify-center">
                  <ArrowRight className="w-5 h-5 text-slate-500 rotate-90" />
                </div>
                <div className="flex items-center justify-between p-3 rounded-lg bg-white/5">
                  <span className="text-slate-400">{t('pitch.wallet.contract', '智能合约')}</span>
                  <span className="text-cyan-400">AgentWallet.sol</span>
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-4">
            {features.map((feature, index) => (
              <div
                key={index}
                className="flex gap-4 p-5 rounded-xl bg-white/5 border border-white/10 hover:border-primary-400/30 transition-all"
              >
                <div className="shrink-0 w-12 h-12 rounded-xl bg-primary-500/10 flex items-center justify-center text-primary-400">
                  {feature.icon}
                </div>
                <div>
                  <h4 className="font-medium mb-1">{feature.title}</h4>
                  <p className="text-slate-400 text-sm">{feature.desc}</p>
                </div>
              </div>
            ))}

            <div className="p-5 rounded-xl bg-green-500/10 border border-green-400/20">
              <h4 className="font-medium mb-2 text-green-400">{t('pitch.wallet.securityTitle', '安全保障')}</h4>
              <ul className="text-slate-400 text-sm space-y-1">
                <li>• {t('pitch.wallet.sec1', '紧急暂停功能')}</li>
                <li>• {t('pitch.wallet.sec2', '重入攻击防护')}</li>
                <li>• {t('pitch.wallet.sec3', '可升级限额设置')}</li>
              </ul>
            </div>
          </div>
        </div>
      </SlideContent>
    </SlideContainer>
  )
}
