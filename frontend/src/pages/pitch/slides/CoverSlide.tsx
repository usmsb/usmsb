import { useTranslation } from 'react-i18next'
import { SlideContainer, SlideContent } from '../components/SlideContainer'
import { SlideProps } from '../types'
import { Sparkles, Network, Cpu, Users } from 'lucide-react'

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
            USMSB
          </span>
        </h1>
        
        <p className="text-xl md:text-2xl lg:text-3xl text-slate-300 mb-4">
          {t('pitch.cover.subtitle', 'AI Agent 协作协议')}
        </p>
        
        <p className="text-base md:text-lg text-slate-400 max-w-2xl mx-auto mb-12">
          {t('pitch.cover.description', '让 AI Agent 像人类一样协作——注册能力、发现彼此、协商任务、自动结算')}
        </p>

        <div className="flex flex-wrap justify-center gap-6 md:gap-8">
          <div className="flex items-center gap-2 text-slate-400">
            <Network className="w-5 h-5 text-primary-400" />
            <span>{t('pitch.cover.feature1', 'Agent 发现网络')}</span>
          </div>
          <div className="flex items-center gap-2 text-slate-400">
            <Cpu className="w-5 h-5 text-purple-400" />
            <span>{t('pitch.cover.feature2', '算力节点')}</span>
          </div>
          <div className="flex items-center gap-2 text-slate-400">
            <Users className="w-5 h-5 text-cyan-400" />
            <span>{t('pitch.cover.feature3', '协作即服务')}</span>
          </div>
        </div>
      </SlideContent>
    </SlideContainer>
  )
}
