import { useParams, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ArrowLeft, FileText, Shield, Cookie, Scale } from 'lucide-react'
import clsx from 'clsx'

const legalDocs = {
  privacy: {
    icon: Shield,
    color: 'text-blue-500',
    bgColor: 'bg-blue-500/10',
  },
  terms: {
    icon: Scale,
    color: 'text-purple-500',
    bgColor: 'bg-purple-500/10',
  },
  cookies: {
    icon: Cookie,
    color: 'text-orange-500',
    bgColor: 'bg-orange-500/10',
  },
  license: {
    icon: FileText,
    color: 'text-green-500',
    bgColor: 'bg-green-500/10',
  },
}

export default function LegalPage() {
  const { type } = useParams<{ type: keyof typeof legalDocs }>()
  const { t } = useTranslation()

  const doc = legalDocs[type || 'privacy']
  const DocIcon = doc.icon

  const getTitle = () => {
    switch (type) {
      case 'privacy':
        return t('legal.privacy.title', 'Privacy Policy')
      case 'terms':
        return t('legal.terms.title', 'Terms of Service')
      case 'cookies':
        return t('legal.cookies.title', 'Cookie Policy')
      case 'license':
        return t('legal.license.title', 'License Agreement')
      default:
        return t('legal.privacy.title', 'Privacy Policy')
    }
  }

  const getLastUpdated = () => {
    return t('legal.lastUpdated', 'Last updated: February 2025')
  }

  return (
    <div className="min-h-screen bg-secondary-50 dark:bg-secondary-950">
      {/* Header */}
      <header className="bg-white dark:bg-secondary-900 border-b border-secondary-200 dark:border-secondary-800">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 text-secondary-600 dark:text-secondary-400 hover:text-secondary-900 dark:hover:text-secondary-100">
            <ArrowLeft size={20} />
            <span>{t('legal.backToHome', 'Back to Home')}</span>
          </Link>
          <div className={clsx('flex items-center gap-2 px-3 py-1.5 rounded-full', doc.bgColor)}>
            <DocIcon className={clsx('w-4 h-4', doc.color)} />
            <span className={clsx('text-sm font-medium', doc.color)}>{getTitle()}</span>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-4xl mx-auto px-4 py-12">
        <article className="card">
          <h1 className="text-3xl font-bold text-secondary-900 dark:text-secondary-100 mb-2">
            {getTitle()}
          </h1>
          <p className="text-secondary-500 dark:text-secondary-400 mb-8">{getLastUpdated()}</p>

          <div className="prose prose-slate dark:prose-invert max-w-none">
            {type === 'privacy' && <PrivacyContent t={t} />}
            {type === 'terms' && <TermsContent t={t} />}
            {type === 'cookies' && <CookiesContent t={t} />}
            {type === 'license' && <LicenseContent t={t} />}
          </div>
        </article>

        {/* Related Links */}
        <div className="mt-8 grid grid-cols-2 md:grid-cols-4 gap-4">
          {Object.entries(legalDocs).map(([key, value]) => {
            const Icon = value.icon
            const isActive = key === type
            return (
              <Link
                key={key}
                to={`/legal/${key}`}
                className={clsx(
                  'p-4 rounded-xl border transition-all',
                  isActive
                    ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                    : 'border-secondary-200 dark:border-secondary-700 hover:border-primary-300 dark:hover:border-primary-700'
                )}
              >
                <div className={clsx('w-10 h-10 rounded-lg flex items-center justify-center mb-2', value.bgColor)}>
                  <Icon className={clsx('w-5 h-5', value.color)} />
                </div>
                <span className={clsx(
                  'text-sm font-medium',
                  isActive ? 'text-primary-600 dark:text-primary-400' : 'text-secondary-700 dark:text-secondary-300'
                )}>
                  {t(`legal.${key}.title`, key.charAt(0).toUpperCase() + key.slice(1))}
                </span>
              </Link>
            )
          })}
        </div>
      </main>
    </div>
  )
}

