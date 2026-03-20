'use client'

import {
  MessageSquare,
  Lightbulb,
  ChevronDown,
  ChevronUp,
  Play,
  Pause,
  RotateCcw,
  Shuffle,
  Save,
  Wand2,
  Building2,
  Target,
  Search,
  CheckCircle,
  AlertCircle,
  Clock,
  BookOpen,
  Star,
  Trash2,
  X,
  Copy,
  Check,
  Calendar,
  CalendarClock,
  ExternalLink,
  Video,
  MapPin,
  Users,
  Edit3,
  Plus,
} from 'lucide-react'
import { useEffect, useState, useMemo, useCallback, useRef, Suspense } from 'react'

import { AIMarkdown } from '@/components/AIMarkdown'
import { aiApi, resumesApi, starStoriesApi, companyResearchApi, interviewEventsApi } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { migrateLocalStorage } from '@/lib/localStorageMigration'
import { cn, generateId } from '@/lib/utils'

import type { StarStory as ApiStarStory, CompanyResearch as ApiCompanyResearch, InterviewEventResponse } from '@/lib/api'
import type { Resume } from '@/types'

// Loading skeleton for tab transitions
function TabLoadingSkeleton() {
  return (
    <div className="animate-pulse space-y-4">
      <div className="h-8 bg-[var(--line)] rounded-[var(--radius-md)] w-1/4" />
      <div className="h-48 bg-[var(--line)] rounded-[var(--radius-md)]" />
      <div className="h-48 bg-[var(--line)] rounded-[var(--radius-md)]" />
      <div className="h-48 bg-[var(--line)] rounded-[var(--radius-md)]" />
    </div>
  )
}

// ============================================================================
// Types
// ============================================================================

type TabType = 'questions' | 'star' | 'research' | 'practice' | 'events'

type QuestionCategory =
  | 'Behavioral'
  | 'Technical'
  | 'Situational'
  | 'Company/Role'
  | 'Career Goals'

interface Question {
  id: string
  category: QuestionCategory
  text: string
  tips: string[]
}

interface STARStory {
  id: number | string
  title: string
  situation: string
  task: string
  action: string
  result: string
  tags: string[]
  createdAt: string
}

interface CompanyResearch {
  id?: number
  companyName: string
  talkingPoints: string[]
  notes: string
  checklist: {
    id?: string
    text?: string
    label?: string
    done?: boolean
    checked?: boolean
  }[]
}

function apiStoryToLocal(s: ApiStarStory): STARStory {
  return {
    id: s.id,
    title: s.title,
    situation: s.situation,
    task: s.task,
    action: s.action,
    result: s.result,
    tags: s.tags ?? [],
    createdAt: s.created_at,
  }
}

function apiResearchToLocal(r: ApiCompanyResearch): CompanyResearch {
  return {
    id: r.id,
    companyName: r.company_name,
    talkingPoints: r.talking_points ?? [],
    notes: r.notes ?? '',
    checklist: (r.checklist ?? []).map((c) => ({
      text: c.text,
      label: c.text,
      done: c.done,
      checked: c.done,
    })),
  }
}

interface InterviewEventLocal {
  id: number
  jobApplicationId: number | null
  company: string
  position: string
  eventType: string
  scheduledDate: string
  scheduledTime: string | null
  durationMinutes: number | null
  location: string | null
  meetingLink: string | null
  interviewerNames: string[] | null
  notes: string | null
  isCompleted: boolean
  followUpDate: string | null
  followUpDone: boolean
  createdAt: string
  updatedAt: string
}

function apiEventToLocal(e: InterviewEventResponse): InterviewEventLocal {
  return {
    id: e.id,
    jobApplicationId: e.job_application_id,
    company: e.company,
    position: e.position,
    eventType: e.event_type,
    scheduledDate: e.scheduled_date,
    scheduledTime: e.scheduled_time,
    durationMinutes: e.duration_minutes,
    location: e.location,
    meetingLink: e.meeting_link,
    interviewerNames: e.interviewer_names,
    notes: e.notes,
    isCompleted: e.is_completed,
    followUpDate: e.follow_up_date,
    followUpDone: e.follow_up_done,
    createdAt: e.created_at,
    updatedAt: e.updated_at,
  }
}

function localEventToApi(
  e: Omit<InterviewEventLocal, 'id' | 'createdAt' | 'updatedAt'>
): Omit<InterviewEventResponse, 'id' | 'profile_id' | 'created_at' | 'updated_at'> {
  return {
    job_application_id: e.jobApplicationId,
    company: e.company,
    position: e.position,
    event_type: e.eventType,
    scheduled_date: e.scheduledDate,
    scheduled_time: e.scheduledTime,
    duration_minutes: e.durationMinutes,
    location: e.location,
    meeting_link: e.meetingLink,
    interviewer_names: e.interviewerNames,
    notes: e.notes,
    is_completed: e.isCompleted,
    follow_up_date: e.followUpDate,
    follow_up_done: e.followUpDone,
  }
}

const EVENT_TYPE_OPTIONS = [
  { value: 'phone_screen', label: 'Phone Screen' },
  { value: 'technical', label: 'Technical' },
  { value: 'behavioral', label: 'Behavioral' },
  { value: 'onsite', label: 'Onsite' },
  { value: 'panel', label: 'Panel' },
  { value: 'hr', label: 'HR' },
  { value: 'final', label: 'Final Round' },
  { value: 'follow_up', label: 'Follow Up' },
  { value: 'other', label: 'Other' },
]

function getCountdownText(dateStr: string): string {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const target = new Date(dateStr + 'T00:00:00')
  target.setHours(0, 0, 0, 0)
  const diffMs = target.getTime() - today.getTime()
  const diffDays = Math.round(diffMs / (1000 * 60 * 60 * 24))
  if (diffDays === 0) return 'Today!'
  if (diffDays === 1) return 'Tomorrow'
  if (diffDays > 1) return `In ${diffDays} days`
  if (diffDays === -1) return '1 day ago'
  return `${Math.abs(diffDays)} days ago`
}

interface PracticeSession {
  id: string
  questionId: string
  answer: string
  feedback: string | null
  score: number | null
  timeSpent: number
}

// ============================================================================
// Constants
// ============================================================================

const QUESTION_CATEGORIES: QuestionCategory[] = [
  'Behavioral',
  'Technical',
  'Situational',
  'Company/Role',
  'Career Goals',
]

const SAMPLE_QUESTIONS: Question[] = [
  // Behavioral
  {
    id: 'beh-1',
    category: 'Behavioral',
    text: 'Tell me about a time you had to work with a difficult team member.',
    tips: [
      'Focus on the resolution, not the conflict',
      'Show empathy and understanding',
      'Highlight what you learned from the experience',
    ],
  },
  {
    id: 'beh-2',
    category: 'Behavioral',
    text: 'Describe a situation where you had to meet a tight deadline.',
    tips: [
      'Explain your prioritization process',
      'Mention any tools or methods you used',
      'Share the outcome and what you learned',
    ],
  },
  {
    id: 'beh-3',
    category: 'Behavioral',
    text: 'Give an example of when you showed leadership.',
    tips: [
      'Leadership does not require a formal title',
      'Focus on how you influenced or motivated others',
      'Include measurable outcomes if possible',
    ],
  },
  {
    id: 'beh-4',
    category: 'Behavioral',
    text: 'Tell me about a time you failed and how you handled it.',
    tips: [
      'Be honest but choose a professional failure',
      'Focus on the lessons learned',
      'Show how you applied those lessons later',
    ],
  },
  {
    id: 'beh-5',
    category: 'Behavioral',
    text: 'Describe a time when you had to adapt to a significant change.',
    tips: [
      'Show flexibility and resilience',
      'Explain your thought process',
      'Highlight positive outcomes from the change',
    ],
  },
  // Technical
  {
    id: 'tech-1',
    category: 'Technical',
    text: 'Walk me through your approach to solving a complex technical problem.',
    tips: [
      'Start with understanding the problem',
      'Explain your debugging/analysis process',
      'Mention collaboration if applicable',
    ],
  },
  {
    id: 'tech-2',
    category: 'Technical',
    text: 'How do you stay current with new technologies and industry trends?',
    tips: [
      'Mention specific resources you use',
      'Share recent examples of learning',
      'Show enthusiasm for continuous learning',
    ],
  },
  {
    id: 'tech-3',
    category: 'Technical',
    text: 'Describe a project you are most proud of and your technical contribution.',
    tips: [
      'Choose a relevant project',
      'Explain technical decisions and tradeoffs',
      'Quantify impact if possible',
    ],
  },
  {
    id: 'tech-4',
    category: 'Technical',
    text: 'How do you ensure code quality in your work?',
    tips: [
      'Mention testing strategies',
      'Discuss code reviews and documentation',
      'Include CI/CD and automation if relevant',
    ],
  },
  // Situational
  {
    id: 'sit-1',
    category: 'Situational',
    text: 'How would you handle a disagreement with your manager about a project approach?',
    tips: [
      'Show respect for authority while standing your ground',
      'Focus on data and facts, not emotions',
      'Demonstrate willingness to compromise',
    ],
  },
  {
    id: 'sit-2',
    category: 'Situational',
    text: 'What would you do if you realized you would not meet a deadline?',
    tips: [
      'Emphasize proactive communication',
      'Explain how you would re-prioritize',
      'Show problem-solving skills',
    ],
  },
  {
    id: 'sit-3',
    category: 'Situational',
    text: 'How would you approach joining a new team with an ongoing project?',
    tips: [
      'Show willingness to listen and learn first',
      'Ask about documentation and onboarding',
      'Offer to start with smaller tasks to build trust',
    ],
  },
  // Company/Role
  {
    id: 'comp-1',
    category: 'Company/Role',
    text: 'Why do you want to work for our company?',
    tips: [
      'Research the company thoroughly',
      'Connect your values to their mission',
      'Be specific, avoid generic answers',
    ],
  },
  {
    id: 'comp-2',
    category: 'Company/Role',
    text: 'What interests you about this specific role?',
    tips: [
      'Reference specific job requirements',
      'Explain how it fits your career path',
      'Show genuine enthusiasm',
    ],
  },
  {
    id: 'comp-3',
    category: 'Company/Role',
    text: 'What do you know about our products/services?',
    tips: [
      'Do your homework before the interview',
      'Mention specific products or features',
      'Share your perspective as a potential user',
    ],
  },
  // Career Goals
  {
    id: 'goal-1',
    category: 'Career Goals',
    text: 'Where do you see yourself in 5 years?',
    tips: [
      'Align goals with the company trajectory',
      'Show ambition but be realistic',
      'Express commitment to growth',
    ],
  },
  {
    id: 'goal-2',
    category: 'Career Goals',
    text: 'What are your greatest professional strengths?',
    tips: [
      'Choose strengths relevant to the role',
      'Provide specific examples',
      'Be confident but not arrogant',
    ],
  },
  {
    id: 'goal-3',
    category: 'Career Goals',
    text: 'What motivates you in your work?',
    tips: [
      'Be authentic and specific',
      'Connect motivation to the role',
      'Avoid cliches like "money" unless genuine',
    ],
  },
]

