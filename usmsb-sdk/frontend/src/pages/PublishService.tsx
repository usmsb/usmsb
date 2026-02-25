import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import {
  Plus,
  Trash2,
  DollarSign,
  Clock,
  Zap,
  Send,
  CheckCircle,
  AlertCircle,
  Briefcase,
} from 'lucide-react'
import { getAgents } from '@/lib/api'
import api from '@/lib/api'
import { toast } from '../stores/toastStore'

interface ServiceForm {
  name: string
  description: string
  category: string
  skills: string[]
  skillInput: string
  priceType: 'hourly' | 'fixed' | 'negotiable'
  priceMin: string
  priceMax: string
  availability: string
  deliveryTime: string
  portfolio: string[]
}

export default function PublishService() {
  const { t } = useTranslation()

  const categories = [
    { value: 'development', label: t('publishService.categoryDevelopment'), icon: '💻' },
    { value: 'data', label: t('publishService.categoryData'), icon: '📊' },
    { value: 'design', label: t('publishService.categoryDesign'), icon: '🎨' },
    { value: 'content', label: t('publishService.categoryContent'), icon: '✍️' },
    { value: 'consulting', label: t('publishService.categoryConsulting'), icon: '💡' },
    { value: 'marketing', label: t('publishService.categoryMarketing'), icon: '📢' },
    { value: 'education', label: t('publishService.categoryEducation'), icon: '📚' },
    { value: 'other', label: t('publishService.categoryOther'), icon: '🌐' },
  ]

  // Get agents
  const { data: agents } = useQuery({
    queryKey: ['agents'],
    queryFn: () => getAgents(undefined, 1),
  })

  const [form, setForm] = useState<ServiceForm>({
    name: '',
    description: '',
    category: '',
    skills: [],
    skillInput: '',
    priceType: 'hourly',
    priceMin: '',
    priceMax: '',
    availability: 'full-time',
    deliveryTime: '',
    portfolio: [],
  })
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  const addSkill = () => {
    if (form.skillInput.trim() && !form.skills.includes(form.skillInput.trim())) {
      setForm({
        ...form,
        skills: [...form.skills, form.skillInput.trim()],
        skillInput: '',
      })
    }
  }

  const removeSkill = (skill: string) => {
    setForm({
      ...form,
      skills: form.skills.filter((s) => s !== skill),
    })
  }

  const handleSubmit = async () => {
    if (!agents || agents.length === 0) {
      toast.error(t('publishService.pleaseCreateAgent'))
      return
    }

    setIsSubmitting(true)
    try {
      const agentId = agents[0].id
      await api.post(`/agents/${agentId}/services`, {
        service_type: form.category,
        service_name: form.name,
        capabilities: form.skills,
        price: form.priceMin ? parseFloat(form.priceMin) : 0,
        description: form.description,
        availability: form.availability,
      })
      setIsSubmitting(false)
      setSubmitted(true)
      toast.success(t('publishService.publishSuccess'))
    } catch (error) {
      console.error('Failed to create service:', error)
      setIsSubmitting(false)
      toast.error(t('publishService.failedToCreateService'))
    }
  }

  if (submitted) {
    return (
      <div className="max-w-2xl mx-auto py-12 px-4">
        <div className="card text-center py-12">
          <div className="w-16 h-16 bg-green-100 dark:bg-green-800 rounded-full flex items-center justify-center mx-auto mb-4">
            <CheckCircle className="text-green-600 dark:text-green-400" size={32} />
          </div>
          <h2 className="text-2xl font-bold text-light-text-primary dark:text-secondary-100 mb-2">
            {t('publishService.publishSuccess')}
          </h2>
          <p className="text-secondary-600 dark:text-secondary-400 mb-6">
            {t('publishService.publishSuccessDesc')}
          </p>
          <div className="space-y-3">
            <button
              className="btn btn-primary w-full"
              onClick={() => setSubmitted(false)}
            >
              {t('publishService.publishAnother')}
            </button>
            <button
              className="btn btn-secondary w-full"
              onClick={() => window.location.href = '/dashboard'}
            >
              {t('publishService.backToDashboard')}
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
          <h1 className="text-xl md:text-2xl font-bold text-light-text-primary dark:text-secondary-100">{t('publishService.publishMyService')}</h1>
          <p className="text-sm md:text-base text-secondary-500 dark:text-secondary-400">
            {t('publishService.broadcastToMarket')}
          </p>
          <div className="mt-2 px-3 py-2 bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-700 rounded-lg">
            <p className="text-xs md:text-sm text-blue-700 dark:text-blue-300">
              {t('publishService.differenceHint')}
            </p>
          </div>
        </div>
      </div>

      {/* Form */}
      <div className="card">
        <div className="space-y-6">
          {/* Basic Info */}
          <div>
            <h3 className="font-semibold text-light-text-primary dark:text-secondary-100 mb-4 flex items-center gap-2">
              <Briefcase size={20} />
              {t('publishService.basicInfo')}
            </h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                  {t('publishService.serviceName')} *
                </label>
                <input
                  type="text"
                  className="input dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100 dark:placeholder-secondary-400"
                  placeholder={t('publishService.serviceName')}
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                  {t('publishService.serviceCategory')} *
                </label>
                <select
                  className="input dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100"
                  value={form.category}
                  onChange={(e) => setForm({ ...form, category: e.target.value })}
                >
                  <option value="">{t('publishService.selectCategory')}</option>
                  {categories.map((cat) => (
                    <option key={cat.value} value={cat.value}>
                      {cat.icon} {cat.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                  {t('publishService.serviceDescription')} *
                </label>
                <textarea
                  className="input min-h-[120px] dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100 dark:placeholder-secondary-400"
                  placeholder={t('publishService.describeService')}
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                />
              </div>
            </div>
          </div>

          {/* Skills */}
          <div>
            <h3 className="font-semibold text-light-text-primary dark:text-secondary-100 mb-4 flex items-center gap-2">
              <Zap size={20} />
              {t('publishService.skillsSection')}
            </h3>
            <div className="space-y-3">
              <div className="flex gap-2">
                <input
                  type="text"
                  className="input flex-1 dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100 dark:placeholder-secondary-400"
                  placeholder={t('publishService.enterSkillAdd')}
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
              {form.skills.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {form.skills.map((skill) => (
                    <span
                      key={skill}
                      className="inline-flex items-center gap-1 px-3 py-1 bg-primary-100 dark:bg-primary-800 text-primary-700 dark:text-primary-300 rounded-full"
                    >
                      {skill}
                      <button
                        onClick={() => removeSkill(skill)}
                        className="hover:text-primary-900 dark:hover:text-primary-200"
                      >
                        <Trash2 size={14} />
                      </button>
                    </span>
                  ))}
                </div>
              )}
              <p className="text-xs text-secondary-500 dark:text-secondary-400">
                {t('publishService.aiDiscover')}
              </p>
            </div>
          </div>

          {/* Pricing */}
          <div>
            <h3 className="font-semibold text-light-text-primary dark:text-secondary-100 mb-4 flex items-center gap-2">
              <DollarSign size={20} />
              {t('publishService.pricing')}
            </h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-2">
                  {t('publishService.priceType')}
                </label>
                <div className="flex gap-4 dark:text-secondary-200">
                  <label className="flex items-center gap-2">
                    <input
                      type="radio"
                      name="priceType"
                      checked={form.priceType === 'hourly'}
                      onChange={() => setForm({ ...form, priceType: 'hourly' })}
                    />
                    <span>{t('publishService.hourly')}</span>
                  </label>
                  <label className="flex items-center gap-2">
                    <input
                      type="radio"
                      name="priceType"
                      checked={form.priceType === 'fixed'}
                      onChange={() => setForm({ ...form, priceType: 'fixed' })}
                    />
                    <span>{t('publishService.fixed')}</span>
                  </label>
                  <label className="flex items-center gap-2">
                    <input
                      type="radio"
                      name="priceType"
                      checked={form.priceType === 'negotiable'}
                      onChange={() => setForm({ ...form, priceType: 'negotiable' })}
                    />
                    <span>{t('publishService.negotiable')}</span>
                  </label>
                </div>
              </div>

              {(form.priceType === 'hourly' || form.priceType === 'fixed') && (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                      {form.priceType === 'hourly' ? t('publishService.priceMin') : t('publishService.priceMin')}
                    </label>
                    <input
                      type="number"
                      className="input dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100 dark:placeholder-secondary-400"
                      placeholder="50"
                      value={form.priceMin}
                      onChange={(e) => setForm({ ...form, priceMin: e.target.value })}
                    />
                  </div>
                  {form.priceType === 'hourly' && (
                    <div>
                      <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                        {t('publishService.maxRate')}
                      </label>
                      <input
                        type="number"
                        className="input dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100 dark:placeholder-secondary-400"
                        placeholder="100"
                        value={form.priceMax}
                        onChange={(e) => setForm({ ...form, priceMax: e.target.value })}
                      />
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Availability */}
          <div>
            <h3 className="font-semibold text-light-text-primary dark:text-secondary-100 mb-4 flex items-center gap-2">
              <Clock size={20} />
              {t('publishService.availability')}
            </h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                  {t('publishService.availableTime')}
                </label>
                <select
                  className="input dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100"
                  value={form.availability}
                  onChange={(e) => setForm({ ...form, availability: e.target.value })}
                >
                  <option value="full-time">{t('publishService.fullTime40')}</option>
                  <option value="part-time">{t('publishService.partTime20')}</option>
                  <option value="available">{t('publishService.alwaysAvailableOpt')}</option>
                  <option value="limited">{t('publishService.limited')}</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                  {t('publishService.deliveryTime')}
                </label>
                <input
                  type="text"
                  className="input dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100 dark:placeholder-secondary-400"
                  placeholder={t('publishService.deliveryPlaceholder')}
                  value={form.deliveryTime}
                  onChange={(e) => setForm({ ...form, deliveryTime: e.target.value })}
                />
              </div>
            </div>
          </div>

          {/* Submit */}
          <div className="pt-4 border-t border-secondary-200 dark:border-secondary-700">
            <button
              className="btn btn-primary w-full py-3 flex items-center justify-center gap-2"
              onClick={handleSubmit}
              disabled={isSubmitting || !form.name || !form.category || !form.description}
            >
              {isSubmitting ? (
                <>
                  <div className="animate-spin w-5 h-5 border-2 border-white border-t-transparent rounded-full" />
                  {t('publishService.publishing')}
                </>
              ) : (
                <>
                  <Send size={18} />
                  {t('publishService.publish')}
                </>
              )}
            </button>
            <p className="text-xs text-secondary-500 dark:text-secondary-400 text-center mt-2">
              {t('publishService.publishSuccessDesc')}
            </p>
          </div>
        </div>
      </div>

      {/* Tips */}
      <div className="card bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-700">
        <div className="flex items-start gap-3">
          <AlertCircle className="text-blue-600 dark:text-blue-400 dark:text-blue-400 mt-1" size={20} />
          <div>
            <h4 className="font-medium text-blue-900 dark:text-blue-100 dark:text-blue-300">{t('publishService.publishTips')}</h4>
            <ul className="text-sm text-blue-800 dark:text-blue-200 dark:text-blue-300 mt-2 space-y-1">
              <li>{t('publishService.tip1')}</li>
              <li>{t('publishService.tip2')}</li>
              <li>{t('publishService.tip3')}</li>
              <li>{t('publishService.tip4')}</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
