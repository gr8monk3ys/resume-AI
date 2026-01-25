'use client'

import { useVirtualizer } from '@tanstack/react-virtual'
import {
  Plus,
  FileText,
  Trash2,
  BarChart3,
  Search,
  Upload,
  Sparkles,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Pencil,
  Copy,
  Download,
  Target,
  FileSearch,
  Palette,
} from 'lucide-react'
import { useRouter } from 'next/navigation'
import { useEffect, useState, useCallback, useRef, Suspense, memo } from 'react'

import { resumesApi, aiApi } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { cn, formatDate } from '@/lib/utils'

import type { Resume, ATSAnalysis } from '@/types'

// Row height constant for virtualization
const RESUME_ROW_HEIGHT = 64

// Loading skeleton for tab transitions
function TabLoadingSkeleton() {
  return (
    <div className="animate-pulse space-y-4">
      <div className="h-8 bg-gray-200 rounded w-1/4" />
      <div className="h-32 bg-gray-200 rounded" />
      <div className="h-32 bg-gray-200 rounded" />
      <div className="h-32 bg-gray-200 rounded" />
    </div>
  )
}

// Tab types
type TabId = 'list' | 'analysis' | 'keywords' | 'templates'

interface Tab {
  id: TabId
  label: string
  icon: React.ReactNode
}

const TABS: Tab[] = [
  { id: 'list', label: 'My Resumes', icon: <FileText className="w-4 h-4" /> },
  { id: 'analysis', label: 'ATS Analysis', icon: <Target className="w-4 h-4" /> },
  { id: 'keywords', label: 'Keyword Gap', icon: <FileSearch className="w-4 h-4" /> },
  { id: 'templates', label: 'Templates', icon: <Palette className="w-4 h-4" /> },
]

// Template types
type TemplateId = 'professional' | 'modern' | 'technical' | 'executive' | 'creative'

interface Template {
  id: TemplateId
  name: string
  description: string
  color: string
  features: string[]
}

const TEMPLATES: Template[] = [
  {
    id: 'professional',
    name: 'Professional',
    description: 'Clean and classic design suitable for traditional industries',
    color: 'bg-slate-600',
    features: ['Clean layout', 'Traditional formatting', 'ATS-optimized'],
  },
  {
    id: 'modern',
    name: 'Modern',
    description: 'Contemporary design with subtle visual elements',
    color: 'bg-blue-600',
    features: ['Two-column layout', 'Visual hierarchy', 'Skill bars'],
  },
  {
    id: 'technical',
    name: 'Technical',
    description: 'Optimized for software engineers and technical roles',
    color: 'bg-emerald-600',
    features: ['Technical skills section', 'Project highlights', 'GitHub links'],
  },
  {
    id: 'executive',
    name: 'Executive',
    description: 'Premium design for senior leadership positions',
    color: 'bg-purple-600',
    features: ['Executive summary', 'Leadership focus', 'Achievement metrics'],
  },
  {
    id: 'creative',
    name: 'Creative',
    description: 'Bold design for creative and design professionals',
    color: 'bg-pink-600',
    features: ['Portfolio section', 'Visual elements', 'Custom branding'],
  },
]

// Score breakdown categories
interface ScoreCategory {
  key: string
  label: string
  description: string
  weight: number
}

const SCORE_CATEGORIES: ScoreCategory[] = [
  { key: 'formatting', label: 'Formatting', description: 'Structure and readability', weight: 15 },
  { key: 'keywords', label: 'Keywords', description: 'Industry-relevant terms', weight: 25 },
  { key: 'action_verbs', label: 'Action Verbs', description: 'Strong, active language', weight: 15 },
  { key: 'quantifiable_results', label: 'Quantifiable Results', description: 'Measurable achievements', weight: 20 },
  { key: 'length', label: 'Length', description: 'Appropriate content volume', weight: 10 },
  { key: 'job_match', label: 'Job Match', description: 'Alignment with job description', weight: 15 },
]

export function ResumesPageClient() {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth()
  const router = useRouter()
  const [activeTab, setActiveTab] = useState<TabId>('list')

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

  if (!user || !isAuthenticated) {
    return null
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Resume Hub</h1>
        <p className="text-gray-500">Manage, analyze, and optimize your resumes</p>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8" aria-label="Tabs">
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

      {/* Tab Content - Wrapped in Suspense for better code splitting */}
      <Suspense fallback={<TabLoadingSkeleton />}>
        {activeTab === 'list' && <ResumeListTab />}
        {activeTab === 'analysis' && <ATSAnalysisTab />}
        {activeTab === 'keywords' && <KeywordGapTab />}
        {activeTab === 'templates' && <TemplatesTab />}
      </Suspense>
    </div>
  )
}

// =============================================================================
// Resume List Tab
// =============================================================================

// Memoized row component for resume table
interface ResumeRowProps {
  resume: Resume
  onEdit: (resume: Resume) => void
  onDelete: (id: number) => void | Promise<void>
}

const ResumeRow = memo(function ResumeRow({
  resume,
  onEdit,
  onDelete,
}: ResumeRowProps) {
  const handleEdit = useCallback(() => {
    onEdit(resume)
  }, [onEdit, resume])

  const handleDelete = useCallback(() => {
    if (!confirm('Are you sure you want to delete this resume?')) return
    void onDelete(resume.id)
  }, [onDelete, resume.id])

  return (
    <tr className="hover:bg-gray-50">
      <td className="px-6 py-4 whitespace-nowrap">
        <div className="flex items-center">
          <FileText className="w-5 h-5 text-gray-400 mr-3" />
          <span className="font-medium text-gray-900">{resume.version_name}</span>
        </div>
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        {resume.ats_score !== null ? (
          <div className="flex items-center">
            <ScoreBadge score={resume.ats_score} />
          </div>
        ) : (
          <span className="text-gray-400 text-sm">Not analyzed</span>
        )}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
        {formatDate(resume.created_at)}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
        {formatDate(resume.updated_at)}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
        <div className="flex justify-end gap-2">
          <button
            onClick={handleEdit}
            className="p-2 text-gray-400 hover:text-primary-600 rounded-md hover:bg-gray-100"
            title="Edit resume"
            aria-label="Edit resume"
          >
            <Pencil className="w-4 h-4" />
          </button>
          <button
            onClick={handleDelete}
            className="p-2 text-gray-400 hover:text-red-600 rounded-md hover:bg-gray-100"
            title="Delete resume"
            aria-label="Delete resume"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </td>
    </tr>
  )
})