const RESEARCH_CHECKLIST_ITEMS = [
  { id: 'rc-1', label: 'Company mission and values', checked: false },
  { id: 'rc-2', label: 'Recent news and press releases', checked: false },
  { id: 'rc-3', label: 'Key products and services', checked: false },
  { id: 'rc-4', label: 'Main competitors', checked: false },
  { id: 'rc-5', label: 'Company culture and reviews', checked: false },
  { id: 'rc-6', label: 'Leadership team', checked: false },
  { id: 'rc-7', label: 'Financial health and growth', checked: false },
  { id: 'rc-8', label: 'Interview format and process', checked: false },
]

const CATEGORY_COLORS: Record<QuestionCategory, string> = {
  Behavioral: 'bg-[var(--status-info-bg)] text-[var(--status-info-text)] border border-[var(--status-info-border)]',
  Technical: 'bg-purple-50/80 text-purple-700 border border-purple-200/60',
  Situational: 'bg-[var(--status-warning-bg)] text-[var(--status-warning-text)] border border-[var(--status-warning-border)]',
  'Company/Role': 'bg-[var(--status-success-bg)] text-[var(--status-success-text)] border border-[var(--status-success-border)]',
  'Career Goals': 'bg-pink-50/80 text-pink-700 border border-pink-200/60',
}

// ============================================================================
// Question Bank Tab
// ============================================================================

interface QuestionBankTabProps {
  resumes: Resume[]
  selectedResume: Resume | null
  jobDescription: string
}

