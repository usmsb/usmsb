import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useParams, useNavigate, Link } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { ArchitectureDiagram, AsciiDiagram } from '@/components/ArchitectureDiagram'
import {
  BookOpen,
  FileText,
  Code,
  User,
  Shield,
  FileCheck,
  Copyright,
  ChevronRight,
  Menu,
  X,
  ExternalLink,
  ArrowLeft,
  List,
  Copy,
  Check,
  Rocket,
  Globe,
  Layers,
  Wallet,
  Cpu,
  Network,
  FileCode,
  Settings,
  Puzzle,
  Users,
  Binary,
  BookMarked,
} from 'lucide-react'
import clsx from 'clsx'

interface DocItem {
  id: string
  file: string
  icon: typeof BookOpen
  titleKey: string
  // Optional section header
  isSectionHeader?: boolean
  sectionKey?: string
}

// 文档文件映射 - 支持中英文版本
const docFiles: Record<string, { en: string; zh: string }> = {
  'whitepaper': { en: '/docs/whitepaper.md', zh: '/docs/whitepaper.zh.md' },
  'user-guide': { en: '/docs/user-guide.md', zh: '/docs/user-guide.zh.md' },
  'deployment': { en: '/docs/deployment.md', zh: '/docs/deployment.zh.md' },
  'concepts': { en: '/docs/concepts.md', zh: '/docs/concepts.zh.md' },
  'agent-sdk': { en: '/docs/agent-sdk.md', zh: '/docs/agent-sdk.zh.md' },
  'usmsb-sdk': { en: '/docs/usmsb-sdk.md', zh: '/docs/usmsb-sdk.zh.md' },
  'meta-agent-usage': { en: '/docs/meta-agent-usage.md', zh: '/docs/meta-agent-usage.zh.md' },
  'integration-guide': { en: '/docs/integration-guide.md', zh: '/docs/integration-guide.zh.md' },
  'blockchain-whitepaper': { en: '/docs/blockchain-whitepaper.md', zh: '/docs/blockchain-whitepaper.zh.md' },
  'smart-contracts': { en: '/docs/smart-contracts.md', zh: '/docs/smart-contracts.zh.md' },
  'api': { en: '/docs/api-reference.md', zh: '/docs/api-reference.zh.md' },
  'cases': { en: '/docs/cases.md', zh: '/docs/cases.zh.md' },
  'privacy': { en: '/docs/privacy-policy.md', zh: '/docs/privacy-policy.md' },
  'terms': { en: '/docs/terms-of-service.md', zh: '/docs/terms-of-service.md' },
  'copyright': { en: '/docs/copyright.md', zh: '/docs/copyright.md' },
}

// 获取当前语言对应的文档文件
const getDocFile = (docId: string, lang: string): string => {
  const files = docFiles[docId]
  if (!files) return ''
  return lang === 'zh' ? files.zh : files.en
}

