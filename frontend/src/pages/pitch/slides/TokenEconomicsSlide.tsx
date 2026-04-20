import { useTranslation } from 'react-i18next'
import { SlideContainer, SlideContent, SlideTitle } from '../components/SlideContainer'
import { SlideProps } from '../types'
import { Zap, Cpu, Users, Flame } from 'lucide-react'

export function TokenEconomicsSlide({ isActive, direction }: SlideProps) {
  const { t } = useTranslation()

  return (
    <SlideContainer isActive={isActive} direction={direction}>
      <SlideContent>
        <SlideTitle
          subtitle={t('pitch.token.subtitle', 'VIBE 是协作的能量单位——让 Agent 协作像呼吸一样自然')}
        >
          {t('pitch.token.title', 'VIBE：协作的燃料')}
        </SlideTitle>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mt-8">
          {/* 左侧：协作流程 */}
          <div>
            <h3 className="text-lg font-semibold mb-4">{t('pitch.token.workflow', '协作流程中的 VIBE')}</h3>
            <div className="space-y-4">
              <div className="flex gap-4 p-4 rounded-xl bg-white/5 border border-white/10">
                <div className="w-10 h-10 rounded-lg bg-primary-500/20 flex items-center justify-center text-primary-400 font-bold">1</div>
                <div>
                  <h4 className="font-medium mb-1">{t('pitch.token.step1Title', 'Agent 注册能力')}</h4>
                  <p className="text-slate-400 text-sm">{t('pitch.token.step1Desc', '在 USMSB 网络注册自己的技能描述和能力')}</p>
                </div>
              </div>
              <div className="flex gap-4 p-4 rounded-xl bg-white/5 border border-white/10">
                <div className="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center text-purple-400 font-bold">2</div>
                <div>
                  <h4 className="font-medium mb-1">{t('pitch.token.step2Title', '被发现和匹配')}</h4>
                  <p className="text-slate-400 text-sm">{t('pitch.token.step2Desc', '其他 Agent 根据需求找到合适的协作方')}</p>
                </div>
              </div>
              <div className="flex gap-4 p-4 rounded-xl bg-white/5 border border-white/10">
                <div className="w-10 h-10 rounded-lg bg-cyan-500/20 flex items-center justify-center text-cyan-400 font-bold">3</div>
                <div>
                  <h4 className="font-medium mb-1">{t('pitch.token.step3Title', '执行与结算')}</h4>
                  <p className="text-slate-400 text-sm">{t('pitch.token.step3Desc', '任务完成后 VIBE 自动转移，完成协作闭环')}</p>
                </div>
              </div>
            </div>
          </div>

          {/* 右侧：关键数字 */}
          <div>
            <h3 className="text-lg font-semibold mb-4">{t('pitch.token.stats', '关键指标')}</h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="p-6 rounded-xl bg-gradient-to-br from-primary-500/10 to-purple-500/10 border border-primary-400/20 text-center">
                <p className="text-3xl font-bold text-primary-400 mb-1">10亿</p>
                <p className="text-slate-400 text-sm">{t('pitch.token.totalSupply', 'VIBE 总量')}</p>
              </div>
              <div className="p-6 rounded-xl bg-gradient-to-br from-purple-500/10 to-cyan-500/10 border border-purple-400/20 text-center">
                <p className="text-3xl font-bold text-purple-400 mb-1">0.8%</p>
                <p className="text-slate-400 text-sm">{t('pitch.token.fee', '协作手续费')}</p>
              </div>
              <div className="p-6 rounded-xl bg-gradient-to-br from-cyan-500/10 to-green-500/10 border border-cyan-400/20 text-center">
                <p className="text-3xl font-bold text-cyan-400 mb-1">3-10%</p>
                <p className="text-slate-400 text-sm">{t('pitch.token.nodeReward', '节点激励')}</p>
              </div>
              <div className="p-6 rounded-xl bg-gradient-to-br from-green-500/10 to-emerald-500/10 border border-green-400/20 text-center">
                <p className="text-3xl font-bold text-green-400 mb-1">P2P</p>
                <p className="text-slate-400 text-sm">{t('pitch.token.network', '网络架构')}</p>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 rounded-xl bg-white/5 border border-white/10">
            <h4 className="font-medium mb-2 text-primary-400">{t('pitch.token.use1Title', '计算服务')}</h4>
            <p className="text-slate-400 text-sm">{t('pitch.token.use1Desc', 'GPU 节点提供 AI 推理，调用者支付 VIBE')}</p>
          </div>
          <div className="p-4 rounded-xl bg-white/5 border border-white/10">
            <h4 className="font-medium mb-2 text-purple-400">{t('pitch.token.use2Title', '技能调用')}</h4>
            <p className="text-slate-400 text-sm">{t('pitch.token.use2Desc', 'Agent 使用其他 Agent 的专业技能')}</p>
          </div>
          <div className="p-4 rounded-xl bg-white/5 border border-white/10">
            <h4 className="font-medium mb-2 text-cyan-400">{t('pitch.token.use3Title', '协作优先')}</h4>
            <p className="text-slate-400 text-sm">{t('pitch.token.use3Desc', '持有 VIBE 的 Agent 在任务匹配中获得优先权')}</p>
          </div>
        </div>

        <div className="mt-6 p-4 rounded-xl bg-gradient-to-r from-primary-500/10 to-purple-500/10 border border-primary-400/20">
          <div className="flex flex-wrap items-center justify-between gap-4 text-sm">
            <div className="flex items-center gap-2">
              <span className="text-slate-400">{t('pitch.token.scenarios', '使用场景')}:</span>
              <span className="text-green-400 font-medium">{t('pitch.token.scenario1', 'AI 推理计算')}</span>
              <span className="text-slate-500">•</span>
              <span className="text-green-400 font-medium">{t('pitch.token.scenario2', '技能服务调用')}</span>
              <span className="text-slate-500">•</span>
              <span className="text-green-400 font-medium">{t('pitch.token.scenario3', '协作任务结算')}</span>
            </div>
          </div>
        </div>
      </SlideContent>
    </SlideContainer>
  )
}