function PrivacyContent({ t }: { t: (key: string, fallback: string) => string }) {
  return (
    <div className="space-y-6 text-secondary-700 dark:text-secondary-300">
      <section>
        <h2 className="text-xl font-semibold text-secondary-900 dark:text-secondary-100 mb-3">
          {t('legal.privacy.intro.title', 'Introduction')}
        </h2>
        <p>
          {t('legal.privacy.intro.content', 'USMSB SDK ("we", "our", or "us") is committed to protecting your privacy. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our platform.')}
        </p>
      </section>

      <section>
        <h2 className="text-xl font-semibold text-secondary-900 dark:text-secondary-100 mb-3">
          {t('legal.privacy.collect.title', 'Information We Collect')}
        </h2>
        <p className="mb-2">{t('legal.privacy.collect.intro', 'We may collect information about you in various ways, including:')}</p>
        <ul className="list-disc pl-6 space-y-2">
          <li>{t('legal.privacy.collect.wallet', 'Wallet addresses and blockchain transaction data')}</li>
          <li>{t('legal.privacy.collect.usage', 'Usage data and analytics information')}</li>
          <li>{t('legal.privacy.collect.device', 'Device and browser information')}</li>
          <li>{t('legal.privacy.collect.agent', 'AI Agent registration and capability data')}</li>
        </ul>
      </section>

      <section>
        <h2 className="text-xl font-semibold text-secondary-900 dark:text-secondary-100 mb-3">
          {t('legal.privacy.use.title', 'How We Use Your Information')}
        </h2>
        <p>{t('legal.privacy.use.content', 'We use the information we collect to provide, maintain, and improve our services, including AI agent matching, reputation scoring, and settlement processing.')}</p>
      </section>

      <section>
        <h2 className="text-xl font-semibold text-secondary-900 dark:text-secondary-100 mb-3">
          {t('legal.privacy.security.title', 'Data Security')}
        </h2>
        <p>{t('legal.privacy.security.content', 'We implement appropriate technical and organizational measures to protect your personal information against unauthorized access, alteration, disclosure, or destruction.')}</p>
      </section>

      <section>
        <h2 className="text-xl font-semibold text-secondary-900 dark:text-secondary-100 mb-3">
          {t('legal.privacy.contact.title', 'Contact Us')}
        </h2>
        <p>{t('legal.privacy.contact.content', 'If you have questions about this Privacy Policy, please contact us at privacy@usmsb.io')}</p>
      </section>
    </div>
  )
}

function TermsContent({ t }: { t: (key: string, fallback: string) => string }) {
  return (
    <div className="space-y-6 text-secondary-700 dark:text-secondary-300">
      <section>
        <h2 className="text-xl font-semibold text-secondary-900 dark:text-secondary-100 mb-3">
          {t('legal.terms.intro.title', 'Terms of Service')}
        </h2>
        <p>
          {t('legal.terms.intro.content', 'By accessing and using USMSB SDK, you agree to be bound by these Terms of Service and all applicable laws and regulations.')}
        </p>
      </section>

      <section>
        <h2 className="text-xl font-semibold text-secondary-900 dark:text-secondary-100 mb-3">
          {t('legal.terms.use.title', 'Use License')}
        </h2>
        <p>{t('legal.terms.use.content', 'Permission is granted to temporarily use USMSB SDK for personal or commercial purposes subject to the restrictions in these terms.')}</p>
      </section>

      <section>
        <h2 className="text-xl font-semibold text-secondary-900 dark:text-secondary-100 mb-3">
          {t('legal.terms.prohibited.title', 'Prohibited Activities')}
        </h2>
        <ul className="list-disc pl-6 space-y-2">
          <li>{t('legal.terms.prohibited.1', 'Using the platform for any unlawful purpose')}</li>
          <li>{t('legal.terms.prohibited.2', 'Attempting to gain unauthorized access to any part of the platform')}</li>
          <li>{t('legal.terms.prohibited.3', 'Interfering with the proper working of the platform')}</li>
          <li>{t('legal.terms.prohibited.4', 'Registering malicious or harmful AI agents')}</li>
        </ul>
      </section>

      <section>
        <h2 className="text-xl font-semibold text-secondary-900 dark:text-secondary-100 mb-3">
          {t('legal.terms.disclaimer.title', 'Disclaimer')}
        </h2>
        <p>{t('legal.terms.disclaimer.content', 'USMSB SDK is provided "as is" without any warranties, expressed or implied. We do not warrant that the platform will be uninterrupted or error-free.')}</p>
      </section>
    </div>
  )
}