function ResumeListTab() {
  const [resumes, setResumes] = useState<Resume[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [showAddForm, setShowAddForm] = useState(false)
  const [editingResume, setEditingResume] = useState<Resume | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Ref for the scrollable container
  const tableContainerRef = useRef<HTMLDivElement>(null)

  const loadResumes = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await resumesApi.list()
      setResumes(data)
    } catch (err) {
      console.error('Failed to load resumes:', err)
      setError('Failed to load resumes. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadResumes()
  }, [loadResumes])

  // Set up virtualizer for table rows
  const rowVirtualizer = useVirtualizer({
    count: resumes.length,
    getScrollElement: () => tableContainerRef.current,
    estimateSize: () => RESUME_ROW_HEIGHT,
    overscan: 10,
    getItemKey: (index) => resumes[index]?.id ?? index,
  })

  const virtualRows = rowVirtualizer.getVirtualItems()
  const totalSize = rowVirtualizer.getTotalSize()

  // Calculate padding for proper table structure
  const paddingTop = virtualRows.length > 0 ? virtualRows[0]?.start ?? 0 : 0
  const paddingBottom = virtualRows.length > 0
    ? totalSize - (virtualRows[virtualRows.length - 1]?.end ?? totalSize)
    : 0

  const deleteResume = useCallback(async (id: number) => {
    try {
      await resumesApi.delete(id)
      setResumes((prev) => prev.filter((r) => r.id !== id))
    } catch (err) {
      console.error('Failed to delete resume:', err)
      setError('Failed to delete resume. Please try again.')
    }
  }, [])

  const handleEdit = useCallback((resume: Resume) => {
    setEditingResume(resume)
  }, [])

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
          onClick={() => void loadResumes()}
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
        <p className="text-gray-600">{resumes.length} resume(s) saved</p>
        <button
          onClick={() => setShowAddForm(true)}
          className="inline-flex items-center px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700"
        >
          <Plus className="w-4 h-4 mr-2" />
          Create New Resume
        </button>
      </div>

      {resumes.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg shadow">
          <FileText className="w-12 h-12 mx-auto text-gray-400" />
          <h3 className="mt-4 text-lg font-medium text-gray-900">No resumes yet</h3>
          <p className="mt-2 text-gray-500">Create your first resume to get started</p>
          <button
            onClick={() => setShowAddForm(true)}
            className="mt-4 inline-flex items-center px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700"
          >
            <Plus className="w-4 h-4 mr-2" />
            Create Resume
          </button>
        </div>
      ) : (
        <div
          ref={tableContainerRef}
          className="bg-white rounded-lg shadow overflow-auto"
          style={{ maxHeight: 'calc(100vh - 320px)', minHeight: '300px' }}
        >
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50 sticky top-0 z-10">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Version Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  ATS Score
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Created
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Last Updated
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {/* Top padding row for virtualization */}
              {paddingTop > 0 && (
                <tr>
                  <td colSpan={5} style={{ height: paddingTop, padding: 0, border: 0 }} />
                </tr>
              )}
              {virtualRows.map((virtualRow) => {
                const resume = resumes[virtualRow.index]
                if (!resume) return null
                return (
                  <ResumeRow
                    key={resume.id}
                    resume={resume}
                    onEdit={handleEdit}
                    onDelete={deleteResume}
                  />
                )
              })}
              {/* Bottom padding row for virtualization */}
              {paddingBottom > 0 && (
                <tr>
                  <td colSpan={5} style={{ height: paddingBottom, padding: 0, border: 0 }} />
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {showAddForm && (
        <ResumeFormModal
          onClose={() => setShowAddForm(false)}
          onSave={(newResume) => {
            setResumes([newResume, ...resumes])
            setShowAddForm(false)
          }}
        />
      )}

      {editingResume && (
        <ResumeFormModal
          resume={editingResume}
          onClose={() => setEditingResume(null)}
          onSave={(updatedResume) => {
            setResumes(resumes.map((r) => (r.id === updatedResume.id ? updatedResume : r)))
            setEditingResume(null)
          }}
        />
      )}
    </div>
  )
}

// =============================================================================
// ATS Analysis Tab
// =============================================================================

function ATSAnalysisTab() {
  const [resumeText, setResumeText] = useState('')
  const [jobDescription, setJobDescription] = useState('')
  const [analysis, setAnalysis] = useState<ATSAnalysis | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [isOptimizing, setIsOptimizing] = useState(false)
  const [optimizedResume, setOptimizedResume] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    try {
      const result = await resumesApi.upload(file)
      setResumeText(result.content)
    } catch (err) {
      console.error('Failed to upload file:', err)
      setError('Failed to parse file. Please try pasting your resume text instead.')
    }
  }

  const analyzeResume = async () => {
    if (!resumeText.trim()) {
      setError('Please provide resume content')
      return
    }

    setIsAnalyzing(true)
    setError(null)
    setAnalysis(null)

    try {
      const result = await resumesApi.analyzeContent(
        resumeText,
        jobDescription || undefined
      )
      setAnalysis(result)
    } catch (err) {
      console.error('Failed to analyze resume:', err)
      setError('Failed to analyze resume. Please try again.')
    } finally {
      setIsAnalyzing(false)
    }
  }

  const optimizeResume = async () => {
    if (!resumeText.trim() || !jobDescription.trim()) {
      setError('Please provide both resume content and job description for AI optimization')
      return
    }

    setIsOptimizing(true)
    setError(null)

    try {
      const result = await aiApi.tailorResume(resumeText, jobDescription)
      setOptimizedResume(result.tailored_resume)
    } catch (err) {
      console.error('Failed to optimize resume:', err)
      setError('Failed to optimize resume. Please try again.')
    } finally {
      setIsOptimizing(false)
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Input Section */}
      <div className="space-y-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Resume Content</h3>
          <div className="space-y-4">
            <div className="flex gap-2">
              <button
                onClick={() => fileInputRef.current?.click()}
                className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md text-sm text-gray-700 hover:bg-gray-50"
              >
                <Upload className="w-4 h-4 mr-2" />
                Upload File
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".txt,.pdf,.docx"
                onChange={(e) => void handleFileUpload(e)}
                className="hidden"
              />
              <span className="text-xs text-gray-500 self-center">Supports .txt, .pdf, .docx</span>
            </div>
            <textarea
              value={resumeText}
              onChange={(e) => setResumeText(e.target.value)}
              placeholder="Paste your resume content here..."
              rows={12}
              className="w-full px-3 py-2 border border-gray-300 rounded-md font-mono text-sm focus:ring-primary-500 focus:border-primary-500"
            />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Job Description (Optional)</h3>
          <textarea
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
            placeholder="Paste the job description for job-specific analysis..."
            rows={8}
            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-primary-500 focus:border-primary-500"
          />
        </div>

        <div className="flex gap-3">
          <button
            onClick={() => void analyzeResume()}
            disabled={isAnalyzing || !resumeText.trim()}
            className="flex-1 inline-flex items-center justify-center px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isAnalyzing ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                Analyzing...
              </>
            ) : (
              <>
                <BarChart3 className="w-4 h-4 mr-2" />
                Analyze Resume
              </>
            )}
          </button>
          <button
            onClick={() => void optimizeResume()}
            disabled={isOptimizing || !resumeText.trim() || !jobDescription.trim()}
            className="flex-1 inline-flex items-center justify-center px-4 py-2 bg-emerald-600 text-white rounded-md hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isOptimizing ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                Optimizing...
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4 mr-2" />
                AI Optimize
              </>
            )}
          </button>
        </div>

        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-md">
            <p className="text-red-600 text-sm">{error}</p>
          </div>
        )}
      </div>

      {/* Results Section */}
      <div className="space-y-6">
        {analysis ? (
          <>
            {/* Score Gauge */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">ATS Score</h3>
              <div className="flex items-center justify-center">
                <ScoreGauge score={analysis.ats_score} />
              </div>
            </div>

            {/* Score Breakdown */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Score Breakdown</h3>
              <div className="space-y-4">
                {SCORE_CATEGORIES.map((category) => {
                  const score = analysis.score_breakdown?.[category.key] ?? 0
                  return (
                    <div key={category.key}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="font-medium text-gray-700">{category.label}</span>
                        <span className="text-gray-500">{score}%</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className={cn(
                            'h-2 rounded-full transition-all duration-300',
                            score >= 80 ? 'bg-green-500' : score >= 60 ? 'bg-yellow-500' : 'bg-red-500'
                          )}
                          style={{ width: `${score}%` }}
                        />
                      </div>
                      <p className="text-xs text-gray-400 mt-1">{category.description}</p>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Suggestions */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Improvement Suggestions</h3>
              {analysis.suggestions.length > 0 ? (
                <ul className="space-y-3">
                  {analysis.suggestions.map((suggestion, idx) => (
                    <li key={idx} className="flex items-start gap-3">
                      <AlertCircle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
                      <span className="text-sm text-gray-700">{suggestion}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-gray-500 text-sm">Your resume looks great! No major improvements needed.</p>
              )}
            </div>
          </>
        ) : (
          <div className="bg-white rounded-lg shadow p-12 text-center">
            <BarChart3 className="w-16 h-16 mx-auto text-gray-300" />
            <h3 className="mt-4 text-lg font-medium text-gray-500">No Analysis Yet</h3>
            <p className="mt-2 text-sm text-gray-400">
              Upload or paste your resume, then click "Analyze Resume" to see your ATS score and suggestions.
            </p>
          </div>
        )}

        {/* Optimized Resume */}
        {optimizedResume && (
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-medium text-gray-900">AI Optimized Resume</h3>
              <button
                onClick={() => {
                  void navigator.clipboard.writeText(optimizedResume)
                }}
                className="inline-flex items-center px-3 py-1.5 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
              >
                <Copy className="w-4 h-4 mr-1" />
                Copy
              </button>
            </div>
            <div className="bg-gray-50 rounded-md p-4 max-h-96 overflow-y-auto">
              <pre className="text-sm text-gray-700 whitespace-pre-wrap font-mono">{optimizedResume}</pre>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// =============================================================================
// Keyword Gap Tab
// =============================================================================

interface KeywordAnalysis {
  matchPercentage: number
  foundKeywords: string[]
  missingKeywords: string[]
  placements: Record<string, string>
}

function KeywordGapTab() {
  const [resumeText, setResumeText] = useState('')
  const [jobDescription, setJobDescription] = useState('')
  const [analysis, setAnalysis] = useState<KeywordAnalysis | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [aiSuggestions, setAiSuggestions] = useState<string[]>([])
  const [isGettingSuggestions, setIsGettingSuggestions] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    try {
      const result = await resumesApi.upload(file)
      setResumeText(result.content)
    } catch (err) {
      console.error('Failed to upload file:', err)
      setError('Failed to parse file. Please try pasting your resume text instead.')
    }
  }

  const analyzeKeywords = async () => {
    if (!resumeText.trim() || !jobDescription.trim()) {
      setError('Please provide both resume content and job description')
      return
    }

    setIsAnalyzing(true)
    setError(null)

    try {
      // Use the ATS analysis endpoint to get keyword data
      const result = await resumesApi.analyzeContent(resumeText, jobDescription)

      // Extract keywords from job description for gap analysis
      const jobKeywords = extractKeywordsFromText(jobDescription)
      const resumeKeywordsLower = (result.keyword_matches || []).map((k) => k.toLowerCase())

      const foundKeywords = jobKeywords.filter((k) =>
        resumeKeywordsLower.some((rk) => rk.includes(k.toLowerCase()) || k.toLowerCase().includes(rk))
      )
      const missingKeywords = result.missing_keywords || jobKeywords.filter(
        (k) => !resumeKeywordsLower.some((rk) => rk.includes(k.toLowerCase()) || k.toLowerCase().includes(rk))
      )

      const matchPercentage =
        jobKeywords.length > 0 ? Math.round((foundKeywords.length / jobKeywords.length) * 100) : 0

      // Generate placement suggestions
      const placements: Record<string, string> = {}
      missingKeywords.slice(0, 10).forEach((keyword) => {
        placements[keyword] = getSuggestedPlacement(keyword)
      })

      setAnalysis({
        matchPercentage,
        foundKeywords: result.keyword_matches || foundKeywords,
        missingKeywords,
        placements,
      })
    } catch (err) {
      console.error('Failed to analyze keywords:', err)
      setError('Failed to analyze keywords. Please try again.')
    } finally {
      setIsAnalyzing(false)
    }
  }

  const getAISuggestions = async () => {
    if (!analysis || analysis.missingKeywords.length === 0) return

    setIsGettingSuggestions(true)
    setError(null)

    try {
      const result = await aiApi.optimizeResume(resumeText, jobDescription)
      setAiSuggestions(result.suggestions)
    } catch (err) {
      console.error('Failed to get AI suggestions:', err)
      setError('Failed to get AI suggestions. Please try again.')
    } finally {
      setIsGettingSuggestions(false)
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Input Section */}
      <div className="space-y-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Resume Content</h3>
          <div className="space-y-4">
            <div className="flex gap-2">
              <button
                onClick={() => fileInputRef.current?.click()}
                className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md text-sm text-gray-700 hover:bg-gray-50"
              >
                <Upload className="w-4 h-4 mr-2" />
                Upload File
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".txt,.pdf,.docx"
                onChange={(e) => void handleFileUpload(e)}
                className="hidden"
              />
            </div>
            <textarea
              value={resumeText}
              onChange={(e) => setResumeText(e.target.value)}
              placeholder="Paste your resume content here..."
              rows={10}
              className="w-full px-3 py-2 border border-gray-300 rounded-md font-mono text-sm focus:ring-primary-500 focus:border-primary-500"
            />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Job Description</h3>
          <textarea
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
            placeholder="Paste the job description here..."
            rows={10}
            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-primary-500 focus:border-primary-500"
          />
        </div>

        <button
          onClick={() => void analyzeKeywords()}
          disabled={isAnalyzing || !resumeText.trim() || !jobDescription.trim()}
          className="w-full inline-flex items-center justify-center px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isAnalyzing ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
              Analyzing Keywords...
            </>
          ) : (
            <>
              <Search className="w-4 h-4 mr-2" />
              Analyze Keyword Gap
            </>
          )}
        </button>

        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-md">
            <p className="text-red-600 text-sm">{error}</p>
          </div>
        )}
      </div>

      {/* Results Section */}
      <div className="space-y-6">
        {analysis ? (
          <>
            {/* Match Percentage */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Keyword Match</h3>
              <div className="flex items-center justify-center">
                <div className="relative w-32 h-32">
                  <svg className="w-full h-full transform -rotate-90">
                    <circle
                      cx="64"
                      cy="64"
                      r="56"
                      fill="none"
                      stroke="#e5e7eb"
                      strokeWidth="12"
                    />
                    <circle
                      cx="64"
                      cy="64"
                      r="56"
                      fill="none"
                      stroke={
                        analysis.matchPercentage >= 80
                          ? '#22c55e'
                          : analysis.matchPercentage >= 60
                          ? '#eab308'
                          : '#ef4444'
                      }
                      strokeWidth="12"
                      strokeDasharray={`${(analysis.matchPercentage / 100) * 351.86} 351.86`}
                      strokeLinecap="round"
                    />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-3xl font-bold text-gray-900">{analysis.matchPercentage}%</span>
                  </div>
                </div>
              </div>
              <p className="text-center text-sm text-gray-500 mt-4">
                {analysis.foundKeywords.length} of {analysis.foundKeywords.length + analysis.missingKeywords.length}{' '}
                keywords found
              </p>
            </div>

            {/* Found Keywords */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
                <CheckCircle2 className="w-5 h-5 text-green-500 mr-2" />
                Found Keywords ({analysis.foundKeywords.length})
              </h3>
              <div className="flex flex-wrap gap-2">
                {analysis.foundKeywords.map((keyword, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-green-100 text-green-800"
                  >
                    {keyword}
                  </span>
                ))}
                {analysis.foundKeywords.length === 0 && (
                  <p className="text-gray-500 text-sm">No matching keywords found</p>
                )}
              </div>
            </div>

            {/* Missing Keywords */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
                <XCircle className="w-5 h-5 text-red-500 mr-2" />
                Missing Keywords ({analysis.missingKeywords.length})
              </h3>
              <div className="flex flex-wrap gap-2 mb-4">
                {analysis.missingKeywords.map((keyword, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-red-100 text-red-800"
                  >
                    {keyword}
                  </span>
                ))}
                {analysis.missingKeywords.length === 0 && (
                  <p className="text-gray-500 text-sm">No missing keywords - great job!</p>
                )}
              </div>

              {analysis.missingKeywords.length > 0 && (
                <button
                  onClick={() => void getAISuggestions()}
                  disabled={isGettingSuggestions}
                  className="inline-flex items-center px-4 py-2 bg-emerald-600 text-white rounded-md hover:bg-emerald-700 disabled:opacity-50"
                >
                  {isGettingSuggestions ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                      Getting Suggestions...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4 mr-2" />
                      Get AI Suggestions
                    </>
                  )}
                </button>
              )}
            </div>

            {/* Placement Recommendations */}
            {Object.keys(analysis.placements).length > 0 && (
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">Placement Recommendations</h3>
                <ul className="space-y-3">
                  {Object.entries(analysis.placements).map(([keyword, placement], idx) => (
                    <li key={idx} className="flex items-start gap-3 text-sm">
                      <span className="font-medium text-gray-900 min-w-[120px]">{keyword}:</span>
                      <span className="text-gray-600">{placement}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* AI Suggestions */}
            {aiSuggestions && (
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">AI Optimization Suggestions</h3>
                <div className="bg-emerald-50 rounded-md p-4">
                  <pre className="text-sm text-gray-700 whitespace-pre-wrap">{aiSuggestions}</pre>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="bg-white rounded-lg shadow p-12 text-center">
            <FileSearch className="w-16 h-16 mx-auto text-gray-300" />
            <h3 className="mt-4 text-lg font-medium text-gray-500">No Analysis Yet</h3>
            <p className="mt-2 text-sm text-gray-400">
              Provide your resume and job description, then click "Analyze Keyword Gap" to see which keywords you are
              missing.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

// =============================================================================
// Templates Tab
// =============================================================================

interface ResumeFormData {
  contact: {
    name: string
    email: string
    phone: string
    location: string
    linkedin: string
    github: string
    portfolio: string
  }
  summary: string
  experience: Array<{
    id: string
    company: string
    position: string
    location: string
    startDate: string
    endDate: string
    current: boolean
    bullets: string[]
  }>
  education: Array<{
    id: string
    school: string
    degree: string
    field: string
    graduationDate: string
    gpa: string
  }>
  skills: {
    technical: string[]
    soft: string[]
    languages: string[]
    certifications: string[]
  }
}

const initialFormData: ResumeFormData = {
  contact: {
    name: '',
    email: '',
    phone: '',
    location: '',
    linkedin: '',
    github: '',
    portfolio: '',
  },
  summary: '',
  experience: [],
  education: [],
  skills: {
    technical: [],
    soft: [],
    languages: [],
    certifications: [],
  },
}

function TemplatesTab() {
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateId>('professional')
  const [formData, setFormData] = useState<ResumeFormData>(initialFormData)
  const [activeSection, setActiveSection] = useState<'contact' | 'summary' | 'experience' | 'education' | 'skills'>(
    'contact'
  )
  const [isSaving, setIsSaving] = useState(false)
  const [saveMessage, setSaveMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const updateContact = (field: keyof ResumeFormData['contact'], value: string) => {
    setFormData((prev) => ({
      ...prev,
      contact: { ...prev.contact, [field]: value },
    }))
  }

  const addExperience = () => {
    setFormData((prev) => ({
      ...prev,
      experience: [
        ...prev.experience,
        {
          id: crypto.randomUUID(),
          company: '',
          position: '',
          location: '',
          startDate: '',
          endDate: '',
          current: false,
          bullets: [''],
        },
      ],
    }))
  }

  const updateExperience = (id: string, field: string, value: string | boolean | string[]) => {
    setFormData((prev) => ({
      ...prev,
      experience: prev.experience.map((exp) => (exp.id === id ? { ...exp, [field]: value } : exp)),
    }))
  }

  const removeExperience = (id: string) => {
    setFormData((prev) => ({
      ...prev,
      experience: prev.experience.filter((exp) => exp.id !== id),
    }))
  }

  const addEducation = () => {
    setFormData((prev) => ({
      ...prev,
      education: [
        ...prev.education,
        {
          id: crypto.randomUUID(),
          school: '',
          degree: '',
          field: '',
          graduationDate: '',
          gpa: '',
        },
      ],
    }))
  }

  const updateEducation = (id: string, field: string, value: string) => {
    setFormData((prev) => ({
      ...prev,
      education: prev.education.map((edu) => (edu.id === id ? { ...edu, [field]: value } : edu)),
    }))
  }

  const removeEducation = (id: string) => {
    setFormData((prev) => ({
      ...prev,
      education: prev.education.filter((edu) => edu.id !== id),
    }))
  }

  const updateSkills = (category: keyof ResumeFormData['skills'], value: string[]) => {
    setFormData((prev) => ({
      ...prev,
      skills: { ...prev.skills, [category]: value },
    }))
  }

  const generateResumeContent = (): string => {
    const lines: string[] = []

    // Contact
    if (formData.contact.name) {
      lines.push(formData.contact.name.toUpperCase())
      const contactDetails = [
        formData.contact.email,
        formData.contact.phone,
        formData.contact.location,
        formData.contact.linkedin,
        formData.contact.github,
        formData.contact.portfolio,
      ].filter(Boolean)
      if (contactDetails.length > 0) {
        lines.push(contactDetails.join(' | '))
      }
      lines.push('')
    }

    // Summary
    if (formData.summary) {
      lines.push('PROFESSIONAL SUMMARY')
      lines.push('-'.repeat(50))
      lines.push(formData.summary)
      lines.push('')
    }

    // Experience
    if (formData.experience.length > 0) {
      lines.push('EXPERIENCE')
      lines.push('-'.repeat(50))
      formData.experience.forEach((exp) => {
        if (exp.company || exp.position) {
          lines.push(`${exp.position}${exp.position && exp.company ? ' | ' : ''}${exp.company}`)
          const dateLocation = [
            exp.startDate && exp.endDate
              ? `${exp.startDate} - ${exp.current ? 'Present' : exp.endDate}`
              : '',
            exp.location,
          ]
            .filter(Boolean)
            .join(' | ')
          if (dateLocation) lines.push(dateLocation)
          exp.bullets.filter(Boolean).forEach((bullet) => {
            lines.push(`  * ${bullet}`)
          })
          lines.push('')
        }
      })
    }

    // Education
    if (formData.education.length > 0) {
      lines.push('EDUCATION')
      lines.push('-'.repeat(50))
      formData.education.forEach((edu) => {
        if (edu.school || edu.degree) {
          lines.push(`${edu.degree}${edu.field ? ` in ${edu.field}` : ''}`)
          lines.push(`${edu.school}${edu.graduationDate ? ` | ${edu.graduationDate}` : ''}${edu.gpa ? ` | GPA: ${edu.gpa}` : ''}`)
          lines.push('')
        }
      })
    }

    // Skills
    const hasSkills = Object.values(formData.skills).some((arr) => arr.length > 0)
    if (hasSkills) {
      lines.push('SKILLS')
      lines.push('-'.repeat(50))
      if (formData.skills.technical.length > 0) {
        lines.push(`Technical: ${formData.skills.technical.join(', ')}`)
      }
      if (formData.skills.soft.length > 0) {
        lines.push(`Soft Skills: ${formData.skills.soft.join(', ')}`)
      }
      if (formData.skills.languages.length > 0) {
        lines.push(`Languages: ${formData.skills.languages.join(', ')}`)
      }
      if (formData.skills.certifications.length > 0) {
        lines.push(`Certifications: ${formData.skills.certifications.join(', ')}`)
      }
    }

    return lines.join('\n')
  }

  const saveToProfile = async () => {
    const content = generateResumeContent()
    if (!content.trim()) {
      setSaveMessage({ type: 'error', text: 'Please fill in some resume details first' })
      return
    }

    setIsSaving(true)
    setSaveMessage(null)

    try {
      await resumesApi.create({
        version_name: `${TEMPLATES.find((t) => t.id === selectedTemplate)?.name} Template - ${new Date().toLocaleDateString()}`,
        content,
      })
      setSaveMessage({ type: 'success', text: 'Resume saved to your profile!' })
    } catch (err) {
      console.error('Failed to save resume:', err)
      setSaveMessage({ type: 'error', text: 'Failed to save resume. Please try again.' })
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
      {/* Template Selection */}
      <div className="xl:col-span-1 space-y-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Select Template</h3>
          <div className="space-y-3">
            {TEMPLATES.map((template) => (
              <button
                key={template.id}
                onClick={() => setSelectedTemplate(template.id)}
                className={cn(
                  'w-full text-left p-4 rounded-lg border-2 transition-all',
                  selectedTemplate === template.id
                    ? 'border-primary-600 bg-primary-50'
                    : 'border-gray-200 hover:border-gray-300'
                )}
              >
                <div className="flex items-center gap-3">
                  <div className={cn('w-3 h-3 rounded-full', template.color)} />
                  <span className="font-medium text-gray-900">{template.name}</span>
                </div>
                <p className="mt-1 text-sm text-gray-500">{template.description}</p>
                <div className="mt-2 flex flex-wrap gap-1">
                  {template.features.map((feature, idx) => (
                    <span key={idx} className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                      {feature}
                    </span>
                  ))}
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Form Builder */}
      <div className="xl:col-span-1 space-y-6">
        <div className="bg-white rounded-lg shadow">
          {/* Section Tabs */}
          <div className="border-b border-gray-200">
            <nav className="flex -mb-px overflow-x-auto">
              {(['contact', 'summary', 'experience', 'education', 'skills'] as const).map((section) => (
                <button
                  key={section}
                  onClick={() => setActiveSection(section)}
                  className={cn(
                    'px-4 py-3 text-sm font-medium whitespace-nowrap border-b-2',
                    activeSection === section
                      ? 'border-primary-600 text-primary-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  )}
                >
                  {section.charAt(0).toUpperCase() + section.slice(1)}
                </button>
              ))}
            </nav>
          </div>

          <div className="p-6">
            {/* Contact Section */}
            {activeSection === 'contact' && (
              <div className="space-y-4">
                <div>
                  <label htmlFor="contact-name" className="block text-sm font-medium text-gray-700">Full Name</label>
                  <input
                    id="contact-name"
                    type="text"
                    value={formData.contact.name}
                    onChange={(e) => updateContact('name', e.target.value)}
                    className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md"
                    placeholder="John Doe"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="contact-email" className="block text-sm font-medium text-gray-700">Email</label>
                    <input
                      id="contact-email"
                      type="email"
                      value={formData.contact.email}
                      onChange={(e) => updateContact('email', e.target.value)}
                      className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md"
                      placeholder="john@example.com"
                    />
                  </div>
                  <div>
                    <label htmlFor="contact-phone" className="block text-sm font-medium text-gray-700">Phone</label>
                    <input
                      id="contact-phone"
                      type="tel"
                      value={formData.contact.phone}
                      onChange={(e) => updateContact('phone', e.target.value)}
                      className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md"
                      placeholder="(555) 123-4567"
                    />
                  </div>
                </div>
                <div>
                  <label htmlFor="contact-location" className="block text-sm font-medium text-gray-700">Location</label>
                  <input
                    id="contact-location"
                    type="text"
                    value={formData.contact.location}
                    onChange={(e) => updateContact('location', e.target.value)}
                    className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md"
                    placeholder="San Francisco, CA"
                  />
                </div>
                <div>
                  <label htmlFor="contact-linkedin" className="block text-sm font-medium text-gray-700">LinkedIn</label>
                  <input
                    id="contact-linkedin"
                    type="url"
                    value={formData.contact.linkedin}
                    onChange={(e) => updateContact('linkedin', e.target.value)}
                    className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md"
                    placeholder="linkedin.com/in/johndoe"
                  />
                </div>
                <div>
                  <label htmlFor="contact-github" className="block text-sm font-medium text-gray-700">GitHub</label>
                  <input
                    id="contact-github"
                    type="url"
                    value={formData.contact.github}
                    onChange={(e) => updateContact('github', e.target.value)}
                    className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md"
                    placeholder="github.com/johndoe"
                  />
                </div>
                <div>
                  <label htmlFor="contact-portfolio" className="block text-sm font-medium text-gray-700">Portfolio</label>
                  <input
                    id="contact-portfolio"
                    type="url"
                    value={formData.contact.portfolio}
                    onChange={(e) => updateContact('portfolio', e.target.value)}
                    className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md"
                    placeholder="johndoe.com"
                  />
                </div>
              </div>
            )}

            {/* Summary Section */}
            {activeSection === 'summary' && (
              <div>
                <label htmlFor="summary-text" className="block text-sm font-medium text-gray-700 mb-2">Professional Summary</label>
                <textarea
                  id="summary-text"
                  value={formData.summary}
                  onChange={(e) => setFormData((prev) => ({ ...prev, summary: e.target.value }))}
                  rows={6}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  placeholder="Write a brief professional summary highlighting your key qualifications, experience, and career goals..."
                />
                <p className="mt-2 text-xs text-gray-500">Aim for 3-5 sentences that highlight your value proposition.</p>
              </div>
            )}

            {/* Experience Section */}
            {activeSection === 'experience' && (
              <div className="space-y-6">
                {formData.experience.map((exp, index) => (
                  <div key={exp.id} className="p-4 border border-gray-200 rounded-lg">
                    <div className="flex justify-between items-center mb-4">
                      <h4 className="font-medium text-gray-900">Experience {index + 1}</h4>
                      <button
                        onClick={() => removeExperience(exp.id)}
                        className="text-red-500 hover:text-red-700"
                        aria-label="Remove experience"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                    <div className="space-y-3">
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label htmlFor={`exp-position-${exp.id}`} className="block text-xs font-medium text-gray-600">Position</label>
                          <input
                            id={`exp-position-${exp.id}`}
                            type="text"
                            value={exp.position}
                            onChange={(e) => updateExperience(exp.id, 'position', e.target.value)}
                            className="mt-1 w-full px-2 py-1.5 text-sm border border-gray-300 rounded-md"
                            placeholder="Software Engineer"
                          />
                        </div>
                        <div>
                          <label htmlFor={`exp-company-${exp.id}`} className="block text-xs font-medium text-gray-600">Company</label>
                          <input
                            id={`exp-company-${exp.id}`}
                            type="text"
                            value={exp.company}
                            onChange={(e) => updateExperience(exp.id, 'company', e.target.value)}
                            className="mt-1 w-full px-2 py-1.5 text-sm border border-gray-300 rounded-md"
                            placeholder="Acme Inc."
                          />
                        </div>
                      </div>
                      <div>
                        <label htmlFor={`exp-location-${exp.id}`} className="block text-xs font-medium text-gray-600">Location</label>
                        <input
                          id={`exp-location-${exp.id}`}
                          type="text"
                          value={exp.location}
                          onChange={(e) => updateExperience(exp.id, 'location', e.target.value)}
                          className="mt-1 w-full px-2 py-1.5 text-sm border border-gray-300 rounded-md"
                          placeholder="San Francisco, CA"
                        />
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label htmlFor={`exp-start-${exp.id}`} className="block text-xs font-medium text-gray-600">Start Date</label>
                          <input
                            id={`exp-start-${exp.id}`}
                            type="text"
                            value={exp.startDate}
                            onChange={(e) => updateExperience(exp.id, 'startDate', e.target.value)}
                            className="mt-1 w-full px-2 py-1.5 text-sm border border-gray-300 rounded-md"
                            placeholder="Jan 2022"
                          />
                        </div>
                        <div>
                          <label htmlFor={`exp-end-${exp.id}`} className="block text-xs font-medium text-gray-600">End Date</label>
                          <input
                            id={`exp-end-${exp.id}`}
                            type="text"
                            value={exp.endDate}
                            onChange={(e) => updateExperience(exp.id, 'endDate', e.target.value)}
                            disabled={exp.current}
                            className="mt-1 w-full px-2 py-1.5 text-sm border border-gray-300 rounded-md disabled:bg-gray-100"
                            placeholder="Present"
                          />
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <input
                          id={`exp-current-${exp.id}`}
                          type="checkbox"
                          checked={exp.current}
                          onChange={(e) => updateExperience(exp.id, 'current', e.target.checked)}
                          className="rounded border-gray-300"
                        />
                        <label htmlFor={`exp-current-${exp.id}`} className="text-sm text-gray-600">Currently working here</label>
                      </div>
                      <div>
                        <div className="block text-xs font-medium text-gray-600 mb-1">Bullet Points</div>
                        {exp.bullets.map((bullet, bulletIdx) => (
                          <div key={bulletIdx} className="flex gap-2 mb-2">
                            <input
                              type="text"
                              value={bullet}
                              onChange={(e) => {
                                const newBullets = [...exp.bullets]
                                newBullets[bulletIdx] = e.target.value
                                updateExperience(exp.id, 'bullets', newBullets)
                              }}
                              className="flex-1 px-2 py-1.5 text-sm border border-gray-300 rounded-md"
                              placeholder="Describe your achievement..."
                            />
                            <button
                              onClick={() => {
                                const newBullets = exp.bullets.filter((_, i) => i !== bulletIdx)
                                updateExperience(exp.id, 'bullets', newBullets.length ? newBullets : [''])
                              }}
                              className="text-gray-400 hover:text-red-500"
                              aria-label="Remove bullet point"
                            >
                              <XCircle className="w-4 h-4" />
                            </button>
                          </div>
                        ))}
                        <button
                          onClick={() => {
                            const newBullets = [...exp.bullets, '']
                            updateExperience(exp.id, 'bullets', newBullets)
                          }}
                          className="text-sm text-primary-600 hover:text-primary-700"
                        >
                          + Add bullet point
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
                <button
                  onClick={addExperience}
                  className="w-full py-2 border-2 border-dashed border-gray-300 rounded-lg text-gray-500 hover:border-primary-400 hover:text-primary-600"
                >
                  <Plus className="w-4 h-4 inline mr-1" />
                  Add Experience
                </button>
              </div>
            )}

            {/* Education Section */}
            {activeSection === 'education' && (
              <div className="space-y-6">
                {formData.education.map((edu, index) => (
                  <div key={edu.id} className="p-4 border border-gray-200 rounded-lg">
                    <div className="flex justify-between items-center mb-4">
                      <h4 className="font-medium text-gray-900">Education {index + 1}</h4>
                      <button
                        onClick={() => removeEducation(edu.id)}
                        className="text-red-500 hover:text-red-700"
                        aria-label="Remove education"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                    <div className="space-y-3">
                      <div>
                        <label htmlFor={`edu-school-${edu.id}`} className="block text-xs font-medium text-gray-600">School</label>
                        <input
                          id={`edu-school-${edu.id}`}
                          type="text"
                          value={edu.school}
                          onChange={(e) => updateEducation(edu.id, 'school', e.target.value)}
                          className="mt-1 w-full px-2 py-1.5 text-sm border border-gray-300 rounded-md"
                          placeholder="University of California"
                        />
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label htmlFor={`edu-degree-${edu.id}`} className="block text-xs font-medium text-gray-600">Degree</label>
                          <input
                            id={`edu-degree-${edu.id}`}
                            type="text"
                            value={edu.degree}
                            onChange={(e) => updateEducation(edu.id, 'degree', e.target.value)}
                            className="mt-1 w-full px-2 py-1.5 text-sm border border-gray-300 rounded-md"
                            placeholder="Bachelor of Science"
                          />
                        </div>
                        <div>
                          <label htmlFor={`edu-field-${edu.id}`} className="block text-xs font-medium text-gray-600">Field of Study</label>
                          <input
                            id={`edu-field-${edu.id}`}
                            type="text"
                            value={edu.field}
                            onChange={(e) => updateEducation(edu.id, 'field', e.target.value)}
                            className="mt-1 w-full px-2 py-1.5 text-sm border border-gray-300 rounded-md"
                            placeholder="Computer Science"
                          />
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label htmlFor={`edu-grad-${edu.id}`} className="block text-xs font-medium text-gray-600">Graduation Date</label>
                          <input
                            id={`edu-grad-${edu.id}`}
                            type="text"
                            value={edu.graduationDate}
                            onChange={(e) => updateEducation(edu.id, 'graduationDate', e.target.value)}
                            className="mt-1 w-full px-2 py-1.5 text-sm border border-gray-300 rounded-md"
                            placeholder="May 2023"
                          />
                        </div>
                        <div>
                          <label htmlFor={`edu-gpa-${edu.id}`} className="block text-xs font-medium text-gray-600">GPA (Optional)</label>
                          <input
                            id={`edu-gpa-${edu.id}`}
                            type="text"
                            value={edu.gpa}
                            onChange={(e) => updateEducation(edu.id, 'gpa', e.target.value)}
                            className="mt-1 w-full px-2 py-1.5 text-sm border border-gray-300 rounded-md"
                            placeholder="3.8"
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
                <button
                  onClick={addEducation}
                  className="w-full py-2 border-2 border-dashed border-gray-300 rounded-lg text-gray-500 hover:border-primary-400 hover:text-primary-600"
                >
                  <Plus className="w-4 h-4 inline mr-1" />
                  Add Education
                </button>
              </div>
            )}

            {/* Skills Section */}
            {activeSection === 'skills' && (
              <div className="space-y-6">
                <div>
                  <div className="block text-sm font-medium text-gray-700 mb-2">Technical Skills</div>
                  <SkillInput
                    skills={formData.skills.technical}
                    onChange={(skills) => updateSkills('technical', skills)}
                    placeholder="e.g., JavaScript, Python, React"
                  />
                </div>
                <div>
                  <div className="block text-sm font-medium text-gray-700 mb-2">Soft Skills</div>
                  <SkillInput
                    skills={formData.skills.soft}
                    onChange={(skills) => updateSkills('soft', skills)}
                    placeholder="e.g., Leadership, Communication"
                  />
                </div>
                <div>
                  <div className="block text-sm font-medium text-gray-700 mb-2">Languages</div>
                  <SkillInput
                    skills={formData.skills.languages}
                    onChange={(skills) => updateSkills('languages', skills)}
                    placeholder="e.g., English (Native), Spanish (Fluent)"
                  />
                </div>
                <div>
                  <div className="block text-sm font-medium text-gray-700 mb-2">Certifications</div>
                  <SkillInput
                    skills={formData.skills.certifications}
                    onChange={(skills) => updateSkills('certifications', skills)}
                    placeholder="e.g., AWS Solutions Architect"
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Preview */}
      <div className="xl:col-span-1 space-y-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-medium text-gray-900">Preview</h3>
            <div className="flex gap-2">
              <button
                onClick={() => {
                  void navigator.clipboard.writeText(generateResumeContent())
                }}
                className="inline-flex items-center px-3 py-1.5 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
                title="Copy to clipboard"
              >
                <Copy className="w-4 h-4" />
              </button>
              <button
                onClick={() => {
                  const content = generateResumeContent()
                  const blob = new Blob([content], { type: 'text/plain' })
                  const url = URL.createObjectURL(blob)
                  const a = document.createElement('a')
                  a.href = url
                  a.download = 'resume.txt'
                  a.click()
                  URL.revokeObjectURL(url)
                }}
                className="inline-flex items-center px-3 py-1.5 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
                title="Download as text"
              >
                <Download className="w-4 h-4" />
              </button>
            </div>
          </div>
          <div
            className={cn(
              'border rounded-lg p-6 min-h-[400px] max-h-[600px] overflow-y-auto',
              selectedTemplate === 'professional' && 'bg-white border-slate-300',
              selectedTemplate === 'modern' && 'bg-blue-50 border-blue-200',
              selectedTemplate === 'technical' && 'bg-emerald-50 border-emerald-200',
              selectedTemplate === 'executive' && 'bg-purple-50 border-purple-200',
              selectedTemplate === 'creative' && 'bg-pink-50 border-pink-200'
            )}
          >
            <pre className="text-sm text-gray-700 whitespace-pre-wrap font-mono">{generateResumeContent() || 'Fill in the form to see your resume preview...'}</pre>
          </div>
        </div>

        <button
          onClick={() => void saveToProfile()}
          disabled={isSaving}
          className="w-full inline-flex items-center justify-center px-4 py-3 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50"
        >
          {isSaving ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
              Saving...
            </>
          ) : (
            <>
              <FileText className="w-4 h-4 mr-2" />
              Save to Profile
            </>
          )}
        </button>

        {saveMessage && (
          <div
            className={cn(
              'p-4 rounded-md',
              saveMessage.type === 'success' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
            )}
          >
            {saveMessage.text}
          </div>
        )}
      </div>
    </div>
  )
}

// =============================================================================
// Shared Components
// =============================================================================

function ScoreBadge({ score }: { score: number }) {
  const getScoreColor = (score: number) => {
    if (score >= 80) return 'bg-green-100 text-green-800'
    if (score >= 60) return 'bg-yellow-100 text-yellow-800'
    return 'bg-red-100 text-red-800'
  }

  return (
    <span className={cn('inline-flex items-center px-2.5 py-0.5 rounded-full text-sm font-medium', getScoreColor(score))}>
      <BarChart3 className="w-3 h-3 mr-1" />
      {score}
    </span>
  )
}

function ScoreGauge({ score }: { score: number }) {
  const getColor = (score: number) => {
    if (score >= 80) return '#22c55e'
    if (score >= 60) return '#eab308'
    return '#ef4444'
  }

  const circumference = 2 * Math.PI * 70
  const strokeDasharray = `${(score / 100) * circumference} ${circumference}`

  return (
    <div className="relative w-48 h-48">
      <svg className="w-full h-full transform -rotate-90">
        <circle cx="96" cy="96" r="70" fill="none" stroke="#e5e7eb" strokeWidth="16" />
        <circle
          cx="96"
          cy="96"
          r="70"
          fill="none"
          stroke={getColor(score)}
          strokeWidth="16"
          strokeDasharray={strokeDasharray}
          strokeLinecap="round"
          className="transition-all duration-500"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-4xl font-bold text-gray-900">{score}</span>
        <span className="text-sm text-gray-500">ATS Score</span>
      </div>
    </div>
  )
}

function ResumeFormModal({
  resume,
  onClose,
  onSave,
}: {
  resume?: Resume
  onClose: () => void
  onSave: (resume: Resume) => void
}) {
  const [formData, setFormData] = useState({
    version_name: resume?.version_name || '',
    content: resume?.content || '',
  })
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    void (async () => {
      try {
        const result = await resumesApi.upload(file)
        setFormData((prev) => ({ ...prev, content: result.content }))
      } catch (err) {
        console.error('Failed to upload file:', err)
        setError('Failed to parse file. Please try pasting your resume text instead.')
      }
    })()
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)
    setError(null)

    try {
      let savedResume: Resume
      if (resume) {
        savedResume = await resumesApi.update(resume.id, formData)
      } else {
        savedResume = await resumesApi.create(formData)
      }
      onSave(savedResume)
    } catch (err) {
      console.error('Failed to save resume:', err)
      setError('Failed to save resume. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50"
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          onClose()
        }
      }}
      onKeyDown={(e) => {
        if (e.key === 'Escape') {
          onClose()
        }
      }}
      role="button"
      tabIndex={0}
      aria-label="Close modal"
    >
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full p-6">
        <h2 id="modal-title" className="text-xl font-bold mb-4">
          {resume ? 'Edit Resume' : 'Add Resume'}
        </h2>

        <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4">
          <div>
            <label htmlFor="version_name" className="block text-sm font-medium text-gray-700">
              Version Name
            </label>
            <input
              id="version_name"
              type="text"
              required
              value={formData.version_name}
              onChange={(e) => setFormData({ ...formData, version_name: e.target.value })}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
              placeholder="e.g., Software Engineer - Google"
            />
          </div>

          <div>
            <label htmlFor="content" className="block text-sm font-medium text-gray-700">
              Resume Content
            </label>
            <div className="mt-1 mb-2">
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md text-sm text-gray-700 hover:bg-gray-50"
              >
                <Upload className="w-4 h-4 mr-2" />
                Upload File
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".txt,.pdf,.docx"
                onChange={handleFileUpload}
                className="hidden"
              />
              <span className="ml-2 text-xs text-gray-500">Supports .txt, .pdf, .docx</span>
            </div>
            <textarea
              id="content"
              required
              rows={12}
              value={formData.content}
              onChange={(e) => setFormData({ ...formData, content: e.target.value })}
              className="block w-full px-3 py-2 border border-gray-300 rounded-md font-mono text-sm focus:ring-primary-500 focus:border-primary-500"
              placeholder="Paste your resume content here..."
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
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50"
            >
              {isSubmitting ? 'Saving...' : resume ? 'Update Resume' : 'Save Resume'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function SkillInput({
  skills,
  onChange,
  placeholder,
}: {
  skills: string[]
  onChange: (skills: string[]) => void
  placeholder: string
}) {
  const [inputValue, setInputValue] = useState('')

  const addSkill = () => {
    const trimmed = inputValue.trim()
    if (trimmed && !skills.includes(trimmed)) {
      onChange([...skills, trimmed])
      setInputValue('')
    }
  }

  const removeSkill = (index: number) => {
    onChange(skills.filter((_, i) => i !== index))
  }

  return (
    <div>
      <div className="flex gap-2 mb-2">
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault()
              addSkill()
            }
          }}
          className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm"
          placeholder={placeholder}
        />
        <button
          type="button"
          onClick={addSkill}
          className="px-3 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 text-sm"
        >
          Add
        </button>
      </div>
      <div className="flex flex-wrap gap-2">
        {skills.map((skill, index) => (
          <span
            key={index}
            className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-gray-100 text-gray-800"
          >
            {skill}
            <button
              type="button"
              onClick={() => removeSkill(index)}
              className="ml-2 text-gray-500 hover:text-red-500"
              aria-label={`Remove ${skill}`}
            >
              <XCircle className="w-4 h-4" />
            </button>
          </span>
        ))}
      </div>
    </div>
  )
}

// =============================================================================
// Helper Functions
// =============================================================================

function extractKeywordsFromText(text: string): string[] {
  // Common keywords to look for in job descriptions
  const commonTechKeywords = [
    'javascript', 'typescript', 'python', 'java', 'react', 'angular', 'vue', 'node',
    'sql', 'nosql', 'mongodb', 'postgresql', 'aws', 'azure', 'gcp', 'docker', 'kubernetes',
    'git', 'ci/cd', 'agile', 'scrum', 'rest', 'api', 'graphql', 'machine learning', 'ai',
    'data analysis', 'data science', 'frontend', 'backend', 'full stack', 'devops',
  ]

  const commonSoftSkills = [
    'leadership', 'communication', 'teamwork', 'problem solving', 'analytical',
    'project management', 'collaboration', 'time management', 'attention to detail',
  ]

  const allKeywords = [...commonTechKeywords, ...commonSoftSkills]
  const textLower = text.toLowerCase()

  const found = allKeywords.filter((keyword) => textLower.includes(keyword.toLowerCase()))

  // Also extract capitalized words that might be technologies or skills
  const words = text.match(/\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b/g) || []
  const uniqueWords = Array.from(new Set(words))
    .filter((word) => word.length > 2 && !['The', 'And', 'For', 'With', 'Our', 'You', 'Your'].includes(word))
    .slice(0, 10)

  return Array.from(new Set([...found, ...uniqueWords]))
}

function getSuggestedPlacement(keyword: string): string {
  const keywordLower = keyword.toLowerCase()

  // Technical skills
  if (
    ['javascript', 'typescript', 'python', 'java', 'react', 'angular', 'vue', 'node', 'sql', 'aws', 'docker', 'kubernetes', 'git'].some(
      (tech) => keywordLower.includes(tech)
    )
  ) {
    return 'Add to Technical Skills section and mention in relevant experience bullet points'
  }

  // Soft skills
  if (
    ['leadership', 'communication', 'teamwork', 'collaboration', 'management'].some((skill) =>
      keywordLower.includes(skill)
    )
  ) {
    return 'Demonstrate in experience bullet points with specific examples and outcomes'
  }

  // Methodologies
  if (['agile', 'scrum', 'waterfall', 'kanban'].some((method) => keywordLower.includes(method))) {
    return 'Add to Skills section and reference in project/experience descriptions'
  }

  // Default
  return 'Consider adding to Skills section or incorporating into experience descriptions'
}
