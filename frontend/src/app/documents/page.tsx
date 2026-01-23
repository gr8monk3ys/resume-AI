'use client'

import { useEffect, useState, useCallback } from 'react'
import { useAuth } from '@/lib/auth'
import { useRouter } from 'next/navigation'
import { coverLettersApi, resumesApi, jobsApi, aiApi } from '@/lib/api'
import type { CoverLetter, Resume, JobApplication } from '@/types'
import { cn, formatDate } from '@/lib/utils'
import {
  FileText,
  Mail,
  Trash2,
  Wand2,
  Copy,
  Check,
  AlertCircle,
  Plus,
  Pencil,
  Link2,
  Send,
  MessageSquare,
  FileEdit,
  Sparkles,
  RefreshCw,
} from 'lucide-react'

// Tab types
type TabId = 'cover-letters' | 'networking' | 'professional' | 'composer'

interface Tab {
  id: TabId
  label: string
  icon: React.ReactNode
}

const TABS: Tab[] = [
  { id: 'cover-letters', label: 'Cover Letters', icon: <FileText className="w-4 h-4" /> },
  { id: 'networking', label: 'Networking Emails', icon: <Send className="w-4 h-4" /> },
  { id: 'professional', label: 'Professional Emails', icon: <Mail className="w-4 h-4" /> },
  { id: 'composer', label: 'Custom Composer', icon: <FileEdit className="w-4 h-4" /> },
]

// Email types for networking
type NetworkingEmailType = 'informational' | 'inquiry' | 'thank-you' | 'follow-up'

interface NetworkingEmailTypeOption {
  id: NetworkingEmailType
  label: string
  description: string
}

const NETWORKING_EMAIL_TYPES: NetworkingEmailTypeOption[] = [
  { id: 'informational', label: 'Informational Interview', description: 'Request to learn about someone\'s career path' },
  { id: 'inquiry', label: 'Job Inquiry', description: 'Express interest in potential opportunities' },
  { id: 'thank-you', label: 'Thank You', description: 'Thank someone for their time or help' },
  { id: 'follow-up', label: 'Follow-up', description: 'Follow up after an initial contact' },
]

// Professional email templates
type ProfessionalTemplateId = 'post-interview' | 'no-response' | 'negotiation' | 'accept' | 'decline'

interface ProfessionalTemplate {
  id: ProfessionalTemplateId
  name: string
  description: string
  subjectTemplate: string
  bodyTemplate: string
  placeholders: string[]
}

const PROFESSIONAL_TEMPLATES: ProfessionalTemplate[] = [
  {
    id: 'post-interview',
    name: 'Thank You (Post-Interview)',
    description: 'Send after completing an interview',
    subjectTemplate: 'Thank You - {{POSITION}} Interview',
    bodyTemplate: `Dear {{INTERVIEWER_NAME}},

Thank you for taking the time to meet with me today regarding the {{POSITION}} position at {{COMPANY}}. I enjoyed learning more about the role and the team.

Our conversation about {{DISCUSSION_TOPIC}} was particularly interesting, and I'm excited about the opportunity to contribute to {{SPECIFIC_PROJECT_OR_GOAL}}.

I'm confident that my experience in {{YOUR_RELEVANT_EXPERIENCE}} would allow me to make meaningful contributions to your team.

Please don't hesitate to reach out if you need any additional information. I look forward to hearing from you about the next steps.

Best regards,
{{YOUR_NAME}}`,
    placeholders: ['INTERVIEWER_NAME', 'POSITION', 'COMPANY', 'DISCUSSION_TOPIC', 'SPECIFIC_PROJECT_OR_GOAL', 'YOUR_RELEVANT_EXPERIENCE', 'YOUR_NAME'],
  },
  {
    id: 'no-response',
    name: 'Follow-up (No Response)',
    description: 'Follow up when you haven\'t heard back',
    subjectTemplate: 'Following Up - {{POSITION}} Application',
    bodyTemplate: `Dear {{HIRING_MANAGER_NAME}},

I hope this email finds you well. I wanted to follow up on my application for the {{POSITION}} position at {{COMPANY}}, which I submitted on {{APPLICATION_DATE}}.

I remain very interested in this opportunity and would welcome the chance to discuss how my background in {{YOUR_EXPERTISE}} could contribute to your team's success.

I understand you may be busy reviewing many applications, but I wanted to reiterate my enthusiasm for this role. Please let me know if there's any additional information I can provide.

Thank you for your time and consideration.

Best regards,
{{YOUR_NAME}}
{{YOUR_PHONE}}
{{YOUR_EMAIL}}`,
    placeholders: ['HIRING_MANAGER_NAME', 'POSITION', 'COMPANY', 'APPLICATION_DATE', 'YOUR_EXPERTISE', 'YOUR_NAME', 'YOUR_PHONE', 'YOUR_EMAIL'],
  },
  {
    id: 'negotiation',
    name: 'Salary Negotiation',
    description: 'Negotiate salary or benefits',
    subjectTemplate: 'Re: {{POSITION}} Offer - Compensation Discussion',
    bodyTemplate: `Dear {{HIRING_MANAGER_NAME}},

Thank you so much for extending the offer for the {{POSITION}} position at {{COMPANY}}. I'm thrilled about the opportunity to join your team.

After careful consideration, I would like to discuss the compensation package. Based on my {{YEARS_EXPERIENCE}} years of experience and expertise in {{YOUR_EXPERTISE}}, as well as the market rate for similar positions in {{LOCATION}}, I was hoping we could discuss a base salary of {{DESIRED_SALARY}}.

I'm confident that my skills in {{KEY_SKILLS}} will enable me to make significant contributions to {{COMPANY}} and deliver strong results.

I'm very excited about this opportunity and hope we can find a mutually beneficial arrangement. I'm open to discussing this further at your convenience.

Thank you for your consideration.

Best regards,
{{YOUR_NAME}}`,
    placeholders: ['HIRING_MANAGER_NAME', 'POSITION', 'COMPANY', 'YEARS_EXPERIENCE', 'YOUR_EXPERTISE', 'LOCATION', 'DESIRED_SALARY', 'KEY_SKILLS', 'YOUR_NAME'],
  },
  {
    id: 'accept',
    name: 'Accept Offer',
    description: 'Formally accept a job offer',
    subjectTemplate: 'Acceptance of {{POSITION}} Offer',
    bodyTemplate: `Dear {{HIRING_MANAGER_NAME}},

I am delighted to formally accept the offer for the {{POSITION}} position at {{COMPANY}}. Thank you for this wonderful opportunity.

As discussed, I understand my starting salary will be {{SALARY}}, and my start date will be {{START_DATE}}.

I am excited to join the team and contribute to {{COMPANY}}'s success. Please let me know if there are any documents or forms you need me to complete before my first day.

Thank you again for this opportunity. I look forward to working with you and the team.

Best regards,
{{YOUR_NAME}}`,
    placeholders: ['HIRING_MANAGER_NAME', 'POSITION', 'COMPANY', 'SALARY', 'START_DATE', 'YOUR_NAME'],
  },
  {
    id: 'decline',
    name: 'Decline Offer',
    description: 'Politely decline a job offer',
    subjectTemplate: 'Re: {{POSITION}} Offer',
    bodyTemplate: `Dear {{HIRING_MANAGER_NAME}},

Thank you so much for offering me the {{POSITION}} position at {{COMPANY}}. I truly appreciate the time and effort you and your team invested in the interview process.

After careful consideration, I have decided to decline this opportunity. {{REASON_OPTIONAL}}

This was not an easy decision, as I was impressed by {{POSITIVE_ASPECT}} during our conversations. I hope we can stay in touch and perhaps work together in the future.

Thank you again for your consideration and understanding.

Best regards,
{{YOUR_NAME}}`,
    placeholders: ['HIRING_MANAGER_NAME', 'POSITION', 'COMPANY', 'REASON_OPTIONAL', 'POSITIVE_ASPECT', 'YOUR_NAME'],
  },
]