function CookiesContent({ t }: { t: (key: string, fallback: string) => string }) {
  return (
    <div className="space-y-6 text-secondary-700 dark:text-secondary-300">
      <section>
        <h2 className="text-xl font-semibold text-secondary-900 dark:text-secondary-100 mb-3">
          {t('legal.cookies.intro.title', 'Cookie Policy')}
        </h2>
        <p>
          {t('legal.cookies.intro.content', 'This Cookie Policy explains how USMSB SDK uses cookies and similar technologies to recognize you when you visit our platform.')}
        </p>
      </section>

      <section>
        <h2 className="text-xl font-semibold text-secondary-900 dark:text-secondary-100 mb-3">
          {t('legal.cookies.what.title', 'What Are Cookies?')}
        </h2>
        <p>{t('legal.cookies.what.content', 'Cookies are small data files that are placed on your computer or mobile device when you visit a website. Cookies are widely used by website owners to make their websites work, work more efficiently, and to provide reporting information.')}</p>
      </section>

      <section>
        <h2 className="text-xl font-semibold text-secondary-900 dark:text-secondary-100 mb-3">
          {t('legal.cookies.types.title', 'Types of Cookies We Use')}
        </h2>
        <ul className="list-disc pl-6 space-y-2">
          <li><strong>Essential Cookies:</strong> {t('legal.cookies.types.essential', 'Required for the platform to function properly')}</li>
          <li><strong>Preference Cookies:</strong> {t('legal.cookies.types.preference', 'Remember your settings and preferences')}</li>
          <li><strong>Analytics Cookies:</strong> {t('legal.cookies.types.analytics', 'Help us understand how visitors interact with our platform')}</li>
        </ul>
      </section>

      <section>
        <h2 className="text-xl font-semibold text-secondary-900 dark:text-secondary-100 mb-3">
          {t('legal.cookies.control.title', 'Controlling Cookies')}
        </h2>
        <p>{t('legal.cookies.control.content', 'You can set your browser to refuse all or some browser cookies, or to alert you when websites set or access cookies.')}</p>
      </section>
    </div>
  )
}

function LicenseContent({ t }: { t: (key: string, fallback: string) => string }) {
  return (
    <div className="space-y-6 text-secondary-700 dark:text-secondary-300">
      <section>
        <h2 className="text-xl font-semibold text-secondary-900 dark:text-secondary-100 mb-3">
          {t('legal.license.intro.title', 'MIT License')}
        </h2>
        <p>
          {t('legal.license.intro.content', 'Copyright (c) 2025 USMSB SDK')}
        </p>
      </section>

      <section>
        <h2 className="text-xl font-semibold text-secondary-900 dark:text-secondary-100 mb-3">
          {t('legal.license.grant.title', 'License Grant')}
        </h2>
        <p>{t('legal.license.grant.content', 'Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software.')}</p>
      </section>

      <section>
        <h2 className="text-xl font-semibold text-secondary-900 dark:text-secondary-100 mb-3">
          {t('legal.license.conditions.title', 'Conditions')}
        </h2>
        <p>{t('legal.license.conditions.content', 'The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.')}</p>
      </section>

      <section>
        <h2 className="text-xl font-semibold text-secondary-900 dark:text-secondary-100 mb-3">
          {t('legal.license.disclaimer.title', 'Disclaimer')}
        </h2>
        <p className="font-mono text-sm bg-secondary-100 dark:bg-secondary-800 p-4 rounded-lg">
          {t('legal.license.disclaimer.content', 'THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.')}
        </p>
      </section>
    </div>
  )
}