const docItems: DocItem[] = [
  // ========== 1. Getting Started / 入门 ==========
  { id: 'section-getting-started', file: '', icon: BookOpen, titleKey: '', isSectionHeader: true, sectionKey: 'docs.sectionGettingStarted' },
  { id: 'whitepaper', file: '', icon: BookOpen, titleKey: 'docs.whitepaper' },

  // ========== 2. User Guide / 用户指南 ==========
  { id: 'section-user-guide', file: '', icon: User, titleKey: '', isSectionHeader: true, sectionKey: 'docs.sectionUserGuide' },
  { id: 'user-guide', file: '', icon: User, titleKey: 'docs.userGuide' },
  { id: 'deployment', file: '', icon: Rocket, titleKey: 'docs.deployment' },
  { id: 'concepts', file: '', icon: FileText, titleKey: 'docs.concepts' },

  // ========== 3. SDK Development / SDK开发 ==========
  { id: 'section-sdk-dev', file: '', icon: Puzzle, titleKey: '', isSectionHeader: true, sectionKey: 'docs.sectionSdkDev' },
  { id: 'agent-sdk', file: '', icon: Puzzle, titleKey: 'docs.agentSdk' },
  { id: 'usmsb-sdk', file: '', icon: Cpu, titleKey: 'docs.usmsbSdk' },
  { id: 'meta-agent-usage', file: '', icon: Globe, titleKey: 'docs.metaAgentUsage' },
  { id: 'integration-guide', file: '', icon: BookMarked, titleKey: 'docs.integrationGuide' },

  // ========== 4. Technical Reference / 技术参考 ==========

  // 技术参考 ==========
  { id: 'section-tech-ref', file: '', icon: Code, titleKey: '', isSectionHeader: true, sectionKey: 'docs.sectionTechRef' },
  { id: 'blockchain-whitepaper', file: '', icon: Binary, titleKey: 'docs.blockchainWhitepaper' },
  { id: 'smart-contracts', file: '', icon: FileCode, titleKey: 'docs.smartContracts' },
  { id: 'api', file: '', icon: Code, titleKey: 'docs.apiReference' },

  // ========== 5. Use Cases / 应用案例 ==========
  { id: 'section-use-cases', file: '', icon: Layers, titleKey: '', isSectionHeader: true, sectionKey: 'docs.sectionUseCases' },
  { id: 'cases', file: '', icon: Layers, titleKey: 'docs.cases' },

  // ========== 6. Legal / 法律合规 ==========
  { id: 'section-legal', file: '', icon: Shield, titleKey: '', isSectionHeader: true, sectionKey: 'docs.sectionLegal' },
  { id: 'privacy', file: '', icon: Shield, titleKey: 'docs.privacyPolicy' },
  { id: 'terms', file: '', icon: FileCheck, titleKey: 'docs.termsOfService' },
  { id: 'copyright', file: '', icon: Copyright, titleKey: 'docs.copyright' },
]

interface TocItem {
  id: string
  text: string
  level: number
}

// Code block component with copy button and line numbers
function CodeBlock({
  className,
  children,
  ...props
}: {
  className?: string
  children?: React.ReactNode
  [key: string]: unknown
}) {
  const [copied, setCopied] = useState(false)
  const match = /language-(\w+)/.exec(className || '')
  const language = match ? match[1] : ''

  // Get code content as string
  const codeContent = typeof children === 'string'
    ? children
    : children?.toString() || ''

  // Split into lines for line numbers
  const lines = codeContent.split('\n')
  const lineCount = lines.length
  const lineNumberWidth = lineCount.toString().length * 0.6 + 1

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(codeContent.replace(/\n$/, ''))
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // Fallback for older browsers
      const textArea = document.createElement('textarea')
      textArea.value = codeContent.replace(/\n$/, '')
      document.body.appendChild(textArea)
      textArea.select()
      document.execCommand('copy')
      document.body.removeChild(textArea)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <div className="relative group my-6">
      {/* Language badge and copy button */}
      <div className={clsx(
        'absolute top-0 right-0 flex items-center gap-2 px-3 py-2',
        'bg-secondary-800 dark:bg-secondary-900 rounded-t-lg',
        'border-b border-secondary-700 z-10'
      )}>
        {language && (
          <span className="text-xs font-medium text-secondary-400 uppercase tracking-wider">
            {language}
          </span>
        )}
        <button
          onClick={handleCopy}
          className={clsx(
            'p-1.5 rounded-md transition-all duration-200',
            'hover:bg-secondary-700 active:scale-95',
            copied
              ? 'text-green-400 bg-green-400/10'
              : 'text-secondary-400 hover:text-white'
          )}
          title={copied ? 'Copied!' : 'Copy code'}
          aria-label="Copy code to clipboard"
        >
          {copied ? <Check size={14} /> : <Copy size={14} />}
        </button>
      </div>

      {/* Code with line numbers */}
      <pre
        className={clsx(
          'pt-10 pb-4 px-4 overflow-x-auto',
          'bg-secondary-900 dark:bg-secondary-950',
          'rounded-lg border border-secondary-700',
          'text-sm leading-relaxed'
        )}
      >
        <code
          className={clsx(
            className,
            'block'
          )}
          {...props}
        >
          {lines.map((line, index) => (
            <div key={index} className="flex">
              {/* Line number */}
              <span
                className={clsx(
                  'select-none text-secondary-600 dark:text-secondary-500',
                  'text-right pr-4 flex-shrink-0',
                  'border-r border-secondary-700 mr-4'
                )}
                style={{ width: `${lineNumberWidth}rem` }}
                aria-hidden="true"
              >
                {index + 1}
              </span>
              {/* Line content */}
              <span className="flex-1 text-secondary-100">
                {line || ' '}
              </span>
            </div>
          ))}
        </code>
      </pre>
    </div>
  )
}