// Tone options for custom composer
type ToneOption = 'formal' | 'friendly' | 'assertive'

interface ToneConfig {
  id: ToneOption
  label: string
  description: string
}

const TONE_OPTIONS: ToneConfig[] = [
  { id: 'formal', label: 'Formal', description: 'Professional and businesslike' },
  { id: 'friendly', label: 'Friendly', description: 'Warm and approachable' },
  { id: 'assertive', label: 'Assertive', description: 'Confident and direct' },
]

export default function DocumentsPage() {
  const { user, tokens, isLoading: authLoading } = useAuth()
  const router = useRouter()
  const [activeTab, setActiveTab] = useState<TabId>('cover-letters')

  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login')
    }
  }, [user, authLoading, router])

  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    )
  }

  if (!user || !tokens?.access_token) {
    return null
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Document Generator</h1>
        <p className="text-gray-500">Create cover letters, emails, and professional documents</p>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8 overflow-x-auto" aria-label="Tabs">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'flex items-center gap-2 py-4 px-1 border-b-2 font-medium text-sm whitespace-nowrap',
                activeTab === tab.id
                  ? 'border-primary-600 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              )}
              aria-current={activeTab === tab.id ? 'page' : undefined}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'cover-letters' && <CoverLettersTab token={tokens.access_token} />}
      {activeTab === 'networking' && <NetworkingEmailsTab token={tokens.access_token} />}
      {activeTab === 'professional' && <ProfessionalEmailsTab token={tokens.access_token} />}
      {activeTab === 'composer' && <CustomComposerTab token={tokens.access_token} />}
    </div>
  )
}

// =============================================================================
// Cover Letters Tab
// =============================================================================

