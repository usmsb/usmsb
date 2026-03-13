import { useState } from 'react'
import {
  Bot,
  Plug,
  FileCode,
  Link2,
  CheckCircle,
  AlertCircle,
  RefreshCw,
  ArrowLeft,
  Send,
  Info,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import clsx from 'clsx'
import { authFetch } from '@/lib/api'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

type RegistrationProtocol = 'standard' | 'mcp' | 'a2a' | 'skill_md'

interface AgentFormData {
  // Standard & MCP
  agent_id: string
  name: string
  capabilities: string
  endpoint: string
  stake: number
  description: string
  // MCP specific
  mcp_endpoint: string
  // A2A specific
  a2a_endpoint: string
  agent_card_json: string
  // Skill.md specific
  skill_url: string
}

const initialFormData: AgentFormData = {
  agent_id: '',
  name: '',
  capabilities: '',
  endpoint: '',
  stake: 0,
  description: '',
  mcp_endpoint: '',
  a2a_endpoint: '',
  agent_card_json: '',
  skill_url: '',
}

const protocolOptions = [
  {
    id: 'standard' as const,
    name: 'Standard',
    icon: Bot,
    description: 'Register AI agent with endpoint and capabilities',
    color: 'bg-blue-100 text-blue-600',
  },
  {
    id: 'mcp' as const,
    name: 'MCP',
    icon: Plug,
    description: 'Model Context Protocol - Claude & AI assistants',
    color: 'bg-green-100 text-green-600',
  },
  {
    id: 'a2a' as const,
    name: 'A2A',
    icon: Link2,
    description: 'Agent-to-Agent Protocol - inter-agent communication',
    color: 'bg-purple-100 text-purple-600',
  },
  {
    id: 'skill_md' as const,
    name: 'Skills.md',
    icon: FileCode,
    description: 'Register via skills.md file URL',
    color: 'bg-orange-100 text-orange-600',
  },
]

export default function RegisterAgent() {
  const navigate = useNavigate()
  const [protocol, setProtocol] = useState<RegistrationProtocol>('standard')
  const [formData, setFormData] = useState<AgentFormData>(initialFormData)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [result, setResult] = useState<{ success: boolean; message: string; agent_id?: string } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [formErrors, setFormErrors] = useState<string[]>([])

  const validateForm = (): boolean => {
    const errors: string[] = []

    switch (protocol) {
      case 'standard':
        if (!formData.name.trim()) errors.push('Name is required')
        if (!formData.capabilities.trim()) errors.push('Capabilities is required')
        if (!formData.endpoint.trim()) errors.push('Endpoint URL is required')
        break
      case 'mcp':
        if (!formData.name.trim()) errors.push('Name is required')
        if (!formData.mcp_endpoint.trim()) errors.push('MCP Endpoint is required')
        if (!formData.capabilities.trim()) errors.push('Capabilities is required')
        break
      case 'a2a':
        if (!formData.a2a_endpoint.trim()) errors.push('A2A Endpoint is required')
        if (!formData.agent_card_json.trim()) errors.push('Agent Card JSON is required')
        break
      case 'skill_md':
        if (!formData.skill_url.trim()) errors.push('Skills.md URL is required')
        break
    }

    setFormErrors(errors)
    return errors.length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!validateForm()) {
      return
    }

    setIsSubmitting(true)
    setError(null)
    setResult(null)
    setFormErrors([])

    try {
      let endpoint = ''
      let body: Record<string, unknown> = {}

      switch (protocol) {
        case 'standard':
          endpoint = `${API_BASE}/agents/register`
          body = {
            agent_id: formData.agent_id || `agent-${Date.now()}`,
            name: formData.name,
            agent_type: 'ai_agent',
            capabilities: formData.capabilities.split(',').map((c) => c.trim()).filter(Boolean),
            skills: [],
            endpoint: formData.endpoint,
            protocol: 'standard',
            stake: formData.stake,
            description: formData.description,
            metadata: {},
          }
          break

        case 'mcp':
          endpoint = `${API_BASE}/agents/register/mcp`
          body = {
            agent_id: formData.agent_id || `mcp-${Date.now()}`,
            name: formData.name,
            mcp_endpoint: formData.mcp_endpoint || formData.endpoint,
            capabilities: formData.capabilities.split(',').map((c) => c.trim()).filter(Boolean),
            stake: formData.stake,
          }
          break

        case 'a2a':
          endpoint = `${API_BASE}/agents/register/a2a`
          let agentCard = {}
          try {
            agentCard = formData.agent_card_json ? JSON.parse(formData.agent_card_json) : {}
          } catch {
            setError('Invalid JSON format for Agent Card')
            setIsSubmitting(false)
            return
          }
          body = {
            agent_card: agentCard,
            endpoint: formData.a2a_endpoint || formData.endpoint,
          }
          break

        case 'skill_md':
          endpoint = `${API_BASE}/agents/register/skill-md`
          body = {
            skill_url: formData.skill_url,
            agent_id: formData.agent_id || '',
          }
          break
      }

      const response = await authFetch(endpoint, {
        method: 'POST',
        body: JSON.stringify(body),
      })

      const data = await response.json()

      if (response.ok) {
        setResult({
          success: true,
          message: data.message || 'Agent registered successfully!',
          agent_id: data.agent_id,
        })
        setFormData(initialFormData)
      } else {
        setError(data.detail || 'Registration failed')
      }
    } catch (err) {
      console.error('Registration error:', err)
      setError('Network error. Please check if the backend is running.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const renderForm = () => {
    switch (protocol) {
      case 'standard':
        return (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                Agent ID (optional)
              </label>
              <input
                type="text"
                className="input dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100 dark:placeholder-secondary-400"
                placeholder="Auto-generated if empty"
                value={formData.agent_id}
                onChange={(e) => setFormData({ ...formData, agent_id: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                className="input dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100 dark:placeholder-secondary-400"
                placeholder="My AI Agent"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                Capabilities (comma-separated) <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                className="input dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100 dark:placeholder-secondary-400"
                placeholder="data-processing, nlp, machine-learning"
                value={formData.capabilities}
                onChange={(e) => setFormData({ ...formData, capabilities: e.target.value })}
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                Endpoint URL <span className="text-red-500">*</span>
              </label>
              <input
                type="url"
                className="input dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100 dark:placeholder-secondary-400"
                placeholder="https://api.example.com/agent"
                value={formData.endpoint}
                onChange={(e) => setFormData({ ...formData, endpoint: e.target.value })}
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                Initial Stake (VIBE)
              </label>
              <input
                type="number"
                className="input dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100 dark:placeholder-secondary-400"
                placeholder="100"
                min="0"
                value={formData.stake}
                onChange={(e) => setFormData({ ...formData, stake: parseFloat(e.target.value) || 0 })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                Description
              </label>
              <textarea
                className="input dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100 dark:placeholder-secondary-400"
                rows={3}
                placeholder="Describe your agent's capabilities and purpose"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              />
            </div>
          </div>
        )

      case 'mcp':
        return (
          <div className="space-y-4">
            <div className="bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-700 rounded-lg p-4 mb-4">
              <div className="flex items-center gap-2 text-green-700 dark:text-green-400">
                <Info size={18} />
                <span className="font-medium">MCP Protocol</span>
              </div>
              <p className="text-sm text-green-600 dark:text-green-300 mt-1">
                Model Context Protocol is used by Claude and other AI assistants.
                Provide your MCP server endpoint.
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                Agent ID (optional)
              </label>
              <input
                type="text"
                className="input dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100 dark:placeholder-secondary-400"
                placeholder="Auto-generated if empty"
                value={formData.agent_id}
                onChange={(e) => setFormData({ ...formData, agent_id: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                className="input dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100 dark:placeholder-secondary-400"
                placeholder="My MCP Agent"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                MCP Endpoint <span className="text-red-500">*</span>
              </label>
              <input
                type="url"
                className="input dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100 dark:placeholder-secondary-400"
                placeholder="https://mcp.example.com/sse"
                value={formData.mcp_endpoint}
                onChange={(e) => setFormData({ ...formData, mcp_endpoint: e.target.value })}
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                Capabilities (comma-separated) <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                className="input dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100 dark:placeholder-secondary-400"
                placeholder="file-read, web-search, code-execution"
                value={formData.capabilities}
                onChange={(e) => setFormData({ ...formData, capabilities: e.target.value })}
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                Initial Stake (VIBE)
              </label>
              <input
                type="number"
                className="input dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100 dark:placeholder-secondary-400"
                placeholder="100"
                min="0"
                value={formData.stake}
                onChange={(e) => setFormData({ ...formData, stake: parseFloat(e.target.value) || 0 })}
              />
            </div>
          </div>
        )

      case 'a2a':
        return (
          <div className="space-y-4">
            <div className="bg-purple-50 dark:bg-purple-900/30 border border-purple-200 dark:border-purple-700 rounded-lg p-4 mb-4">
              <div className="flex items-center gap-2 text-purple-700 dark:text-purple-400">
                <Info size={18} />
                <span className="font-medium">A2A Protocol</span>
              </div>
              <p className="text-sm text-purple-600 dark:text-purple-300 mt-1">
                Agent-to-Agent Protocol for inter-agent communication.
                Provide your agent card JSON and endpoint.
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                A2A Endpoint <span className="text-red-500">*</span>
              </label>
              <input
                type="url"
                className="input dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100 dark:placeholder-secondary-400"
                placeholder="https://agent.example.com/a2a"
                value={formData.a2a_endpoint}
                onChange={(e) => setFormData({ ...formData, a2a_endpoint: e.target.value })}
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                Agent Card JSON <span className="text-red-500">*</span>
              </label>
              <textarea
                className="input font-mono text-sm dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100 dark:placeholder-secondary-400"
                rows={8}
                placeholder={`{
  "agent_id": "my-agent",
  "name": "My A2A Agent",
  "capabilities": ["task-execution", "data-analysis"],
  "skills": [{"name": "python", "level": "expert"}],
  "description": "An A2A compatible agent"
}`}
                value={formData.agent_card_json}
                onChange={(e) => setFormData({ ...formData, agent_card_json: e.target.value })}
                required
              />
            </div>
          </div>
        )

      case 'skill_md':
        return (
          <div className="space-y-4">
            <div className="bg-orange-50 dark:bg-orange-900/30 border border-orange-200 dark:border-orange-700 rounded-lg p-4 mb-4">
              <div className="flex items-center gap-2 text-orange-700 dark:text-orange-400">
                <Info size={18} />
                <span className="font-medium">Skills.md Registration</span>
              </div>
              <p className="text-sm text-orange-600 dark:text-orange-300 mt-1">
                Register an agent via its skills.md file URL.
                The system will parse the file and extract capabilities.
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                Agent ID (optional)
              </label>
              <input
                type="text"
                className="input dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100 dark:placeholder-secondary-400"
                placeholder="Auto-generated if empty"
                value={formData.agent_id}
                onChange={(e) => setFormData({ ...formData, agent_id: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                Skills.md URL <span className="text-red-500">*</span>
              </label>
              <input
                type="url"
                className="input dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100 dark:placeholder-secondary-400"
                placeholder="https://raw.githubusercontent.com/user/repo/main/skills.md"
                value={formData.skill_url}
                onChange={(e) => setFormData({ ...formData, skill_url: e.target.value })}
                required
              />
            </div>
          </div>
        )
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate('/agents')}
          aria-label="Go back to agents"
          className="p-2 rounded-lg hover:bg-secondary-100 dark:hover:bg-secondary-700 text-secondary-600 dark:text-secondary-400"
        >
          <ArrowLeft size={20} />
        </button>
        <div>
          <h1 className="text-xl md:text-2xl font-bold text-light-text-primary dark:text-secondary-100">Register External Agent</h1>
          <p className="text-sm md:text-base text-secondary-500 dark:text-secondary-400">Register an AI agent using various protocols</p>
        </div>
      </div>

      {/* Protocol Selection */}
      <div className="card">
        <h2 className="text-base md:text-lg font-semibold text-light-text-primary dark:text-secondary-100 mb-4">Select Protocol</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
          {protocolOptions.map((option) => (
            <button
              key={option.id}
              onClick={() => setProtocol(option.id)}
              className={clsx(
                'p-3 md:p-4 rounded-xl border-2 text-left transition-all',
                protocol === option.id
                  ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/30'
                  : 'border-secondary-200 dark:border-secondary-700 hover:border-secondary-300 dark:hover:border-secondary-600'
              )}
            >
              <div className={clsx('w-10 h-10 rounded-lg flex items-center justify-center mb-2', option.color)}>
                <option.icon size={20} />
              </div>
              <h3 className="font-semibold text-light-text-primary dark:text-secondary-100">{option.name}</h3>
              <p className="text-xs text-secondary-500 dark:text-secondary-400 mt-1 line-clamp-2">{option.description}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Registration Form */}
      <form onSubmit={handleSubmit} className="card">
        <h2 className="text-lg font-semibold text-light-text-primary dark:text-secondary-100 mb-4">
          {protocolOptions.find((p) => p.id === protocol)?.name} Registration
        </h2>

        {renderForm()}

        {/* Form Validation Errors */}
        {formErrors.length > 0 && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-start gap-2 text-red-700">
              <AlertCircle size={18} className="mt-0.5 flex-shrink-0" />
              <div>
                <p className="font-medium">Please fix the following errors:</p>
                <ul className="list-disc list-inside text-sm mt-1">
                  {formErrors.map((err, idx) => (
                    <li key={idx}>{err}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-center gap-2 text-red-700">
              <AlertCircle size={18} />
              <span>{error}</span>
            </div>
          </div>
        )}

        {/* Success Message */}
        {result && result.success && (
          <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
            <div className="flex items-center gap-2 text-green-700">
              <CheckCircle size={18} />
              <div>
                <span className="font-medium">{result.message}</span>
                {result.agent_id && (
                  <p className="text-sm mt-1">Agent ID: {result.agent_id}</p>
                )}
              </div>
            </div>
            <button
              type="button"
              onClick={() => navigate(`/agents/${result.agent_id}`)}
              className="mt-3 btn btn-primary btn-sm"
            >
              View Agent Details
            </button>
          </div>
        )}

        {/* Submit Button */}
        <div className="flex justify-end gap-3 mt-6">
          <button
            type="button"
            onClick={() => navigate('/agents')}
            className="btn btn-secondary"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isSubmitting}
            className="btn btn-primary flex items-center gap-2 disabled:opacity-50"
          >
            {isSubmitting ? (
              <>
                <RefreshCw className="animate-spin" size={18} />
                Registering...
              </>
            ) : (
              <>
                <Send size={18} />
                Register Agent
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  )
}