// Inline code component
function InlineCode({
  children,
  ...props
}: {
  children?: React.ReactNode
  [key: string]: unknown
}) {
  return (
    <code
      className={clsx(
        'px-1.5 py-0.5 rounded',
        'bg-primary-100 dark:bg-primary-900/30',
        'text-primary-700 dark:text-primary-300',
        'text-[0.9em] font-medium',
        'border border-primary-200 dark:border-primary-800'
      )}
      {...props}
    >
      {children}
    </code>
  )
}

export default function DocsPage() {
  const { t, i18n } = useTranslation()
  const { docId } = useParams<{ docId?: string }>()
  const navigate = useNavigate()

  // 语言状态 - 监听i18n.language变化
  const [currentLang, setCurrentLang] = useState<string>(() =>
    i18n.language?.startsWith('zh') ? 'zh' : 'en'
  )

  // 监听语言变化
  useEffect(() => {
    const newLang = i18n.language?.startsWith('zh') ? 'zh' : 'en'
    setCurrentLang(newLang)
  }, [i18n.language])

  const [selectedDoc, setSelectedDoc] = useState<string>(docId || 'whitepaper')
  const [content, setContent] = useState<string>('')
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(false)
  const [tocItems, setTocItems] = useState<TocItem[]>([])
  const [showToc, setShowToc] = useState<boolean>(true)

  // Extract TOC from content
  const extractToc = useCallback((markdown: string) => {
    const headings = markdown.match(/^#{1,3}\s+.+$/gm) || []
    return headings.map((heading) => {
      const level = heading.match(/^#+/)?.[0].length || 1
      const text = heading.replace(/^#+\s+/, '')
      const id = text
        .toLowerCase()
        .replace(/[^\w\s-]/g, '')
        .replace(/\s+/g, '-')
      return { id, text, level }
    })
  }, [])

  useEffect(() => {
    const fetchContent = async () => {
      setLoading(true)
      setError(null)
      const doc = docItems.find((d) => d.id === selectedDoc)
      if (!doc || doc.isSectionHeader) {
        setError('Document not found')
        setLoading(false)
        return
      }

      // 根据当前语言获取文档文件
      const docFile = getDocFile(doc.id, currentLang)
      if (!docFile) {
        setError('Document not found')
        setLoading(false)
        return
      }

      try {
        const response = await fetch(docFile)
        if (!response.ok) {
          // 如果指定语言版本不存在，尝试英文版本
          const fallbackFile = getDocFile(doc.id, 'en')
          if (fallbackFile !== docFile) {
            const fallbackResponse = await fetch(fallbackFile)
            if (!fallbackResponse.ok) {
              throw new Error(`Failed to load document: ${response.status}`)
            }
            const text = await fallbackResponse.text()
            setContent(text)
            setTocItems(extractToc(text))
            setLoading(false)
            return
          }
          throw new Error(`Failed to load document: ${response.status}`)
        }
        const text = await response.text()
        setContent(text)
        setTocItems(extractToc(text))
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load document')
      } finally {
        setLoading(false)
      }
    }

    fetchContent()
  }, [selectedDoc, currentLang, extractToc])

  // Sync URL with selected doc
  const handleDocSelect = useCallback(
    (docId: string) => {
      setSelectedDoc(docId)
      setSidebarOpen(false)
      navigate(`/docs/${docId}`, { replace: true })
      window.scrollTo({ top: 0, behavior: 'smooth' })
    },
    [navigate]
  )

  // Handle URL param changes
  useEffect(() => {
    if (docId && docId !== selectedDoc) {
      const validDoc = docItems.find((d) => d.id === docId)
      if (validDoc) {
        setSelectedDoc(docId)
      }
    }
  }, [docId, selectedDoc])

  const currentDoc = docItems.find((d) => d.id === selectedDoc)

  // Scroll to heading
  const scrollToHeading = useCallback((id: string) => {
    const element = document.getElementById(id)
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }, [])

  return (
    <div className="min-h-screen bg-light-bg-secondary dark:bg-cyber-dark">
      {/* Top Header Bar */}
      <header className="sticky top-0 z-50 bg-white/95 dark:bg-cyber-card/95 backdrop-blur-sm border-b border-light-border dark:border-secondary-700 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            {/* Mobile sidebar toggle */}
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 rounded-lg md:hidden hover:bg-secondary-100 dark:hover:bg-secondary-700 text-secondary-600 dark:text-secondary-400"
            >
              {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
            </button>

            {/* Back Button */}
            <Link
              to="/"
              className="flex items-center gap-2 text-sm text-secondary-600 dark:text-secondary-400 hover:text-primary-600 dark:hover:text-primary-400 transition-colors"
            >
              <ArrowLeft size={16} />
              <span className="hidden sm:inline">{t('common.back', 'Back')}</span>
            </Link>

            <div className="h-4 w-px bg-secondary-200 dark:bg-secondary-700 mx-2" />

            <h1 className="font-semibold text-light-text-primary dark:text-secondary-100">
              {t('docs.title', 'Documentation')}
            </h1>
          </div>

          {/* TOC Toggle for desktop */}
          {tocItems.length > 0 && (
            <button
              onClick={() => setShowToc(!showToc)}
              className={clsx(
                'hidden xl:flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors',
                showToc
                  ? 'bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400'
                  : 'text-secondary-600 dark:text-secondary-400 hover:bg-secondary-100 dark:hover:bg-secondary-700'
              )}
            >
              <List size={16} />
              <span>{t('docs.toc', 'Table of Contents')}</span>
            </button>
          )}
        </div>
      </header>

      <div className="flex">
        {/* Sidebar */}
        <aside
          className={clsx(
            'fixed md:sticky top-14 left-0 z-40 w-64 transform transition-transform duration-300 h-[calc(100vh-3.5rem)]',
            'bg-white dark:bg-secondary-800 border-r border-secondary-200 dark:border-secondary-700',
            'overflow-y-auto flex-shrink-0',
            sidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
          )}
        >
          <div className="p-4">
            <nav className="space-y-1">
              {docItems.map((doc) => {
                // Section header
                if (doc.isSectionHeader) {
                  return (
                    <div
                      key={doc.id}
                      className="px-3 py-2 mt-4 first:mt-0 text-xs font-semibold text-primary-600 dark:text-primary-400 uppercase tracking-wider"
                    >
                      {t(doc.sectionKey || '', doc.id)}
                    </div>
                  )
                }

                // Regular doc item
                return (
                  <button
                    key={doc.id}
                    onClick={() => handleDocSelect(doc.id)}
                    className={clsx(
                      'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors',
                      selectedDoc === doc.id
                        ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400'
                        : 'text-secondary-600 dark:text-secondary-400 hover:bg-secondary-50 dark:hover:bg-secondary-700/50'
                    )}
                  >
                    <doc.icon size={18} />
                    <span className="font-medium text-sm">{t(doc.titleKey, doc.id)}</span>
                    {selectedDoc === doc.id && (
                      <ChevronRight size={16} className="ml-auto" />
                    )}
                  </button>
                )
              })}
            </nav>
          </div>
        </aside>

        {/* Mobile overlay */}
        {sidebarOpen && (
          <div
            className="fixed inset-0 bg-black/50 z-30 md:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        {/* Table of Contents - Left side of content */}
        {showToc && tocItems.length > 0 && (
          <aside className="hidden xl:block w-56 flex-shrink-0 h-[calc(100vh-3.5rem)] sticky top-14 overflow-y-auto border-r border-secondary-200 dark:border-secondary-700 bg-white dark:bg-secondary-800">
            <div className="p-4">
              <h3 className="text-xs font-semibold text-secondary-500 dark:text-secondary-400 uppercase tracking-wider mb-3">
                {t('docs.onThisPage', 'On This Page')}
              </h3>
              <nav className="space-y-1 border-l border-secondary-200 dark:border-secondary-700">
                {tocItems.map((item, index) => (
                  <button
                    key={index}
                    onClick={() => scrollToHeading(item.id)}
                    className={clsx(
                      'w-full text-left text-sm py-1.5 px-3 transition-colors',
                      'text-secondary-600 dark:text-secondary-400',
                      'hover:text-primary-600 dark:hover:text-primary-400',
                      'border-l-2 -ml-px',
                      item.level === 1 && 'font-medium border-transparent',
                      item.level === 2 && 'pl-5 border-transparent hover:border-primary-400',
                      item.level === 3 && 'pl-7 text-xs border-transparent hover:border-primary-400'
                    )}
                  >
                    {item.text}
                  </button>
                ))}
              </nav>
            </div>
          </aside>
        )}

        {/* Main Content */}
        <main className="flex-1 min-w-0 overflow-y-auto">
          <div className="max-w-4xl mx-auto px-4 py-8 md:px-8 xl:px-12">
            {/* Document Header */}
            {currentDoc && (
              <div className="mb-8 flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-100 to-primary-200 dark:from-primary-900/30 dark:to-primary-800/30 flex items-center justify-center shadow-sm">
                  <currentDoc.icon className="text-primary-600 dark:text-primary-400" size={24} />
                </div>
                <div>
                  <h1 className="text-2xl md:text-3xl font-bold text-light-text-primary dark:text-secondary-100">
                    {t(currentDoc.titleKey, currentDoc.id)}
                  </h1>
                  <p className="text-sm text-secondary-500 dark:text-secondary-400 mt-1">
                    {t('docs.lastUpdated', 'Last updated')}: {new Date().toLocaleDateString()}
                  </p>
                </div>
              </div>
            )}

            {/* Loading state */}
            {loading && (
              <div className="flex flex-col items-center justify-center py-20">
                <div className="animate-spin rounded-full h-10 w-10 border-2 border-primary-600 border-t-transparent dark:border-primary-400" />
                <p className="mt-4 text-secondary-500 dark:text-secondary-400">{t('common.loading', 'Loading...')}</p>
              </div>
            )}

            {/* Error state */}
            {error && (
              <div className="p-8 text-center">
                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
                  <X size={32} className="text-red-500 dark:text-red-400" />
                </div>
                <div className="text-red-500 dark:text-red-400 mb-4">{error}</div>
                <button
                  onClick={() => setSelectedDoc(selectedDoc)}
                  className="px-6 py-2.5 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium transition-colors"
                >
                  {t('common.retry', 'Retry')}
                </button>
              </div>
            )}

            {/* Markdown content */}
            {!loading && !error && (
              <article className="docs-content">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    // Heading components with IDs for TOC navigation
                    h1: ({ children }) => {
                      const text = String(children)
                      const id = text
                        .toLowerCase()
                        .replace(/[^\w\s-]/g, '')
                        .replace(/\s+/g, '-')
                      return (
                        <h1
                          id={id}
                          className="text-3xl font-bold text-light-text-primary dark:text-secondary-100 mt-8 mb-4 first:mt-0 scroll-mt-20"
                        >
                          {children}
                        </h1>
                      )
                    },
                    h2: ({ children }) => {
                      const text = String(children)
                      const id = text
                        .toLowerCase()
                        .replace(/[^\w\s-]/g, '')
                        .replace(/\s+/g, '-')
                      return (
                        <h2
                          id={id}
                          className="text-2xl font-semibold text-light-text-primary dark:text-secondary-100 mt-10 mb-4 pb-2 border-b border-secondary-200 dark:border-secondary-700 scroll-mt-20"
                        >
                          {children}
                        </h2>
                      )
                    },
                    h3: ({ children }) => {
                      const text = String(children)
                      const id = text
                        .toLowerCase()
                        .replace(/[^\w\s-]/g, '')
                        .replace(/\s+/g, '-')
                      return (
                        <h3
                          id={id}
                          className="text-xl font-semibold text-light-text-primary dark:text-secondary-100 mt-8 mb-3 scroll-mt-20"
                        >
                          {children}
                        </h3>
                      )
                    },
                    h4: ({ children }) => {
                      const text = String(children)
                      const id = text
                        .toLowerCase()
                        .replace(/[^\w\s-]/g, '')
                        .replace(/\s+/g, '-')
                      return (
                        <h4
                          id={id}
                          className="text-lg font-semibold text-light-text-primary dark:text-secondary-100 mt-6 mb-2 scroll-mt-20"
                        >
                          {children}
                        </h4>
                      )
                    },
                    // Paragraph
                    p: ({ children }) => (
                      <p className="text-secondary-700 dark:text-secondary-300 leading-relaxed mb-4">
                        {children}
                      </p>
                    ),
                    // Link with external icon
                    a: ({ href, children }) => {
                      const isExternal = href?.startsWith('http')
                      return (
                        <a
                          href={href}
                          target={isExternal ? '_blank' : undefined}
                          rel={isExternal ? 'noopener noreferrer' : undefined}
                          className={clsx(
                            'text-primary-600 dark:text-primary-400',
                            'font-medium hover:text-primary-700 dark:hover:text-primary-300',
                            'border-b border-primary-300 dark:border-primary-600',
                            'hover:border-primary-600 dark:hover:border-primary-400',
                            'transition-colors',
                            isExternal && 'inline-flex items-center gap-1'
                          )}
                        >
                          {children}
                          {isExternal && <ExternalLink size={14} className="flex-shrink-0" />}
                        </a>
                      )
                    },
                    // Code block with line numbers and copy button
                    pre: ({ children }) => {
                      // Try to get the code content from children
                      let codeContent = ''

                      // Check if children is a React element with props.children
                      if (children && typeof children === 'object' && 'props' in children) {
                        const childProps = (children as React.ReactElement).props
                        codeContent = String(childProps?.children || '').trim()
                      }

                      // Check for architecture diagram
                      const boxChars = '│┌┐└┘├┤┬┴─═║'
                      const hasBoxChars = boxChars.split('').some(char => codeContent.includes(char))
                      const lines = codeContent.split('\n').filter(l => l.trim())
                      const isAsciiDiagram = hasBoxChars && lines.length >= 4

                      if (isAsciiDiagram) {
                        // TODO: 架构图可视化功能暂时禁用，需要重新设计 ASCII -> Mermaid 转换逻辑
                        // 当前问题：无法正确区分层内组件和层标题，无法处理嵌套的 │ 框线
                        // 建议：使用自定义渲染组件，分别处理层标题和层内组件的提取
                        console.log('>>> ASCII diagram detected, showing as plain text')
                        return (
                          <div className="my-6">
                            {/* 暂时只显示原始 ASCII，等 TODO 完成后启用可视化 */}
                            <AsciiDiagram code={codeContent} />
                            {/* <ArchitectureDiagram code={codeContent} type="graph" /> */}
                          </div>
                        )
                      }

                      // The children should be a code element
                      return <>{children}</>
                    },
                    code: ({ className, children, ...props }) => {
                      const isInline = !className
                      if (isInline) {
                        return <InlineCode {...props}>{children}</InlineCode>
                      }

                      // Check if this is a code block with a language specifier (e.g., ```python)
                      // className would be like "language-python" or "language-ts"
                      // If there's NO language (just ``` ), className might be undefined or just empty
                      const hasLanguage = className && typeof className === 'string' && className.startsWith('language-') && className.length > 9

                      const codeContent = String(children).trim()

                      // Check if it's Mermaid diagram
                      const isMermaid = codeContent.startsWith('graph') ||
                        codeContent.startsWith('flowchart') ||
                        codeContent.startsWith('sequenceDiagram') ||
                        codeContent.startsWith('classDiagram')

                      // For code blocks WITHOUT language specifier (like ``` ),
                      // check if it's an architecture diagram
                      const boxChars = '│┌┐└┘├┤┬┴─═║'
                      const hasBoxChars = boxChars.split('').some(char => codeContent.includes(char))
                      const lines = codeContent.split('\n').filter(l => l.trim())
                      const isAsciiDiagram = !hasLanguage && !isMermaid && hasBoxChars && lines.length >= 4

                      // If it has a language specifier (e.g., ```python ), render as regular code
                      if (hasLanguage && !isMermaid) {
                        return (
                          <CodeBlock className={className} {...props}>
                            {children}
                          </CodeBlock>
                        )
                      }

                      // Render as architecture diagram if detected
                      // TODO: 暂时禁用 ArchitectureDiagram 可视化，只保留原始 ASCII 显示
                      if (isAsciiDiagram || isMermaid) {
                        return (
                          <div className="space-y-4">
                            {/* <ArchitectureDiagram code={codeContent} type={isMermaid ? 'flowchart' : 'graph'} /> */}
                            {isAsciiDiagram && (
                              <AsciiDiagram code={codeContent} />
                            )}
                            {isMermaid && (
                              <ArchitectureDiagram code={codeContent} type="flowchart" />
                            )}
                          </div>
                        )
                      }

                      return (
                        <CodeBlock className={className} {...props}>
                          {children}
                        </CodeBlock>
                      )
                    },
                    // Lists
                    ul: ({ children }) => (
                      <ul className="list-disc list-outside ml-6 mb-4 space-y-2 text-secondary-700 dark:text-secondary-300">
                        {children}
                      </ul>
                    ),
                    ol: ({ children }) => (
                      <ol className="list-decimal list-outside ml-6 mb-4 space-y-2 text-secondary-700 dark:text-secondary-300">
                        {children}
                      </ol>
                    ),
                    li: ({ children }) => (
                      <li className="pl-1 leading-relaxed">
                        {children}
                      </li>
                    ),
                    // Blockquote
                    blockquote: ({ children }) => (
                      <blockquote className={clsx(
                        'my-6 pl-4 pr-4 py-4',
                        'border-l-4 border-primary-500',
                        'bg-primary-50/50 dark:bg-primary-900/10',
                        'rounded-r-lg',
                        'text-secondary-700 dark:text-secondary-300',
                        'italic'
                      )}>
                        {children}
                      </blockquote>
                    ),
                    // Table
                    table: ({ children }) => (
                      <div className="my-6 overflow-x-auto rounded-lg border border-secondary-200 dark:border-secondary-700 shadow-sm">
                        <table className="min-w-full divide-y divide-secondary-200 dark:divide-secondary-700">
                          {children}
                        </table>
                      </div>
                    ),
                    thead: ({ children }) => (
                      <thead className="bg-secondary-100 dark:bg-secondary-800">
                        {children}
                      </thead>
                    ),
                    th: ({ children }) => (
                      <th className="px-4 py-3 text-left text-sm font-semibold text-light-text-primary dark:text-secondary-100">
                        {children}
                      </th>
                    ),
                    tbody: ({ children }) => (
                      <tbody className="divide-y divide-secondary-200 dark:divide-secondary-700 bg-white dark:bg-secondary-900">
                        {children}
                      </tbody>
                    ),
                    tr: ({ children }) => (
                      <tr className="hover:bg-secondary-50 dark:hover:bg-secondary-800/50 transition-colors even:bg-secondary-50/50 dark:even:bg-secondary-800/30">
                        {children}
                      </tr>
                    ),
                    td: ({ children }) => (
                      <td className="px-4 py-3 text-sm text-secondary-700 dark:text-secondary-300">
                        {children}
                      </td>
                    ),
                    // Horizontal rule
                    hr: () => (
                      <hr className="my-8 border-t border-secondary-200 dark:border-secondary-700" />
                    ),
                    // Image
                    img: ({ src, alt }) => (
                      <figure className="my-6">
                        <img
                          src={src}
                          alt={alt}
                          className="rounded-lg shadow-md max-w-full h-auto mx-auto"
                        />
                        {alt && (
                          <figcaption className="mt-2 text-sm text-center text-secondary-500 dark:text-secondary-400">
                            {alt}
                          </figcaption>
                        )}
                      </figure>
                    ),
                    // Strong
                    strong: ({ children }) => (
                      <strong className="font-semibold text-light-text-primary dark:text-secondary-100">
                        {children}
                      </strong>
                    ),
                    // Emphasis
                    em: ({ children }) => (
                      <em className="italic text-secondary-700 dark:text-secondary-300">
                        {children}
                      </em>
                    ),
                  }}
                >
                  {content}
                </ReactMarkdown>
              </article>
            )}
          </div>
        </main>

      </div>
    </div>
  )
}
