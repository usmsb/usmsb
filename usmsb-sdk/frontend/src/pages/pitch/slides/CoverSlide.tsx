import { useTranslation } from 'react-i18next'
import { SlideContainer, SlideContent } from '../components/SlideContainer'
import { SlideProps } from '../types'
import { Sparkles, Network, Wallet, Landmark } from 'lucide-react'

export function CoverSlide({ isActive, direction }: SlideProps) {
  const { t } = useTranslation()

  return (
    <SlideContainer isActive={isActive} direction={direction}>
      <SlideContent className="text-center">
        <div className="mb-8 flex justify-center gap-4">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-500 to-purple-600 flex items-center justify-center animate-pulse">
            <Sparkles className="w-8 h-8 text-white" />
          </div>
        </div>
        
        <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold mb-6 font-['Orbitron']">
          <span className="bg-gradient-to-r from-primary-400 via-purple-400 to-cyan-400 bg-clip-text text-transparent">
            VIBE
          </span>
        </h1>
        
        <p className="text-xl md:text-2xl lg:text-3xl text-slate-300 mb-4">
          {t('pitch.cover.subtitle', 'AI 文明基础设施')}
        </p>
        
        <p className="text-base md:text-lg text-slate-400 max-w-2xl mx-auto mb-12">
          {t('pitch.cover.description', '构建去中心化 AI Agent 经济生态，让 AI 成为独立的经济主体')}
        </p>

        <div className="flex flex-wrap justify-center gap-6 md:gap-8">
          <div className="flex items-center gap-2 text-slate-400">
            <Network className="w-5 h-5 text-primary-400" />
            <span>{t('pitch.cover.feature1', '去中心化网络')}</span>
          </div>
          <div className="flex items-center gap-2 text-slate-400">
            <Wallet className="w-5 h-5 text-purple-400" />
            <span>{t('pitch.cover.feature2', 'Agent 智能钱包')}</span>
          </div>
          <div className="flex items-center gap-2 text-slate-400">
            <Landmark className="w-5 h-5 text-cyan-400" />
            <span>{t('pitch.cover.feature3', 'DAO 治理')}</span>
          </div>
        </div>
      </SlideContent>
    </SlideContainer>
  )
}
