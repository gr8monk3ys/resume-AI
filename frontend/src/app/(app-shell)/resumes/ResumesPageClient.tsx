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
  const [activeTab, setActiveTab] = useState<TabId>('list')

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

interface ResumeListTabState {
  resumes: Resume[]
  isLoading: boolean
  showAddForm: boolean
  editingResume: Resume | null
  error: string | null
}

const INITIAL_RESUME_LIST_TAB_STATE: ResumeListTabState = {
  resumes: [],
  isLoading: true,
  showAddForm: false,
  editingResume: null,
  error: null,
}

function ResumeListTab() {
  const {
    resumes,
    isLoading,
    showAddForm,
    editingResume,
    error,
    tableContainerRef,
    loadResumes,
    openAddForm,
    closeAddForm,
    deleteResume,
    startEditingResume,
    stopEditingResume,
    handleResumeCreated,
    handleResumeUpdated,
  } = useResumeListTabController()

  if (isLoading) {
    return <TabSpinner />
  }

  if (error) {
    return <ResumeListErrorState error={error} onRetry={loadResumes} />
  }

  return (
    <div>
      <ResumeListToolbar resumeCount={resumes.length} onCreateResume={openAddForm} />

      {resumes.length === 0 ? (
        <ResumeListEmptyState onCreateResume={openAddForm} />
      ) : (
        <ResumeListTable
          resumes={resumes}
          tableContainerRef={tableContainerRef}
          onEdit={startEditingResume}
          onDelete={deleteResume}
        />
      )}

      {showAddForm && (
        <ResumeFormModal onClose={closeAddForm} onSave={handleResumeCreated} />
      )}

      {editingResume && (
        <ResumeFormModal
          resume={editingResume}
          onClose={stopEditingResume}
          onSave={handleResumeUpdated}
        />
      )}
    </div>
  )
}

function ResumeListToolbar({
  resumeCount,
  onCreateResume,
}: {
  resumeCount: number
  onCreateResume: () => void
}) {
  return (
    <div className="mb-6 flex items-center justify-between">
      <p className="text-gray-600">{resumeCount} resume(s) saved</p>
      <button
        onClick={onCreateResume}
        className="inline-flex items-center rounded-md bg-primary-600 px-4 py-2 text-white hover:bg-primary-700"
      >
        <Plus className="mr-2 h-4 w-4" />
        Create New Resume
      </button>
    </div>
  )
}

function ResumeListEmptyState({
  onCreateResume,
}: {
  onCreateResume: () => void
}) {
  return (
    <div className="rounded-lg bg-white py-12 text-center shadow">
      <FileText className="mx-auto h-12 w-12 text-gray-400" />
      <h3 className="mt-4 text-lg font-medium text-gray-900">No resumes yet</h3>
      <p className="mt-2 text-gray-500">Create your first resume to get started</p>
      <button
        onClick={onCreateResume}
        className="mt-4 inline-flex items-center rounded-md bg-primary-600 px-4 py-2 text-white hover:bg-primary-700"
      >
        <Plus className="mr-2 h-4 w-4" />
        Create Resume
      </button>
    </div>
  )
}

function ResumeListErrorState({
  error,
  onRetry,
}: {
  error: string
  onRetry: () => Promise<void>
}) {
  return (
    <div className="py-12 text-center">
      <AlertCircle className="mx-auto h-12 w-12 text-red-400" />
      <p className="mt-4 text-red-600">{error}</p>
      <button
        onClick={() => void onRetry()}
        className="mt-4 rounded-md bg-primary-600 px-4 py-2 text-white hover:bg-primary-700"
      >
        Try Again
      </button>
    </div>
  )
}

function ResumeListTable({
  resumes,
  tableContainerRef,
  onEdit,
  onDelete,
}: {
  resumes: Resume[]
  tableContainerRef: React.RefObject<HTMLDivElement | null>
  onEdit: (resume: Resume) => void
  onDelete: (id: number) => Promise<void>
}) {
  const rowVirtualizer = useVirtualizer({
    count: resumes.length,
    getScrollElement: () => tableContainerRef.current,
    estimateSize: () => RESUME_ROW_HEIGHT,
    overscan: 10,
    getItemKey: (index) => resumes[index]?.id ?? index,
  })

  const virtualRows = rowVirtualizer.getVirtualItems()
  const totalSize = rowVirtualizer.getTotalSize()
  const paddingTop = virtualRows.length > 0 ? virtualRows[0]?.start ?? 0 : 0
  const paddingBottom = virtualRows.length > 0
    ? totalSize - (virtualRows[virtualRows.length - 1]?.end ?? totalSize)
    : 0

  return (
    <div
      ref={tableContainerRef}
      className="overflow-auto rounded-lg bg-white shadow"
      style={{ maxHeight: 'calc(100vh - 320px)', minHeight: '300px' }}
    >
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="sticky top-0 z-10 bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
              Version Name
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
              ATS Score
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
              Created
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
              Last Updated
            </th>
            <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 bg-white">
          {paddingTop > 0 && (
            <tr>
              <td colSpan={5} style={{ height: paddingTop, padding: 0, border: 0 }} />
            </tr>
          )}
          {virtualRows.map((virtualRow) => {
            const resume = resumes[virtualRow.index]
            if (!resume) {
              return null
            }

            return (
              <ResumeRow
                key={resume.id}
                resume={resume}
                onEdit={onEdit}
                onDelete={onDelete}
              />
            )
          })}
          {paddingBottom > 0 && (
            <tr>
              <td colSpan={5} style={{ height: paddingBottom, padding: 0, border: 0 }} />
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}

function useResumeListTabController() {
  const [state, setState] = useState(INITIAL_RESUME_LIST_TAB_STATE)
  const tableContainerRef = useRef<HTMLDivElement>(null)

  const loadResumes = useCallback(async () => {
    setState((current) => ({ ...current, isLoading: true, error: null }))

    try {
      const resumes = await resumesApi.list()
      setState((current) => ({
        ...current,
        resumes,
        isLoading: false,
        error: null,
      }))
    } catch (error) {
      console.error('Failed to load resumes:', error)
      setState((current) => ({
        ...current,
        isLoading: false,
        error: 'Failed to load resumes. Please try again.',
      }))
    }
  }, [])

  useEffect(() => {
    void loadResumes()
  }, [loadResumes])

  const openAddForm = useCallback(() => {
    setState((current) => ({ ...current, showAddForm: true }))
  }, [])

  const closeAddForm = useCallback(() => {
    setState((current) => ({ ...current, showAddForm: false }))
  }, [])

  const startEditingResume = useCallback((resume: Resume) => {
    setState((current) => ({ ...current, editingResume: resume }))
  }, [])

  const stopEditingResume = useCallback(() => {
    setState((current) => ({ ...current, editingResume: null }))
  }, [])

  const deleteResume = useCallback(async (id: number) => {
    try {
      await resumesApi.delete(id)
      setState((current) => ({
        ...current,
        resumes: current.resumes.filter((resume) => resume.id !== id),
      }))
    } catch (error) {
      console.error('Failed to delete resume:', error)
      setState((current) => ({
        ...current,
        error: 'Failed to delete resume. Please try again.',
      }))
    }
  }, [])

  const handleResumeCreated = useCallback((resume: Resume) => {
    setState((current) => ({
      ...current,
      resumes: [resume, ...current.resumes],
      showAddForm: false,
    }))
  }, [])

  const handleResumeUpdated = useCallback((resume: Resume) => {
    setState((current) => ({
      ...current,
      resumes: current.resumes.map((entry) => (entry.id === resume.id ? resume : entry)),
      editingResume: null,
    }))
  }, [])

  return {
    ...state,
    tableContainerRef,
    loadResumes,
    openAddForm,
    closeAddForm,
    deleteResume,
    startEditingResume,
    stopEditingResume,
    handleResumeCreated,
    handleResumeUpdated,
  }
}

// =============================================================================
// ATS Analysis Tab
// =============================================================================

interface ATSAnalysisTabState {
  resumeText: string
  jobDescription: string
  analysis: ATSAnalysis | null
  isAnalyzing: boolean
  isOptimizing: boolean
  optimizedResume: string | null
  error: string | null
}

const INITIAL_ATS_ANALYSIS_TAB_STATE: ATSAnalysisTabState = {
  resumeText: '',
  jobDescription: '',
  analysis: null,
  isAnalyzing: false,
  isOptimizing: false,
  optimizedResume: null,
  error: null,
}

function ATSAnalysisTab() {
  const {
    resumeText,
    jobDescription,
    analysis,
    optimizedResume,
    isAnalyzing,
    isOptimizing,
    error,
    fileInputRef,
    setResumeText,
    setJobDescription,
    handleFileUpload,
    analyzeResume,
    optimizeResume,
  } = useATSAnalysisTabController()

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <ATSAnalysisInputSection
        resumeText={resumeText}
        jobDescription={jobDescription}
        error={error}
        fileInputRef={fileInputRef}
        isAnalyzing={isAnalyzing}
        isOptimizing={isOptimizing}
        onResumeTextChange={setResumeText}
        onJobDescriptionChange={setJobDescription}
        onFileUpload={handleFileUpload}
        onAnalyze={analyzeResume}
        onOptimize={optimizeResume}
      />
      <ATSAnalysisResultsSection analysis={analysis} optimizedResume={optimizedResume} />
    </div>
  )
}

function ATSAnalysisInputSection({
  resumeText,
  jobDescription,
  error,
  fileInputRef,
  isAnalyzing,
  isOptimizing,
  onResumeTextChange,
  onJobDescriptionChange,
  onFileUpload,
  onAnalyze,
  onOptimize,
}: {
  resumeText: string
  jobDescription: string
  error: string | null
  fileInputRef: React.RefObject<HTMLInputElement | null>
  isAnalyzing: boolean
  isOptimizing: boolean
  onResumeTextChange: (value: string) => void
  onJobDescriptionChange: (value: string) => void
  onFileUpload: (event: React.ChangeEvent<HTMLInputElement>) => Promise<void>
  onAnalyze: () => Promise<void>
  onOptimize: () => Promise<void>
}) {
  return (
    <div className="space-y-6">
      <div className="rounded-lg bg-white p-6 shadow">
        <h3 className="mb-4 text-lg font-medium text-gray-900">Resume Content</h3>
        <div className="space-y-4">
          <UploadResumeButton
            fileInputRef={fileInputRef}
            helperText="Supports .txt, .pdf, .docx"
            onChange={onFileUpload}
          />
          <textarea
            value={resumeText}
            onChange={(event) => onResumeTextChange(event.target.value)}
            placeholder="Paste your resume content here..."
            rows={12}
            className="w-full rounded-md border border-gray-300 px-3 py-2 font-mono text-sm focus:border-primary-500 focus:ring-primary-500"
          />
        </div>
      </div>

      <div className="rounded-lg bg-white p-6 shadow">
        <h3 className="mb-4 text-lg font-medium text-gray-900">Job Description (Optional)</h3>
        <textarea
          value={jobDescription}
          onChange={(event) => onJobDescriptionChange(event.target.value)}
          placeholder="Paste the job description for job-specific analysis..."
          rows={8}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:ring-primary-500"
        />
      </div>

      <ATSAnalysisActions
        canAnalyze={resumeText.trim().length > 0}
        canOptimize={resumeText.trim().length > 0 && jobDescription.trim().length > 0}
        isAnalyzing={isAnalyzing}
        isOptimizing={isOptimizing}
        onAnalyze={onAnalyze}
        onOptimize={onOptimize}
      />

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 p-4">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}
    </div>
  )
}

function ATSAnalysisActions({
  canAnalyze,
  canOptimize,
  isAnalyzing,
  isOptimizing,
  onAnalyze,
  onOptimize,
}: {
  canAnalyze: boolean
  canOptimize: boolean
  isAnalyzing: boolean
  isOptimizing: boolean
  onAnalyze: () => Promise<void>
  onOptimize: () => Promise<void>
}) {
  return (
    <div className="flex gap-3">
      <button
        onClick={() => void onAnalyze()}
        disabled={isAnalyzing || !canAnalyze}
        className="flex-1 inline-flex items-center justify-center rounded-md bg-primary-600 px-4 py-2 text-white hover:bg-primary-700 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isAnalyzing ? (
          <>
            <InlineSpinner />
            Analyzing...
          </>
        ) : (
          <>
            <BarChart3 className="mr-2 h-4 w-4" />
            Analyze Resume
          </>
        )}
      </button>
      <button
        onClick={() => void onOptimize()}
        disabled={isOptimizing || !canOptimize}
        className="flex-1 inline-flex items-center justify-center rounded-md bg-emerald-600 px-4 py-2 text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isOptimizing ? (
          <>
            <InlineSpinner />
            Optimizing...
          </>
        ) : (
          <>
            <Sparkles className="mr-2 h-4 w-4" />
            AI Optimize
          </>
        )}
      </button>
    </div>
  )
}

