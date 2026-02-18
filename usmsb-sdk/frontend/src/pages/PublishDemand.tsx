import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import {
  Plus,
  Trash2,
  Target,
  DollarSign,
  Send,
  CheckCircle,
  AlertCircle,
  FileText,
  Zap,
} from 'lucide-react'
import { createDemand, getAgents } from '@/lib/api'
import { toast } from '../stores/toastStore'

interface DemandForm {
  title: string
  description: string
  category: string
  requiredSkills: string[]
  skillInput: string
  budgetMin: string
  budgetMax: string
  deadline: string
  priority: 'low' | 'medium' | 'high' | 'urgent'
  qualityRequirements: string
  attachmentUrls: string[]
}

export default function PublishDemand() {
  const { t } = useTranslation()

  const categories = [
    { value: 'development', label: t('publishDemand.categoryDevelopment'), icon: '💻' },
    { value: 'data', label: t('publishDemand.categoryData'), icon: '📊' },
    { value: 'design', label: t('publishDemand.categoryDesign'), icon: '🎨' },
    { value: 'content', label: t('publishDemand.categoryContent'), icon: '✍️' },
    { value: 'consulting', label: t('publishDemand.categoryConsulting'), icon: '💡' },
    { value: 'marketing', label: t('publishDemand.categoryMarketing'), icon: '📢' },
    { value: 'education', label: t('publishDemand.categoryEducation'), icon: '📚' },
    { value: 'other', label: t('publishDemand.categoryOther'), icon: '🌐' },
  ]

  // Get agents for creating demand
  const { data: agents } = useQuery({
    queryKey: ['agents'],
    queryFn: () => getAgents(undefined, 1),
  })

  const [form, setForm] = useState<DemandForm>({
    title: '',
    description: '',
    category: '',
    requiredSkills: [],
    skillInput: '',
    budgetMin: '',
    budgetMax: '',
    deadline: '',
    priority: 'medium',
    qualityRequirements: '',
    attachmentUrls: [],
  })
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  const addSkill = () => {
    if (form.skillInput.trim() && !form.requiredSkills.includes(form.skillInput.trim())) {
      setForm({
        ...form,
        requiredSkills: [...form.requiredSkills, form.skillInput.trim()],
        skillInput: '',
      })
    }
  }

  const removeSkill = (skill: string) => {
    setForm({
      ...form,
      requiredSkills: form.requiredSkills.filter((s) => s !== skill),
    })
  }

  const handleSubmit = async () => {
    if (!agents || agents.length === 0) {
      toast.warning(t('publishDemand.pleaseCreateAgent'))
      return
    }

    setIsSubmitting(true)
    try {
      const agentId = agents[0].id
      await createDemand({
        agent_id: agentId,
        title: form.title,
        description: form.description,
        category: form.category,
        required_skills: form.requiredSkills,
        budget_min: form.budgetMin ? parseFloat(form.budgetMin) : undefined,
        budget_max: form.budgetMax ? parseFloat(form.budgetMax) : undefined,
        deadline: form.deadline,
        priority: form.priority,
        quality_requirements: form.qualityRequirements,
      })
      setIsSubmitting(false)
      setSubmitted(true)
    } catch (error) {
      console.error('Failed to create demand:', error)
      setIsSubmitting(false)
      toast.error(t('publishDemand.failedToCreateDemand'))
    }
  }

  if (submitted) {
    return (
      <div className="max-w-2xl mx-auto py-12 px-4">
        <div className="card text-center py-12">
          <div className="w-16 h-16 bg-green-100 dark:bg-green-800 rounded-full flex items-center justify-center mx-auto mb-4">
            <CheckCircle className="text-green-600 dark:text-green-400" size={32} />
          </div>
          <h2 className="text-2xl font-bold text-secondary-900 dark:text-secondary-100 mb-2">
            {t('publishDemand.publishSuccess')}
          </h2>
          <p className="text-secondary-600 dark:text-secondary-400 mb-6">
            {t('publishDemand.publishSuccessDesc')}
          </p>
          <div className="space-y-3">
            <button
              className="btn btn-primary w-full"
              onClick={() => setSubmitted(false)}
            >
              {t('publishDemand.publishAnother')}
            </button>
            <button
              className="btn btn-secondary w-full"
              onClick={() => window.location.href = '/matching'}
            >
              {t('publishDemand.findSuppliers')}
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4">
        <div>
          <h1 className="text-xl md:text-2xl font-bold text-secondary-900 dark:text-secondary-100">{t('publishDemand.publishMyDemand')}</h1>
          <p className="text-sm md:text-base text-secondary-500 dark:text-secondary-400">
            {t('publishDemand.broadcastToMarket')}
          </p>
          <div className="mt-2 px-3 py-2 bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-700 rounded-lg">
            <p className="text-xs md:text-sm text-green-700 dark:text-green-300">
              {t('publishDemand.differenceHint')}
            </p>
          </div>
        </div>
      </div>

      {/* Form */}
      <div className="card">
        <div className="space-y-6">
          {/* Basic Info */}
          <div>
            <h3 className="font-semibold text-secondary-900 dark:text-secondary-100 mb-4 flex items-center gap-2">
              <Target size={20} />
              {t('publishDemand.basicInfo')}
            </h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                  {t('publishDemand.demandTitle')} *
                </label>
                <input
                  type="text"
                  className="input dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100 dark:placeholder-secondary-400"
                  placeholder={t('publishDemand.titlePlaceholder')}
                  value={form.title}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                  {t('publishDemand.demandCategory')} *
                </label>
                <select
                  className="input dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100"
                  value={form.category}
                  onChange={(e) => setForm({ ...form, category: e.target.value })}
                >
                  <option value="">{t('publishDemand.selectCategory')}</option>
                  {categories.map((cat) => (
                    <option key={cat.value} value={cat.value}>
                      {cat.icon} {cat.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                  {t('publishDemand.detailedDescription')} *
                </label>
                <textarea
                  className="input min-h-[150px] dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100 dark:placeholder-secondary-400"
                  placeholder={t('publishDemand.describeNeeds')}
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                />
              </div>
            </div>
          </div>

          {/* Required Skills */}
          <div>
            <h3 className="font-semibold text-secondary-900 dark:text-secondary-100 mb-4 flex items-center gap-2">
              <Zap size={20} />
              {t('publishDemand.requiredSkills')}
            </h3>
            <div className="space-y-3">
              <div className="flex gap-2">
                <input
                  type="text"
                  className="input flex-1 dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100 dark:placeholder-secondary-400"
                  placeholder={t('publishDemand.enterSkill')}
                  value={form.skillInput}
                  onChange={(e) => setForm({ ...form, skillInput: e.target.value })}
                  onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addSkill())}
                />
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={addSkill}
                >
                  <Plus size={18} />
                </button>
              </div>
              {form.requiredSkills.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {form.requiredSkills.map((skill) => (
                    <span
                      key={skill}
                      className="inline-flex items-center gap-1 px-3 py-1 bg-green-100 dark:bg-green-800 text-green-700 dark:text-green-300 rounded-full"
                    >
                      {skill}
                      <button
                        onClick={() => removeSkill(skill)}
                        className="hover:text-green-900 dark:text-green-100 dark:hover:text-green-200"
                      >
                        <Trash2 size={14} />
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Budget & Timeline */}
          <div>
            <h3 className="font-semibold text-secondary-900 dark:text-secondary-100 mb-4 flex items-center gap-2">
              <DollarSign size={20} />
              {t('publishDemand.budgetTime')}
            </h3>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                    {t('publishDemand.budgetMin')}
                  </label>
                  <input
                    type="number"
                    className="input dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100 dark:placeholder-secondary-400"
                    placeholder="500"
                    value={form.budgetMin}
                    onChange={(e) => setForm({ ...form, budgetMin: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                    {t('publishDemand.budgetMax')}
                  </label>
                  <input
                    type="number"
                    className="input dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100 dark:placeholder-secondary-400"
                    placeholder="2000"
                    value={form.budgetMax}
                    onChange={(e) => setForm({ ...form, budgetMax: e.target.value })}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                    {t('publishDemand.deadline')}
                  </label>
                  <input
                    type="date"
                    className="input dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100"
                    value={form.deadline}
                    onChange={(e) => setForm({ ...form, deadline: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                    {t('publishDemand.priority')}
                  </label>
                  <select
                    className="input dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100"
                    value={form.priority}
                    onChange={(e) => setForm({ ...form, priority: e.target.value as any })}
                  >
                    <option value="low">{t('publishDemand.low')}</option>
                    <option value="medium">{t('publishDemand.medium')}</option>
                    <option value="high">{t('publishDemand.high')}</option>
                    <option value="urgent">{t('publishDemand.urgent')}</option>
                  </select>
                </div>
              </div>
            </div>
          </div>

          {/* Quality */}
          <div>
            <h3 className="font-semibold text-secondary-900 dark:text-secondary-100 mb-4 flex items-center gap-2">
              <FileText size={20} />
              {t('publishDemand.quality')}
            </h3>
            <div>
              <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                {t('publishDemand.qualityStandard')}
              </label>
              <textarea
                className="input min-h-[100px] dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100 dark:placeholder-secondary-400"
                placeholder={t('publishDemand.qualityPlaceholder')}
                value={form.qualityRequirements}
                onChange={(e) => setForm({ ...form, qualityRequirements: e.target.value })}
              />
            </div>
          </div>

          {/* Submit */}
          <div className="pt-4 border-t border-secondary-200 dark:border-secondary-700">
            <button
              className="btn btn-primary w-full py-3 flex items-center justify-center gap-2"
              onClick={handleSubmit}
              disabled={isSubmitting || !form.title || !form.category || !form.description}
            >
              {isSubmitting ? (
                <>
                  <div className="animate-spin w-5 h-5 border-2 border-white border-t-transparent rounded-full" />
                  {t('publishDemand.publishing')}
                </>
              ) : (
                <>
                  <Send size={18} />
                  {t('publishDemand.publish')}
                </>
              )}
            </button>
            <p className="text-xs text-secondary-500 dark:text-secondary-400 text-center mt-2">
              {t('publishDemand.publishSuccessDesc')}
            </p>
          </div>
        </div>
      </div>

      {/* Tips */}
      <div className="card bg-green-50 dark:bg-green-900/30 border-green-200 dark:border-green-700">
        <div className="flex items-start gap-3">
          <AlertCircle className="text-green-600 dark:text-green-400 dark:text-green-400 mt-1" size={20} />
          <div>
            <h4 className="font-medium text-green-900 dark:text-green-100 dark:text-green-300">{t('publishDemand.publishTips')}</h4>
            <ul className="text-sm text-green-800 dark:text-green-200 dark:text-green-300 mt-2 space-y-1">
              <li>{t('publishDemand.tip1')}</li>
              <li>{t('publishDemand.tip2')}</li>
              <li>{t('publishDemand.tip3')}</li>
              <li>{t('publishDemand.tip4')}</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
