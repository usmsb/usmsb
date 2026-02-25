import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { SlideContainer, SlideContent } from '../components/SlideContainer'
import { SlideProps } from '../types'
import { ArrowRight, Mail, Twitter, Github, Linkedin, Wallet } from 'lucide-react'
import { Button } from '@/components/ui/Button'

export function CtaSlide({ isActive, direction }: SlideProps) {
  const { t } = useTranslation()

  const socialLinks = [
    { icon: <Twitter className="w-5 h-5" />, href: 'https://twitter.com/vibe_ai', label: 'Twitter' },
    { icon: <Github className="w-5 h-5" />, href: 'https://github.com/vibe-ai', label: 'GitHub' },
    { icon: <Linkedin className="w-5 h-5" />, href: 'https://linkedin.com/company/vibe-ai', label: 'LinkedIn' },
    { icon: <Mail className="w-5 h-5" />, href: 'mailto:contact@vibe.ai', label: 'Email' },
  ]

  return (
    <SlideContainer isActive={isActive} direction={direction}>
      <SlideContent className="text-center">
        <div className="mb-8">
          <h1 className="text-4xl sm:text-5xl md:text-6xl font-bold mb-6 font-['Orbitron']">
            <span className="bg-gradient-to-r from-primary-400 via-purple-400 to-cyan-400 bg-clip-text text-transparent">
              {t('pitch.cta.title', '加入 AI 文明')}
            </span>
          </h1>
          <p className="text-xl text-slate-400 max-w-2xl mx-auto">
            {t('pitch.cta.subtitle', '与我们一起构建去中心化 AI Agent 经济生态')}
          </p>
        </div>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-12">
          <Link to="/app/onboarding">
            <Button
              size="lg"
              className="bg-gradient-to-r from-primary-500 to-purple-600 hover:from-primary-600 hover:to-purple-700 text-white border-0 px-8 py-4 text-lg group"
            >
              <Wallet className="w-5 h-5 mr-2" />
              {t('pitch.cta.connectWallet', '连接钱包开始')}
              <ArrowRight className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform" />
            </Button>
          </Link>
          <Link to="/docs">
            <Button
              variant="outline"
              size="lg"
              className="border-white/20 text-white hover:bg-white/10 px-8 py-4 text-lg"
            >
              {t('pitch.cta.readDocs', '阅读文档')}
            </Button>
          </Link>
        </div>

        <div className="p-8 rounded-2xl bg-gradient-to-br from-primary-500/10 to-purple-500/10 border border-primary-400/20 mb-8">
          <h3 className="font-semibold mb-4">{t('pitch.cta.contactTitle', '联系我们')}</h3>
          <div className="flex justify-center gap-4">
            {socialLinks.map((link, index) => (
              <a
                key={index}
                href={link.href}
                target="_blank"
                rel="noopener noreferrer"
                className="w-12 h-12 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-slate-400 hover:text-primary-400 hover:border-primary-400/30 transition-all"
                title={link.label}
              >
                {link.icon}
              </a>
            ))}
          </div>
        </div>

        <div className="text-center text-slate-500 text-sm">
          <p className="mb-2">{t('pitch.cta.copyright', '© 2025 VIBE. All rights reserved.')}</p>
          <p>{t('pitch.cta.tagline', 'Building the infrastructure for AI civilization.')}</p>
        </div>
      </SlideContent>
    </SlideContainer>
  )
}
