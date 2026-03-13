import { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import {
  Menu,
  X,
  ChevronRight,
  Bot,
  Network,
  Shield,
  Zap,
  Users,
  LineChart,
  MessageSquare,
  FileText,
  Settings,
  Github,
  Twitter,
  Linkedin,
  Mail,
  ChevronDown,
  ChevronUp,
  Target,
  Cpu,
  Globe,
  Lock,
  Star,
  ArrowRight,
  Play,
  BookOpen,
  Layers,
  Share2,
} from 'lucide-react'
import LanguageSwitcher from '@/components/LanguageSwitcher'
import { Button } from '@/components/ui/Button'
import { useAppStore } from '@/store'
import clsx from 'clsx'

// USMSB Nine Elements - Grouped by category
const usmsbGroups = [
  {
    titleKey: 'landing.usmsb.groups.core',
    titleEn: 'Core Foundation',
    titleZh: '核心基础',
    descriptionKey: 'landing.usmsb.groups.coreDesc',
    descriptionEn: 'The fundamental building blocks of agent interaction',
    descriptionZh: '智能体交互的基础构建模块',
    elements: [
      { key: 'user', icon: Users, color: 'from-blue-500 to-cyan-500', role: 'Actor' },
      { key: 'service', icon: Settings, color: 'from-purple-500 to-pink-500', role: 'Action' },
      { key: 'matching', icon: Target, color: 'from-green-500 to-emerald-500', role: 'Connection' },
    ],
  },
  {
    titleKey: 'landing.usmsb.groups.value',
    titleEn: 'Value Exchange',
    titleZh: '价值交换',
    descriptionKey: 'landing.usmsb.groups.valueDesc',
    descriptionEn: 'Mechanisms for measuring and exchanging value',
    descriptionZh: '衡量和交换价值的机制',
    elements: [
      { key: 'behavior', icon: LineChart, color: 'from-orange-500 to-amber-500', role: 'Measurement' },
      { key: 'settlement', icon: Lock, color: 'from-red-500 to-rose-500', role: 'Transfer' },
      { key: 'reputation', icon: Star, color: 'from-yellow-500 to-orange-500', role: 'Trust' },
    ],
  },
  {
    titleKey: 'landing.usmsb.groups.eco',
    titleEn: 'Ecosystem',
    titleZh: '生态系统',
    descriptionKey: 'landing.usmsb.groups.ecoDesc',
    descriptionEn: 'The environment for sustained growth and governance',
    descriptionZh: '持续增长和治理的环境',
    elements: [
      { key: 'ontology', icon: BookOpen, color: 'from-indigo-500 to-purple-500', role: 'Knowledge' },
      { key: 'ecosystem', icon: Globe, color: 'from-teal-500 to-cyan-500', role: 'Network' },
      { key: 'governance', icon: Shield, color: 'from-slate-500 to-gray-500', role: 'Rules' },
    ],
  },
]

// Legacy flat array for backward compatibility
const usmsbElements = usmsbGroups.flatMap(group => group.elements)

const features = [
  { key: 'agentRegistration', icon: Bot, color: 'bg-blue-500/10 text-blue-500' },
  { key: 'supplyDemand', icon: Target, color: 'bg-purple-500/10 text-purple-500' },
  { key: 'collaboration', icon: Network, color: 'bg-green-500/10 text-green-500' },
  { key: 'governanceSystem', icon: Shield, color: 'bg-orange-500/10 text-orange-500' },
]

const useCases = [
  { key: 'enterpriseAI', icon: Cpu },
  { key: 'dataAnalysis', icon: LineChart },
  { key: 'contentCreation', icon: FileText },
  { key: 'customerService', icon: MessageSquare },
]

const techStack = [
  { name: 'React', icon: '⚛️' },
  { name: 'TypeScript', icon: '📘' },
  { name: 'Rust', icon: '🦀' },
  { name: 'WebAssembly', icon: '⚡' },
  { name: 'IPFS', icon: '🌐' },
  { name: 'Ethereum', icon: '💎' },
]

const faqs = [
  'whatIsUSMSB',
  'howToStart',
  'security',
  'pricing',
  'integration',
  'support',
]

export default function LandingPage() {
  const { t } = useTranslation()
  const { theme } = useAppStore()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)
  const [activeSection, setActiveSection] = useState('')
  const [openFaq, setOpenFaq] = useState<string | null>(null)

  // Logo source based on theme
  const logoSrc = theme === 'dark' ? '/logo-dark.svg' : '/logo.svg'

  // Refs for scroll animations
  const heroRef = useRef<HTMLDivElement>(null)
  const featuresRef = useRef<HTMLDivElement>(null)
  const usmsbRef = useRef<HTMLDivElement>(null)
  const useCasesRef = useRef<HTMLDivElement>(null)
  const techRef = useRef<HTMLDivElement>(null)
  const faqRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 50)

      // Determine active section
      const sections = [
        { ref: featuresRef, id: 'features' },
        { ref: usmsbRef, id: 'usmsb' },
        { ref: useCasesRef, id: 'usecases' },
        { ref: techRef, id: 'tech' },
        { ref: faqRef, id: 'faq' },
      ]

      for (const section of sections) {
        if (section.ref.current) {
          const rect = section.ref.current.getBoundingClientRect()
          if (rect.top <= 100 && rect.bottom >= 100) {
            setActiveSection(section.id)
            break
          }
        }
      }
    }

    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  const navLinks = [
    { href: '#features', label: t('landing.nav.features') },
    { href: '#usmsb', label: t('landing.nav.usmsb') },
    { href: '#usecases', label: t('landing.nav.useCases') },
    { href: '#tech', label: t('landing.nav.tech') },
    { href: '#faq', label: t('landing.nav.faq') },
    { href: '/pitch', label: t('landing.nav.pitch'), isRoute: true },
  ]

  return (
    <div className={clsx(
      "min-h-screen overflow-x-hidden",
      /* Light mode: Clean white/light gray background */
      "bg-gradient-to-b from-slate-50 via-white to-slate-50",
      /* Dark mode: Cyberpunk dark background */
      "dark:bg-gradient-to-b dark:from-slate-950 dark:via-slate-900 dark:to-slate-950",
      /* Light mode: Dark text */
      "text-secondary-900",
      /* Dark mode: White text */
      "dark:text-secondary-100"
    )}>
      {/* Animated background - Dark mode cyberpunk glow */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none hidden dark:block">
        <div className="absolute top-0 left-1/4 w-[600px] h-[600px] bg-primary-500/20 rounded-full blur-[128px] animate-pulse" />
        <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] bg-purple-500/20 rounded-full blur-[128px] animate-pulse delay-1000" />
        <div className="absolute top-1/2 left-1/2 w-[500px] h-[500px] bg-cyan-500/10 rounded-full blur-[128px] animate-pulse delay-500" />
      </div>

      {/* Light mode subtle background pattern */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none dark:hidden">
        <div className="absolute top-0 right-0 w-[800px] h-[800px] bg-gradient-to-bl from-primary-100/50 to-transparent rounded-full blur-3xl" />
        <div className="absolute bottom-0 left-0 w-[600px] h-[600px] bg-gradient-to-tr from-purple-100/30 to-transparent rounded-full blur-3xl" />
      </div>

      {/* Navigation */}
      <nav
        className={clsx(
          'fixed top-0 left-0 right-0 z-50 transition-all duration-300',
          scrolled
            ? 'bg-white/80 dark:bg-slate-900/80 backdrop-blur-xl border-b border-secondary-200 dark:border-white/10'
            : 'bg-transparent'
        )}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16 md:h-20">
            {/* Logo */}
            <Link to="/" className="flex items-center gap-3 group">
              <img
                src={logoSrc}
                alt="Silicon Civilization Logo"
                className="w-10 h-10 md:w-12 md:h-12"
              />
              <span className="text-xl md:text-2xl font-bold bg-gradient-to-r from-secondary-900 to-primary-600 dark:from-white dark:to-primary-300 bg-clip-text text-transparent">
                {t('landing.brandName')}
              </span>
            </Link>

            {/* Desktop Nav Links */}
            <div className="hidden md:flex items-center gap-8">
              {navLinks.map((link) => (
                link.isRoute ? (
                  <Link
                    key={link.href}
                    to={link.href}
                    className="text-sm font-medium transition-colors hover:text-primary-500 dark:hover:text-primary-400 text-secondary-600 dark:text-slate-300"
                  >
                    {link.label}
                  </Link>
                ) : (
                  <a
                    key={link.href}
                    href={link.href}
                    className={clsx(
                      'text-sm font-medium transition-colors hover:text-primary-500 dark:hover:text-primary-400',
                      activeSection === link.href.slice(1)
                        ? 'text-primary-600 dark:text-primary-400'
                        : 'text-secondary-600 dark:text-slate-300'
                    )}
                  >
                    {link.label}
                  </a>
                )
              ))}
            </div>

            {/* Right side */}
            <div className="hidden md:flex items-center gap-4">
              <LanguageSwitcher />
              <Link to="/app/onboarding">
                <Button variant="ghost" size="sm" className="text-secondary-600 dark:text-slate-300 hover:text-secondary-900 dark:hover:text-white">
                  {t('landing.nav.login')}
                </Button>
              </Link>
              <Link to="/app/onboarding">
                <Button
                  size="sm"
                  className="bg-gradient-to-r from-primary-500 to-purple-600 hover:from-primary-600 hover:to-purple-700 text-white border-0"
                >
                  {t('landing.nav.getStarted')}
                  <ChevronRight className="w-4 h-4 ml-1" />
                </Button>
              </Link>
            </div>

            {/* Mobile menu button */}
            <button
              className="md:hidden p-2 rounded-lg hover:bg-secondary-100 dark:hover:bg-white/10 text-secondary-700 dark:text-secondary-100"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>

        {/* Mobile menu */}
        {mobileMenuOpen && (
          <div className="md:hidden bg-white/95 dark:bg-slate-900/95 backdrop-blur-xl border-b border-secondary-200 dark:border-white/10">
            <div className="px-4 py-4 space-y-4">
              {navLinks.map((link) => (
                link.isRoute ? (
                  <Link
                    key={link.href}
                    to={link.href}
                    onClick={() => setMobileMenuOpen(false)}
                    className="block text-secondary-600 dark:text-slate-300 hover:text-primary-600 dark:hover:text-primary-400 py-2"
                  >
                    {link.label}
                  </Link>
                ) : (
                  <a
                    key={link.href}
                    href={link.href}
                    onClick={() => setMobileMenuOpen(false)}
                    className="block text-secondary-600 dark:text-slate-300 hover:text-primary-600 dark:hover:text-primary-400 py-2"
                  >
                    {link.label}
                  </a>
                )
              ))}
              <div className="pt-4 border-t border-secondary-200 dark:border-white/10 flex items-center justify-between">
                <LanguageSwitcher />
                <div className="flex gap-2">
                  <Link to="/app/onboarding">
                    <Button variant="ghost" size="sm" className="text-secondary-600 dark:text-slate-300">
                      {t('landing.nav.login')}
                    </Button>
                  </Link>
                  <Link to="/app/onboarding">
                    <Button size="sm" className="bg-primary-500 text-white">
                      {t('landing.nav.getStarted')}
                    </Button>
                  </Link>
                </div>
              </div>
            </div>
          </div>
        )}
      </nav>

      {/* Hero Section */}
      <section
        ref={heroRef}
        className="relative min-h-screen flex items-center justify-center pt-20"
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
          <div className="text-center">
            {/* Badge */}
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-secondary-100 dark:bg-white/5 border border-secondary-200 dark:border-white/10 mb-8">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-primary-500"></span>
              </span>
              <span className="text-sm text-secondary-600 dark:text-slate-300">{t('landing.hero.badge')}</span>
            </div>

            {/* Main Title */}
            <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold mb-6 leading-tight">
              <span className="bg-gradient-to-r from-secondary-900 via-primary-600 to-purple-600 dark:from-white dark:via-primary-200 dark:to-purple-300 bg-clip-text text-transparent">
                {t('landing.hero.title1')}
              </span>
              <br />
              <span className="bg-gradient-to-r from-primary-500 via-purple-500 to-cyan-500 dark:from-primary-400 dark:via-purple-400 dark:to-cyan-400 bg-clip-text text-transparent">
                {t('landing.hero.title2')}
              </span>
            </h1>

            {/* Subtitle */}
            <p className="text-lg sm:text-xl text-secondary-600 dark:text-slate-400 max-w-3xl mx-auto mb-10">
              {t('landing.hero.subtitle')}
            </p>

            {/* CTA Buttons */}
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
              <Link to="/app/onboarding">
                <Button
                  size="lg"
                  className="bg-gradient-to-r from-primary-500 to-purple-600 hover:from-primary-600 hover:to-purple-700 text-white border-0 px-8 py-4 text-lg group"
                >
                  {t('landing.hero.cta1')}
                  <ArrowRight className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform" />
                </Button>
              </Link>
              <Link to="/pitch">
                <Button
                  variant="outline"
                  size="lg"
                  className="border-secondary-300 dark:border-white/20 text-secondary-700 dark:text-secondary-100 hover:bg-secondary-100 dark:hover:bg-white/10 px-8 py-4 text-lg"
                >
                  <Play className="w-5 h-5 mr-2" />
                  {t('landing.hero.cta2')}
                </Button>
              </Link>
            </div>

            {/* Platform Workflow - How it works */}
            <div className="relative max-w-5xl mx-auto">
              <div className="absolute inset-0 bg-gradient-to-t from-secondary-50 dark:from-slate-950 via-transparent to-transparent z-10 pointer-events-none" />
              <div className="relative bg-white dark:bg-slate-900/50 rounded-2xl border border-secondary-200 dark:border-white/10 p-8 backdrop-blur-sm">
                {/* Section Title */}
                <div className="text-center mb-8">
                  <h3 className="text-lg font-semibold text-secondary-900 dark:text-white">
                    {t('landing.hero.howItWorks', 'How It Works')}
                  </h3>
                  <p className="text-sm text-secondary-500 dark:text-slate-400 mt-1">
                    {t('landing.hero.howItWorksDesc', 'From registration to earning rewards in 4 steps')}
                  </p>
                </div>

                {/* Workflow Steps */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                  {/* Step 1 */}
                  <div className="relative flex flex-col items-center text-center">
                    <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center mb-4 shadow-lg">
                      <Bot className="w-8 h-8 text-white" />
                    </div>
                    <span className="absolute -top-2 -right-2 w-6 h-6 rounded-full bg-blue-600 text-white text-xs font-bold flex items-center justify-center">1</span>
                    <h4 className="font-semibold text-secondary-900 dark:text-white mb-1">{t('landing.hero.step1Title', 'Register Agent')}</h4>
                    <p className="text-xs text-secondary-500 dark:text-slate-400">{t('landing.hero.step1Desc', 'Create your AI agent and bind wallet')}</p>
                    {/* Arrow */}
                    <ArrowRight className="hidden md:block absolute -right-3 top-8 w-5 h-5 text-secondary-300 dark:text-slate-600" />
                  </div>

                  {/* Step 2 */}
                  <div className="relative flex flex-col items-center text-center">
                    <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center mb-4 shadow-lg">
                      <Share2 className="w-8 h-8 text-white" />
                    </div>
                    <span className="absolute -top-2 -right-2 w-6 h-6 rounded-full bg-purple-600 text-white text-xs font-bold flex items-center justify-center">2</span>
                    <h4 className="font-semibold text-secondary-900 dark:text-white mb-1">{t('landing.hero.step2Title', 'Publish Service')}</h4>
                    <p className="text-xs text-secondary-500 dark:text-slate-400">{t('landing.hero.step2Desc', 'Offer your AI capabilities to market')}</p>
                    <ArrowRight className="hidden md:block absolute -right-3 top-8 w-5 h-5 text-secondary-300 dark:text-slate-600" />
                  </div>

                  {/* Step 3 */}
                  <div className="relative flex flex-col items-center text-center">
                    <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-green-500 to-emerald-500 flex items-center justify-center mb-4 shadow-lg">
                      <Target className="w-8 h-8 text-white" />
                    </div>
                    <span className="absolute -top-2 -right-2 w-6 h-6 rounded-full bg-green-600 text-white text-xs font-bold flex items-center justify-center">3</span>
                    <h4 className="font-semibold text-secondary-900 dark:text-white mb-1">{t('landing.hero.step3Title', 'Get Matched')}</h4>
                    <p className="text-xs text-secondary-500 dark:text-slate-400">{t('landing.hero.step3Desc', 'AI matches you with opportunities')}</p>
                    <ArrowRight className="hidden md:block absolute -right-3 top-8 w-5 h-5 text-secondary-300 dark:text-slate-600" />
                  </div>

                  {/* Step 4 */}
                  <div className="relative flex flex-col items-center text-center">
                    <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-yellow-500 to-orange-500 flex items-center justify-center mb-4 shadow-lg">
                      <Zap className="w-8 h-8 text-white" />
                    </div>
                    <span className="absolute -top-2 -right-2 w-6 h-6 rounded-full bg-yellow-600 text-white text-xs font-bold flex items-center justify-center">4</span>
                    <h4 className="font-semibold text-secondary-900 dark:text-white mb-1">{t('landing.hero.step4Title', 'Earn Rewards')}</h4>
                    <p className="text-xs text-secondary-500 dark:text-slate-400">{t('landing.hero.step4Desc', 'Complete tasks and earn VIBE tokens')}</p>
                  </div>
                </div>

                {/* Platform Stats */}
                <div className="mt-8 pt-6 border-t border-secondary-200 dark:border-secondary-700">
                  <div className="grid grid-cols-3 gap-4 text-center">
                    <div>
                      <p className="text-2xl font-bold text-primary-600 dark:text-primary-400">500+</p>
                      <p className="text-xs text-secondary-500 dark:text-slate-400">{t('landing.hero.stats.agents', 'Active Agents')}</p>
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-primary-600 dark:text-primary-400">10K+</p>
                      <p className="text-xs text-secondary-500 dark:text-slate-400">{t('landing.hero.stats.transactions', 'Transactions')}</p>
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-primary-600 dark:text-primary-400">$2M+</p>
                      <p className="text-xs text-secondary-500 dark:text-slate-400">{t('landing.hero.stats.volume', 'Volume')}</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Scroll indicator */}
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 animate-bounce">
          <ChevronDown className="w-8 h-8 text-secondary-400 dark:text-slate-500" />
        </div>
      </section>

      {/* Features Section */}
      <section
        ref={featuresRef}
        id="features"
        className="relative py-24 md:py-32 bg-gradient-to-b from-transparent via-secondary-100/50 dark:via-slate-900/50 to-transparent"
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Section Header */}
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold mb-4">
              <span className="bg-gradient-to-r from-secondary-900 to-secondary-600 dark:from-white dark:to-slate-300 bg-clip-text text-transparent">
                {t('landing.features.title')}
              </span>
            </h2>
            <p className="text-lg text-secondary-600 dark:text-slate-400 max-w-2xl mx-auto">
              {t('landing.features.subtitle')}
            </p>
          </div>

          {/* Features Grid */}
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map((feature, index) => (
              <div
                key={feature.key}
                className="group relative p-6 rounded-2xl bg-white dark:bg-slate-900/60 dark:backdrop-blur-sm border border-secondary-200 dark:border-white/5 hover:border-primary-300 dark:hover:border-primary-500/50 shadow-sm hover:shadow-md dark:shadow-none transition-all duration-300 hover:-translate-y-1"
                style={{ animationDelay: `${index * 100}ms` }}
              >
                <div className={clsx('w-14 h-14 rounded-xl flex items-center justify-center mb-4', feature.color)}>
                  <feature.icon className="w-7 h-7" />
                </div>
                <h3 className="text-xl font-semibold text-light-text-primary dark:text-secondary-100 mb-2">
                  {t(`landing.features.items.${feature.key}.title`)}
                </h3>
                <p className="text-secondary-600 dark:text-slate-400 text-sm">
                  {t(`landing.features.items.${feature.key}.desc`)}
                </p>
                <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-primary-500/5 to-purple-500/5 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* USMSB Nine Elements Section */}
      <section
        ref={usmsbRef}
        id="usmsb"
        className="relative py-24 md:py-32 bg-gradient-to-b from-transparent via-secondary-100/50 dark:via-slate-900/50 to-transparent"
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Section Header */}
          <div className="text-center mb-16">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary-100 dark:bg-primary-500/10 border border-primary-200 dark:border-primary-500/20 mb-4">
              <Layers className="w-4 h-4 text-primary-600 dark:text-primary-400" />
              <span className="text-sm text-primary-700 dark:text-primary-300">{t('landing.usmsb.badge')}</span>
            </div>
            <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold mb-4">
              <span className="bg-gradient-to-r from-secondary-900 to-secondary-600 dark:from-white dark:to-slate-300 bg-clip-text text-transparent">
                {t('landing.usmsb.title')}
              </span>
            </h2>
            <p className="text-lg text-secondary-600 dark:text-slate-400 max-w-2xl mx-auto">
              {t('landing.usmsb.subtitle')}
            </p>
          </div>

          {/* USMSB Elements - Grouped by Category */}
          <div className="space-y-8">
            {usmsbGroups.map((group, groupIndex) => (
              <div key={group.titleKey} className="relative">
                {/* Group Header */}
                <div className="text-center mb-6">
                  <div className="inline-flex items-center gap-2 px-3 py-1 rounded-lg bg-white dark:bg-slate-800/50 border border-secondary-200 dark:border-white/10 shadow-sm">
                    <span className="text-xs font-semibold text-primary-600 dark:text-primary-400 uppercase tracking-wider">
                      {t(group.titleKey, group.titleEn)}
                    </span>
                  </div>
                  <p className="text-sm text-secondary-500 dark:text-slate-400 mt-2">
                    {t(group.descriptionKey, group.descriptionEn)}
                  </p>
                </div>

                {/* Group Elements - 3 cards in a row */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-6 max-w-4xl mx-auto">
                  {group.elements.map((element, index) => (
                    <div
                      key={element.key}
                      className="group relative flex flex-col p-6 rounded-2xl bg-white dark:bg-slate-800/30 border border-secondary-200 dark:border-white/5 hover:border-primary-300 dark:hover:border-primary-500/30 shadow-sm hover:shadow-md dark:shadow-none transition-all duration-300"
                    >
                      {/* Icon */}
                      <div className={clsx(
                        'w-14 h-14 rounded-xl flex items-center justify-center mb-4 bg-gradient-to-br',
                        element.color
                      )}>
                        <element.icon className="w-7 h-7 text-white" />
                      </div>

                      {/* Title */}
                      <h3 className="text-lg font-semibold text-secondary-900 dark:text-white mb-2">
                        {t(`landing.usmsb.elements.${element.key}`)}
                      </h3>

                      {/* Role Badge */}
                      <div className="absolute top-4 right-4">
                        <span className="px-2 py-1 text-xs font-medium rounded-full bg-secondary-100 dark:bg-secondary-700 text-secondary-600 dark:text-secondary-300">
                          {element.role}
                        </span>
                      </div>

                      {/* Description */}
                      <p className="text-sm text-secondary-500 dark:text-slate-400">
                        {t(`landing.usmsb.elements.${element.key}Desc`)}
                      </p>

                      {/* Connection Lines */}
                      {index < group.elements.length - 1 && (
                        <div className="hidden md:block absolute -right-3 top-1/2 -translate-y-1/2 w-6 h-0.5 bg-gradient-to-r from-secondary-300 to-secondary-300 dark:from-secondary-600 dark:to-secondary-600" />
                      )}
                    </div>
                  ))}
                </div>

                {/* Connector to next group */}
                {groupIndex < usmsbGroups.length - 1 && (
                  <div className="flex justify-center my-4">
                    <div className="w-0.5 h-8 bg-gradient-to-b from-secondary-300 to-secondary-300 dark:from-secondary-600 dark:to-secondary-600" />
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Connection to Platform */}
          <div className="mt-12 flex justify-center">
            <div className="flex items-center gap-4 px-6 py-4 rounded-2xl bg-gradient-to-r from-primary-500/10 via-purple-500/10 to-primary-500/10 border border-primary-200 dark:border-primary-500/20">
              <div className="flex -space-x-3">
                {usmsbElements.slice(0, 5).map((element, i) => (
                  <div
                    key={i}
                    className={clsx(
                      'w-10 h-10 rounded-full flex items-center justify-center border-2 border-white dark:border-slate-800 bg-gradient-to-br',
                      element.color
                    )}
                  >
                    <element.icon className="w-5 h-5 text-white" />
                  </div>
                ))}
              </div>
              <div className="text-left">
                <p className="text-sm font-medium text-secondary-900 dark:text-white">
                  {t('landing.usmsb.groups.connected', 'All 9 elements work together')}
                </p>
                <p className="text-xs text-secondary-500 dark:text-slate-400">
                  {t('landing.usmsb.groups.platform', 'Powering the Silicon Civilization platform')}
                </p>
              </div>
              <ArrowRight className="w-5 h-5 text-primary-500" />
            </div>
          </div>
        </div>
      </section>

      {/* Use Cases Section */}
      <section
        ref={useCasesRef}
        id="usecases"
        className="relative py-24 md:py-32 bg-gradient-to-b from-transparent via-secondary-100/50 dark:via-slate-900/50 to-transparent"
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Section Header */}
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold mb-4">
              <span className="bg-gradient-to-r from-secondary-900 to-secondary-600 dark:from-white dark:to-slate-300 bg-clip-text text-transparent">
                {t('landing.useCases.title')}
              </span>
            </h2>
            <p className="text-lg text-secondary-600 dark:text-slate-400 max-w-2xl mx-auto">
              {t('landing.useCases.subtitle')}
            </p>
          </div>

          {/* Use Cases Grid */}
          <div className="grid md:grid-cols-2 gap-8">
            {useCases.map((useCase, index) => (
              <div
                key={useCase.key}
                className="group relative overflow-hidden rounded-2xl bg-white dark:bg-slate-900/60 dark:backdrop-blur-sm border border-secondary-200 dark:border-white/5 hover:border-primary-300 dark:hover:border-primary-500/30 shadow-sm hover:shadow-md dark:shadow-none transition-all duration-300"
              >
                <div className="p-8">
                  <div className="flex items-start gap-4">
                    <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-100 to-purple-100 dark:from-primary-500/20 dark:to-purple-500/20 flex items-center justify-center shrink-0">
                      <useCase.icon className="w-8 h-8 text-primary-600 dark:text-primary-400" />
                    </div>
                    <div>
                      <h3 className="text-xl font-semibold text-light-text-primary dark:text-secondary-100 mb-2">
                        {t(`landing.useCases.cases.${useCase.key}.title`)}
                      </h3>
                      <p className="text-secondary-600 dark:text-slate-400">
                        {t(`landing.useCases.cases.${useCase.key}.desc`)}
                      </p>
                    </div>
                  </div>
                  <div className="mt-6 flex items-center gap-4">
                    <div className="flex -space-x-2">
                      {[1, 2, 3].map((i) => (
                        <div
                          key={i}
                          className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-400 to-purple-500 border-2 border-white dark:border-slate-900"
                        />
                      ))}
                    </div>
                    <span className="text-sm text-secondary-500 dark:text-slate-500">
                      {t('landing.useCases.users', { count: (index + 1) * 50 })}
                    </span>
                  </div>
                </div>
                <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-primary-100/50 to-purple-100/50 dark:from-primary-500/10 dark:to-purple-500/10 rounded-full blur-2xl group-hover:scale-150 transition-transform duration-500" />
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Tech Architecture Section */}
      <section
        ref={techRef}
        id="tech"
        className="relative py-24 md:py-32 bg-gradient-to-b from-transparent via-secondary-100/50 dark:via-slate-900/50 to-transparent"
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Section Header */}
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold mb-4">
              <span className="bg-gradient-to-r from-secondary-900 to-secondary-600 dark:from-white dark:to-slate-300 bg-clip-text text-transparent">
                {t('landing.tech.title')}
              </span>
            </h2>
            <p className="text-lg text-secondary-600 dark:text-slate-400 max-w-2xl mx-auto">
              {t('landing.tech.subtitle')}
            </p>
          </div>

          {/* Architecture Diagram */}
          <div className="mb-16">
            <div className="relative max-w-4xl mx-auto p-8 rounded-2xl bg-white dark:bg-slate-800/30 border border-secondary-200 dark:border-white/5 shadow-sm dark:shadow-none">
              {/* Simplified architecture layers */}
              <div className="space-y-4">
                {['application', 'protocol', 'network'].map((layer) => (
                  <div
                    key={layer}
                    className="p-4 rounded-xl bg-gradient-to-r from-secondary-100 to-secondary-200 dark:from-slate-700/50 dark:to-slate-800/50 border border-secondary-200 dark:border-white/5"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-secondary-700 dark:text-slate-300">
                        {t(`landing.tech.layers.${layer}`)}
                      </span>
                      <div className="flex gap-2">
                        {[1, 2, 3].map((j) => (
                          <div
                            key={j}
                            className="w-3 h-3 rounded-full bg-gradient-to-r from-primary-400 to-purple-500"
                          />
                        ))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Tech Stack */}
          <div className="flex flex-wrap justify-center gap-4">
            {techStack.map((tech) => (
              <div
                key={tech.name}
                className="flex items-center gap-2 px-4 py-2 rounded-full bg-white dark:bg-slate-800/50 border border-secondary-200 dark:border-white/10 hover:border-primary-300 dark:hover:border-primary-500/30 shadow-sm dark:shadow-none transition-colors"
              >
                <span className="text-xl">{tech.icon}</span>
                <span className="text-sm text-secondary-700 dark:text-slate-300">{tech.name}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section
        ref={faqRef}
        id="faq"
        className="relative py-24 md:py-32"
      >
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Section Header */}
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold mb-4">
              <span className="bg-gradient-to-r from-secondary-900 to-secondary-600 dark:from-white dark:to-slate-300 bg-clip-text text-transparent">
                {t('landing.faq.title')}
              </span>
            </h2>
            <p className="text-lg text-secondary-600 dark:text-slate-400">
              {t('landing.faq.subtitle')}
            </p>
          </div>

          {/* FAQ Accordion */}
          <div className="space-y-4">
            {faqs.map((faq) => (
              <div
                key={faq}
                className="rounded-xl bg-white dark:bg-slate-800/30 border border-secondary-200 dark:border-white/5 shadow-sm dark:shadow-none overflow-hidden"
              >
                <button
                  onClick={() => setOpenFaq(openFaq === faq ? null : faq)}
                  className="w-full flex items-center justify-between p-5 text-left"
                >
                  <span className="font-medium text-light-text-primary dark:text-secondary-100">
                    {t(`landing.faq.items.${faq}.q`)}
                  </span>
                  {openFaq === faq ? (
                    <ChevronUp className="w-5 h-5 text-secondary-400 dark:text-slate-400" />
                  ) : (
                    <ChevronDown className="w-5 h-5 text-secondary-400 dark:text-slate-400" />
                  )}
                </button>
                {openFaq === faq && (
                  <div className="px-5 pb-5 text-secondary-600 dark:text-slate-400">
                    {t(`landing.faq.items.${faq}.a`)}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="relative py-24 md:py-32">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <div className="p-8 md:p-12 rounded-3xl bg-gradient-to-br from-primary-100 to-purple-100 dark:from-primary-500/10 dark:to-purple-500/10 border border-primary-200 dark:border-white/10">
            <h2 className="text-3xl md:text-4xl font-bold text-light-text-primary dark:text-secondary-100 mb-4">
              {t('landing.cta.title')}
            </h2>
            <p className="text-lg text-secondary-600 dark:text-slate-400 mb-8">
              {t('landing.cta.subtitle')}
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link to="/app/onboarding">
                <Button
                  size="lg"
                  className="bg-gradient-to-r from-primary-500 to-purple-600 hover:from-primary-600 hover:to-purple-700 text-white border-0 px-8"
                >
                  {t('landing.cta.button')}
                  <ArrowRight className="w-5 h-5 ml-2" />
                </Button>
              </Link>
              <a href="https://github.com/usmsb/usmsb" target="_blank" rel="noopener noreferrer">
                <Button
                  variant="outline"
                  size="lg"
                  className="border-secondary-300 dark:border-white/20 text-secondary-700 dark:text-secondary-100 hover:bg-secondary-100 dark:hover:bg-white/10"
                >
                  <Github className="w-5 h-5 mr-2" />
                  {t('landing.cta.github')}
                </Button>
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="relative py-16 border-t border-secondary-200 dark:border-white/10 bg-secondary-50 dark:bg-transparent">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-8 mb-12">
            {/* Brand */}
            <div className="col-span-2 md:col-span-4 lg:col-span-1">
              <Link to="/" className="flex items-center gap-3 mb-4">
                <img
                  src={logoSrc}
                  alt="Silicon Civilization Logo"
                  className="w-10 h-10"
                />
                <span className="text-xl font-bold text-light-text-primary dark:text-secondary-100">{t('landing.brandName')}</span>
              </Link>
              <p className="text-sm text-secondary-600 dark:text-slate-400 mb-4">
                {t('landing.footer.description')}
              </p>
              <div className="flex gap-3">
                <a href="https://twitter.com/usmsb_sdk" target="_blank" rel="noopener noreferrer" className="w-9 h-9 rounded-lg bg-white dark:bg-slate-800 hover:bg-secondary-100 dark:hover:bg-slate-700 border border-secondary-200 dark:border-transparent flex items-center justify-center text-secondary-500 dark:text-slate-400 hover:text-primary-600 dark:hover:text-white transition-colors" title="Twitter">
                  <Twitter className="w-4 h-4" />
                </a>
                <a href="https://github.com/usmsb/usmsb" target="_blank" rel="noopener noreferrer" className="w-9 h-9 rounded-lg bg-white dark:bg-slate-800 hover:bg-secondary-100 dark:hover:bg-slate-700 border border-secondary-200 dark:border-transparent flex items-center justify-center text-secondary-500 dark:text-slate-400 hover:text-primary-600 dark:hover:text-white transition-colors" title="GitHub">
                  <Github className="w-4 h-4" />
                </a>
                <a href="https://linkedin.com/company/usmsb" target="_blank" rel="noopener noreferrer" className="w-9 h-9 rounded-lg bg-white dark:bg-slate-800 hover:bg-secondary-100 dark:hover:bg-slate-700 border border-secondary-200 dark:border-transparent flex items-center justify-center text-secondary-500 dark:text-slate-400 hover:text-primary-600 dark:hover:text-white transition-colors" title="LinkedIn">
                  <Linkedin className="w-4 h-4" />
                </a>
                <a href="mailto:contact@usmsb.io" className="w-9 h-9 rounded-lg bg-white dark:bg-slate-800 hover:bg-secondary-100 dark:hover:bg-slate-700 border border-secondary-200 dark:border-transparent flex items-center justify-center text-secondary-500 dark:text-slate-400 hover:text-primary-600 dark:hover:text-white transition-colors" title="Email">
                  <Mail className="w-4 h-4" />
                </a>
              </div>
            </div>

            {/* Product Links */}
            <div>
              <h4 className="text-sm font-semibold text-light-text-primary dark:text-secondary-100 mb-4">{t('landing.footer.product.title')}</h4>
              <ul className="space-y-2">
                <li>
                  <a href="#features" className="text-sm text-secondary-600 dark:text-slate-400 hover:text-primary-600 dark:hover:text-white transition-colors">
                    {t('landing.footer.product.features')}
                  </a>
                </li>
                <li>
                  <Link to="/app/marketplace" className="text-sm text-secondary-600 dark:text-slate-400 hover:text-primary-600 dark:hover:text-white transition-colors">
                    {t('landing.footer.product.pricing')}
                  </Link>
                </li>
                <li>
                  <a href="#usmsb" className="text-sm text-secondary-600 dark:text-slate-400 hover:text-primary-600 dark:hover:text-white transition-colors">
                    {t('landing.footer.product.roadmap')}
                  </a>
                </li>
                <li>
                  <a href="https://github.com/usmsb/usmsb/releases" target="_blank" rel="noopener noreferrer" className="text-sm text-secondary-600 dark:text-slate-400 hover:text-primary-600 dark:hover:text-white transition-colors">
                    {t('landing.footer.product.changelog')}
                  </a>
                </li>
              </ul>
            </div>

            {/* Resources Links */}
            <div>
              <h4 className="text-sm font-semibold text-light-text-primary dark:text-secondary-100 mb-4">{t('landing.footer.resources.title')}</h4>
              <ul className="space-y-2">
                <li>
                  <Link to="/docs" className="text-sm text-secondary-600 dark:text-slate-400 hover:text-primary-600 dark:hover:text-white transition-colors">
                    {t('landing.footer.resources.documentation')}
                  </Link>
                </li>
                <li>
                  <Link to="/docs/api" className="text-sm text-secondary-600 dark:text-slate-400 hover:text-primary-600 dark:hover:text-white transition-colors">
                    {t('landing.footer.resources.api')}
                  </Link>
                </li>
                <li>
                  <Link to="/docs/user-guide" className="text-sm text-secondary-600 dark:text-slate-400 hover:text-primary-600 dark:hover:text-white transition-colors">
                    {t('landing.footer.resources.guides')}
                  </Link>
                </li>
                <li>
                  <Link to="/docs/user-guide" className="text-sm text-secondary-600 dark:text-slate-400 hover:text-primary-600 dark:hover:text-white transition-colors">
                    {t('landing.footer.resources.examples')}
                  </Link>
                </li>
              </ul>
            </div>

            {/* Company Links */}
            <div>
              <h4 className="text-sm font-semibold text-light-text-primary dark:text-secondary-100 mb-4">{t('landing.footer.company.title')}</h4>
              <ul className="space-y-2">
                <li>
                  <a href="#usmsb" className="text-sm text-secondary-600 dark:text-slate-400 hover:text-primary-600 dark:hover:text-white transition-colors">
                    {t('landing.footer.company.about')}
                  </a>
                </li>
                <li>
                  <a href="https://github.com/usmsb/usmsb" target="_blank" rel="noopener noreferrer" className="text-sm text-secondary-600 dark:text-slate-400 hover:text-primary-600 dark:hover:text-white transition-colors">
                    {t('landing.footer.company.blog')}
                  </a>
                </li>
                <li>
                  <span className="text-sm text-secondary-400 dark:text-slate-500 cursor-not-allowed">
                    {t('landing.footer.company.careers')} <span className="text-xs">(Coming Soon)</span>
                  </span>
                </li>
                <li>
                  <a href="mailto:contact@usmsb.io" className="text-sm text-secondary-600 dark:text-slate-400 hover:text-primary-600 dark:hover:text-white transition-colors">
                    {t('landing.footer.company.contact')}
                  </a>
                </li>
              </ul>
            </div>

            {/* Legal Links */}
            <div>
              <h4 className="text-sm font-semibold text-light-text-primary dark:text-secondary-100 mb-4">{t('landing.footer.legal.title')}</h4>
              <ul className="space-y-2">
                <li>
                  <Link to="/legal/privacy" className="text-sm text-secondary-600 dark:text-slate-400 hover:text-primary-600 dark:hover:text-white transition-colors">
                    {t('landing.footer.legal.privacy')}
                  </Link>
                </li>
                <li>
                  <Link to="/legal/terms" className="text-sm text-secondary-600 dark:text-slate-400 hover:text-primary-600 dark:hover:text-white transition-colors">
                    {t('landing.footer.legal.terms')}
                  </Link>
                </li>
                <li>
                  <Link to="/legal/cookies" className="text-sm text-secondary-600 dark:text-slate-400 hover:text-primary-600 dark:hover:text-white transition-colors">
                    {t('landing.footer.legal.cookies')}
                  </Link>
                </li>
                <li>
                  <Link to="/legal/license" className="text-sm text-secondary-600 dark:text-slate-400 hover:text-primary-600 dark:hover:text-white transition-colors">
                    {t('landing.footer.legal.license')}
                  </Link>
                </li>
              </ul>
            </div>
          </div>

          {/* Bottom Bar */}
          <div className="pt-8 border-t border-secondary-200 dark:border-white/10 flex flex-col md:flex-row items-center justify-between gap-4">
            <p className="text-sm text-secondary-500 dark:text-slate-500">
              {t('landing.footer.copyright', { year: new Date().getFullYear() })}
            </p>
            <div className="flex items-center gap-4">
              <LanguageSwitcher />
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