function ATSAnalysisResultsSection({
  analysis,
  optimizedResume,
}: {
  analysis: ATSAnalysis | null
  optimizedResume: string | null
}) {
  return (
    <div className="space-y-6">
      {analysis ? (
        <>
          <ATSScoreCard score={analysis.ats_score} />
          <ATSScoreBreakdownCard analysis={analysis} />
          <ATSImprovementSuggestionsCard suggestions={analysis.suggestions} />
        </>
      ) : (
        <ATSAnalysisEmptyState />
      )}

      {optimizedResume && <OptimizedResumeCard optimizedResume={optimizedResume} />}
    </div>
  )
}

function ATSScoreCard({
  score,
}: {
  score: number
}) {
  return (
    <div className="rounded-lg bg-white p-6 shadow">
      <h3 className="mb-4 text-lg font-medium text-gray-900">ATS Score</h3>
      <div className="flex items-center justify-center">
        <ScoreGauge score={score} />
      </div>
    </div>
  )
}

function ATSScoreBreakdownCard({
  analysis,
}: {
  analysis: ATSAnalysis
}) {
  return (
    <div className="rounded-lg bg-white p-6 shadow">
      <h3 className="mb-4 text-lg font-medium text-gray-900">Score Breakdown</h3>
      <div className="space-y-4">
        {SCORE_CATEGORIES.map((category) => {
          const score = analysis.score_breakdown?.[category.key] ?? 0

          return (
            <div key={category.key}>
              <div className="mb-1 flex justify-between text-sm">
                <span className="font-medium text-gray-700">{category.label}</span>
                <span className="text-gray-500">{score}%</span>
              </div>
              <div className="h-2 w-full rounded-full bg-gray-200">
                <div
                  className={cn(
                    'h-2 rounded-full transition-all duration-300',
                    score >= 80 ? 'bg-green-500' : score >= 60 ? 'bg-yellow-500' : 'bg-red-500'
                  )}
                  style={{ width: `${score}%` }}
                />
              </div>
              <p className="mt-1 text-xs text-gray-400">{category.description}</p>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function ATSImprovementSuggestionsCard({
  suggestions,
}: {
  suggestions: string[]
}) {
  return (
    <div className="rounded-lg bg-white p-6 shadow">
      <h3 className="mb-4 text-lg font-medium text-gray-900">Improvement Suggestions</h3>
      {suggestions.length > 0 ? (
        <ul className="space-y-3">
          {suggestions.map((suggestion) => (
            <li key={suggestion} className="flex items-start gap-3">
              <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-amber-500" />
              <span className="text-sm text-gray-700">{suggestion}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-gray-500">Your resume looks great! No major improvements needed.</p>
      )}
    </div>
  )
}

function ATSAnalysisEmptyState() {
  return (
    <div className="rounded-lg bg-white p-12 text-center shadow">
      <BarChart3 className="mx-auto h-16 w-16 text-gray-300" />
      <h3 className="mt-4 text-lg font-medium text-gray-500">No Analysis Yet</h3>
      <p className="mt-2 text-sm text-gray-400">
        Upload or paste your resume, then click &quot;Analyze Resume&quot; to see your ATS score and suggestions.
      </p>
    </div>
  )
}

function OptimizedResumeCard({
  optimizedResume,
}: {
  optimizedResume: string
}) {
  return (
    <div className="rounded-lg bg-white p-6 shadow">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-medium text-gray-900">AI Optimized Resume</h3>
        <button
          onClick={() => {
            void navigator.clipboard.writeText(optimizedResume)
          }}
          className="inline-flex items-center rounded-md border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-50"
        >
          <Copy className="mr-1 h-4 w-4" />
          Copy
        </button>
      </div>
      <div className="max-h-96 overflow-y-auto rounded-md bg-gray-50 p-4">
        <pre className="whitespace-pre-wrap font-mono text-sm text-gray-700">{optimizedResume}</pre>
      </div>
    </div>
  )
}

function useATSAnalysisTabController() {
  const [state, setState] = useState(INITIAL_ATS_ANALYSIS_TAB_STATE)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const setResumeText = useCallback((resumeText: string) => {
    setState((current) => ({ ...current, resumeText }))
  }, [])

  const setJobDescription = useCallback((jobDescription: string) => {
    setState((current) => ({ ...current, jobDescription }))
  }, [])

  const handleFileUpload = useCallback(async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) {
      return
    }

    try {
      const result = await resumesApi.upload(file)
      setState((current) => ({
        ...current,
        resumeText: result.content,
        error: null,
      }))
    } catch (error) {
      console.error('Failed to upload file:', error)
      setState((current) => ({
        ...current,
        error: 'Failed to parse file. Please try pasting your resume text instead.',
      }))
    }
  }, [])

  const analyzeResume = useCallback(async () => {
    const trimmedResumeText = state.resumeText.trim()
    if (!trimmedResumeText) {
      setState((current) => ({
        ...current,
        error: 'Please provide resume content',
      }))
      return
    }

    setState((current) => ({
      ...current,
      isAnalyzing: true,
      error: null,
      analysis: null,
    }))

    try {
      const analysis = await resumesApi.analyzeContent(
        trimmedResumeText,
        state.jobDescription || undefined
      )
      setState((current) => ({
        ...current,
        analysis,
        isAnalyzing: false,
      }))
    } catch (error) {
      console.error('Failed to analyze resume:', error)
      setState((current) => ({
        ...current,
        isAnalyzing: false,
        error: 'Failed to analyze resume. Please try again.',
      }))
    }
  }, [state.jobDescription, state.resumeText])

  const optimizeResume = useCallback(async () => {
    const trimmedResumeText = state.resumeText.trim()
    const trimmedJobDescription = state.jobDescription.trim()

    if (!trimmedResumeText || !trimmedJobDescription) {
      setState((current) => ({
        ...current,
        error: 'Please provide both resume content and job description for AI optimization',
      }))
      return
    }

    setState((current) => ({
      ...current,
      isOptimizing: true,
      error: null,
    }))

    try {
      const result = await aiApi.tailorResume(trimmedResumeText, trimmedJobDescription)
      setState((current) => ({
        ...current,
        optimizedResume: result.tailored_resume,
        isOptimizing: false,
      }))
    } catch (error) {
      console.error('Failed to optimize resume:', error)
      setState((current) => ({
        ...current,
        isOptimizing: false,
        error: 'Failed to optimize resume. Please try again.',
      }))
    }
  }, [state.jobDescription, state.resumeText])

  return {
    ...state,
    fileInputRef,
    setResumeText,
    setJobDescription,
    handleFileUpload,
    analyzeResume,
    optimizeResume,
  }
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
  const {
    resumeText,
    jobDescription,
    analysis,
    aiSuggestions,
    isAnalyzing,
    isGettingSuggestions,
    error,
    fileInputRef,
    setResumeText,
    setJobDescription,
    handleFileUpload,
    analyzeKeywords,
    getAISuggestions,
  } = useKeywordGapTabController()

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <KeywordGapInputSection
        resumeText={resumeText}
        jobDescription={jobDescription}
        error={error}
        fileInputRef={fileInputRef}
        isAnalyzing={isAnalyzing}
        onResumeTextChange={setResumeText}
        onJobDescriptionChange={setJobDescription}
        onFileUpload={handleFileUpload}
        onAnalyze={analyzeKeywords}
      />
      <KeywordGapResultsSection
        analysis={analysis}
        aiSuggestions={aiSuggestions}
        isGettingSuggestions={isGettingSuggestions}
        onGetSuggestions={getAISuggestions}
      />
    </div>
  )
}

interface KeywordGapTabState {
  resumeText: string
  jobDescription: string
  analysis: KeywordAnalysis | null
  aiSuggestions: string[]
  isAnalyzing: boolean
  isGettingSuggestions: boolean
  error: string | null
}

const INITIAL_KEYWORD_GAP_TAB_STATE: KeywordGapTabState = {
  resumeText: '',
  jobDescription: '',
  analysis: null,
  aiSuggestions: [],
  isAnalyzing: false,
  isGettingSuggestions: false,
  error: null,
}

function KeywordGapInputSection({
  resumeText,
  jobDescription,
  error,
  fileInputRef,
  isAnalyzing,
  onResumeTextChange,
  onJobDescriptionChange,
  onFileUpload,
  onAnalyze,
}: {
  resumeText: string
  jobDescription: string
  error: string | null
  fileInputRef: React.RefObject<HTMLInputElement | null>
  isAnalyzing: boolean
  onResumeTextChange: (value: string) => void
  onJobDescriptionChange: (value: string) => void
  onFileUpload: (event: React.ChangeEvent<HTMLInputElement>) => Promise<void>
  onAnalyze: () => Promise<void>
}) {
  return (
    <div className="space-y-6">
      <div className="rounded-lg bg-white p-6 shadow">
        <h3 className="mb-4 text-lg font-medium text-gray-900">Resume Content</h3>
        <div className="space-y-4">
          <UploadResumeButton fileInputRef={fileInputRef} onChange={onFileUpload} />
          <textarea
            value={resumeText}
            onChange={(event) => onResumeTextChange(event.target.value)}
            placeholder="Paste your resume content here..."
            rows={10}
            className="w-full rounded-md border border-gray-300 px-3 py-2 font-mono text-sm focus:border-primary-500 focus:ring-primary-500"
          />
        </div>
      </div>

      <div className="rounded-lg bg-white p-6 shadow">
        <h3 className="mb-4 text-lg font-medium text-gray-900">Job Description</h3>
        <textarea
          value={jobDescription}
          onChange={(event) => onJobDescriptionChange(event.target.value)}
          placeholder="Paste the job description here..."
          rows={10}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:ring-primary-500"
        />
      </div>

      <button
        onClick={() => void onAnalyze()}
        disabled={isAnalyzing || !resumeText.trim() || !jobDescription.trim()}
        className="inline-flex w-full items-center justify-center rounded-md bg-primary-600 px-4 py-2 text-white hover:bg-primary-700 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isAnalyzing ? (
          <>
            <InlineSpinner />
            Analyzing Keywords...
          </>
        ) : (
          <>
            <Search className="mr-2 h-4 w-4" />
            Analyze Keyword Gap
          </>
        )}
      </button>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 p-4">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}
    </div>
  )
}

function KeywordGapResultsSection({
  analysis,
  aiSuggestions,
  isGettingSuggestions,
  onGetSuggestions,
}: {
  analysis: KeywordAnalysis | null
  aiSuggestions: string[]
  isGettingSuggestions: boolean
  onGetSuggestions: () => Promise<void>
}) {
  if (!analysis) {
    return <KeywordGapEmptyState />
  }

  return (
    <div className="space-y-6">
      <KeywordMatchCard analysis={analysis} />
      <KeywordCollectionCard
        title="Found Keywords"
        icon={<CheckCircle2 className="mr-2 h-5 w-5 text-green-500" />}
        keywords={analysis.foundKeywords}
        emptyMessage="No matching keywords found"
        variant="found"
      />
      <MissingKeywordsCard
        analysis={analysis}
        aiSuggestions={aiSuggestions}
        isGettingSuggestions={isGettingSuggestions}
        onGetSuggestions={onGetSuggestions}
      />
      {Object.keys(analysis.placements).length > 0 && (
        <PlacementRecommendationsCard placements={analysis.placements} />
      )}
      {aiSuggestions.length > 0 && <KeywordSuggestionsCard suggestions={aiSuggestions} />}
    </div>
  )
}

function KeywordMatchCard({
  analysis,
}: {
  analysis: KeywordAnalysis
}) {
  const strokeColor = analysis.matchPercentage >= 80
    ? '#22c55e'
    : analysis.matchPercentage >= 60
    ? '#eab308'
    : '#ef4444'

  return (
    <div className="rounded-lg bg-white p-6 shadow">
      <h3 className="mb-4 text-lg font-medium text-gray-900">Keyword Match</h3>
      <div className="flex items-center justify-center">
        <div className="relative h-32 w-32">
          <svg className="h-full w-full -rotate-90 transform">
            <circle cx="64" cy="64" r="56" fill="none" stroke="#e5e7eb" strokeWidth="12" />
            <circle
              cx="64"
              cy="64"
              r="56"
              fill="none"
              stroke={strokeColor}
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
      <p className="mt-4 text-center text-sm text-gray-500">
        {analysis.foundKeywords.length} of {analysis.foundKeywords.length + analysis.missingKeywords.length} keywords
        found
      </p>
    </div>
  )
}

function KeywordCollectionCard({
  title,
  icon,
  keywords,
  emptyMessage,
  variant,
}: {
  title: string
  icon: React.ReactNode
  keywords: string[]
  emptyMessage: string
  variant: 'found' | 'missing'
}) {
  const pillClassName = variant === 'found'
    ? 'bg-green-100 text-green-800'
    : 'bg-red-100 text-red-800'

  return (
    <div className="rounded-lg bg-white p-6 shadow">
      <h3 className="mb-4 flex items-center text-lg font-medium text-gray-900">
        {icon}
        {title} ({keywords.length})
      </h3>
      <div className="flex flex-wrap gap-2">
        {keywords.length > 0 ? (
          keywords.map((keyword) => (
            <span
              key={keyword}
              className={cn('inline-flex items-center rounded-full px-3 py-1 text-sm', pillClassName)}
            >
              {keyword}
            </span>
          ))
        ) : (
          <p className="text-sm text-gray-500">{emptyMessage}</p>
        )}
      </div>
    </div>
  )
}

function MissingKeywordsCard({
  analysis,
  aiSuggestions,
  isGettingSuggestions,
  onGetSuggestions,
}: {
  analysis: KeywordAnalysis
  aiSuggestions: string[]
  isGettingSuggestions: boolean
  onGetSuggestions: () => Promise<void>
}) {
  return (
    <div className="rounded-lg bg-white p-6 shadow">
      <KeywordCollectionCard
        title="Missing Keywords"
        icon={<XCircle className="mr-2 h-5 w-5 text-red-500" />}
        keywords={analysis.missingKeywords}
        emptyMessage="No missing keywords - great job!"
        variant="missing"
      />

      {analysis.missingKeywords.length > 0 && (
        <div className="mt-4">
          <button
            onClick={() => void onGetSuggestions()}
            disabled={isGettingSuggestions}
            className="inline-flex items-center rounded-md bg-emerald-600 px-4 py-2 text-white hover:bg-emerald-700 disabled:opacity-50"
          >
            {isGettingSuggestions ? (
              <>
                <InlineSpinner />
                Getting Suggestions...
              </>
            ) : (
              <>
                <Sparkles className="mr-2 h-4 w-4" />
                {aiSuggestions.length > 0 ? 'Refresh AI Suggestions' : 'Get AI Suggestions'}
              </>
            )}
          </button>
        </div>
      )}
    </div>
  )
}

function PlacementRecommendationsCard({
  placements,
}: {
  placements: Record<string, string>
}) {
  return (
    <div className="rounded-lg bg-white p-6 shadow">
      <h3 className="mb-4 text-lg font-medium text-gray-900">Placement Recommendations</h3>
      <ul className="space-y-3">
        {Object.entries(placements).map(([keyword, placement]) => (
          <li key={keyword} className="flex items-start gap-3 text-sm">
            <span className="min-w-[120px] font-medium text-gray-900">{keyword}:</span>
            <span className="text-gray-600">{placement}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function KeywordSuggestionsCard({
  suggestions,
}: {
  suggestions: string[]
}) {
  return (
    <div className="rounded-lg bg-white p-6 shadow">
      <h3 className="mb-4 text-lg font-medium text-gray-900">AI Optimization Suggestions</h3>
      <ul className="space-y-3 rounded-md bg-emerald-50 p-4 text-sm text-gray-700">
        {suggestions.map((suggestion) => (
          <li key={suggestion} className="flex items-start gap-2">
            <Sparkles className="mt-0.5 h-4 w-4 flex-shrink-0 text-emerald-600" />
            <span>{suggestion}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function KeywordGapEmptyState() {
  return (
    <div className="rounded-lg bg-white p-12 text-center shadow">
      <FileSearch className="mx-auto h-16 w-16 text-gray-300" />
      <h3 className="mt-4 text-lg font-medium text-gray-500">No Analysis Yet</h3>
      <p className="mt-2 text-sm text-gray-400">
        Provide your resume and job description, then click &quot;Analyze Keyword Gap&quot; to see which keywords you
        are missing.
      </p>
    </div>
  )
}

function useKeywordGapTabController() {
  const [state, setState] = useState(INITIAL_KEYWORD_GAP_TAB_STATE)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const setResumeText = useCallback((resumeText: string) => {
    setState((current) => ({ ...current, resumeText }))
  }, [])

  const setJobDescription = useCallback((jobDescription: string) => {
    setState((current) => ({ ...current, jobDescription }))
  }, [])

  const handleFileUpload = useCallback(async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) {
      return
    }

    try {
      const result = await resumesApi.upload(file)
      setState((current) => ({
        ...current,
        resumeText: result.content,
        error: null,
      }))
    } catch (error) {
      console.error('Failed to upload file:', error)
      setState((current) => ({
        ...current,
        error: 'Failed to parse file. Please try pasting your resume text instead.',
      }))
    }
  }, [])

  const analyzeKeywords = useCallback(async () => {
    const trimmedResumeText = state.resumeText.trim()
    const trimmedJobDescription = state.jobDescription.trim()

    if (!trimmedResumeText || !trimmedJobDescription) {
      setState((current) => ({
        ...current,
        error: 'Please provide both resume content and job description',
      }))
      return
    }

    setState((current) => ({
      ...current,
      isAnalyzing: true,
      error: null,
      aiSuggestions: [],
    }))

    try {
      const result = await resumesApi.analyzeContent(trimmedResumeText, trimmedJobDescription)
      const jobKeywords = extractKeywordsFromText(trimmedJobDescription)
      const resumeKeywordsLower = (result.keyword_matches || []).map((keyword) => keyword.toLowerCase())

      const foundKeywords = jobKeywords.filter((keyword) =>
        resumeKeywordsLower.some(
          (resumeKeyword) =>
            resumeKeyword.includes(keyword.toLowerCase()) ||
            keyword.toLowerCase().includes(resumeKeyword)
        )
      )
      const missingKeywords = result.missing_keywords || jobKeywords.filter(
        (keyword) =>
          !resumeKeywordsLower.some(
            (resumeKeyword) =>
              resumeKeyword.includes(keyword.toLowerCase()) ||
              keyword.toLowerCase().includes(resumeKeyword)
          )
      )
      const placements = missingKeywords.slice(0, 10).reduce<Record<string, string>>((accumulator, keyword) => {
        accumulator[keyword] = getSuggestedPlacement(keyword)
        return accumulator
      }, {})
      const matchPercentage = jobKeywords.length > 0
        ? Math.round((foundKeywords.length / jobKeywords.length) * 100)
        : 0

      setState((current) => ({
        ...current,
        analysis: {
          matchPercentage,
          foundKeywords: result.keyword_matches || foundKeywords,
          missingKeywords,
          placements,
        },
        isAnalyzing: false,
      }))
    } catch (error) {
      console.error('Failed to analyze keywords:', error)
      setState((current) => ({
        ...current,
        isAnalyzing: false,
        error: 'Failed to analyze keywords. Please try again.',
      }))
    }
  }, [state.jobDescription, state.resumeText])

  const getAISuggestions = useCallback(async () => {
    if (!state.analysis || state.analysis.missingKeywords.length === 0) {
      return
    }

    setState((current) => ({
      ...current,
      isGettingSuggestions: true,
      error: null,
    }))

    try {
      const result = await aiApi.optimizeResume(state.resumeText, state.jobDescription)
      setState((current) => ({
        ...current,
        aiSuggestions: result.suggestions,
        isGettingSuggestions: false,
      }))
    } catch (error) {
      console.error('Failed to get AI suggestions:', error)
      setState((current) => ({
        ...current,
        isGettingSuggestions: false,
        error: 'Failed to get AI suggestions. Please try again.',
      }))
    }
  }, [state.analysis, state.jobDescription, state.resumeText])

  return {
    ...state,
    fileInputRef,
    setResumeText,
    setJobDescription,
    handleFileUpload,
    analyzeKeywords,
    getAISuggestions,
  }
}

// =============================================================================
// Templates Tab
// =============================================================================

interface ResumeBullet {
  id: string
  text: string
}

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
    bullets: ResumeBullet[]
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

type TemplateSectionId = 'contact' | 'summary' | 'experience' | 'education' | 'skills'
type ResumeExperienceEntry = ResumeFormData['experience'][number]
type ResumeEducationEntry = ResumeFormData['education'][number]
type TemplateSaveMessage = { type: 'success' | 'error'; text: string }

const TEMPLATE_SECTIONS: TemplateSectionId[] = ['contact', 'summary', 'experience', 'education', 'skills']

interface TemplatesTabState {
  selectedTemplate: TemplateId
  formData: ResumeFormData
  activeSection: TemplateSectionId
  isSaving: boolean
  saveMessage: TemplateSaveMessage | null
}

function createInitialFormData(): ResumeFormData {
  return {
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
}

function createResumeBullet(): ResumeBullet {
  return {
    id: crypto.randomUUID(),
    text: '',
  }
}

function createExperienceEntry(): ResumeExperienceEntry {
  return {
    id: crypto.randomUUID(),
    company: '',
    position: '',
    location: '',
    startDate: '',
    endDate: '',
    current: false,
    bullets: [createResumeBullet()],
  }
}

function createEducationEntry(): ResumeEducationEntry {
  return {
    id: crypto.randomUUID(),
    school: '',
    degree: '',
    field: '',
    graduationDate: '',
    gpa: '',
  }
}

const INITIAL_TEMPLATES_TAB_STATE: TemplatesTabState = {
  selectedTemplate: 'professional',
  formData: createInitialFormData(),
  activeSection: 'contact',
  isSaving: false,
  saveMessage: null,
}

function buildResumeContent(formData: ResumeFormData): string {
  const lines: string[] = []

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

  if (formData.summary) {
    lines.push('PROFESSIONAL SUMMARY')
    lines.push('-'.repeat(50))
    lines.push(formData.summary)
    lines.push('')
  }

  if (formData.experience.length > 0) {
    lines.push('EXPERIENCE')
    lines.push('-'.repeat(50))

    formData.experience.forEach((experience) => {
      if (!experience.company && !experience.position) {
        return
      }

      lines.push(`${experience.position}${experience.position && experience.company ? ' | ' : ''}${experience.company}`)

      const dateLocation = [
        experience.startDate && experience.endDate
          ? `${experience.startDate} - ${experience.current ? 'Present' : experience.endDate}`
          : '',
        experience.location,
      ]
        .filter(Boolean)
        .join(' | ')

      if (dateLocation) {
        lines.push(dateLocation)
      }

      experience.bullets
        .map((bullet) => bullet.text.trim())
        .filter(Boolean)
        .forEach((bullet) => {
          lines.push(`  * ${bullet}`)
        })
      lines.push('')
    })
  }

  if (formData.education.length > 0) {
    lines.push('EDUCATION')
    lines.push('-'.repeat(50))

    formData.education.forEach((education) => {
      if (!education.school && !education.degree) {
        return
      }

      lines.push(`${education.degree}${education.field ? ` in ${education.field}` : ''}`)
      lines.push(
        `${education.school}${education.graduationDate ? ` | ${education.graduationDate}` : ''}${education.gpa ? ` | GPA: ${education.gpa}` : ''}`
      )
      lines.push('')
    })
  }

  const hasSkills = Object.values(formData.skills).some((skills) => skills.length > 0)
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

function downloadTextFile(fileName: string, content: string) {
  const blob = new Blob([content], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = fileName
  link.click()
  URL.revokeObjectURL(url)
}

function TemplatesTab() {
  const {
    selectedTemplate,
    formData,
    activeSection,
    isSaving,
    saveMessage,
    previewContent,
    selectTemplate,
    setActiveSection,
    updateContact,
    updateSummary,
    addExperience,
    updateExperienceField,
    removeExperience,
    updateExperienceBullet,
    addExperienceBullet,
    removeExperienceBullet,
    addEducation,
    updateEducation,
    removeEducation,
    updateSkills,
    copyPreview,
    downloadPreview,
    saveToProfile,
  } = useTemplatesTabController()

  return (
    <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
      <TemplateSelectionPanel
        selectedTemplate={selectedTemplate}
        onSelectTemplate={selectTemplate}
      />
      <TemplateBuilderPanel
        activeSection={activeSection}
        formData={formData}
        onActiveSectionChange={setActiveSection}
        onContactChange={updateContact}
        onSummaryChange={updateSummary}
        onAddExperience={addExperience}
        onExperienceFieldChange={updateExperienceField}
        onRemoveExperience={removeExperience}
        onExperienceBulletChange={updateExperienceBullet}
        onAddExperienceBullet={addExperienceBullet}
        onRemoveExperienceBullet={removeExperienceBullet}
        onAddEducation={addEducation}
        onEducationChange={updateEducation}
        onRemoveEducation={removeEducation}
        onSkillsChange={updateSkills}
      />
      <TemplatePreviewPanel
        selectedTemplate={selectedTemplate}
        previewContent={previewContent}
        isSaving={isSaving}
        saveMessage={saveMessage}
        onCopy={copyPreview}
        onDownload={downloadPreview}
        onSave={saveToProfile}
      />
    </div>
  )
}

function TemplateSelectionPanel({
  selectedTemplate,
  onSelectTemplate,
}: {
  selectedTemplate: TemplateId
  onSelectTemplate: (templateId: TemplateId) => void
}) {
  return (
    <div className="space-y-6 xl:col-span-1">
      <div className="rounded-lg bg-white p-6 shadow">
        <h3 className="mb-4 text-lg font-medium text-gray-900">Select Template</h3>
        <div className="space-y-3">
          {TEMPLATES.map((template) => (
            <button
              key={template.id}
              onClick={() => onSelectTemplate(template.id)}
              className={cn(
                'w-full rounded-lg border-2 p-4 text-left transition-all',
                selectedTemplate === template.id
                  ? 'border-primary-600 bg-primary-50'
                  : 'border-gray-200 hover:border-gray-300'
              )}
            >
              <div className="flex items-center gap-3">
                <div className={cn('h-3 w-3 rounded-full', template.color)} />
                <span className="font-medium text-gray-900">{template.name}</span>
              </div>
              <p className="mt-1 text-sm text-gray-500">{template.description}</p>
              <div className="mt-2 flex flex-wrap gap-1">
                {template.features.map((feature) => (
                  <span
                    key={feature}
                    className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600"
                  >
                    {feature}
                  </span>
                ))}
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

function TemplateBuilderPanel({
  activeSection,
  formData,
  onActiveSectionChange,
  onContactChange,
  onSummaryChange,
  onAddExperience,
  onExperienceFieldChange,
  onRemoveExperience,
  onExperienceBulletChange,
  onAddExperienceBullet,
  onRemoveExperienceBullet,
  onAddEducation,
  onEducationChange,
  onRemoveEducation,
  onSkillsChange,
}: {
  activeSection: TemplateSectionId
  formData: ResumeFormData
  onActiveSectionChange: (section: TemplateSectionId) => void
  onContactChange: (field: keyof ResumeFormData['contact'], value: string) => void
  onSummaryChange: (value: string) => void
  onAddExperience: () => void
  onExperienceFieldChange: (
    id: string,
    field: keyof Omit<ResumeExperienceEntry, 'id' | 'bullets'>,
    value: string | boolean
  ) => void
  onRemoveExperience: (id: string) => void
  onExperienceBulletChange: (experienceId: string, bulletId: string, value: string) => void
  onAddExperienceBullet: (experienceId: string) => void
  onRemoveExperienceBullet: (experienceId: string, bulletId: string) => void
  onAddEducation: () => void
  onEducationChange: (
    id: string,
    field: keyof Omit<ResumeEducationEntry, 'id'>,
    value: string
  ) => void
  onRemoveEducation: (id: string) => void
  onSkillsChange: (category: keyof ResumeFormData['skills'], value: string[]) => void
}) {
  return (
    <div className="space-y-6 xl:col-span-1">
      <div className="rounded-lg bg-white shadow">
        <TemplateSectionTabs
          activeSection={activeSection}
          onActiveSectionChange={onActiveSectionChange}
        />
        <div className="p-6">
          <TemplateFormSectionContent
            activeSection={activeSection}
            formData={formData}
            onContactChange={onContactChange}
            onSummaryChange={onSummaryChange}
            onAddExperience={onAddExperience}
            onExperienceFieldChange={onExperienceFieldChange}
            onRemoveExperience={onRemoveExperience}
            onExperienceBulletChange={onExperienceBulletChange}
            onAddExperienceBullet={onAddExperienceBullet}
            onRemoveExperienceBullet={onRemoveExperienceBullet}
            onAddEducation={onAddEducation}
            onEducationChange={onEducationChange}
            onRemoveEducation={onRemoveEducation}
            onSkillsChange={onSkillsChange}
          />
        </div>
      </div>
    </div>
  )
}

function TemplateSectionTabs({
  activeSection,
  onActiveSectionChange,
}: {
  activeSection: TemplateSectionId
  onActiveSectionChange: (section: TemplateSectionId) => void
}) {
  return (
    <div className="border-b border-gray-200">
      <nav className="-mb-px flex overflow-x-auto">
        {TEMPLATE_SECTIONS.map((section) => (
          <button
            key={section}
            onClick={() => onActiveSectionChange(section)}
            className={cn(
              'whitespace-nowrap border-b-2 px-4 py-3 text-sm font-medium',
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
  )
}

function TemplateFormSectionContent({
  activeSection,
  formData,
  onContactChange,
  onSummaryChange,
  onAddExperience,
  onExperienceFieldChange,
  onRemoveExperience,
  onExperienceBulletChange,
  onAddExperienceBullet,
  onRemoveExperienceBullet,
  onAddEducation,
  onEducationChange,
  onRemoveEducation,
  onSkillsChange,
}: {
  activeSection: TemplateSectionId
  formData: ResumeFormData
  onContactChange: (field: keyof ResumeFormData['contact'], value: string) => void
  onSummaryChange: (value: string) => void
  onAddExperience: () => void
  onExperienceFieldChange: (
    id: string,
    field: keyof Omit<ResumeExperienceEntry, 'id' | 'bullets'>,
    value: string | boolean
  ) => void
  onRemoveExperience: (id: string) => void
  onExperienceBulletChange: (experienceId: string, bulletId: string, value: string) => void
  onAddExperienceBullet: (experienceId: string) => void
  onRemoveExperienceBullet: (experienceId: string, bulletId: string) => void
  onAddEducation: () => void
  onEducationChange: (
    id: string,
    field: keyof Omit<ResumeEducationEntry, 'id'>,
    value: string
  ) => void
  onRemoveEducation: (id: string) => void
  onSkillsChange: (category: keyof ResumeFormData['skills'], value: string[]) => void
}) {
  if (activeSection === 'contact') {
    return (
      <ContactFormSection
        contact={formData.contact}
        onContactChange={onContactChange}
      />
    )
  }

  if (activeSection === 'summary') {
    return (
      <SummaryFormSection
        summary={formData.summary}
        onSummaryChange={onSummaryChange}
      />
    )
  }

  if (activeSection === 'experience') {
    return (
      <ExperienceFormSection
        experience={formData.experience}
        onAddExperience={onAddExperience}
        onExperienceFieldChange={onExperienceFieldChange}
        onRemoveExperience={onRemoveExperience}
        onExperienceBulletChange={onExperienceBulletChange}
        onAddExperienceBullet={onAddExperienceBullet}
        onRemoveExperienceBullet={onRemoveExperienceBullet}
      />
    )
  }

  if (activeSection === 'education') {
    return (
      <EducationFormSection
        education={formData.education}
        onAddEducation={onAddEducation}
        onEducationChange={onEducationChange}
        onRemoveEducation={onRemoveEducation}
      />
    )
  }

  return (
    <SkillsFormSection
      skills={formData.skills}
      onSkillsChange={onSkillsChange}
    />
  )
}

function ContactFormSection({
  contact,
  onContactChange,
}: {
  contact: ResumeFormData['contact']
  onContactChange: (field: keyof ResumeFormData['contact'], value: string) => void
}) {
  return (
    <div className="space-y-4">
      <TemplateTextField
        id="contact-name"
        label="Full Name"
        value={contact.name}
        placeholder="John Doe"
        onChange={(value) => onContactChange('name', value)}
      />
      <div className="grid grid-cols-2 gap-4">
        <TemplateTextField
          id="contact-email"
          label="Email"
          type="email"
          value={contact.email}
          placeholder="john@example.com"
          onChange={(value) => onContactChange('email', value)}
        />
        <TemplateTextField
          id="contact-phone"
          label="Phone"
          type="tel"
          value={contact.phone}
          placeholder="(555) 123-4567"
          onChange={(value) => onContactChange('phone', value)}
        />
      </div>
      <TemplateTextField
        id="contact-location"
        label="Location"
        value={contact.location}
        placeholder="San Francisco, CA"
        onChange={(value) => onContactChange('location', value)}
      />
      <TemplateTextField
        id="contact-linkedin"
        label="LinkedIn"
        type="url"
        value={contact.linkedin}
        placeholder="linkedin.com/in/johndoe"
        onChange={(value) => onContactChange('linkedin', value)}
      />
      <TemplateTextField
        id="contact-github"
        label="GitHub"
        type="url"
        value={contact.github}
        placeholder="github.com/johndoe"
        onChange={(value) => onContactChange('github', value)}
      />
      <TemplateTextField
        id="contact-portfolio"
        label="Portfolio"
        type="url"
        value={contact.portfolio}
        placeholder="johndoe.com"
        onChange={(value) => onContactChange('portfolio', value)}
      />
    </div>
  )
}

function SummaryFormSection({
  summary,
  onSummaryChange,
}: {
  summary: string
  onSummaryChange: (value: string) => void
}) {
  return (
    <div>
      <TemplateTextArea
        id="summary-text"
        label="Professional Summary"
        rows={6}
        value={summary}
        placeholder="Write a brief professional summary highlighting your key qualifications, experience, and career goals..."
        onChange={onSummaryChange}
      />
      <p className="mt-2 text-xs text-gray-500">
        Aim for 3-5 sentences that highlight your value proposition.
      </p>
    </div>
  )
}

function ExperienceFormSection({
  experience,
  onAddExperience,
  onExperienceFieldChange,
  onRemoveExperience,
  onExperienceBulletChange,
  onAddExperienceBullet,
  onRemoveExperienceBullet,
}: {
  experience: ResumeFormData['experience']
  onAddExperience: () => void
  onExperienceFieldChange: (
    id: string,
    field: keyof Omit<ResumeExperienceEntry, 'id' | 'bullets'>,
    value: string | boolean
  ) => void
  onRemoveExperience: (id: string) => void
  onExperienceBulletChange: (experienceId: string, bulletId: string, value: string) => void
  onAddExperienceBullet: (experienceId: string) => void
  onRemoveExperienceBullet: (experienceId: string, bulletId: string) => void
}) {
  return (
    <div className="space-y-6">
      {experience.map((entry, index) => (
        <ExperienceEditorCard
          key={entry.id}
          experience={entry}
          index={index}
          onFieldChange={onExperienceFieldChange}
          onRemove={onRemoveExperience}
          onBulletChange={onExperienceBulletChange}
          onAddBullet={onAddExperienceBullet}
          onRemoveBullet={onRemoveExperienceBullet}
        />
      ))}
      <button
        onClick={onAddExperience}
        className="w-full rounded-lg border-2 border-dashed border-gray-300 py-2 text-gray-500 hover:border-primary-400 hover:text-primary-600"
      >
        <Plus className="mr-1 inline h-4 w-4" />
        Add Experience
      </button>
    </div>
  )
}

function ExperienceEditorCard({
  experience,
  index,
  onFieldChange,
  onRemove,
  onBulletChange,
  onAddBullet,
  onRemoveBullet,
}: {
  experience: ResumeExperienceEntry
  index: number
  onFieldChange: (
    id: string,
    field: keyof Omit<ResumeExperienceEntry, 'id' | 'bullets'>,
    value: string | boolean
  ) => void
  onRemove: (id: string) => void
  onBulletChange: (experienceId: string, bulletId: string, value: string) => void
  onAddBullet: (experienceId: string) => void
  onRemoveBullet: (experienceId: string, bulletId: string) => void
}) {
  return (
    <div className="rounded-lg border border-gray-200 p-4">
      <div className="mb-4 flex items-center justify-between">
        <h4 className="font-medium text-gray-900">Experience {index + 1}</h4>
        <button
          onClick={() => onRemove(experience.id)}
          className="text-red-500 hover:text-red-700"
          aria-label="Remove experience"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>

      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <TemplateTextField
            id={`exp-position-${experience.id}`}
            label="Position"
            value={experience.position}
            placeholder="Software Engineer"
            compact
            onChange={(value) => onFieldChange(experience.id, 'position', value)}
          />
          <TemplateTextField
            id={`exp-company-${experience.id}`}
            label="Company"
            value={experience.company}
            placeholder="Acme Inc."
            compact
            onChange={(value) => onFieldChange(experience.id, 'company', value)}
          />
        </div>
        <TemplateTextField
          id={`exp-location-${experience.id}`}
          label="Location"
          value={experience.location}
          placeholder="San Francisco, CA"
          compact
          onChange={(value) => onFieldChange(experience.id, 'location', value)}
        />
        <div className="grid grid-cols-2 gap-3">
          <TemplateTextField
            id={`exp-start-${experience.id}`}
            label="Start Date"
            value={experience.startDate}
            placeholder="Jan 2022"
            compact
            onChange={(value) => onFieldChange(experience.id, 'startDate', value)}
          />
          <TemplateTextField
            id={`exp-end-${experience.id}`}
            label="End Date"
            value={experience.endDate}
            placeholder="Present"
            compact
            disabled={experience.current}
            onChange={(value) => onFieldChange(experience.id, 'endDate', value)}
          />
        </div>
        <div className="flex items-center gap-2">
          <input
            id={`exp-current-${experience.id}`}
            type="checkbox"
            checked={experience.current}
            onChange={(event) => onFieldChange(experience.id, 'current', event.target.checked)}
            className="rounded border-gray-300"
          />
          <label htmlFor={`exp-current-${experience.id}`} className="text-sm text-gray-600">
            Currently working here
          </label>
        </div>
        <div>
          <div className="mb-1 block text-xs font-medium text-gray-600">Bullet Points</div>
          <div className="space-y-2">
            {experience.bullets.map((bullet) => (
              <div key={bullet.id} className="flex gap-2">
                <input
                  type="text"
                  value={bullet.text}
                  onChange={(event) => onBulletChange(experience.id, bullet.id, event.target.value)}
                  className="flex-1 rounded-md border border-gray-300 px-2 py-1.5 text-sm"
                  placeholder="Describe your achievement..."
                />
                <button
                  onClick={() => onRemoveBullet(experience.id, bullet.id)}
                  className="text-gray-400 hover:text-red-500"
                  aria-label="Remove bullet point"
                >
                  <XCircle className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
          <button
            onClick={() => onAddBullet(experience.id)}
            className="mt-2 text-sm text-primary-600 hover:text-primary-700"
          >
            + Add bullet point
          </button>
        </div>
      </div>
    </div>
  )
}

function EducationFormSection({
  education,
  onAddEducation,
  onEducationChange,
  onRemoveEducation,
}: {
  education: ResumeFormData['education']
  onAddEducation: () => void
  onEducationChange: (
    id: string,
    field: keyof Omit<ResumeEducationEntry, 'id'>,
    value: string
  ) => void
  onRemoveEducation: (id: string) => void
}) {
  return (
    <div className="space-y-6">
      {education.map((entry, index) => (
        <EducationEditorCard
          key={entry.id}
          education={entry}
          index={index}
          onEducationChange={onEducationChange}
          onRemove={onRemoveEducation}
        />
      ))}
      <button
        onClick={onAddEducation}
        className="w-full rounded-lg border-2 border-dashed border-gray-300 py-2 text-gray-500 hover:border-primary-400 hover:text-primary-600"
      >
        <Plus className="mr-1 inline h-4 w-4" />
        Add Education
      </button>
    </div>
  )
}

function EducationEditorCard({
  education,
  index,
  onEducationChange,
  onRemove,
}: {
  education: ResumeEducationEntry
  index: number
  onEducationChange: (
    id: string,
    field: keyof Omit<ResumeEducationEntry, 'id'>,
    value: string
  ) => void
  onRemove: (id: string) => void
}) {
  return (
    <div className="rounded-lg border border-gray-200 p-4">
      <div className="mb-4 flex items-center justify-between">
        <h4 className="font-medium text-gray-900">Education {index + 1}</h4>
        <button
          onClick={() => onRemove(education.id)}
          className="text-red-500 hover:text-red-700"
          aria-label="Remove education"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>
      <div className="space-y-3">
        <TemplateTextField
          id={`edu-school-${education.id}`}
          label="School"
          value={education.school}
          placeholder="University of California"
          compact
          onChange={(value) => onEducationChange(education.id, 'school', value)}
        />
        <div className="grid grid-cols-2 gap-3">
          <TemplateTextField
            id={`edu-degree-${education.id}`}
            label="Degree"
            value={education.degree}
            placeholder="Bachelor of Science"
            compact
            onChange={(value) => onEducationChange(education.id, 'degree', value)}
          />
          <TemplateTextField
            id={`edu-field-${education.id}`}
            label="Field of Study"
            value={education.field}
            placeholder="Computer Science"
            compact
            onChange={(value) => onEducationChange(education.id, 'field', value)}
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <TemplateTextField
            id={`edu-grad-${education.id}`}
            label="Graduation Date"
            value={education.graduationDate}
            placeholder="May 2023"
            compact
            onChange={(value) => onEducationChange(education.id, 'graduationDate', value)}
          />
          <TemplateTextField
            id={`edu-gpa-${education.id}`}
            label="GPA (Optional)"
            value={education.gpa}
            placeholder="3.8"
            compact
            onChange={(value) => onEducationChange(education.id, 'gpa', value)}
          />
        </div>
      </div>
    </div>
  )
}

function SkillsFormSection({
  skills,
  onSkillsChange,
}: {
  skills: ResumeFormData['skills']
  onSkillsChange: (category: keyof ResumeFormData['skills'], value: string[]) => void
}) {
  return (
    <div className="space-y-6">
      <div>
        <div className="mb-2 block text-sm font-medium text-gray-700">Technical Skills</div>
        <SkillInput
          skills={skills.technical}
          onChange={(nextSkills) => onSkillsChange('technical', nextSkills)}
          placeholder="e.g., JavaScript, Python, React"
        />
      </div>
      <div>
        <div className="mb-2 block text-sm font-medium text-gray-700">Soft Skills</div>
        <SkillInput
          skills={skills.soft}
          onChange={(nextSkills) => onSkillsChange('soft', nextSkills)}
          placeholder="e.g., Leadership, Communication"
        />
      </div>
      <div>
        <div className="mb-2 block text-sm font-medium text-gray-700">Languages</div>
        <SkillInput
          skills={skills.languages}
          onChange={(nextSkills) => onSkillsChange('languages', nextSkills)}
          placeholder="e.g., English (Native), Spanish (Fluent)"
        />
      </div>
      <div>
        <div className="mb-2 block text-sm font-medium text-gray-700">Certifications</div>
        <SkillInput
          skills={skills.certifications}
          onChange={(nextSkills) => onSkillsChange('certifications', nextSkills)}
          placeholder="e.g., AWS Solutions Architect"
        />
      </div>
    </div>
  )
}

function TemplatePreviewPanel({
  selectedTemplate,
  previewContent,
  isSaving,
  saveMessage,
  onCopy,
  onDownload,
  onSave,
}: {
  selectedTemplate: TemplateId
  previewContent: string
  isSaving: boolean
  saveMessage: TemplateSaveMessage | null
  onCopy: () => void
  onDownload: () => void
  onSave: () => Promise<void>
}) {
  return (
    <div className="space-y-6 xl:col-span-1">
      <div className="rounded-lg bg-white p-6 shadow">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-medium text-gray-900">Preview</h3>
          <div className="flex gap-2">
            <button
              onClick={onCopy}
              className="inline-flex items-center rounded-md border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-50"
              title="Copy to clipboard"
            >
              <Copy className="h-4 w-4" />
            </button>
            <button
              onClick={onDownload}
              className="inline-flex items-center rounded-md border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-50"
              title="Download as text"
            >
              <Download className="h-4 w-4" />
            </button>
          </div>
        </div>
        <TemplatePreviewSurface
          selectedTemplate={selectedTemplate}
          previewContent={previewContent}
        />
      </div>

      <button
        onClick={() => void onSave()}
        disabled={isSaving}
        className="inline-flex w-full items-center justify-center rounded-md bg-primary-600 px-4 py-3 text-white hover:bg-primary-700 disabled:opacity-50"
      >
        {isSaving ? (
          <>
            <InlineSpinner />
            Saving...
          </>
        ) : (
          <>
            <FileText className="mr-2 h-4 w-4" />
            Save to Profile
          </>
        )}
      </button>

      {saveMessage && <TemplateSaveMessageBanner message={saveMessage} />}
    </div>
  )
}

function TemplatePreviewSurface({
  selectedTemplate,
  previewContent,
}: {
  selectedTemplate: TemplateId
  previewContent: string
}) {
  return (
    <div
      className={cn(
        'min-h-[400px] max-h-[600px] overflow-y-auto rounded-lg border p-6',
        selectedTemplate === 'professional' && 'border-slate-300 bg-white',
        selectedTemplate === 'modern' && 'border-blue-200 bg-blue-50',
        selectedTemplate === 'technical' && 'border-emerald-200 bg-emerald-50',
        selectedTemplate === 'executive' && 'border-purple-200 bg-purple-50',
        selectedTemplate === 'creative' && 'border-pink-200 bg-pink-50'
      )}
    >
      <pre className="whitespace-pre-wrap font-mono text-sm text-gray-700">
        {previewContent || 'Fill in the form to see your resume preview...'}
      </pre>
    </div>
  )
}

function TemplateSaveMessageBanner({
  message,
}: {
  message: TemplateSaveMessage
}) {
  return (
    <div
      className={cn(
        'rounded-md p-4',
        message.type === 'success' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
      )}
    >
      {message.text}
    </div>
  )
}

function TemplateTextField({
  id,
  label,
  value,
  onChange,
  type = 'text',
  placeholder,
  disabled = false,
  compact = false,
}: {
  id: string
  label: string
  value: string
  onChange: (value: string) => void
  type?: React.HTMLInputTypeAttribute
  placeholder: string
  disabled?: boolean
  compact?: boolean
}) {
  return (
    <div>
      <label
        htmlFor={id}
        className={cn(
          compact ? 'text-xs text-gray-600' : 'text-sm text-gray-700',
          'block font-medium'
        )}
      >
        {label}
      </label>
      <input
        id={id}
        type={type}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        className={cn(
          'mt-1 w-full rounded-md border border-gray-300',
          compact ? 'px-2 py-1.5 text-sm' : 'px-3 py-2',
          disabled && 'bg-gray-100'
        )}
        placeholder={placeholder}
      />
    </div>
  )
}

function TemplateTextArea({
  id,
  label,
  rows,
  value,
  placeholder,
  onChange,
}: {
  id: string
  label: string
  rows: number
  value: string
  placeholder: string
  onChange: (value: string) => void
}) {
  return (
    <div>
      <label htmlFor={id} className="mb-2 block text-sm font-medium text-gray-700">
        {label}
      </label>
      <textarea
        id={id}
        rows={rows}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-md border border-gray-300 px-3 py-2"
        placeholder={placeholder}
      />
    </div>
  )
}

function useTemplatesTabController() {
  const [state, setState] = useState(INITIAL_TEMPLATES_TAB_STATE)
  const previewContent = buildResumeContent(state.formData)

  const updateFormData = useCallback((updater: (formData: ResumeFormData) => ResumeFormData) => {
    setState((current) => ({
      ...current,
      formData: updater(current.formData),
    }))
  }, [])

  const selectTemplate = useCallback((selectedTemplate: TemplateId) => {
    setState((current) => ({ ...current, selectedTemplate }))
  }, [])

  const setActiveSection = useCallback((activeSection: TemplateSectionId) => {
    setState((current) => ({ ...current, activeSection }))
  }, [])

  const updateContact = useCallback((field: keyof ResumeFormData['contact'], value: string) => {
    updateFormData((formData) => ({
      ...formData,
      contact: { ...formData.contact, [field]: value },
    }))
  }, [updateFormData])

  const updateSummary = useCallback((summary: string) => {
    updateFormData((formData) => ({
      ...formData,
      summary,
    }))
  }, [updateFormData])

  const addExperience = useCallback(() => {
    updateFormData((formData) => ({
      ...formData,
      experience: [...formData.experience, createExperienceEntry()],
    }))
  }, [updateFormData])

  const updateExperienceField = useCallback((
    id: string,
    field: keyof Omit<ResumeExperienceEntry, 'id' | 'bullets'>,
    value: string | boolean
  ) => {
    updateFormData((formData) => ({
      ...formData,
      experience: formData.experience.map((experience) =>
        experience.id === id ? { ...experience, [field]: value } : experience
      ),
    }))
  }, [updateFormData])

  const removeExperience = useCallback((id: string) => {
    updateFormData((formData) => ({
      ...formData,
      experience: formData.experience.filter((experience) => experience.id !== id),
    }))
  }, [updateFormData])

  const updateExperienceBullet = useCallback((experienceId: string, bulletId: string, value: string) => {
    updateFormData((formData) => ({
      ...formData,
      experience: formData.experience.map((experience) =>
        experience.id === experienceId
          ? {
              ...experience,
              bullets: experience.bullets.map((bullet) =>
                bullet.id === bulletId ? { ...bullet, text: value } : bullet
              ),
            }
          : experience
      ),
    }))
  }, [updateFormData])

  const addExperienceBullet = useCallback((experienceId: string) => {
    updateFormData((formData) => ({
      ...formData,
      experience: formData.experience.map((experience) =>
        experience.id === experienceId
          ? { ...experience, bullets: [...experience.bullets, createResumeBullet()] }
          : experience
      ),
    }))
  }, [updateFormData])

  const removeExperienceBullet = useCallback((experienceId: string, bulletId: string) => {
    updateFormData((formData) => ({
      ...formData,
      experience: formData.experience.map((experience) => {
        if (experience.id !== experienceId) {
          return experience
        }

        const bullets = experience.bullets.filter((bullet) => bullet.id !== bulletId)
        return {
          ...experience,
          bullets: bullets.length > 0 ? bullets : [createResumeBullet()],
        }
      }),
    }))
  }, [updateFormData])

  const addEducation = useCallback(() => {
    updateFormData((formData) => ({
      ...formData,
      education: [...formData.education, createEducationEntry()],
    }))
  }, [updateFormData])

  const updateEducation = useCallback((
    id: string,
    field: keyof Omit<ResumeEducationEntry, 'id'>,
    value: string
  ) => {
    updateFormData((formData) => ({
      ...formData,
      education: formData.education.map((education) =>
        education.id === id ? { ...education, [field]: value } : education
      ),
    }))
  }, [updateFormData])

  const removeEducation = useCallback((id: string) => {
    updateFormData((formData) => ({
      ...formData,
      education: formData.education.filter((education) => education.id !== id),
    }))
  }, [updateFormData])

  const updateSkills = useCallback((category: keyof ResumeFormData['skills'], value: string[]) => {
    updateFormData((formData) => ({
      ...formData,
      skills: { ...formData.skills, [category]: value },
    }))
  }, [updateFormData])

  const copyPreview = useCallback(() => {
    if (!previewContent.trim()) {
      return
    }

    void navigator.clipboard.writeText(previewContent)
  }, [previewContent])

  const downloadPreview = useCallback(() => {
    if (!previewContent.trim()) {
      return
    }

    downloadTextFile('resume.txt', previewContent)
  }, [previewContent])

  const saveToProfile = useCallback(async () => {
    if (!previewContent.trim()) {
      setState((current) => ({
        ...current,
        saveMessage: { type: 'error', text: 'Please fill in some resume details first' },
      }))
      return
    }

    setState((current) => ({
      ...current,
      isSaving: true,
      saveMessage: null,
    }))

    try {
      await resumesApi.create({
        version_name: `${TEMPLATES.find((template) => template.id === state.selectedTemplate)?.name} Template - ${new Date().toLocaleDateString()}`,
        content: previewContent,
      })
      setState((current) => ({
        ...current,
        isSaving: false,
        saveMessage: { type: 'success', text: 'Resume saved to your profile!' },
      }))
    } catch (error) {
      console.error('Failed to save resume:', error)
      setState((current) => ({
        ...current,
        isSaving: false,
        saveMessage: { type: 'error', text: 'Failed to save resume. Please try again.' },
      }))
    }
  }, [previewContent, state.selectedTemplate])

  return {
    ...state,
    previewContent,
    selectTemplate,
    setActiveSection,
    updateContact,
    updateSummary,
    addExperience,
    updateExperienceField,
    removeExperience,
    updateExperienceBullet,
    addExperienceBullet,
    removeExperienceBullet,
    addEducation,
    updateEducation,
    removeEducation,
    updateSkills,
    copyPreview,
    downloadPreview,
    saveToProfile,
  }
}

// =============================================================================
// Shared Components
// =============================================================================

function TabSpinner() {
  return (
    <div className="flex items-center justify-center py-12">
      <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-primary-600" />
    </div>
  )
}

function InlineSpinner() {
  return <div className="mr-2 h-4 w-4 animate-spin rounded-full border-b-2 border-white" />
}

function UploadResumeButton({
  fileInputRef,
  onChange,
  helperText,
}: {
  fileInputRef: React.RefObject<HTMLInputElement | null>
  onChange: (event: React.ChangeEvent<HTMLInputElement>) => Promise<void>
  helperText?: string
}) {
  return (
    <div className="flex gap-2">
      <button
        onClick={() => fileInputRef.current?.click()}
        className="inline-flex items-center rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
      >
        <Upload className="mr-2 h-4 w-4" />
        Upload File
      </button>
      <input
        ref={fileInputRef}
        type="file"
        accept=".txt,.pdf,.docx"
        onChange={(event) => void onChange(event)}
        className="hidden"
      />
      {helperText && (
        <span className="self-center text-xs text-gray-500">{helperText}</span>
      )}
    </div>
  )
}

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
            key={skill}
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