function CoverLettersTab({ token }: { token: string }) {
  const [coverLetters, setCoverLetters] = useState<CoverLetter[]>([])
  const [resumes, setResumes] = useState<Resume[]>([])
  const [jobs, setJobs] = useState<JobApplication[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showGenerator, setShowGenerator] = useState(false)
  const [editingLetter, setEditingLetter] = useState<CoverLetter | null>(null)
  const [copiedId, setCopiedId] = useState<number | null>(null)

  const loadData = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const [lettersData, resumesData, jobsData] = await Promise.all([
        coverLettersApi.list(token),
        resumesApi.list(token),
        jobsApi.list(token),
      ])
      setCoverLetters(lettersData as CoverLetter[])
      setResumes(resumesData as Resume[])
      setJobs(jobsData as JobApplication[])
    } catch (err) {
      console.error('Failed to load data:', err)
      setError('Failed to load data. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }, [token])

  useEffect(() => {
    loadData()
  }, [loadData])

  const deleteCoverLetter = async (id: number) => {
    if (!confirm('Are you sure you want to delete this cover letter?')) return
    try {
      await coverLettersApi.delete(token, id)
      setCoverLetters(coverLetters.filter((cl) => cl.id !== id))
    } catch (err) {
      console.error('Failed to delete cover letter:', err)
      setError('Failed to delete cover letter.')
    }
  }

  const copyToClipboard = async (text: string, id: number) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedId(id)
      setTimeout(() => setCopiedId(null), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  const getJobForLetter = (jobApplicationId: number | null): JobApplication | undefined => {
    if (!jobApplicationId) return undefined
    return jobs.find((job) => job.id === jobApplicationId)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="w-12 h-12 mx-auto text-red-400" />
        <p className="mt-4 text-red-600">{error}</p>
        <button
          onClick={loadData}
          className="mt-4 px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700"
        >
          Try Again
        </button>
      </div>
    )
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <p className="text-gray-600">{coverLetters.length} cover letter(s) saved</p>
        <button
          onClick={() => setShowGenerator(true)}
          className="inline-flex items-center px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700"
        >
          <Wand2 className="w-4 h-4 mr-2" />
          Generate Cover Letter
        </button>
      </div>

      {coverLetters.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg shadow">
          <Mail className="w-12 h-12 mx-auto text-gray-400" />
          <h3 className="mt-4 text-lg font-medium text-gray-900">No cover letters yet</h3>
          <p className="mt-2 text-gray-500">Generate your first cover letter with AI</p>
          <button
            onClick={() => setShowGenerator(true)}
            className="mt-4 inline-flex items-center px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700"
          >
            <Wand2 className="w-4 h-4 mr-2" />
            Generate Cover Letter
          </button>
        </div>
      ) : (
        <div className="grid gap-4">
          {coverLetters.map((letter) => {
            const linkedJob = getJobForLetter(letter.job_application_id)
            return (
              <div key={letter.id} className="bg-white rounded-lg shadow p-6">
                <div className="flex justify-between items-start mb-4">
                  <div className="flex-1">
                    {linkedJob && (
                      <div className="flex items-center gap-2 mb-2">
                        <Link2 className="w-4 h-4 text-primary-600" />
                        <span className="text-sm font-medium text-primary-600">
                          {linkedJob.position} at {linkedJob.company}
                        </span>
                      </div>
                    )}
                    <p className="text-sm text-gray-500">
                      Created: {formatDate(letter.created_at)}
                      {letter.updated_at !== letter.created_at && (
                        <span className="ml-2">| Updated: {formatDate(letter.updated_at)}</span>
                      )}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => copyToClipboard(letter.content, letter.id)}
                      className="p-2 text-gray-400 hover:text-primary-600 rounded-md hover:bg-gray-100"
                      title="Copy to clipboard"
                      aria-label="Copy to clipboard"
                    >
                      {copiedId === letter.id ? (
                        <Check className="w-5 h-5 text-green-500" />
                      ) : (
                        <Copy className="w-5 h-5" />
                      )}
                    </button>
                    <button
                      onClick={() => setEditingLetter(letter)}
                      className="p-2 text-gray-400 hover:text-primary-600 rounded-md hover:bg-gray-100"
                      title="Edit"
                      aria-label="Edit cover letter"
                    >
                      <Pencil className="w-5 h-5" />
                    </button>
                    <button
                      onClick={() => deleteCoverLetter(letter.id)}
                      className="p-2 text-gray-400 hover:text-red-600 rounded-md hover:bg-gray-100"
                      title="Delete"
                      aria-label="Delete cover letter"
                    >
                      <Trash2 className="w-5 h-5" />
                    </button>
                  </div>
                </div>
                <div className="bg-gray-50 rounded-md p-4">
                  <p className="text-sm text-gray-700 whitespace-pre-line line-clamp-6">
                    {letter.content}
                  </p>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {showGenerator && (
        <CoverLetterGeneratorModal
          onClose={() => setShowGenerator(false)}
          onGenerate={(newLetter) => {
            setCoverLetters([newLetter, ...coverLetters])
            setShowGenerator(false)
          }}
          token={token}
          resumes={resumes}
          jobs={jobs}
        />
      )}

      {editingLetter && (
        <CoverLetterEditModal
          letter={editingLetter}
          jobs={jobs}
          onClose={() => setEditingLetter(null)}
          onSave={(updatedLetter) => {
            setCoverLetters(
              coverLetters.map((cl) => (cl.id === updatedLetter.id ? updatedLetter : cl))
            )
            setEditingLetter(null)
          }}
          token={token}
        />
      )}
    </div>
  )
}

function CoverLetterGeneratorModal({
  onClose,
  onGenerate,
  token,
  resumes,
  jobs,
}: {
  onClose: () => void
  onGenerate: (letter: CoverLetter) => void
  token: string
  resumes: Resume[]
  jobs: JobApplication[]
}) {
  const [formData, setFormData] = useState({
    resume_id: '',
    company_name: '',
    position: '',
    job_description: '',
    job_application_id: '',
    tone: 'professional' as 'professional' | 'enthusiastic' | 'formal',
  })
  const [isGenerating, setIsGenerating] = useState(false)
  const [generatedContent, setGeneratedContent] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleJobSelect = (jobId: string) => {
    if (!jobId) {
      setFormData({ ...formData, job_application_id: '' })
      return
    }
    const job = jobs.find((j) => j.id === Number(jobId))
    if (job) {
      setFormData({
        ...formData,
        job_application_id: jobId,
        company_name: job.company,
        position: job.position,
        job_description: job.job_description || '',
      })
    }
  }

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault()
    const selectedResume = resumes.find((r) => r.id === Number(formData.resume_id))
    if (!selectedResume) {
      setError('Please select a resume')
      return
    }

    setIsGenerating(true)
    setError(null)
    try {
      const result = await coverLettersApi.generate(token, {
        resume_content: selectedResume.content,
        job_description: formData.job_description,
        company_name: formData.company_name,
        position: formData.position,
        tone: formData.tone,
      })
      setGeneratedContent((result as CoverLetter).content)
    } catch (err) {
      console.error('Failed to generate cover letter:', err)
      setError('Failed to generate cover letter. Please try again.')
    } finally {
      setIsGenerating(false)
    }
  }

  const handleSave = async () => {
    if (!generatedContent) return

    try {
      const newLetter = await coverLettersApi.create(token, {
        content: generatedContent,
        job_application_id: formData.job_application_id ? Number(formData.job_application_id) : undefined,
      })
      onGenerate(newLetter as CoverLetter)
    } catch (err) {
      console.error('Failed to save cover letter:', err)
      setError('Failed to save cover letter. Please try again.')
    }
  }

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50"
      onClick={(e) => e.target === e.currentTarget && onClose()}
      role="dialog"
      aria-modal="true"
    >
      <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto p-6">
        <h2 className="text-xl font-bold mb-4">Generate Cover Letter</h2>

        {!generatedContent ? (
          <form onSubmit={handleGenerate} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Link to Job Application (Optional)</label>
              <select
                value={formData.job_application_id}
                onChange={(e) => handleJobSelect(e.target.value)}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="">Select a job application...</option>
                {jobs.map((job) => (
                  <option key={job.id} value={job.id}>
                    {job.position} at {job.company}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Select Resume</label>
              <select
                required
                value={formData.resume_id}
                onChange={(e) => setFormData({ ...formData, resume_id: e.target.value })}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="">Select a resume...</option>
                {resumes.map((resume) => (
                  <option key={resume.id} value={resume.id}>
                    {resume.version_name}
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Company Name</label>
                <input
                  type="text"
                  required
                  value={formData.company_name}
                  onChange={(e) => setFormData({ ...formData, company_name: e.target.value })}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
                  placeholder="Acme Inc."
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Position</label>
                <input
                  type="text"
                  required
                  value={formData.position}
                  onChange={(e) => setFormData({ ...formData, position: e.target.value })}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
                  placeholder="Software Engineer"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Job Description</label>
              <textarea
                required
                rows={6}
                value={formData.job_description}
                onChange={(e) => setFormData({ ...formData, job_description: e.target.value })}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
                placeholder="Paste the job description here..."
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Tone</label>
              <div className="mt-2 flex gap-4">
                {(['professional', 'enthusiastic', 'formal'] as const).map((tone) => (
                  <label key={tone} className="flex items-center">
                    <input
                      type="radio"
                      name="tone"
                      value={tone}
                      checked={formData.tone === tone}
                      onChange={(e) =>
                        setFormData({ ...formData, tone: e.target.value as typeof formData.tone })
                      }
                      className="mr-2"
                    />
                    <span className="text-sm text-gray-700 capitalize">{tone}</span>
                  </label>
                ))}
              </div>
            </div>

            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-md">
                <p className="text-red-600 text-sm">{error}</p>
              </div>
            )}

            <div className="flex justify-end space-x-3 pt-4">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-md"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isGenerating}
                className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50 flex items-center"
              >
                {isGenerating ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Wand2 className="w-4 h-4 mr-2" />
                    Generate
                  </>
                )}
              </button>
            </div>
          </form>
        ) : (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Generated Cover Letter</label>
              <textarea
                value={generatedContent}
                onChange={(e) => setGeneratedContent(e.target.value)}
                rows={16}
                className="w-full px-3 py-2 border border-gray-300 rounded-md font-mono text-sm focus:ring-primary-500 focus:border-primary-500"
              />
            </div>

            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-md">
                <p className="text-red-600 text-sm">{error}</p>
              </div>
            )}

            <div className="flex justify-between pt-4">
              <button
                type="button"
                onClick={() => setGeneratedContent(null)}
                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-md flex items-center"
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                Regenerate
              </button>
              <div className="flex space-x-3">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-md"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleSave}
                  className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 flex items-center"
                >
                  <FileText className="w-4 h-4 mr-2" />
                  Save Cover Letter
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function CoverLetterEditModal({
  letter,
  jobs,
  onClose,
  onSave,
  token,
}: {
  letter: CoverLetter
  jobs: JobApplication[]
  onClose: () => void
  onSave: (letter: CoverLetter) => void
  token: string
}) {
  const [content, setContent] = useState(letter.content)
  const [jobApplicationId, setJobApplicationId] = useState<string>(
    letter.job_application_id?.toString() || ''
  )
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSave = async () => {
    setIsSaving(true)
    setError(null)
    try {
      // The API doesn't have an update endpoint shown, so we delete and recreate
      await coverLettersApi.delete(token, letter.id)
      const newLetter = await coverLettersApi.create(token, {
        content,
        job_application_id: jobApplicationId ? Number(jobApplicationId) : undefined,
      })
      onSave(newLetter as CoverLetter)
    } catch (err) {
      console.error('Failed to save cover letter:', err)
      setError('Failed to save cover letter. Please try again.')
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50"
      onClick={(e) => e.target === e.currentTarget && onClose()}
      role="dialog"
      aria-modal="true"
    >
      <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto p-6">
        <h2 className="text-xl font-bold mb-4">Edit Cover Letter</h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Link to Job Application</label>
            <select
              value={jobApplicationId}
              onChange={(e) => setJobApplicationId(e.target.value)}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
            >
              <option value="">None</option>
              {jobs.map((job) => (
                <option key={job.id} value={job.id}>
                  {job.position} at {job.company}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Content</label>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              rows={16}
              className="w-full px-3 py-2 border border-gray-300 rounded-md font-mono text-sm focus:ring-primary-500 focus:border-primary-500"
            />
          </div>

          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-red-600 text-sm">{error}</p>
            </div>
          )}

          <div className="flex justify-end space-x-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-md"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={isSaving}
              className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50 flex items-center"
            >
              {isSaving ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                  Saving...
                </>
              ) : (
                <>
                  <Check className="w-4 h-4 mr-2" />
                  Save Changes
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// =============================================================================
// Networking Emails Tab
// =============================================================================

function NetworkingEmailsTab({ token }: { token: string }) {
  const [emailType, setEmailType] = useState<NetworkingEmailType>('informational')
  const [formData, setFormData] = useState({
    recipientName: '',
    company: '',
    purpose: '',
    yourBackground: '',
  })
  const [generatedEmail, setGeneratedEmail] = useState<{ subject: string; body: string } | null>(null)
  const [isGenerating, setIsGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState<'subject' | 'body' | 'all' | null>(null)

  const generateEmailPrompt = (): string => {
    const typeConfig = NETWORKING_EMAIL_TYPES.find((t) => t.id === emailType)
    return `Write a professional ${typeConfig?.label || 'networking'} email with the following details:

Recipient: ${formData.recipientName}
Company: ${formData.company}
Purpose: ${formData.purpose}
My Background: ${formData.yourBackground}

Please provide:
1. A subject line (short and compelling)
2. The email body (professional, concise, and personable)

Format the response as:
SUBJECT: [subject line]
BODY:
[email body]`
  }

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsGenerating(true)
    setError(null)
    setGeneratedEmail(null)

    try {
      const result = await aiApi.answerQuestion(token, {
        question: generateEmailPrompt(),
        question_type: 'general',
      })

      // Parse the response
      const response = result.answer
      const subjectMatch = response.match(/SUBJECT:\s*([^\n]+?)(?:\n|BODY:)/i)
      const bodyMatch = response.match(/BODY:\s*([\s\S]+)/i)

      if (subjectMatch && bodyMatch) {
        setGeneratedEmail({
          subject: subjectMatch[1].trim(),
          body: bodyMatch[1].trim(),
        })
      } else {
        // Fallback parsing
        const lines = response.split('\n').filter((l) => l.trim())
        setGeneratedEmail({
          subject: lines[0]?.replace(/^subject:?\s*/i, '') || 'Networking Email',
          body: lines.slice(1).join('\n'),
        })
      }
    } catch (err) {
      console.error('Failed to generate email:', err)
      setError('Failed to generate email. Please try again.')
    } finally {
      setIsGenerating(false)
    }
  }

  const copyToClipboard = async (text: string, type: 'subject' | 'body' | 'all') => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(type)
      setTimeout(() => setCopied(null), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Input Section */}
      <div className="space-y-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Email Type</h3>
          <div className="grid grid-cols-2 gap-3">
            {NETWORKING_EMAIL_TYPES.map((type) => (
              <button
                key={type.id}
                onClick={() => setEmailType(type.id)}
                className={cn(
                  'p-4 rounded-lg border-2 text-left transition-all',
                  emailType === type.id
                    ? 'border-primary-600 bg-primary-50'
                    : 'border-gray-200 hover:border-gray-300'
                )}
              >
                <span className="font-medium text-gray-900 block">{type.label}</span>
                <span className="text-xs text-gray-500">{type.description}</span>
              </button>
            ))}
          </div>
        </div>

        <form onSubmit={handleGenerate} className="bg-white rounded-lg shadow p-6 space-y-4">
          <h3 className="text-lg font-medium text-gray-900">Email Details</h3>

          <div>
            <label className="block text-sm font-medium text-gray-700">Recipient Name</label>
            <input
              type="text"
              required
              value={formData.recipientName}
              onChange={(e) => setFormData({ ...formData, recipientName: e.target.value })}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
              placeholder="Jane Smith"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Company</label>
            <input
              type="text"
              required
              value={formData.company}
              onChange={(e) => setFormData({ ...formData, company: e.target.value })}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
              placeholder="Acme Inc."
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Purpose</label>
            <textarea
              required
              rows={3}
              value={formData.purpose}
              onChange={(e) => setFormData({ ...formData, purpose: e.target.value })}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
              placeholder="What is the goal of this email? What are you hoping to achieve?"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Your Background</label>
            <textarea
              required
              rows={3}
              value={formData.yourBackground}
              onChange={(e) => setFormData({ ...formData, yourBackground: e.target.value })}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
              placeholder="Brief description of your experience and what you're looking for"
            />
          </div>

          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-red-600 text-sm">{error}</p>
            </div>
          )}

          <button
            type="submit"
            disabled={isGenerating}
            className="w-full inline-flex items-center justify-center px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50"
          >
            {isGenerating ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                Generating...
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4 mr-2" />
                Generate Email
              </>
            )}
          </button>
        </form>
      </div>

      {/* Preview Section */}
      <div className="space-y-6">
        {generatedEmail ? (
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-medium text-gray-900">Generated Email</h3>
              <button
                onClick={() =>
                  copyToClipboard(`Subject: ${generatedEmail.subject}\n\n${generatedEmail.body}`, 'all')
                }
                className="inline-flex items-center px-3 py-1.5 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
              >
                {copied === 'all' ? (
                  <>
                    <Check className="w-4 h-4 mr-1 text-green-500" />
                    Copied!
                  </>
                ) : (
                  <>
                    <Copy className="w-4 h-4 mr-1" />
                    Copy All
                  </>
                )}
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="block text-sm font-medium text-gray-700">Subject</label>
                  <button
                    onClick={() => copyToClipboard(generatedEmail.subject, 'subject')}
                    className="text-xs text-primary-600 hover:text-primary-700"
                  >
                    {copied === 'subject' ? 'Copied!' : 'Copy'}
                  </button>
                </div>
                <div className="bg-gray-50 rounded-md p-3">
                  <p className="text-sm text-gray-900">{generatedEmail.subject}</p>
                </div>
              </div>

              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="block text-sm font-medium text-gray-700">Body</label>
                  <button
                    onClick={() => copyToClipboard(generatedEmail.body, 'body')}
                    className="text-xs text-primary-600 hover:text-primary-700"
                  >
                    {copied === 'body' ? 'Copied!' : 'Copy'}
                  </button>
                </div>
                <div className="bg-gray-50 rounded-md p-4">
                  <p className="text-sm text-gray-900 whitespace-pre-line">{generatedEmail.body}</p>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow p-12 text-center">
            <MessageSquare className="w-16 h-16 mx-auto text-gray-300" />
            <h3 className="mt-4 text-lg font-medium text-gray-500">No Email Generated</h3>
            <p className="mt-2 text-sm text-gray-400">
              Fill out the form and click "Generate Email" to create a networking email.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

// =============================================================================
// Professional Emails Tab
// =============================================================================

function ProfessionalEmailsTab({ token }: { token: string }) {
  const [selectedTemplate, setSelectedTemplate] = useState<ProfessionalTemplateId>('post-interview')
  const [placeholderValues, setPlaceholderValues] = useState<Record<string, string>>({})
  const [isCustomizing, setIsCustomizing] = useState(false)
  const [customizedContent, setCustomizedContent] = useState<{ subject: string; body: string } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState<'subject' | 'body' | 'all' | null>(null)

  const template = PROFESSIONAL_TEMPLATES.find((t) => t.id === selectedTemplate)!

  const getProcessedContent = (templateStr: string): string => {
    let processed = templateStr
    template.placeholders.forEach((placeholder) => {
      const value = placeholderValues[placeholder] || `{{${placeholder}}}`
      processed = processed.replace(new RegExp(`\\{\\{${placeholder}\\}\\}`, 'g'), value)
    })
    return processed
  }

  const processedSubject = getProcessedContent(template.subjectTemplate)
  const processedBody = getProcessedContent(template.bodyTemplate)

  const handleCustomize = async () => {
    setIsCustomizing(true)
    setError(null)

    try {
      const prompt = `Please improve and personalize this email while maintaining its professional tone and core message. Make it sound more natural and engaging:

Subject: ${processedSubject}

${processedBody}

Provide the improved version in the same format:
SUBJECT: [improved subject]
BODY:
[improved body]`

      const result = await aiApi.answerQuestion(token, {
        question: prompt,
        question_type: 'general',
      })

      const response = result.answer
      const subjectMatch = response.match(/SUBJECT:\s*([^\n]+?)(?:\n|BODY:)/i)
      const bodyMatch = response.match(/BODY:\s*([\s\S]+)/i)

      if (subjectMatch && bodyMatch) {
        setCustomizedContent({
          subject: subjectMatch[1].trim(),
          body: bodyMatch[1].trim(),
        })
      }
    } catch (err) {
      console.error('Failed to customize email:', err)
      setError('Failed to customize email. Please try again.')
    } finally {
      setIsCustomizing(false)
    }
  }

  const copyToClipboard = async (text: string, type: 'subject' | 'body' | 'all') => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(type)
      setTimeout(() => setCopied(null), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  const displaySubject = customizedContent?.subject || processedSubject
  const displayBody = customizedContent?.body || processedBody

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Template Selection */}
      <div className="lg:col-span-1 space-y-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Select Template</h3>
          <div className="space-y-3">
            {PROFESSIONAL_TEMPLATES.map((t) => (
              <button
                key={t.id}
                onClick={() => {
                  setSelectedTemplate(t.id)
                  setPlaceholderValues({})
                  setCustomizedContent(null)
                }}
                className={cn(
                  'w-full text-left p-4 rounded-lg border-2 transition-all',
                  selectedTemplate === t.id
                    ? 'border-primary-600 bg-primary-50'
                    : 'border-gray-200 hover:border-gray-300'
                )}
              >
                <span className="font-medium text-gray-900 block">{t.name}</span>
                <span className="text-xs text-gray-500">{t.description}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Placeholder Form */}
      <div className="lg:col-span-1 space-y-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Fill in Details</h3>
          <div className="space-y-4">
            {template.placeholders.map((placeholder) => (
              <div key={placeholder}>
                <label className="block text-sm font-medium text-gray-700">
                  {placeholder.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                </label>
                <input
                  type="text"
                  value={placeholderValues[placeholder] || ''}
                  onChange={(e) =>
                    setPlaceholderValues({ ...placeholderValues, [placeholder]: e.target.value })
                  }
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-primary-500 focus:border-primary-500"
                  placeholder={`Enter ${placeholder.toLowerCase().replace(/_/g, ' ')}`}
                />
              </div>
            ))}
          </div>

          <button
            onClick={handleCustomize}
            disabled={isCustomizing}
            className="mt-6 w-full inline-flex items-center justify-center px-4 py-2 bg-emerald-600 text-white rounded-md hover:bg-emerald-700 disabled:opacity-50"
          >
            {isCustomizing ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                Customizing...
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4 mr-2" />
                AI Customize
              </>
            )}
          </button>

          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-red-600 text-sm">{error}</p>
            </div>
          )}
        </div>
      </div>

      {/* Preview */}
      <div className="lg:col-span-1 space-y-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-medium text-gray-900">Preview</h3>
            <button
              onClick={() => copyToClipboard(`Subject: ${displaySubject}\n\n${displayBody}`, 'all')}
              className="inline-flex items-center px-3 py-1.5 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
            >
              {copied === 'all' ? (
                <>
                  <Check className="w-4 h-4 mr-1 text-green-500" />
                  Copied!
                </>
              ) : (
                <>
                  <Copy className="w-4 h-4 mr-1" />
                  Copy All
                </>
              )}
            </button>
          </div>

          <div className="space-y-4">
            <div>
              <div className="flex justify-between items-center mb-1">
                <label className="block text-sm font-medium text-gray-700">Subject</label>
                <button
                  onClick={() => copyToClipboard(displaySubject, 'subject')}
                  className="text-xs text-primary-600 hover:text-primary-700"
                >
                  {copied === 'subject' ? 'Copied!' : 'Copy'}
                </button>
              </div>
              <div className="bg-gray-50 rounded-md p-3">
                <p className="text-sm text-gray-900">{displaySubject}</p>
              </div>
            </div>

            <div>
              <div className="flex justify-between items-center mb-1">
                <label className="block text-sm font-medium text-gray-700">Body</label>
                <button
                  onClick={() => copyToClipboard(displayBody, 'body')}
                  className="text-xs text-primary-600 hover:text-primary-700"
                >
                  {copied === 'body' ? 'Copied!' : 'Copy'}
                </button>
              </div>
              <div className="bg-gray-50 rounded-md p-4 max-h-96 overflow-y-auto">
                <p className="text-sm text-gray-900 whitespace-pre-line">{displayBody}</p>
              </div>
            </div>
          </div>

          {customizedContent && (
            <button
              onClick={() => setCustomizedContent(null)}
              className="mt-4 w-full text-sm text-gray-500 hover:text-gray-700"
            >
              Reset to original template
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

// =============================================================================
// Custom Composer Tab
// =============================================================================

function CustomComposerTab({ token }: { token: string }) {
  const [content, setContent] = useState('')
  const [selectedTone, setSelectedTone] = useState<ToneOption | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [processedContent, setProcessedContent] = useState<string | null>(null)
  const [corrections, setCorrections] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [savedTemplates, setSavedTemplates] = useState<Array<{ name: string; content: string }>>([])
  const [templateName, setTemplateName] = useState('')
  const [showSaveDialog, setShowSaveDialog] = useState(false)

  const handleGrammarCheck = async () => {
    if (!content.trim()) {
      setError('Please enter some text first')
      return
    }

    setIsProcessing(true)
    setError(null)
    setProcessedContent(null)
    setCorrections([])

    try {
      const result = await aiApi.grammarCheck(token, { text: content })
      setProcessedContent(result.corrected_text)
      setCorrections(result.corrections_made || [])
    } catch (err) {
      console.error('Failed to check grammar:', err)
      setError('Failed to check grammar. Please try again.')
    } finally {
      setIsProcessing(false)
    }
  }

  const handleToneAdjust = async (tone: ToneOption) => {
    if (!content.trim()) {
      setError('Please enter some text first')
      return
    }

    setIsProcessing(true)
    setError(null)
    setProcessedContent(null)
    setSelectedTone(tone)

    const toneDescriptions: Record<ToneOption, string> = {
      formal: 'professional, businesslike, and formal',
      friendly: 'warm, approachable, and friendly while remaining professional',
      assertive: 'confident, direct, and assertive',
    }

    try {
      const result = await aiApi.answerQuestion(token, {
        question: `Rewrite the following text to have a ${toneDescriptions[tone]} tone. Maintain the core message but adjust the language and style accordingly:\n\n${content}`,
        question_type: 'general',
      })
      setProcessedContent(result.answer)
    } catch (err) {
      console.error('Failed to adjust tone:', err)
      setError('Failed to adjust tone. Please try again.')
    } finally {
      setIsProcessing(false)
    }
  }

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  const saveTemplate = () => {
    if (!templateName.trim() || !content.trim()) return
    setSavedTemplates([...savedTemplates, { name: templateName, content }])
    setTemplateName('')
    setShowSaveDialog(false)
  }

  const loadTemplate = (template: { name: string; content: string }) => {
    setContent(template.content)
    setProcessedContent(null)
    setCorrections([])
  }

  const deleteTemplate = (index: number) => {
    setSavedTemplates(savedTemplates.filter((_, i) => i !== index))
  }

  const applyProcessed = () => {
    if (processedContent) {
      setContent(processedContent)
      setProcessedContent(null)
      setCorrections([])
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Editor Section */}
      <div className="space-y-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-medium text-gray-900">Compose</h3>
            <div className="flex items-center gap-2">
              <button
                onClick={() => copyToClipboard(content)}
                disabled={!content.trim()}
                className="inline-flex items-center px-3 py-1.5 text-sm border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
              >
                {copied ? (
                  <>
                    <Check className="w-4 h-4 mr-1 text-green-500" />
                    Copied!
                  </>
                ) : (
                  <>
                    <Copy className="w-4 h-4 mr-1" />
                    Copy
                  </>
                )}
              </button>
              <button
                onClick={() => setShowSaveDialog(true)}
                disabled={!content.trim()}
                className="inline-flex items-center px-3 py-1.5 text-sm border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
              >
                <Plus className="w-4 h-4 mr-1" />
                Save Template
              </button>
            </div>
          </div>

          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={16}
            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-primary-500 focus:border-primary-500"
            placeholder="Write your email or document here..."
          />

          <div className="mt-4 flex flex-wrap gap-3">
            <button
              onClick={handleGrammarCheck}
              disabled={isProcessing || !content.trim()}
              className="inline-flex items-center px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50"
            >
              {isProcessing && !selectedTone ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                  Checking...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4 mr-2" />
                  Grammar Check
                </>
              )}
            </button>

            <div className="border-l border-gray-300 mx-2" />

            <span className="self-center text-sm text-gray-500">Adjust Tone:</span>
            {TONE_OPTIONS.map((tone) => (
              <button
                key={tone.id}
                onClick={() => handleToneAdjust(tone.id)}
                disabled={isProcessing || !content.trim()}
                className={cn(
                  'px-3 py-2 text-sm rounded-md transition-colors disabled:opacity-50',
                  selectedTone === tone.id && isProcessing
                    ? 'bg-gray-200 text-gray-700'
                    : 'border border-gray-300 text-gray-700 hover:bg-gray-50'
                )}
                title={tone.description}
              >
                {selectedTone === tone.id && isProcessing ? (
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-700" />
                ) : (
                  tone.label
                )}
              </button>
            ))}
          </div>

          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-red-600 text-sm">{error}</p>
            </div>
          )}
        </div>

        {/* Saved Templates */}
        {savedTemplates.length > 0 && (
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Saved Templates</h3>
            <div className="space-y-2">
              {savedTemplates.map((template, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-md"
                >
                  <button
                    onClick={() => loadTemplate(template)}
                    className="text-sm font-medium text-gray-900 hover:text-primary-600"
                  >
                    {template.name}
                  </button>
                  <button
                    onClick={() => deleteTemplate(index)}
                    className="text-gray-400 hover:text-red-600"
                    aria-label="Delete template"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Results Section */}
      <div className="space-y-6">
        {processedContent ? (
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-medium text-gray-900">
                {corrections.length > 0 ? 'Grammar Corrections' : 'Adjusted Text'}
              </h3>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => copyToClipboard(processedContent)}
                  className="inline-flex items-center px-3 py-1.5 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
                >
                  <Copy className="w-4 h-4 mr-1" />
                  Copy
                </button>
                <button
                  onClick={applyProcessed}
                  className="inline-flex items-center px-3 py-1.5 text-sm bg-primary-600 text-white rounded-md hover:bg-primary-700"
                >
                  <Check className="w-4 h-4 mr-1" />
                  Apply
                </button>
              </div>
            </div>

            {corrections.length > 0 && (
              <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-md">
                <h4 className="text-sm font-medium text-amber-800 mb-2">
                  Corrections Made ({corrections.length})
                </h4>
                <ul className="text-sm text-amber-700 space-y-1">
                  {corrections.map((correction, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="text-amber-500">-</span>
                      {correction}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="bg-gray-50 rounded-md p-4 max-h-96 overflow-y-auto">
              <p className="text-sm text-gray-900 whitespace-pre-line">{processedContent}</p>
            </div>
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow p-12 text-center">
            <FileEdit className="w-16 h-16 mx-auto text-gray-300" />
            <h3 className="mt-4 text-lg font-medium text-gray-500">Write Your Content</h3>
            <p className="mt-2 text-sm text-gray-400">
              Type your email or document in the editor, then use the grammar check or tone
              adjustment buttons to improve it.
            </p>
          </div>
        )}
      </div>

      {/* Save Template Dialog */}
      {showSaveDialog && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50"
          onClick={(e) => e.target === e.currentTarget && setShowSaveDialog(false)}
          role="dialog"
          aria-modal="true"
        >
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
            <h2 className="text-xl font-bold mb-4">Save as Template</h2>

            <div>
              <label className="block text-sm font-medium text-gray-700">Template Name</label>
              <input
                type="text"
                value={templateName}
                onChange={(e) => setTemplateName(e.target.value)}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
                placeholder="My Email Template"
                autoFocus
              />
            </div>

            <div className="flex justify-end space-x-3 mt-6">
              <button
                type="button"
                onClick={() => setShowSaveDialog(false)}
                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-md"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={saveTemplate}
                disabled={!templateName.trim()}
                className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50"
              >
                Save Template
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
