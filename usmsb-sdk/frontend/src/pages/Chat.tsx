import { useState, useRef, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { Send, Bot, User, Loader2, Sparkles, Wallet, WifiOff, History, Shield, Vote, Settings, CheckCircle, ChevronDown, ChevronUp, RefreshCw } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { sendChatMessage, ChatMessage, getAgentTools, getConversationHistory, HistoryMessage, getUserInfo, getLatestMessages } from '@/lib/api'
import { useAuthStore, USER_ROLE_LABELS } from '@/stores/authStore'
import WalletBindingModal from '@/components/WalletBindingModal'

interface ToolInfo {
  name: string
  description: string
}

// 后台任务消息类型
type ExtendedMessageRole = 'user' | 'assistant' | 'background_task' | 'background_complete' | 'background_error'

interface ExtendedMessage {
  role: ExtendedMessageRole
  content: string
  timestamp?: string
  isExpanded?: boolean
  tool_calls?: Array<{
    id?: string
    function: {
      name: string
      arguments: string | Record<string, unknown>
    }
  }>
}

const DEMO_MODE = false

// 智能判断内容类型，决定展示方式
function analyzeContentType(content: string): {
  isLogLike: boolean       // 是否日志类内容（需要code块+收缩）
  shouldCollapse: boolean  // 是否需要收缩
  needsCodeBlock: boolean  // 是否需要code块
} {
  // 日志特征检测
  const logPatterns = [
    /^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}/,  // 时间戳 2024-01-01 12:00:00
    /^\[?\d{2}:\d{2}:\d{2}\]?/,                   // 简写时间戳 [12:00:00]
    /\b(INFO|WARN|ERROR|DEBUG|TRACE|FATAL)\b/i,   // 日志级别
    /^\s*at\s+[\w.]+\(/m,                          // stack trace
    /\b(Exception|Traceback|Error:)\b/i,         // 错误信息
  ]
  
  // Markdown/人类可读特征检测
  const markdownPatterns = [
    /^\|.*\|$/m,                                   // markdown表格行
    /^#{1,6}\s+/m,                                // 标题
    /^\*\*.*\*\*/m,                               // 粗体
    /^\[.*\]\(.*\)/m,                             // 链接
    /^[-*+]\s+/m,                                 // 无序列表
    /^\d+\.\s+/m,                                 // 有序列表
    /^>\s+/m,                                     // 引用
    /^---\s*$/m,                                  // 分隔线
  ]
  
  const hasLogPattern = logPatterns.some(p => p.test(content))
  const hasMarkdownPattern = markdownPatterns.some(p => p.test(content))
  
  // 判断是否为日志类：必须有日志特征，且不是markdown
  const isLogLike = hasLogPattern && !hasMarkdownPattern
  
  // 日志类：收缩 + code块
  // 非日志类（markdown/人类可读）：完全展开 + 不用code块
  return {
    isLogLike,
    shouldCollapse: isLogLike && content.length > 300,
    needsCodeBlock: isLogLike
  }
}

export default function Chat() {
  const { t } = useTranslation()
  // Global auth state
  const { 
    address, 
    isConnected, 
    bindingType, 
    userRole, 
    permissions, 
    votingPower,
    stake,
    setUserRole,
    setPermissions,
  } = useAuthStore()

  const [messages, setMessages] = useState<ExtendedMessage[]>([{
    role: 'assistant',
    content: t('chat.welcome'),
    timestamp: new Date().toISOString(),
  }])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isLoadingHistory, setIsLoadingHistory] = useState(false)
  const [tools, setTools] = useState<ToolInfo[]>([])
  const [showBindingModal, setShowBindingModal] = useState(false)
  const [lastTimestamp, setLastTimestamp] = useState<number>(0)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Use address from global store as wallet address
  const walletAddress = address || ''

  useEffect(() => {
    loadTools()
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (walletAddress && !DEMO_MODE) {
      loadHistory()
      loadUserInfo()
    }
  }, [walletAddress])

  const loadTools = async () => {
    if (DEMO_MODE) {
      setTools([
        { name: 'start_node', description: '启动节点' },
        { name: 'stop_node', description: '停止节点' },
        { name: 'create_wallet', description: '创建钱包' },
        { name: 'get_balance', description: '查询余额' },
        { name: 'stake', description: '质押代币' },
        { name: 'vote', description: '投票' },
        { name: 'query_db', description: '查询数据库' },
        { name: 'health_check', description: '健康检查' },
      ])
      return
    }
    try {
      const toolList = await getAgentTools()
      setTools(toolList)
    } catch {
      // Ignore
    }
  }

  const loadHistory = async () => {
    if (!walletAddress) return

    setIsLoadingHistory(true)
    try {
      const history = await getConversationHistory(walletAddress, 50)
      if (history.length > 0) {
        const chatMessages: ExtendedMessage[] = history.map((msg: HistoryMessage) => ({
          role: msg.role as ExtendedMessageRole,
          content: msg.content,
          timestamp: msg.timestamp ? new Date(msg.timestamp * 1000).toISOString() : undefined,
          // 后台任务消息默认收起
          isExpanded: msg.role === 'user' || msg.role === 'assistant',
        }))
        setMessages(chatMessages)
        // 设置最后时间戳
        const latestTs = Math.max(...history.map(m => m.timestamp || 0))
        setLastTimestamp(latestTs)
      } else {
        setMessages([{
          role: 'assistant',
          content: t('chat.welcome'),
          timestamp: new Date().toISOString(),
          isExpanded: true,
        }])
      }
    } catch (error) {
      console.error('Failed to load history:', error)
    } finally {
      setIsLoadingHistory(false)
    }
  }

  const loadUserInfo = async () => {
    if (!walletAddress) return

    try {
      const info = await getUserInfo(walletAddress)
      setUserRole(info.role as any)
      setPermissions(info.permissions, info.voting_power)
    } catch (error) {
      console.error('Failed to load user info:', error)
    }
  }

  // 轮询获取最新消息
  useEffect(() => {
    if (!walletAddress || DEMO_MODE || isLoading) return

    const pollInterval = setInterval(async () => {
      try {
        const latestMessages = await getLatestMessages(walletAddress, lastTimestamp)
        if (latestMessages.length > 0) {
          const newMessages: ExtendedMessage[] = latestMessages.map((msg: HistoryMessage) => ({
            role: msg.role as ExtendedMessageRole,
            content: msg.content,
            timestamp: msg.timestamp ? new Date(msg.timestamp * 1000).toISOString() : undefined,
          }))

          // 更新最后时间戳
          const latestTs = Math.max(...latestMessages.map(m => m.timestamp || 0))
          setLastTimestamp(latestTs)

          // 将新消息添加到列表（去重）
          setMessages(prev => {
            const existingIds = new Set(prev.map(m => `${m.timestamp}-${m.content.slice(0, 20)}`))
            const uniqueNew = newMessages.filter(
              m => !existingIds.has(`${m.timestamp}-${m.content.slice(0, 20)}`)
            )
            if (uniqueNew.length === 0) return prev
            return [...prev, ...uniqueNew] as ExtendedMessage[]
          })
        }
      } catch (error) {
        console.error('Polling error:', error)
      }
    }, 5000) // 每5秒轮询一次

    return () => clearInterval(pollInterval)
  }, [walletAddress, lastTimestamp, isLoading])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return

    const userMessage: ChatMessage = {
      role: 'user',
      content: input,
      timestamp: new Date().toISOString(),
    }

    setMessages((prev) => [...prev, userMessage as ExtendedMessage])
    setInput('')
    setIsLoading(true)

    try {
      let responseText: string

      if (DEMO_MODE) {
        await new Promise(resolve => setTimeout(resolve, 500))
        responseText = 'Demo mode: API call skipped'
      } else {
        const response = await sendChatMessage({
          message: input,
          wallet_address: walletAddress || undefined,
        })
        responseText = response.response
      }

      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: responseText,
        timestamp: new Date().toISOString(),
      }

      setMessages((prev) => [...prev, assistantMessage as ExtendedMessage])
    } catch (error) {
      const errorMessage: ChatMessage = {
        role: 'assistant',
        content: error instanceof Error ? error.message : '抱歉，处理你的请求时出错了',
        timestamp: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, errorMessage as ExtendedMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const getBindingTypeLabel = () => {
    switch (bindingType) {
      case 'wallet': return t('chat.realWallet')
      case 'manual': return t('chat.tempId')
      case 'agent': return t('chat.aiAgent')
      default: return t('chat.unbound')
    }
  }

  return (
    <div className="flex flex-col h-full min-h-0">
      {/* Header */}
      <div className="flex-shrink-0 flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg">
            <Bot className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-gray-900 dark:text-white">
              {t('chat.title')}
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {t('chat.subtitle')}
              {DEMO_MODE && (
                <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400">
                  <WifiOff className="w-3 h-3 mr-1" />
                  {t('chat.demoMode')}
                </span>
              )}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {isConnected && walletAddress && !DEMO_MODE && (
            <button
              onClick={loadHistory}
              disabled={isLoadingHistory}
              className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
              title={t('chat.refreshHistory')}
            >
              <History className={`w-4 h-4 ${isLoadingHistory ? 'animate-spin' : ''}`} />
            </button>
          )}
          <button
            onClick={() => setShowBindingModal(true)}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
              isConnected
                ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
                : 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 hover:bg-blue-200 dark:hover:bg-blue-900/50'
            }`}
          >
            {isConnected ? <CheckCircle className="w-4 h-4" /> : <Wallet className="w-4 h-4" />}
            <span className="text-sm font-medium">
              {isConnected && walletAddress
                ? `${walletAddress.slice(0, 6)}...${walletAddress.slice(-4)}`
                : t('chat.bindIdentity')}
            </span>
          </button>
        </div>
      </div>

      {/* User Info Panel */}
      {isConnected && walletAddress && (
        <div className="flex-shrink-0 px-6 py-3 bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <Shield className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  {t('chat.role')}: <span className="text-blue-600 dark:text-blue-400">{USER_ROLE_LABELS[userRole] || userRole}</span>
                </span>
              </div>
              <div className="flex items-center gap-2">
                <Vote className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  {t('chat.votingPower')}: <span className="font-medium">{votingPower.toFixed(2)}</span>
                </span>
              </div>
              <span className="text-xs text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded">
                {getBindingTypeLabel()}
              </span>
            </div>
            <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
              <span>{t('chat.staked')}: {stake.toFixed(2)}</span>
              <span>{t('chat.permissions')}: {permissions.length}</span>
              <button
                onClick={() => setShowBindingModal(true)}
                className="text-blue-600 dark:text-blue-400 hover:underline"
              >
                <Settings className="w-3 h-3 inline mr-1" />
                {t('chat.settings')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 min-h-0 overflow-y-auto px-6 py-4 space-y-4">
        {isLoadingHistory && (
          <div className="flex items-center justify-center py-4">
            <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
            <span className="ml-2 text-sm text-gray-500">{t('chat.loadingHistory')}</span>
          </div>
        )}

        {messages.map((message, index) => {
          // 判断是否为后台任务消息
          const isBackgroundTask = message.role === 'background_task' || message.role === 'background_complete' || message.role === 'background_error'
          
          // 后台任务消息样式
          const getBackgroundStyle = () => {
            switch (message.role) {
              case 'background_task':
                return 'bg-blue-50 dark:bg-blue-900/20 border-l-4 border-blue-500'
              case 'background_complete':
                return 'bg-green-50 dark:bg-green-900/20 border-l-4 border-green-500'
              case 'background_error':
                return 'bg-red-50 dark:bg-red-900/20 border-l-4 border-red-500'
              default:
                return ''
            }
          }

          // 获取图标
          const getIcon = () => {
            if (message.role === 'background_task') return <RefreshCw className="w-4 h-4 text-blue-500" />
            if (message.role === 'background_complete') return <CheckCircle className="w-4 h-4 text-green-500" />
            if (message.role === 'background_error') return <History className="w-4 h-4 text-red-500" />
            return message.role === 'user' ? <User className="w-4 h-4 text-white" /> : <Bot className="w-4 h-4 text-white" />
          }

          // 切换展开/收起
          const toggleExpand = () => {
            setMessages(prev => prev.map((m, i) => 
              i === index ? { ...m, isExpanded: !m.isExpanded } : m
            ))
          }

          // 智能分析内容类型
          const contentAnalysis = analyzeContentType(message.content)
          const shouldShowFull = !contentAnalysis.shouldCollapse || message.isExpanded

          return (
          <div
            key={index}
            className={`flex gap-3 ${message.role === 'user' ? 'flex-row-reverse' : ''}`}
          >
            <div
              className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                message.role === 'user'
                  ? 'bg-blue-500'
                  : isBackgroundTask
                    ? 'bg-gray-200 dark:bg-gray-700'
                    : 'bg-gradient-to-br from-purple-500 to-pink-500'
              }`}
            >
              {getIcon()}
            </div>
            <div
              className={`flex-1 max-w-[70%] ${
                message.role === 'user' ? 'text-right' : ''
              }`}
            >
              <div
                className={`inline-block px-4 py-3 rounded-2xl ${
                  message.role === 'user'
                    ? 'bg-blue-500 text-white'
                    : isBackgroundTask
                      ? getBackgroundStyle()
                      : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100'
                }`}
              >
                {message.role === 'assistant' ? (
                  <div className="markdown-body text-sm">
                    <ReactMarkdown 
                      remarkPlugins={[remarkGfm]}
                      components={{
                      p: ({ children }) => (
                        <p className="mb-3 last:mb-0">{children}</p>
                      ),
                      ul: ({ children }) => (
                        <ul className="list-disc list-outside ml-4 mb-3 space-y-1">{children}</ul>
                      ),
                      ol: ({ children }) => (
                        <ol className="list-decimal list-outside ml-4 mb-3 space-y-1">{children}</ol>
                      ),
                      li: ({ children }) => (
                        <li className="pl-1">{children}</li>
                      ),
                      code: ({ className, children, ...props }) => {
                        const isInline = !className
                        if (isInline) {
                          return (
                            <code className="px-1.5 py-0.5 bg-gray-200 dark:bg-gray-700 rounded text-sm" {...props}>
                              {children}
                            </code>
                          )
                        }
                        return (
                          <code className={`${className} block p-3 my-2 overflow-x-auto bg-gray-900 dark:bg-gray-950 rounded-lg text-sm`} {...props}>
                            {children}
                          </code>
                        )
                      },
                      pre: ({ children }) => (
                        <pre className="my-3 overflow-x-auto">{children}</pre>
                      ),
                      blockquote: ({ children }) => (
                        <blockquote className="border-l-4 border-gray-300 dark:border-gray-600 pl-4 my-3 italic text-gray-600 dark:text-gray-400">{children}</blockquote>
                      ),
                      a: ({ href, children }) => (
                        <a href={href} className="text-blue-600 dark:text-blue-400 hover:underline" target="_blank" rel="noopener noreferrer">{children}</a>
                      ),
                      strong: ({ children }) => (
                        <strong className="font-semibold">{children}</strong>
                      ),
                      h1: ({ children }) => <h1 className="text-xl font-bold mt-4 mb-2">{children}</h1>,
                      h2: ({ children }) => <h2 className="text-lg font-semibold mt-3 mb-2">{children}</h2>,
                      h3: ({ children }) => <h3 className="text-base font-medium mt-2 mb-1">{children}</h3>,
                      table: ({ children }) => (
                        <table className="w-full my-4 border-collapse border border-gray-300 dark:border-gray-600 rounded-lg overflow-hidden">{children}</table>
                      ),
                      thead: ({ children }) => (
                        <thead className="bg-gray-100 dark:bg-gray-800">{children}</thead>
                      ),
                      tbody: ({ children }) => (
                        <tbody>{children}</tbody>
                      ),
                      tr: ({ children }) => (
                        <tr className="border-b border-gray-200 dark:border-gray-700">{children}</tr>
                      ),
                      th: ({ children }) => (
                        <th className="px-4 py-2 text-left font-semibold border-r border-gray-200 dark:border-gray-700">{children}</th>
                      ),
                      td: ({ children }) => (
                        <td className="px-4 py-2 border-r border-gray-200 dark:border-gray-700">{children}</td>
                      ),
                    }}
                  >
                    {message.content}
                  </ReactMarkdown>
                  </div>
                ) : (
                  <>
                    {/* 后台任务消息或普通消息 */}
                    {isBackgroundTask ? (
                      <div className="text-sm">
                        {/* 根据内容类型决定展示方式 */}
                        {shouldShowFull ? (
                          <>
                            {/* 日志类内容用code块 */}
                            {contentAnalysis.needsCodeBlock ? (
                              <pre className="whitespace-pre-wrap text-xs bg-gray-800 text-gray-100 p-3 rounded-lg overflow-x-auto max-h-96 overflow-y-auto">
                                {message.content}
                              </pre>
                            ) : (
                              /* 非日志类内容（markdown）用ReactMarkdown渲染 */
                              <div className="markdown-body text-sm">
                                <ReactMarkdown 
                                  remarkPlugins={[remarkGfm]}
                                  components={{
                                    p: ({ children }) => (
                                      <p className="mb-2 last:mb-0">{children}</p>
                                    ),
                                    ul: ({ children }) => (
                                      <ul className="list-disc list-outside ml-4 mb-2 space-y-1">{children}</ul>
                                    ),
                                    ol: ({ children }) => (
                                      <ol className="list-decimal list-outside ml-4 mb-2 space-y-1">{children}</ol>
                                    ),
                                    li: ({ children }) => (
                                      <li className="pl-1">{children}</li>
                                    ),
                                    table: ({ children }) => (
                                      <table className="w-full my-3 border-collapse border border-gray-300 dark:border-gray-600 rounded-lg overflow-hidden text-xs">{children}</table>
                                    ),
                                    thead: ({ children }) => (
                                      <thead className="bg-gray-100 dark:bg-gray-800">{children}</thead>
                                    ),
                                    tbody: ({ children }) => (
                                      <tbody>{children}</tbody>
                                    ),
                                    tr: ({ children }) => (
                                      <tr className="border-b border-gray-200 dark:border-gray-700">{children}</tr>
                                    ),
                                    th: ({ children }) => (
                                      <th className="px-3 py-2 text-left font-semibold border-r border-gray-200 dark:border-gray-700">{children}</th>
                                    ),
                                    td: ({ children }) => (
                                      <td className="px-3 py-2 border-r border-gray-200 dark:border-gray-700">{children}</td>
                                    ),
                                    h1: ({ children }) => <h1 className="text-lg font-bold mt-3 mb-2">{children}</h1>,
                                    h2: ({ children }) => <h2 className="text-base font-semibold mt-2 mb-1">{children}</h2>,
                                    h3: ({ children }) => <h3 className="text-sm font-medium mt-2 mb-1">{children}</h3>,
                                    hr: () => <hr className="my-3 border-gray-300 dark:border-gray-600" />,
                                    strong: ({ children }) => (
                                      <strong className="font-semibold">{children}</strong>
                                    ),
                                  }}
                                >
                                  {message.content}
                                </ReactMarkdown>
                              </div>
                            )}
                            {/* 收缩按钮：日志类且内容长 */}
                            {contentAnalysis.shouldCollapse && (
                              <button
                                onClick={toggleExpand}
                                className="mt-2 flex items-center gap-1 text-xs text-blue-600 dark:text-blue-400 hover:underline"
                              >
                                <ChevronUp className="w-3 h-3" /> {t('chat.collapse', 'Collapse')}
                              </button>
                            )}
                          </>
                        ) : (
                          <div>
                            <p className="whitespace-pre-wrap">{message.content.slice(0, 150)}...</p>
                            <button
                              onClick={toggleExpand}
                              className="mt-1 flex items-center gap-1 text-xs text-blue-600 dark:text-blue-400 hover:underline"
                            >
                              <ChevronDown className="w-3 h-3" /> {t('chat.expandDetails', 'Expand Details')}
                            </button>
                          </div>
                        )}
                        
                        {/* 显示工具调用详情 */}
                        {message.tool_calls && message.tool_calls.length > 0 && (
                          <div className="mt-3 p-3 bg-gray-100 dark:bg-gray-800 rounded-lg text-xs">
                            <p className="font-semibold mb-2 text-gray-600 dark:text-gray-400">{t('chat.toolCalls', 'Tool Calls')}:</p>
                            {message.tool_calls.map((tc, tcIndex) => (
                              <div key={tcIndex} className="mb-2 pb-2 border-b border-gray-200 dark:border-gray-700 last:border-0">
                                <p className="font-medium text-blue-600 dark:text-blue-400">
                                  🔧 {tc.function.name}
                                </p>
                                {tc.function.arguments && typeof tc.function.arguments === 'object' && (
                                  <pre className="mt-1 p-2 bg-white dark:bg-gray-900 rounded overflow-x-auto">
                                    {JSON.stringify(tc.function.arguments, null, 2)}
                                  </pre>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ) : (
                      <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                    )}
                  </>
                )}
              </div>
              {message.timestamp && (
                <p className="mt-1 text-xs text-gray-400">
                  {new Date(message.timestamp).toLocaleTimeString('zh-CN')}
                </p>
              )}
            </div>
          </div>
          )}        )}

        {isLoading && (
          <div className="flex gap-3">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
              <Bot className="w-4 h-4 text-white" />
            </div>
            <div className="flex items-center gap-2 text-gray-500">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span className="text-sm">{t('chat.thinking')}</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Tools Hint */}
      {tools.length > 0 && (
        <div className="flex-shrink-0 px-6 py-2 border-t border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <Sparkles className="w-3 h-3" />
            <span>{t('chat.availableTools')}: {tools.slice(0, 8).map((t) => t.name).join(', ')}{tools.length > 8 ? '...' : ''}</span>
          </div>
        </div>
      )}

      {/* Input */}
      <div className="flex-shrink-0 p-4 border-t border-gray-200 dark:border-gray-700">
        <form onSubmit={handleSubmit} className="flex gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={t('chat.inputPlaceholder')}
            className="flex-1 px-4 py-3 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-gray-900 dark:text-white placeholder-gray-500 focus:ring-2 focus:ring-blue-500"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="px-4 py-2 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Send className="w-5 h-5" />
          </button>
        </form>
      </div>

      {/* Wallet Binding Modal */}
      <WalletBindingModal
        isOpen={showBindingModal}
        onClose={() => setShowBindingModal(false)}
      />
    </div>
  )
}