function QuestionBankTab({
  resumes: _resumes,
  selectedResume,
  jobDescription,
}: QuestionBankTabProps) {
  const [selectedCategory, setSelectedCategory] = useState<QuestionCategory | 'All'>('All')
  const [expandedQuestions, setExpandedQuestions] = useState<Set<string>>(new Set())
  const [practiceQuestion, setPracticeQuestion] = useState<Question | null>(null)
  const [practiceAnswer, setPracticeAnswer] = useState('')
  const [generatingExample, setGeneratingExample] = useState<string | null>(null)
  const [exampleAnswers, setExampleAnswers] = useState<Record<string, string>>({})
  const [feedback, setFeedback] = useState<string | null>(null)
  const [isGettingFeedback, setIsGettingFeedback] = useState(false)

  const filteredQuestions = useMemo(() => {
    if (selectedCategory === 'All') {
      return SAMPLE_QUESTIONS
    }
    return SAMPLE_QUESTIONS.filter((q) => q.category === selectedCategory)
  }, [selectedCategory])

  const toggleExpand = (questionId: string) => {
    const newExpanded = new Set(expandedQuestions)
    if (newExpanded.has(questionId)) {
      newExpanded.delete(questionId)
    } else {
      newExpanded.add(questionId)
    }
    setExpandedQuestions(newExpanded)
  }

  const generateExampleAnswer = async (question: Question) => {
    setGeneratingExample(question.id)
    try {
      const response = await aiApi.interviewPrep(
        question.text,
        selectedResume?.content,
        jobDescription || undefined
      )
      setExampleAnswers((prev) => ({
        ...prev,
        [question.id]: (response).answer,
      }))
    } catch (error) {
      console.error('Failed to generate example answer:', error)
    } finally {
      setGeneratingExample(null)
    }
  }

  const handleGetFeedback = async () => {
    if (!practiceQuestion || !practiceAnswer.trim()) return
    setIsGettingFeedback(true)
    setFeedback(null)
    try {
      const response = await aiApi.interviewPrep(
        `Please provide feedback on this interview answer. Question: "${practiceQuestion.text}" Answer: "${practiceAnswer}"`,
        selectedResume?.content,
        jobDescription || undefined
      )
      setFeedback((response).answer)
    } catch (error) {
      console.error('Failed to get feedback:', error)
      setFeedback('Failed to get feedback. Please try again.')
    } finally {
      setIsGettingFeedback(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Category Filter */}
      <div className="glass-tabs flex-wrap">
        <button
          onClick={() => setSelectedCategory('All')}
          className={cn(
            'glass-tab',
            selectedCategory === 'All' && 'glass-tab-active'
          )}
        >
          All Questions
        </button>
        {QUESTION_CATEGORIES.map((category) => (
          <button
            key={category}
            onClick={() => setSelectedCategory(category)}
            className={cn(
              'glass-tab',
              selectedCategory === category && 'glass-tab-active'
            )}
          >
            {category}
          </button>
        ))}
      </div>

      {/* Questions List */}
      <div className="space-y-4">
        {filteredQuestions.map((question) => (
          <div
            key={question.id}
            className="surface-card-inner overflow-hidden"
          >
            <div
              className="p-4 cursor-pointer hover:bg-[var(--surface)]"
              onClick={() => toggleExpand(question.id)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  toggleExpand(question.id)
                }
              }}
              role="button"
              tabIndex={0}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <span
                    className={cn(
                      'inline-block px-2 py-1 text-xs font-medium rounded-full mb-2',
                      CATEGORY_COLORS[question.category]
                    )}
                  >
                    {question.category}
                  </span>
                  <p className="text-[var(--ink)] font-medium">{question.text}</p>
                </div>
                {expandedQuestions.has(question.id) ? (
                  <ChevronUp className="w-5 h-5 text-[var(--muted-soft)] flex-shrink-0" />
                ) : (
                  <ChevronDown className="w-5 h-5 text-[var(--muted-soft)] flex-shrink-0" />
                )}
              </div>
            </div>

            {expandedQuestions.has(question.id) && (
              <div className="px-4 pb-4 glass-divider">
                {/* Tips */}
                <div className="mt-4">
                  <h4 className="text-sm font-medium text-[var(--ink-secondary)] flex items-center gap-2 mb-2">
                    <Lightbulb className="w-4 h-4 text-amber-500" />
                    Tips for answering
                  </h4>
                  <ul className="space-y-1">
                    {question.tips.map((tip) => (
                      <li key={tip} className="text-sm text-[var(--muted)] flex items-start gap-2">
                        <span className="text-[var(--accent)] mt-0.5">-</span>
                        {tip}
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Example Answer */}
                {exampleAnswers[question.id] && (
                  <div className="mt-4 p-3 bg-[var(--status-success-bg)] rounded-[var(--radius-md)] border border-[var(--status-success-border)]">
                    <h4 className="text-sm font-medium text-[var(--status-success-text)] mb-2">Example Answer</h4>
                    <AIMarkdown content={exampleAnswers[question.id]!} />
                  </div>
                )}

                {/* Action Buttons */}
                <div className="mt-4 flex flex-wrap gap-2">
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      void generateExampleAnswer(question)
                    }}
                    disabled={generatingExample === question.id}
                    className="glass-button-primary"
                  >
                    {generatingExample === question.id ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                        Generating...
                      </>
                    ) : (
                      <>
                        <Wand2 className="w-4 h-4 mr-1" />
                        Generate Example
                      </>
                    )}
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      setPracticeQuestion(question)
                      setPracticeAnswer('')
                      setFeedback(null)
                    }}
                    className="glass-button-secondary"
                  >
                    <MessageSquare className="w-4 h-4 mr-1" />
                    Practice
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Practice Modal */}
      {practiceQuestion && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="surface-card-strong max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-4 glass-divider">
              <h2 className="text-xl font-bold font-display text-[var(--ink)]">Practice Mode</h2>
              <button
                onClick={() => {
                  setPracticeQuestion(null)
                  setPracticeAnswer('')
                  setFeedback(null)
                }}
                className="p-1 text-[var(--muted-soft)] hover:text-[var(--muted)]"
                aria-label="Close modal"
              >
                <X className="w-6 h-6" />
              </button>
            </div>

            <div className="p-4 space-y-4">
              <div className="p-4 bg-[var(--surface-thin)] rounded-[var(--radius-md)]">
                <span
                  className={cn(
                    'inline-block px-2 py-1 text-xs font-medium rounded-full mb-2',
                    CATEGORY_COLORS[practiceQuestion.category]
                  )}
                >
                  {practiceQuestion.category}
                </span>
                <p className="text-[var(--ink)] font-medium">{practiceQuestion.text}</p>
              </div>

              <div>
                <label htmlFor="practice-answer" className="glass-label">
                  Your Answer
                </label>
                <textarea
                  id="practice-answer"
                  value={practiceAnswer}
                  onChange={(e) => setPracticeAnswer(e.target.value)}
                  rows={8}
                  className="glass-textarea"
                  placeholder="Type your answer here..."
                />
              </div>

              <button
                onClick={() => { void handleGetFeedback() }}
                disabled={!practiceAnswer.trim() || isGettingFeedback}
                className="glass-button-primary w-full"
              >
                {isGettingFeedback ? (
                  <>
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2" />
                    Getting Feedback...
                  </>
                ) : (
                  <>
                    <Wand2 className="w-5 h-5 mr-2" />
                    Get AI Feedback
                  </>
                )}
              </button>

              {feedback && (
                <div className="p-4 bg-[var(--status-info-bg)] rounded-[var(--radius-md)] border border-[var(--status-info-border)]">
                  <h4 className="text-sm font-medium text-[var(--status-info-text)] mb-2 flex items-center gap-2">
                    <MessageSquare className="w-4 h-4" />
                    AI Feedback
                  </h4>
                  <AIMarkdown content={feedback} />
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ============================================================================
// STAR Builder Tab
// ============================================================================

interface STARBuilderTabProps {
  stories: STARStory[]
  onSaveStory: (story: STARStory) => void | Promise<void>
  onDeleteStory: (id: string | number) => void | Promise<void>
}

function STARBuilderTab({ stories, onSaveStory, onDeleteStory }: STARBuilderTabProps) {
  const [formData, setFormData] = useState({
    title: '',
    situation: '',
    task: '',
    action: '',
    result: '',
    tags: '',
  })
  const [editingId, setEditingId] = useState<string | number | null>(null)
  const [isPolishing, setIsPolishing] = useState(false)
  const [polishedStory, setPolishedStory] = useState<string | null>(null)
  const [copiedField, setCopiedField] = useState<string | null>(null)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const story: STARStory = {
      id: editingId || generateId(),
      title: formData.title,
      situation: formData.situation,
      task: formData.task,
      action: formData.action,
      result: formData.result,
      tags: formData.tags.split(',').map((t) => t.trim()).filter(Boolean),
      createdAt: editingId
        ? stories.find((s) => s.id === editingId)?.createdAt || new Date().toISOString()
        : new Date().toISOString(),
    }
    void onSaveStory(story)
    resetForm()
  }

  const resetForm = () => {
    setFormData({
      title: '',
      situation: '',
      task: '',
      action: '',
      result: '',
      tags: '',
    })
    setEditingId(null)
    setPolishedStory(null)
  }

  const editStory = (story: STARStory) => {
    setFormData({
      title: story.title,
      situation: story.situation,
      task: story.task,
      action: story.action,
      result: story.result,
      tags: story.tags.join(', '),
    })
    setEditingId(story.id)
    setPolishedStory(null)
  }

  const handlePolish = async () => {
    if (!formData.situation || !formData.task || !formData.action || !formData.result) return
    setIsPolishing(true)
    setPolishedStory(null)
    try {
      const storyText = `
Situation: ${formData.situation}
Task: ${formData.task}
Action: ${formData.action}
Result: ${formData.result}
      `.trim()

      const response = await aiApi.interviewPrep(
        `Please polish and improve this STAR story while keeping the same structure. Make it more compelling and professional: ${storyText}`,
        undefined,
        undefined
      )
      setPolishedStory((response).answer)
    } catch (error) {
      console.error('Failed to polish story:', error)
    } finally {
      setIsPolishing(false)
    }
  }

  const copyToClipboard = async (text: string, field: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedField(field)
      setTimeout(() => setCopiedField(null), 2000)
    } catch (error) {
      console.error('Failed to copy:', error)
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Form */}
      <div className="surface-card p-6">
        <h3 className="text-lg font-semibold font-display text-[var(--ink)] mb-4 flex items-center gap-2">
          <Star className="w-5 h-5 text-amber-500" />
          {editingId ? 'Edit STAR Story' : 'Create STAR Story'}
        </h3>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="story-title" className="glass-label">
              Story Title
            </label>
            <input
              id="story-title"
              type="text"
              required
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              className="glass-input"
              placeholder="e.g., Led cross-functional project"
            />
          </div>

          <div>
            <label htmlFor="story-situation" className="glass-label">
              <span className="inline-flex items-center gap-1">
                <span className="w-5 h-5 rounded-full bg-[var(--status-info-bg)] text-[var(--status-info-text)] text-xs flex items-center justify-center font-bold">
                  S
                </span>
                Situation
              </span>
            </label>
            <textarea
              id="story-situation"
              required
              value={formData.situation}
              onChange={(e) => setFormData({ ...formData, situation: e.target.value })}
              rows={3}
              className="glass-textarea"
              placeholder="Describe the context and background..."
            />
          </div>

          <div>
            <label htmlFor="story-task" className="glass-label">
              <span className="inline-flex items-center gap-1">
                <span className="w-5 h-5 rounded-full bg-[var(--status-success-bg)] text-[var(--status-success-text)] text-xs flex items-center justify-center font-bold">
                  T
                </span>
                Task
              </span>
            </label>
            <textarea
              id="story-task"
              required
              value={formData.task}
              onChange={(e) => setFormData({ ...formData, task: e.target.value })}
              rows={3}
              className="glass-textarea"
              placeholder="What was your responsibility or goal?"
            />
          </div>

          <div>
            <label htmlFor="story-action" className="glass-label">
              <span className="inline-flex items-center gap-1">
                <span className="w-5 h-5 rounded-full bg-[var(--status-warning-bg)] text-[var(--status-warning-text)] text-xs flex items-center justify-center font-bold">
                  A
                </span>
                Action
              </span>
            </label>
            <textarea
              id="story-action"
              required
              value={formData.action}
              onChange={(e) => setFormData({ ...formData, action: e.target.value })}
              rows={4}
              className="glass-textarea"
              placeholder="What specific actions did you take?"
            />
          </div>

          <div>
            <label htmlFor="story-result" className="glass-label">
              <span className="inline-flex items-center gap-1">
                <span className="w-5 h-5 rounded-full bg-purple-50/80 text-purple-700 text-xs flex items-center justify-center font-bold">
                  R
                </span>
                Result
              </span>
            </label>
            <textarea
              id="story-result"
              required
              value={formData.result}
              onChange={(e) => setFormData({ ...formData, result: e.target.value })}
              rows={3}
              className="glass-textarea"
              placeholder="What was the outcome? Include metrics if possible..."
            />
          </div>

          <div>
            <label htmlFor="story-tags" className="glass-label">
              Tags (comma separated)
            </label>
            <input
              id="story-tags"
              type="text"
              value={formData.tags}
              onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
              className="glass-input"
              placeholder="e.g., leadership, problem-solving, teamwork"
            />
          </div>

          <div className="flex gap-2 pt-2">
            <button
              type="button"
              onClick={() => { void handlePolish() }}
              disabled={isPolishing || !formData.situation || !formData.task || !formData.action || !formData.result}
              className="flex-1 py-2 bg-amber-500 text-white rounded-[var(--radius-md)] hover:bg-amber-600 disabled:opacity-50 flex items-center justify-center font-semibold text-sm"
            >
              {isPolishing ? (
                <>
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2" />
                  Polishing...
                </>
              ) : (
                <>
                  <Wand2 className="w-5 h-5 mr-2" />
                  AI Polish
                </>
              )}
            </button>
            <button
              type="submit"
              className="glass-button-primary flex-1"
            >
              <Save className="w-5 h-5 mr-2" />
              {editingId ? 'Update Story' : 'Save Story'}
            </button>
          </div>

          {editingId && (
            <button
              type="button"
              onClick={resetForm}
              className="w-full py-2 text-[var(--muted)] hover:bg-[var(--surface)] rounded-[var(--radius-md)]"
            >
              Cancel Editing
            </button>
          )}
        </form>

        {/* Polished Story Output */}
        {polishedStory && (
          <div className="mt-4 p-4 bg-[var(--status-warning-bg)] rounded-[var(--radius-md)] border border-[var(--status-warning-border)]">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-medium text-[var(--status-warning-text)]">AI Polished Version</h4>
              <button
                onClick={() => { void copyToClipboard(polishedStory, 'polished') }}
                className="p-1 text-[var(--status-warning-text)] hover:opacity-80"
                aria-label="Copy to clipboard"
              >
                {copiedField === 'polished' ? (
                  <Check className="w-4 h-4" />
                ) : (
                  <Copy className="w-4 h-4" />
                )}
              </button>
            </div>
            <AIMarkdown content={polishedStory} />
          </div>
        )}
      </div>

      {/* Saved Stories */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold font-display text-[var(--ink)] flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-[var(--accent)]" />
          Saved Stories ({stories.length})
        </h3>

        {stories.length === 0 ? (
          <div className="surface-card p-8 text-center text-[var(--muted)]">
            <Star className="w-12 h-12 mx-auto mb-4 text-[var(--muted-soft)]" />
            <p>No STAR stories saved yet</p>
            <p className="text-sm mt-1">Create your first story using the form</p>
          </div>
        ) : (
          <div className="space-y-4">
            {stories.map((story) => (
              <div key={story.id} className="surface-card-inner p-4">
                <div className="flex items-start justify-between mb-2">
                  <h4 className="font-medium text-[var(--ink)]">{story.title}</h4>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => editStory(story)}
                      className="p-1 text-[var(--muted-soft)] hover:text-[var(--accent)]"
                      aria-label="Edit story"
                    >
                      <MessageSquare className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => {
                        if (confirm('Delete this story?')) {
                          void onDeleteStory(story.id)
                        }
                      }}
                      className="p-1 text-[var(--muted-soft)] hover:text-[var(--status-error-text)]"
                      aria-label="Delete story"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {story.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1 mb-3">
                    {story.tags.map((tag) => (
                      <span
                        key={tag}
                        className="px-2 py-0.5 text-xs bg-[var(--surface)] text-[var(--muted)] rounded-full border border-[var(--line)]"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                )}

                <div className="space-y-2 text-sm">
                  <div>
                    <span className="font-medium text-[var(--status-info-text)]">S:</span>{' '}
                    <span className="text-[var(--muted)]">{story.situation.slice(0, 100)}...</span>
                  </div>
                  <div>
                    <span className="font-medium text-[var(--status-success-text)]">T:</span>{' '}
                    <span className="text-[var(--muted)]">{story.task.slice(0, 100)}...</span>
                  </div>
                  <div>
                    <span className="font-medium text-[var(--status-warning-text)]">A:</span>{' '}
                    <span className="text-[var(--muted)]">{story.action.slice(0, 100)}...</span>
                  </div>
                  <div>
                    <span className="font-medium text-purple-700">R:</span>{' '}
                    <span className="text-[var(--muted)]">{story.result.slice(0, 100)}...</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// ============================================================================
// Company Research Tab
// ============================================================================

interface CompanyResearchTabProps {
  research: CompanyResearch
  onUpdateResearch: (research: CompanyResearch) => void | Promise<void>
}

function CompanyResearchTab({ research, onUpdateResearch }: CompanyResearchTabProps) {
  const [companyInput, setCompanyInput] = useState(research.companyName)
  const [isGenerating, setIsGenerating] = useState(false)

  const handleGenerateTalkingPoints = async () => {
    if (!companyInput.trim()) return
    setIsGenerating(true)
    try {
      const response = await aiApi.interviewPrep(
        `Generate interview talking points and research insights for someone interviewing at ${companyInput}. Include: company background, recent news, culture insights, and suggested questions to ask. Format as bullet points.`,
        undefined,
        undefined
      )

      const points = (response).answer
        .split('\n')
        .filter((line) => line.trim())
        .map((line) => line.replace(/^[-*]\s*/, '').trim())
        .filter((line) => line.length > 0)

      void onUpdateResearch({
        ...research,
        companyName: companyInput,
        talkingPoints: points,
      })
    } catch (error) {
      console.error('Failed to generate talking points:', error)
    } finally {
      setIsGenerating(false)
    }
  }

  const toggleChecklistItem = (itemId: string | undefined, index: number) => {
    const updatedChecklist = research.checklist.map((item, i) =>
      (itemId ? item.id === itemId : i === index) ? { ...item, checked: !item.checked, done: !(item.done ?? item.checked) } : item
    )
    void onUpdateResearch({ ...research, checklist: updatedChecklist })
  }

  const completedCount = research.checklist.filter((item) => item.checked).length

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Research Input */}
      <div className="lg:col-span-2 space-y-6">
        <div className="surface-card p-6">
          <h3 className="text-lg font-semibold font-display text-[var(--ink)] mb-4 flex items-center gap-2">
            <Building2 className="w-5 h-5 text-[var(--accent)]" />
            Company Research
          </h3>

          <div className="flex gap-2 mb-4">
            <input
              type="text"
              value={companyInput}
              onChange={(e) => setCompanyInput(e.target.value)}
              className="glass-input flex-1"
              placeholder="Enter company name..."
            />
            <button
              onClick={() => { void handleGenerateTalkingPoints() }}
              disabled={isGenerating || !companyInput.trim()}
              className="glass-button-primary"
            >
              {isGenerating ? (
                <>
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2" />
                  Generating...
                </>
              ) : (
                <>
                  <Search className="w-5 h-5 mr-2" />
                  Research
                </>
              )}
            </button>
          </div>

          {/* Talking Points */}
          {research.talkingPoints.length > 0 && (
            <div className="space-y-3">
              <h4 className="text-sm font-medium text-[var(--ink-secondary)] flex items-center gap-2">
                <Lightbulb className="w-4 h-4 text-amber-500" />
                AI-Generated Talking Points
              </h4>
              <ul className="space-y-2">
                {research.talkingPoints.map((point) => (
                  <li
                    key={point}
                    className="p-3 bg-[var(--surface-thin)] rounded-[var(--radius-md)] text-sm text-[var(--ink-secondary)] flex items-start gap-2"
                  >
                    <Target className="w-4 h-4 text-[var(--accent)] mt-0.5 flex-shrink-0" />
                    {point}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Notes */}
          <div className="mt-6">
            <label htmlFor="research-notes" className="glass-label">
              Your Research Notes
            </label>
            <textarea
              id="research-notes"
              value={research.notes}
              onChange={(e) => { void onUpdateResearch({ ...research, notes: e.target.value }) }}
              rows={6}
              className="glass-textarea"
              placeholder="Add your own research notes here..."
            />
          </div>
        </div>
      </div>

      {/* Research Checklist */}
      <div className="surface-card p-6">
        <h3 className="text-lg font-semibold font-display text-[var(--ink)] mb-4 flex items-center gap-2">
          <CheckCircle className="w-5 h-5 text-[var(--status-success-text)]" />
          Research Checklist
        </h3>

        <div className="mb-4">
          <div className="flex justify-between text-sm text-[var(--muted)] mb-1">
            <span>Progress</span>
            <span>
              {completedCount} / {research.checklist.length}
            </span>
          </div>
          <div className="w-full bg-[var(--surface)] rounded-full h-2">
            <div
              className="bg-[var(--signal)] h-2 rounded-full transition-all"
              style={{
                width: `${(completedCount / research.checklist.length) * 100}%`,
              }}
            />
          </div>
        </div>

        <ul className="space-y-2">
          {research.checklist.map((item, idx) => (
            <li key={item.id ?? idx}>
              <label className="flex items-center gap-3 p-2 rounded-[var(--radius-md)] hover:bg-[var(--surface)] cursor-pointer">
                <input
                  type="checkbox"
                  checked={item.checked ?? item.done ?? false}
                  onChange={() => toggleChecklistItem(item.id, idx)}
                  className="w-4 h-4 text-[var(--signal)] rounded border-[var(--line-strong)] focus:ring-[var(--ink)]/20"
                />
                <span
                  className={cn(
                    'text-sm',
                    (item.checked ?? item.done) ? 'text-[var(--muted-soft)] line-through' : 'text-[var(--ink-secondary)]'
                  )}
                >
                  {item.label ?? item.text}
                </span>
              </label>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

// ============================================================================
// Practice Mode Tab
// ============================================================================

interface PracticeModeTabProps {
  resumes: Resume[]
  selectedResume: Resume | null
  jobDescription: string
}

function PracticeModeTab({
  resumes: _resumes,
  selectedResume,
  jobDescription,
}: PracticeModeTabProps) {
  const [selectedCategory, setSelectedCategory] = useState<QuestionCategory>('Behavioral')
  const [currentQuestion, setCurrentQuestion] = useState<Question | null>(null)
  const [answer, setAnswer] = useState('')
  const [feedback, setFeedback] = useState<{
    text: string
    score: number
    suggestions: string[]
  } | null>(null)
  const [isGettingFeedback, setIsGettingFeedback] = useState(false)
  const [timer, setTimer] = useState(0)
  const [isTimerRunning, setIsTimerRunning] = useState(false)
  const [sessionHistory, setSessionHistory] = useState<PracticeSession[]>([])
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current)
      }
    }
  }, [])

  const startTimer = useCallback(() => {
    setIsTimerRunning(true)
    timerRef.current = setInterval(() => {
      setTimer((prev) => prev + 1)
    }, 1000)
  }, [])

  const pauseTimer = useCallback(() => {
    setIsTimerRunning(false)
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
  }, [])

  const resetTimer = useCallback(() => {
    pauseTimer()
    setTimer(0)
  }, [pauseTimer])

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  const getRandomQuestion = () => {
    const categoryQuestions = SAMPLE_QUESTIONS.filter((q) => q.category === selectedCategory)
    const randomIndex = Math.floor(Math.random() * categoryQuestions.length)
    const question = categoryQuestions[randomIndex]
    setCurrentQuestion(question ?? null)
    setAnswer('')
    setFeedback(null)
    resetTimer()
  }

  const handleGetFeedback = async () => {
    if (!currentQuestion || !answer.trim()) return
    pauseTimer()
    setIsGettingFeedback(true)
    try {
      const response = await aiApi.interviewPrep(
        `You are an interview coach. Evaluate this interview answer and provide:
1. A score from 1-10
2. Analysis of clarity, structure, and relevance
3. Specific improvement suggestions

Question: "${currentQuestion.text}"
Answer: "${answer}"

Format your response as:
SCORE: [number]
ANALYSIS: [your analysis]
SUGGESTIONS:
- [suggestion 1]
- [suggestion 2]
- [suggestion 3]`,
        selectedResume?.content,
        jobDescription || undefined
      )

      const responseText = (response).answer

      // Parse the response
      const scoreMatch = responseText.match(/SCORE:\s*(\d+)/i)
      const score = scoreMatch ? parseInt(scoreMatch[1] ?? '5', 10) : 5

      const analysisMatch = responseText.match(/ANALYSIS:\s*([\s\S]*?)(?=SUGGESTIONS:|$)/i)
      const analysis = analysisMatch?.[1]?.trim() ?? responseText

      const suggestionsMatch = responseText.match(/SUGGESTIONS:\s*([\s\S]*)/i)
      const suggestionsText = suggestionsMatch?.[1] ?? ''
      const suggestions = suggestionsText
        .split('\n')
        .filter((line) => line.trim().startsWith('-'))
        .map((line) => line.replace(/^-\s*/, '').trim())

      setFeedback({
        text: analysis,
        score: Math.min(10, Math.max(1, score)),
        suggestions: suggestions.length > 0 ? suggestions : ['Continue practicing to improve'],
      })

      // Add to session history
      setSessionHistory((prev) => [
        ...prev,
        {
          id: generateId(),
          questionId: currentQuestion.id,
          answer,
          feedback: analysis,
          score,
          timeSpent: timer,
        },
      ])
    } catch (error) {
      console.error('Failed to get feedback:', error)
      setFeedback({
        text: 'Failed to get feedback. Please try again.',
        score: 0,
        suggestions: [],
      })
    } finally {
      setIsGettingFeedback(false)
    }
  }

  const averageScore = useMemo(() => {
    if (sessionHistory.length === 0) return 0
    const validScores = sessionHistory.filter((s) => s.score !== null && s.score > 0)
    if (validScores.length === 0) return 0
    return (
      validScores.reduce((sum, s) => sum + (s.score || 0), 0) / validScores.length
    ).toFixed(1)
  }, [sessionHistory])

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="surface-card p-4">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <label htmlFor="practice-category" className="text-sm font-medium text-[var(--ink-secondary)]">Category:</label>
            <select
              id="practice-category"
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value as QuestionCategory)}
              className="glass-select"
            >
              {QUESTION_CATEGORIES.map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={getRandomQuestion}
            className="glass-button-primary"
          >
            <Shuffle className="w-5 h-5 mr-2" />
            Random Question
          </button>

          {/* Timer */}
          <div className="flex items-center gap-2 ml-auto">
            <Clock className="w-5 h-5 text-[var(--muted)]" />
            <span className="text-xl font-mono font-bold text-[var(--ink)] w-16">
              {formatTime(timer)}
            </span>
            <button
              onClick={isTimerRunning ? pauseTimer : startTimer}
              className="p-2 rounded-[var(--radius-md)] hover:bg-[var(--surface)]"
              aria-label={isTimerRunning ? 'Pause timer' : 'Start timer'}
            >
              {isTimerRunning ? (
                <Pause className="w-5 h-5 text-[var(--muted)]" />
              ) : (
                <Play className="w-5 h-5 text-[var(--muted)]" />
              )}
            </button>
            <button
              onClick={resetTimer}
              className="p-2 rounded-[var(--radius-md)] hover:bg-[var(--surface)]"
              aria-label="Reset timer"
            >
              <RotateCcw className="w-5 h-5 text-[var(--muted)]" />
            </button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Practice Area */}
        <div className="lg:col-span-2 space-y-4">
          {currentQuestion ? (
            <>
              {/* Question */}
              <div className="surface-card p-6">
                <span
                  className={cn(
                    'inline-block px-2 py-1 text-xs font-medium rounded-full mb-3',
                    CATEGORY_COLORS[currentQuestion.category]
                  )}
                >
                  {currentQuestion.category}
                </span>
                <p className="text-lg font-medium text-[var(--ink)]">{currentQuestion.text}</p>
              </div>

              {/* Answer Input */}
              <div className="surface-card p-6">
                <label htmlFor="practice-mode-answer" className="glass-label mb-2">
                  Your Answer
                </label>
                <textarea
                  id="practice-mode-answer"
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                  rows={10}
                  className="glass-textarea"
                  placeholder="Type your answer here... Use the STAR method for behavioral questions."
                />

                <button
                  onClick={() => { void handleGetFeedback() }}
                  disabled={!answer.trim() || isGettingFeedback}
                  className="glass-button-primary mt-4 w-full"
                >
                  {isGettingFeedback ? (
                    <>
                      <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2" />
                      Analyzing Answer...
                    </>
                  ) : (
                    <>
                      <Wand2 className="w-5 h-5 mr-2" />
                      Get AI Feedback
                    </>
                  )}
                </button>
              </div>

              {/* Feedback */}
              {feedback && (
                <div className="surface-card p-6">
                  <div className="flex items-center gap-4 mb-4">
                    <div
                      className={cn(
                        'w-16 h-16 rounded-full flex items-center justify-center text-2xl font-bold',
                        feedback.score >= 8
                          ? 'bg-[var(--status-success-bg)] text-[var(--status-success-text)]'
                          : feedback.score >= 6
                          ? 'bg-[var(--status-warning-bg)] text-[var(--status-warning-text)]'
                          : 'bg-[var(--status-error-bg)] text-[var(--status-error-text)]'
                      )}
                    >
                      {feedback.score}/10
                    </div>
                    <div>
                      <h4 className="font-semibold text-[var(--ink)]">Your Score</h4>
                      <p className="text-sm text-[var(--muted)]">
                        {feedback.score >= 8
                          ? 'Excellent answer!'
                          : feedback.score >= 6
                          ? 'Good, with room for improvement'
                          : 'Needs more work'}
                      </p>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <div>
                      <h4 className="text-sm font-medium text-[var(--ink-secondary)] mb-2">Analysis</h4>
                      <AIMarkdown content={feedback.text} />
                    </div>

                    {feedback.suggestions.length > 0 && (
                      <div>
                        <h4 className="text-sm font-medium text-[var(--ink-secondary)] mb-2 flex items-center gap-2">
                          <AlertCircle className="w-4 h-4 text-amber-500" />
                          Improvement Suggestions
                        </h4>
                        <ul className="space-y-2">
                          {feedback.suggestions.map((suggestion) => (
                            <li
                              key={suggestion}
                              className="text-sm text-[var(--muted)] flex items-start gap-2"
                            >
                              <span className="text-amber-500 mt-0.5">-</span>
                              {suggestion}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="surface-card p-12 text-center">
              <Shuffle className="w-16 h-16 mx-auto mb-4 text-[var(--muted-soft)]" />
              <h3 className="text-lg font-medium font-display text-[var(--ink)] mb-2">Ready to Practice?</h3>
              <p className="text-[var(--muted)] mb-4">
                Select a category and click "Random Question" to start practicing
              </p>
              <button
                onClick={getRandomQuestion}
                className="glass-button-primary"
              >
                <Shuffle className="w-5 h-5 mr-2" />
                Get Started
              </button>
            </div>
          )}
        </div>

        {/* Session Stats */}
        <div className="space-y-4">
          <div className="surface-card p-6">
            <h3 className="text-lg font-semibold font-display text-[var(--ink)] mb-4">Session Stats</h3>

            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-sm text-[var(--muted)]">Questions Practiced</span>
                <span className="font-bold text-[var(--ink)]">{sessionHistory.length}</span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-sm text-[var(--muted)]">Average Score</span>
                <span className="font-bold text-[var(--ink)]">
                  {sessionHistory.length > 0 ? `${averageScore}/10` : '-'}
                </span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-sm text-[var(--muted)]">Total Time</span>
                <span className="font-bold text-[var(--ink)]">
                  {formatTime(sessionHistory.reduce((sum, s) => sum + s.timeSpent, 0))}
                </span>
              </div>
            </div>
          </div>

          {sessionHistory.length > 0 && (
            <div className="surface-card p-6">
              <h3 className="text-lg font-semibold font-display text-[var(--ink)] mb-4">Recent Practice</h3>
              <ul className="space-y-3">
                {sessionHistory
                  .slice(-5)
                  .reverse()
                  .map((session) => {
                    const question = SAMPLE_QUESTIONS.find((q) => q.id === session.questionId)
                    return (
                      <li key={session.id} className="p-3 bg-[var(--surface-thin)] rounded-[var(--radius-md)]">
                        <div className="flex items-center justify-between mb-1">
                          <span
                            className={cn(
                              'text-xs px-2 py-0.5 rounded-full',
                              CATEGORY_COLORS[question?.category || 'Behavioral']
                            )}
                          >
                            {question?.category}
                          </span>
                          <span
                            className={cn(
                              'text-sm font-medium',
                              (session.score || 0) >= 8
                                ? 'text-[var(--status-success-text)]'
                                : (session.score || 0) >= 6
                                ? 'text-[var(--status-warning-text)]'
                                : 'text-[var(--status-error-text)]'
                            )}
                          >
                            {session.score}/10
                          </span>
                        </div>
                        <p className="text-xs text-[var(--muted)] truncate">
                          {question?.text.slice(0, 50)}...
                        </p>
                        <p className="text-xs text-[var(--muted-soft)] mt-1">
                          Time: {formatTime(session.timeSpent)}
                        </p>
                      </li>
                    )
                  })}
              </ul>
            </div>
          )}

          {/* Tips Card */}
          <div className="bg-[var(--status-warning-bg)] rounded-[var(--radius-lg)] border border-[var(--status-warning-border)] p-4">
            <h4 className="text-sm font-medium text-[var(--status-warning-text)] mb-2 flex items-center gap-2">
              <Lightbulb className="w-4 h-4" />
              Practice Tips
            </h4>
            <ul className="text-sm text-[var(--status-warning-text)] space-y-1">
              <li>- Practice out loud, not just in writing</li>
              <li>- Aim for 2-3 minute answers</li>
              <li>- Use specific examples with metrics</li>
              <li>- Structure behavioral answers with STAR</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}

// ============================================================================
// Interview Events Tab
// ============================================================================

interface InterviewEventsTabProps {
  events: InterviewEventLocal[]
  onSaveEvent: (event: Omit<InterviewEventLocal, 'id' | 'createdAt' | 'updatedAt'> & { id?: number }) => void | Promise<void>
  onDeleteEvent: (id: number) => void | Promise<void>
  onMarkComplete: (id: number) => void | Promise<void>
  onToggleFollowUp: (id: number) => void | Promise<void>
}

function InterviewEventsTab({
  events,
  onSaveEvent,
  onDeleteEvent,
  onMarkComplete,
  onToggleFollowUp,
}: InterviewEventsTabProps) {
  const [showModal, setShowModal] = useState(false)
  const [editingEvent, setEditingEvent] = useState<InterviewEventLocal | null>(null)
  const [formData, setFormData] = useState({
    company: '',
    position: '',
    eventType: 'phone_screen',
    scheduledDate: '',
    scheduledTime: '',
    durationMinutes: '',
    location: '',
    meetingLink: '',
    interviewerNames: '',
    notes: '',
    followUpDate: '',
  })

  const resetForm = () => {
    setFormData({
      company: '',
      position: '',
      eventType: 'phone_screen',
      scheduledDate: '',
      scheduledTime: '',
      durationMinutes: '',
      location: '',
      meetingLink: '',
      interviewerNames: '',
      notes: '',
      followUpDate: '',
    })
    setEditingEvent(null)
  }

  const openAddModal = () => {
    resetForm()
    setShowModal(true)
  }

  const openEditModal = (event: InterviewEventLocal) => {
    setEditingEvent(event)
    setFormData({
      company: event.company,
      position: event.position,
      eventType: event.eventType,
      scheduledDate: event.scheduledDate,
      scheduledTime: event.scheduledTime ?? '',
      durationMinutes: event.durationMinutes?.toString() ?? '',
      location: event.location ?? '',
      meetingLink: event.meetingLink ?? '',
      interviewerNames: event.interviewerNames?.join(', ') ?? '',
      notes: event.notes ?? '',
      followUpDate: event.followUpDate ?? '',
    })
    setShowModal(true)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const names = formData.interviewerNames
      .split(',')
      .map((n) => n.trim())
      .filter(Boolean)
    const eventData = {
      ...(editingEvent ? { id: editingEvent.id } : {}),
      jobApplicationId: editingEvent?.jobApplicationId ?? null,
      company: formData.company,
      position: formData.position,
      eventType: formData.eventType,
      scheduledDate: formData.scheduledDate,
      scheduledTime: formData.scheduledTime || null,
      durationMinutes: formData.durationMinutes ? parseInt(formData.durationMinutes, 10) : null,
      location: formData.location || null,
      meetingLink: formData.meetingLink || null,
      interviewerNames: names.length > 0 ? names : null,
      notes: formData.notes || null,
      isCompleted: editingEvent?.isCompleted ?? false,
      followUpDate: formData.followUpDate || null,
      followUpDone: editingEvent?.followUpDone ?? false,
    }
    void onSaveEvent(eventData)
    setShowModal(false)
    resetForm()
  }

  const upcoming = useMemo(() => {
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    return events
      .filter((ev) => {
        if (ev.isCompleted) return false
        const evDate = new Date(ev.scheduledDate + 'T00:00:00')
        evDate.setHours(0, 0, 0, 0)
        return evDate.getTime() >= today.getTime()
      })
      .sort((a, b) => a.scheduledDate.localeCompare(b.scheduledDate))
  }, [events])

  const past = useMemo(() => {
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    return events
      .filter((ev) => {
        if (ev.isCompleted) return true
        const evDate = new Date(ev.scheduledDate + 'T00:00:00')
        evDate.setHours(0, 0, 0, 0)
        return evDate.getTime() < today.getTime()
      })
      .sort((a, b) => b.scheduledDate.localeCompare(a.scheduledDate))
  }, [events])

  const getEventTypeLabel = (value: string): string => {
    return EVENT_TYPE_OPTIONS.find((o) => o.value === value)?.label ?? value
  }

  const getEventTypeBadgeColor = (value: string): string => {
    switch (value) {
      case 'phone_screen':
        return 'bg-[var(--status-info-bg)] text-[var(--status-info-text)] border border-[var(--status-info-border)]'
      case 'technical':
        return 'bg-purple-50/80 text-purple-700 border border-purple-200/60'
      case 'behavioral':
        return 'bg-[var(--status-warning-bg)] text-[var(--status-warning-text)] border border-[var(--status-warning-border)]'
      case 'onsite':
        return 'bg-[var(--status-success-bg)] text-[var(--status-success-text)] border border-[var(--status-success-border)]'
      case 'panel':
        return 'bg-pink-50/80 text-pink-700 border border-pink-200/60'
      case 'final':
        return 'bg-amber-50/80 text-amber-700 border border-amber-200/60'
      default:
        return 'bg-[var(--surface)] text-[var(--muted)] border border-[var(--line)]'
    }
  }

  const getCountdownBadgeColor = (dateStr: string): string => {
    const text = getCountdownText(dateStr)
    if (text === 'Today!') return 'bg-[var(--status-error-bg)] text-[var(--status-error-text)] border border-[var(--status-error-border)]'
    if (text === 'Tomorrow') return 'bg-[var(--status-warning-bg)] text-[var(--status-warning-text)] border border-[var(--status-warning-border)]'
    return 'bg-[var(--status-info-bg)] text-[var(--status-info-text)] border border-[var(--status-info-border)]'
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold font-display text-[var(--ink)] flex items-center gap-2">
          <CalendarClock className="w-5 h-5 text-[var(--accent)]" />
          Interview Events
        </h3>
        <button onClick={openAddModal} className="glass-button-primary">
          <Plus className="w-4 h-4 mr-1" />
          Add Event
        </button>
      </div>

      {events.length === 0 ? (
        /* Empty State */
        <div className="surface-card p-12 text-center">
          <Calendar className="w-16 h-16 mx-auto mb-4 text-[var(--muted-soft)]" />
          <h3 className="text-lg font-medium font-display text-[var(--ink)] mb-2">No Interview Events Yet</h3>
          <p className="text-[var(--muted)] mb-4">
            Add your first interview to start tracking your schedule
          </p>
          <button onClick={openAddModal} className="glass-button-primary">
            <Plus className="w-5 h-5 mr-2" />
            Add Your First Interview
          </button>
        </div>
      ) : (
        <>
          {/* Upcoming Section */}
          {upcoming.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-[var(--ink-secondary)] mb-3 flex items-center gap-2">
                <Clock className="w-4 h-4 text-[var(--accent)]" />
                Upcoming ({upcoming.length})
              </h4>
              <div className="space-y-3">
                {upcoming.map((event) => (
                  <div key={event.id} className="surface-card-inner p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex flex-wrap items-center gap-2 mb-2">
                          <span
                            className={cn(
                              'inline-block px-2 py-0.5 text-xs font-medium rounded-full',
                              getCountdownBadgeColor(event.scheduledDate)
                            )}
                          >
                            {getCountdownText(event.scheduledDate)}
                          </span>
                          <span
                            className={cn(
                              'inline-block px-2 py-0.5 text-xs font-medium rounded-full',
                              getEventTypeBadgeColor(event.eventType)
                            )}
                          >
                            {getEventTypeLabel(event.eventType)}
                          </span>
                          {event.durationMinutes && (
                            <span className="text-xs text-[var(--muted)]">
                              {event.durationMinutes} min
                            </span>
                          )}
                        </div>
                        <h4 className="font-medium text-[var(--ink)]">{event.company}</h4>
                        <p className="text-sm text-[var(--muted)]">{event.position}</p>
                        <div className="flex flex-wrap items-center gap-3 mt-2 text-sm text-[var(--muted)]">
                          <span className="flex items-center gap-1">
                            <Calendar className="w-3.5 h-3.5" />
                            {new Date(event.scheduledDate + 'T00:00:00').toLocaleDateString()}
                            {event.scheduledTime && ` at ${event.scheduledTime}`}
                          </span>
                          {event.location && (
                            <span className="flex items-center gap-1">
                              <MapPin className="w-3.5 h-3.5" />
                              {event.location}
                            </span>
                          )}
                          {event.interviewerNames && event.interviewerNames.length > 0 && (
                            <span className="flex items-center gap-1">
                              <Users className="w-3.5 h-3.5" />
                              {event.interviewerNames.join(', ')}
                            </span>
                          )}
                        </div>
                        {event.notes && (
                          <p className="mt-2 text-xs text-[var(--muted-soft)] truncate">{event.notes}</p>
                        )}
                      </div>
                      <div className="flex flex-col items-end gap-2 flex-shrink-0">
                        {event.meetingLink && (
                          <a
                            href={event.meetingLink}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium bg-[var(--status-info-bg)] text-[var(--status-info-text)] rounded-[var(--radius-md)] border border-[var(--status-info-border)] hover:opacity-80"
                          >
                            <Video className="w-3.5 h-3.5" />
                            Join
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        )}
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => openEditModal(event)}
                            className="p-1 text-[var(--muted-soft)] hover:text-[var(--accent)]"
                            aria-label="Edit event"
                          >
                            <Edit3 className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => { void onMarkComplete(event.id) }}
                            className="p-1 text-[var(--muted-soft)] hover:text-[var(--status-success-text)]"
                            aria-label="Mark complete"
                          >
                            <CheckCircle className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => {
                              if (confirm('Delete this event?')) {
                                void onDeleteEvent(event.id)
                              }
                            }}
                            className="p-1 text-[var(--muted-soft)] hover:text-[var(--status-error-text)]"
                            aria-label="Delete event"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Past Section */}
          {past.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-[var(--ink-secondary)] mb-3 flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-[var(--status-success-text)]" />
                Past / Completed ({past.length})
              </h4>
              <div className="space-y-3">
                {past.map((event) => (
                  <div key={event.id} className="surface-card-inner p-4 opacity-80">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex flex-wrap items-center gap-2 mb-2">
                          <span
                            className={cn(
                              'inline-block px-2 py-0.5 text-xs font-medium rounded-full',
                              getEventTypeBadgeColor(event.eventType)
                            )}
                          >
                            {getEventTypeLabel(event.eventType)}
                          </span>
                          {event.isCompleted && (
                            <span className="inline-block px-2 py-0.5 text-xs font-medium rounded-full bg-[var(--status-success-bg)] text-[var(--status-success-text)] border border-[var(--status-success-border)]">
                              Completed
                            </span>
                          )}
                          {event.followUpDate && event.followUpDone && (
                            <span className="inline-block px-2 py-0.5 text-xs font-medium rounded-full bg-[var(--status-success-bg)] text-[var(--status-success-text)] border border-[var(--status-success-border)]">
                              Follow-up sent
                            </span>
                          )}
                          {event.followUpDate && !event.followUpDone && (() => {
                            const fDate = new Date(event.followUpDate + 'T00:00:00')
                            fDate.setHours(0, 0, 0, 0)
                            const now = new Date()
                            now.setHours(0, 0, 0, 0)
                            if (fDate.getTime() < now.getTime()) {
                              return (
                                <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-[var(--status-error-bg)] text-[var(--status-error-text)] border border-[var(--status-error-border)]">
                                  <AlertCircle className="w-3 h-3" />
                                  Follow-up overdue
                                </span>
                              )
                            }
                            return (
                              <span className="inline-block px-2 py-0.5 text-xs font-medium rounded-full bg-[var(--status-warning-bg)] text-[var(--status-warning-text)] border border-[var(--status-warning-border)]">
                                Follow-up pending
                              </span>
                            )
                          })()}
                        </div>
                        <h4 className="font-medium text-[var(--ink)]">{event.company}</h4>
                        <p className="text-sm text-[var(--muted)]">{event.position}</p>
                        <div className="flex flex-wrap items-center gap-3 mt-2 text-sm text-[var(--muted)]">
                          <span className="flex items-center gap-1">
                            <Calendar className="w-3.5 h-3.5" />
                            {new Date(event.scheduledDate + 'T00:00:00').toLocaleDateString()}
                          </span>
                          {event.interviewerNames && event.interviewerNames.length > 0 && (
                            <span className="flex items-center gap-1">
                              <Users className="w-3.5 h-3.5" />
                              {event.interviewerNames.join(', ')}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-1 flex-shrink-0">
                        {event.followUpDate && !event.followUpDone && (
                          <button
                            onClick={() => { void onToggleFollowUp(event.id) }}
                            className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium bg-[var(--status-warning-bg)] text-[var(--status-warning-text)] rounded-[var(--radius-md)] border border-[var(--status-warning-border)] hover:opacity-80"
                            aria-label="Mark follow-up done"
                          >
                            <Check className="w-3 h-3" />
                            Follow-up done
                          </button>
                        )}
                        <button
                          onClick={() => openEditModal(event)}
                          className="p-1 text-[var(--muted-soft)] hover:text-[var(--accent)]"
                          aria-label="Edit event"
                        >
                          <Edit3 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => {
                            if (confirm('Delete this event?')) {
                              void onDeleteEvent(event.id)
                            }
                          }}
                          className="p-1 text-[var(--muted-soft)] hover:text-[var(--status-error-text)]"
                          aria-label="Delete event"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* Add/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="surface-card-strong max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-4 glass-divider">
              <h2 className="text-xl font-bold font-display text-[var(--ink)]">
                {editingEvent ? 'Edit Interview Event' : 'Add Interview Event'}
              </h2>
              <button
                onClick={() => {
                  setShowModal(false)
                  resetForm()
                }}
                className="p-1 text-[var(--muted-soft)] hover:text-[var(--muted)]"
                aria-label="Close modal"
              >
                <X className="w-6 h-6" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-4 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="event-company" className="glass-label">
                    Company
                  </label>
                  <input
                    id="event-company"
                    type="text"
                    required
                    value={formData.company}
                    onChange={(e) => setFormData({ ...formData, company: e.target.value })}
                    className="glass-input"
                    placeholder="e.g., Google"
                  />
                </div>
                <div>
                  <label htmlFor="event-position" className="glass-label">
                    Position
                  </label>
                  <input
                    id="event-position"
                    type="text"
                    required
                    value={formData.position}
                    onChange={(e) => setFormData({ ...formData, position: e.target.value })}
                    className="glass-input"
                    placeholder="e.g., Senior Software Engineer"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label htmlFor="event-type" className="glass-label">
                    Event Type
                  </label>
                  <select
                    id="event-type"
                    value={formData.eventType}
                    onChange={(e) => setFormData({ ...formData, eventType: e.target.value })}
                    className="glass-select"
                  >
                    {EVENT_TYPE_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label htmlFor="event-date" className="glass-label">
                    Date
                  </label>
                  <input
                    id="event-date"
                    type="date"
                    required
                    value={formData.scheduledDate}
                    onChange={(e) => setFormData({ ...formData, scheduledDate: e.target.value })}
                    className="glass-input"
                  />
                </div>
                <div>
                  <label htmlFor="event-time" className="glass-label">
                    Time
                  </label>
                  <input
                    id="event-time"
                    type="time"
                    value={formData.scheduledTime}
                    onChange={(e) => setFormData({ ...formData, scheduledTime: e.target.value })}
                    className="glass-input"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="event-duration" className="glass-label">
                    Duration (minutes)
                  </label>
                  <input
                    id="event-duration"
                    type="number"
                    min="0"
                    value={formData.durationMinutes}
                    onChange={(e) => setFormData({ ...formData, durationMinutes: e.target.value })}
                    className="glass-input"
                    placeholder="e.g., 60"
                  />
                </div>
                <div>
                  <label htmlFor="event-location" className="glass-label">
                    Location
                  </label>
                  <input
                    id="event-location"
                    type="text"
                    value={formData.location}
                    onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                    className="glass-input"
                    placeholder="e.g., Office / Remote"
                  />
                </div>
              </div>

              <div>
                <label htmlFor="event-meeting-link" className="glass-label">
                  Meeting Link
                </label>
                <input
                  id="event-meeting-link"
                  type="url"
                  value={formData.meetingLink}
                  onChange={(e) => setFormData({ ...formData, meetingLink: e.target.value })}
                  className="glass-input"
                  placeholder="e.g., https://zoom.us/j/..."
                />
              </div>

              <div>
                <label htmlFor="event-interviewers" className="glass-label">
                  Interviewer Names (comma-separated)
                </label>
                <input
                  id="event-interviewers"
                  type="text"
                  value={formData.interviewerNames}
                  onChange={(e) => setFormData({ ...formData, interviewerNames: e.target.value })}
                  className="glass-input"
                  placeholder="e.g., Jane Doe, John Smith"
                />
              </div>

              <div>
                <label htmlFor="event-notes" className="glass-label">
                  Notes
                </label>
                <textarea
                  id="event-notes"
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  rows={3}
                  className="glass-textarea"
                  placeholder="Any preparation notes or details..."
                />
              </div>

              <div>
                <label htmlFor="event-followup-date" className="glass-label">
                  Follow-up Date
                </label>
                <input
                  id="event-followup-date"
                  type="date"
                  value={formData.followUpDate}
                  onChange={(e) => setFormData({ ...formData, followUpDate: e.target.value })}
                  className="glass-input"
                />
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setShowModal(false)
                    resetForm()
                  }}
                  className="flex-1 py-2 text-[var(--muted)] hover:bg-[var(--surface)] rounded-[var(--radius-md)] font-semibold text-sm"
                >
                  Cancel
                </button>
                <button type="submit" className="glass-button-primary flex-1">
                  <Save className="w-5 h-5 mr-2" />
                  {editingEvent ? 'Update Event' : 'Save Event'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

// ============================================================================
// Main Page Component
// ============================================================================

export default function InterviewCenterPage() {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth()

  // State
  const [activeTab, setActiveTab] = useState<TabType>('questions')
  const [resumes, setResumes] = useState<Resume[]>([])
  const [selectedResume, setSelectedResume] = useState<Resume | null>(null)
  const [jobDescription, setJobDescription] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [starStories, setStarStories] = useState<STARStory[]>([])
  const [companyResearch, setCompanyResearch] = useState<CompanyResearch>({
    companyName: '',
    talkingPoints: [],
    notes: '',
    checklist: RESEARCH_CHECKLIST_ITEMS,
  })
  const [interviewEvents, setInterviewEvents] = useState<InterviewEventLocal[]>([])

  // Auth redirect
  const loadData = useCallback(async () => {
    if (!isAuthenticated) return

    try {
      const resumesData = await resumesApi.list()
      setResumes(resumesData)
      if ((resumesData).length > 0) {
        setSelectedResume((resumesData)[0] ?? null)
      }
    } catch (error) {
      console.error('Failed to load resumes:', error)
    } finally {
      setIsLoading(false)
    }
  }, [isAuthenticated])

  // Load data
  useEffect(() => {
    if (isAuthenticated) {
      void loadData()
    }
  }, [isAuthenticated, loadData])

  // Load saved data from backend API (migrating localStorage on first run)
  useEffect(() => {
    if (!isAuthenticated) return
    let mounted = true

    async function loadSavedData() {
      // Migrate STAR stories from localStorage
      await migrateLocalStorage<{ title: string; situation: string; task: string; action: string; result: string; tags?: string[] }, { title: string; situation: string; task: string; action: string; result: string; tags: string[] }>(
        'star_stories',
        () => starStoriesApi.list(),
        (item) => starStoriesApi.create(item as Parameters<typeof starStoriesApi.create>[0]),
        (raw) => ({
          title: raw.title,
          situation: raw.situation,
          task: raw.task,
          action: raw.action,
          result: raw.result,
          tags: raw.tags ?? [],
        })
      ).catch((err) => console.warn('STAR stories migration skipped:', err))

      // Migrate company research from localStorage
      await migrateLocalStorage<{ companyName: string; talkingPoints?: string[]; notes?: string; checklist?: { label?: string; checked?: boolean }[] }, { company_name: string; talking_points: string[]; notes: string; checklist: { text: string; done: boolean }[] }>(
        'company_research',
        () => companyResearchApi.list(),
        (item) => companyResearchApi.create(item as Parameters<typeof companyResearchApi.create>[0]),
        (raw) => ({
          company_name: raw.companyName,
          talking_points: raw.talkingPoints ?? [],
          notes: raw.notes ?? '',
          checklist: (raw.checklist ?? []).map((c) => ({ text: c.label ?? '', done: c.checked ?? false })),
        })
      ).catch((err) => console.warn('Company research migration skipped:', err))

      // Load from API
      try {
        const [stories, research, eventsList] = await Promise.all([
          starStoriesApi.list(),
          companyResearchApi.list(),
          interviewEventsApi.list(),
        ])
        if (mounted) {
          setStarStories(stories.map(apiStoryToLocal))
          if (research.length > 0 && research[0]) {
            setCompanyResearch(apiResearchToLocal(research[0]))
          }
          setInterviewEvents(eventsList.map(apiEventToLocal))
        }
      } catch (error) {
        console.error('Failed to load saved data:', error)
      }
    }

    void loadSavedData()
    return () => { mounted = false }
  }, [isAuthenticated])

  const handleSaveStory = async (story: STARStory) => {
    try {
      const existingIndex = starStories.findIndex((s) => s.id === story.id)
      if (existingIndex >= 0 && typeof story.id === 'number') {
        // Update existing
        const updated = await starStoriesApi.update(story.id, {
          title: story.title,
          situation: story.situation,
          task: story.task,
          action: story.action,
          result: story.result,
          tags: story.tags,
        })
        setStarStories((prev) => prev.map((s) => s.id === story.id ? apiStoryToLocal(updated) : s))
      } else {
        // Create new
        const created = await starStoriesApi.create({
          title: story.title,
          situation: story.situation,
          task: story.task,
          action: story.action,
          result: story.result,
          tags: story.tags,
        })
        setStarStories((prev) => [...prev, apiStoryToLocal(created)])
      }
    } catch (error) {
      console.error('Failed to save story:', error)
    }
  }

  const handleDeleteStory = async (id: string | number) => {
    try {
      if (typeof id === 'number') {
        await starStoriesApi.delete(id)
      }
      setStarStories((prev) => prev.filter((s) => s.id !== id))
    } catch (error) {
      console.error('Failed to delete story:', error)
    }
  }

  const handleUpdateResearch = async (research: CompanyResearch) => {
    setCompanyResearch(research)
    try {
      const apiData = {
        company_name: research.companyName,
        talking_points: research.talkingPoints,
        notes: research.notes,
        checklist: research.checklist.map((c) => ({
          text: c.label ?? c.text ?? '',
          done: c.checked ?? c.done ?? false,
        })),
      }

      if (research.id && typeof research.id === 'number') {
        const updated = await companyResearchApi.update(research.id, apiData)
        setCompanyResearch(apiResearchToLocal(updated))
      } else {
        const created = await companyResearchApi.create(apiData as Parameters<typeof companyResearchApi.create>[0])
        setCompanyResearch(apiResearchToLocal(created))
      }
    } catch (error) {
      console.error('Failed to save company research:', error)
    }
  }

  const handleSaveEvent = async (event: Omit<InterviewEventLocal, 'id' | 'createdAt' | 'updatedAt'> & { id?: number }) => {
    try {
      const apiData = localEventToApi(event)
      if (event.id) {
        const updated = await interviewEventsApi.update(event.id, apiData)
        setInterviewEvents((prev) => prev.map((ev) => ev.id === event.id ? apiEventToLocal(updated) : ev))
      } else {
        const created = await interviewEventsApi.create(apiData)
        setInterviewEvents((prev) => [...prev, apiEventToLocal(created)])
      }
    } catch (error) {
      console.error('Failed to save event:', error)
    }
  }

  const handleDeleteEvent = async (id: number) => {
    try {
      await interviewEventsApi.delete(id)
      setInterviewEvents((prev) => prev.filter((ev) => ev.id !== id))
    } catch (error) {
      console.error('Failed to delete event:', error)
    }
  }

  const handleMarkComplete = async (id: number) => {
    try {
      const updated = await interviewEventsApi.update(id, { is_completed: true })
      setInterviewEvents((prev) => prev.map((ev) => ev.id === id ? apiEventToLocal(updated) : ev))
    } catch (error) {
      console.error('Failed to mark event complete:', error)
    }
  }

  const handleToggleFollowUp = async (id: number) => {
    try {
      const event = interviewEvents.find((ev) => ev.id === id)
      if (!event) return
      const updated = await interviewEventsApi.update(id, { follow_up_done: !event.followUpDone })
      setInterviewEvents((prev) => prev.map((ev) => ev.id === id ? apiEventToLocal(updated) : ev))
    } catch (error) {
      console.error('Failed to toggle follow-up:', error)
    }
  }

  // Loading state
  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[var(--accent)]" />
      </div>
    )
  }

  if (!user || !isAuthenticated) {
    return null
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[var(--accent)]" />
      </div>
    )
  }

  const tabs = [
    { id: 'questions' as const, label: 'Question Bank', icon: BookOpen },
    { id: 'star' as const, label: 'STAR Builder', icon: Star },
    { id: 'research' as const, label: 'Company Research', icon: Building2 },
    { id: 'practice' as const, label: 'Practice Mode', icon: Target },
    { id: 'events' as const, label: 'Interview Events', icon: CalendarClock },
  ]

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold font-display tracking-[-0.02em] text-[var(--ink)]">Interview Center</h1>
        <p className="text-[var(--muted)]">
          Prepare for interviews with AI-powered tools and practice sessions
        </p>
      </div>

      {/* Context Selection */}
      <div className="surface-card p-4 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label htmlFor="resume-select" className="glass-label">
              Select Resume (for personalized answers)
            </label>
            <select
              id="resume-select"
              value={selectedResume?.id || ''}
              onChange={(e) => {
                const resume = resumes.find((r) => r.id === Number(e.target.value))
                setSelectedResume(resume || null)
              }}
              className="glass-select"
            >
              <option value="">No resume selected</option>
              {resumes.map((resume) => (
                <option key={resume.id} value={resume.id}>
                  {resume.version_name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="job-description" className="glass-label">
              Job Description (optional)
            </label>
            <textarea
              id="job-description"
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              rows={2}
              className="glass-textarea"
              placeholder="Paste job description for more relevant answers..."
            />
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="glass-tabs mb-6">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              'glass-tab',
              activeTab === tab.id && 'glass-tab-active'
            )}
            aria-current={activeTab === tab.id ? 'page' : undefined}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content - Wrapped in Suspense for better code splitting */}
      <Suspense fallback={<TabLoadingSkeleton />}>
        {activeTab === 'questions' && (
          <QuestionBankTab
            resumes={resumes}
            selectedResume={selectedResume}
            jobDescription={jobDescription}
          />
        )}

        {activeTab === 'star' && (
          <STARBuilderTab
            stories={starStories}
            onSaveStory={(story) => { void handleSaveStory(story) }}
            onDeleteStory={(id) => { void handleDeleteStory(id) }}
          />
        )}

        {activeTab === 'research' && (
          <CompanyResearchTab
            research={companyResearch}
            onUpdateResearch={(r) => { void handleUpdateResearch(r) }}
          />
        )}

        {activeTab === 'practice' && (
          <PracticeModeTab
            resumes={resumes}
            selectedResume={selectedResume}
            jobDescription={jobDescription}
          />
        )}

        {activeTab === 'events' && (
          <InterviewEventsTab
            events={interviewEvents}
            onSaveEvent={(event) => { void handleSaveEvent(event) }}
            onDeleteEvent={(id) => { void handleDeleteEvent(id) }}
            onMarkComplete={(id) => { void handleMarkComplete(id) }}
            onToggleFollowUp={(id) => { void handleToggleFollowUp(id) }}
          />
        )}
      </Suspense>
    </div>
  )
}
