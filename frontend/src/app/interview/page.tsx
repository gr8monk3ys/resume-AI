'use client'

import { useEffect, useState, useMemo, useCallback, useRef } from 'react'
import { useAuth } from '@/lib/auth'
import { useRouter } from 'next/navigation'
import { aiApi, resumesApi } from '@/lib/api'
import type { Resume, InterviewPrepResponse } from '@/types'
import { cn, generateId } from '@/lib/utils'
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
  Plus,
  Trash2,
  Import,
  X,
  Copy,
  Check,
} from 'lucide-react'

// ============================================================================
// Types
// ============================================================================

type TabType = 'questions' | 'star' | 'research' | 'practice'

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
  id: string
  title: string
  situation: string
  task: string
  action: string
  result: string
  tags: string[]
  createdAt: string
}

interface CompanyResearch {
  companyName: string
  talkingPoints: string[]
  notes: string
  checklist: {
    id: string
    label: string
    checked: boolean
  }[]
}

interface PracticeSession {
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
  Behavioral: 'bg-blue-100 text-blue-800 border-blue-200',
  Technical: 'bg-purple-100 text-purple-800 border-purple-200',
  Situational: 'bg-amber-100 text-amber-800 border-amber-200',
  'Company/Role': 'bg-green-100 text-green-800 border-green-200',
  'Career Goals': 'bg-pink-100 text-pink-800 border-pink-200',
}

// ============================================================================
// Question Bank Tab
// ============================================================================

interface QuestionBankTabProps {
  token: string
  resumes: Resume[]
  selectedResume: Resume | null
  jobDescription: string
}

function QuestionBankTab({
  token,
  resumes,
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
      const response = await aiApi.interviewPrep(token, {
        question: question.text,
        resume_content: selectedResume?.content,
        job_description: jobDescription || undefined,
        use_star_method: question.category === 'Behavioral',
      })
      setExampleAnswers((prev) => ({
        ...prev,
        [question.id]: (response as InterviewPrepResponse).answer,
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
      const response = await aiApi.interviewPrep(token, {
        question: `Please provide feedback on this interview answer. Question: "${practiceQuestion.text}" Answer: "${practiceAnswer}"`,
        resume_content: selectedResume?.content,
        job_description: jobDescription || undefined,
      })
      setFeedback((response as InterviewPrepResponse).answer)
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
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => setSelectedCategory('All')}
          className={cn(
            'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
            selectedCategory === 'All'
              ? 'bg-primary-600 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          )}
        >
          All Questions
        </button>
        {QUESTION_CATEGORIES.map((category) => (
          <button
            key={category}
            onClick={() => setSelectedCategory(category)}
            className={cn(
              'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
              selectedCategory === category
                ? 'bg-primary-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
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
            className="bg-white rounded-lg shadow border border-gray-200 overflow-hidden"
          >
            <div
              className="p-4 cursor-pointer hover:bg-gray-50"
              onClick={() => toggleExpand(question.id)}
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
                  <p className="text-gray-900 font-medium">{question.text}</p>
                </div>
                {expandedQuestions.has(question.id) ? (
                  <ChevronUp className="w-5 h-5 text-gray-400 flex-shrink-0" />
                ) : (
                  <ChevronDown className="w-5 h-5 text-gray-400 flex-shrink-0" />
                )}
              </div>
            </div>

            {expandedQuestions.has(question.id) && (
              <div className="px-4 pb-4 border-t border-gray-100">
                {/* Tips */}
                <div className="mt-4">
                  <h4 className="text-sm font-medium text-gray-700 flex items-center gap-2 mb-2">
                    <Lightbulb className="w-4 h-4 text-amber-500" />
                    Tips for answering
                  </h4>
                  <ul className="space-y-1">
                    {question.tips.map((tip, index) => (
                      <li key={index} className="text-sm text-gray-600 flex items-start gap-2">
                        <span className="text-primary-600 mt-0.5">-</span>
                        {tip}
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Example Answer */}
                {exampleAnswers[question.id] && (
                  <div className="mt-4 p-3 bg-green-50 rounded-lg border border-green-200">
                    <h4 className="text-sm font-medium text-green-800 mb-2">Example Answer</h4>
                    <p className="text-sm text-green-700 whitespace-pre-wrap">
                      {exampleAnswers[question.id]}
                    </p>
                  </div>
                )}

                {/* Action Buttons */}
                <div className="mt-4 flex flex-wrap gap-2">
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      generateExampleAnswer(question)
                    }}
                    disabled={generatingExample === question.id}
                    className="inline-flex items-center px-3 py-1.5 text-sm bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50"
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
                    className="inline-flex items-center px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200"
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
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-4 border-b">
              <h2 className="text-xl font-bold text-gray-900">Practice Mode</h2>
              <button
                onClick={() => {
                  setPracticeQuestion(null)
                  setPracticeAnswer('')
                  setFeedback(null)
                }}
                className="p-1 text-gray-400 hover:text-gray-600"
                aria-label="Close modal"
              >
                <X className="w-6 h-6" />
              </button>
            </div>

            <div className="p-4 space-y-4">
              <div className="p-4 bg-gray-50 rounded-lg">
                <span
                  className={cn(
                    'inline-block px-2 py-1 text-xs font-medium rounded-full mb-2',
                    CATEGORY_COLORS[practiceQuestion.category]
                  )}
                >
                  {practiceQuestion.category}
                </span>
                <p className="text-gray-900 font-medium">{practiceQuestion.text}</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Your Answer
                </label>
                <textarea
                  value={practiceAnswer}
                  onChange={(e) => setPracticeAnswer(e.target.value)}
                  rows={8}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="Type your answer here..."
                />
              </div>

              <button
                onClick={handleGetFeedback}
                disabled={!practiceAnswer.trim() || isGettingFeedback}
                className="w-full py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 flex items-center justify-center"
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
                <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                  <h4 className="text-sm font-medium text-blue-800 mb-2 flex items-center gap-2">
                    <MessageSquare className="w-4 h-4" />
                    AI Feedback
                  </h4>
                  <p className="text-sm text-blue-700 whitespace-pre-wrap">{feedback}</p>
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
  token: string
  stories: STARStory[]
  onSaveStory: (story: STARStory) => void
  onDeleteStory: (id: string) => void
}

function STARBuilderTab({ token, stories, onSaveStory, onDeleteStory }: STARBuilderTabProps) {
  const [formData, setFormData] = useState({
    title: '',
    situation: '',
    task: '',
    action: '',
    result: '',
    tags: '',
  })
  const [editingId, setEditingId] = useState<string | null>(null)
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
    onSaveStory(story)
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

      const response = await aiApi.interviewPrep(token, {
        question: `Please polish and improve this STAR story while keeping the same structure. Make it more compelling and professional: ${storyText}`,
        use_star_method: true,
      })
      setPolishedStory((response as InterviewPrepResponse).answer)
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
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Star className="w-5 h-5 text-amber-500" />
          {editingId ? 'Edit STAR Story' : 'Create STAR Story'}
        </h3>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Story Title
            </label>
            <input
              type="text"
              required
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="e.g., Led cross-functional project"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              <span className="inline-flex items-center gap-1">
                <span className="w-5 h-5 rounded-full bg-blue-100 text-blue-800 text-xs flex items-center justify-center font-bold">
                  S
                </span>
                Situation
              </span>
            </label>
            <textarea
              required
              value={formData.situation}
              onChange={(e) => setFormData({ ...formData, situation: e.target.value })}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="Describe the context and background..."
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              <span className="inline-flex items-center gap-1">
                <span className="w-5 h-5 rounded-full bg-green-100 text-green-800 text-xs flex items-center justify-center font-bold">
                  T
                </span>
                Task
              </span>
            </label>
            <textarea
              required
              value={formData.task}
              onChange={(e) => setFormData({ ...formData, task: e.target.value })}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="What was your responsibility or goal?"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              <span className="inline-flex items-center gap-1">
                <span className="w-5 h-5 rounded-full bg-amber-100 text-amber-800 text-xs flex items-center justify-center font-bold">
                  A
                </span>
                Action
              </span>
            </label>
            <textarea
              required
              value={formData.action}
              onChange={(e) => setFormData({ ...formData, action: e.target.value })}
              rows={4}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="What specific actions did you take?"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              <span className="inline-flex items-center gap-1">
                <span className="w-5 h-5 rounded-full bg-purple-100 text-purple-800 text-xs flex items-center justify-center font-bold">
                  R
                </span>
                Result
              </span>
            </label>
            <textarea
              required
              value={formData.result}
              onChange={(e) => setFormData({ ...formData, result: e.target.value })}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="What was the outcome? Include metrics if possible..."
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Tags (comma separated)
            </label>
            <input
              type="text"
              value={formData.tags}
              onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="e.g., leadership, problem-solving, teamwork"
            />
          </div>

          <div className="flex gap-2 pt-2">
            <button
              type="button"
              onClick={handlePolish}
              disabled={isPolishing || !formData.situation || !formData.task || !formData.action || !formData.result}
              className="flex-1 py-2 bg-amber-500 text-white rounded-lg hover:bg-amber-600 disabled:opacity-50 flex items-center justify-center"
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
              className="flex-1 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 flex items-center justify-center"
            >
              <Save className="w-5 h-5 mr-2" />
              {editingId ? 'Update Story' : 'Save Story'}
            </button>
          </div>

          {editingId && (
            <button
              type="button"
              onClick={resetForm}
              className="w-full py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
            >
              Cancel Editing
            </button>
          )}
        </form>

        {/* Polished Story Output */}
        {polishedStory && (
          <div className="mt-4 p-4 bg-amber-50 rounded-lg border border-amber-200">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-medium text-amber-800">AI Polished Version</h4>
              <button
                onClick={() => copyToClipboard(polishedStory, 'polished')}
                className="p-1 text-amber-600 hover:text-amber-800"
                aria-label="Copy to clipboard"
              >
                {copiedField === 'polished' ? (
                  <Check className="w-4 h-4" />
                ) : (
                  <Copy className="w-4 h-4" />
                )}
              </button>
            </div>
            <p className="text-sm text-amber-700 whitespace-pre-wrap">{polishedStory}</p>
          </div>
        )}
      </div>

      {/* Saved Stories */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-primary-600" />
          Saved Stories ({stories.length})
        </h3>

        {stories.length === 0 ? (
          <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
            <Star className="w-12 h-12 mx-auto mb-4 text-gray-300" />
            <p>No STAR stories saved yet</p>
            <p className="text-sm mt-1">Create your first story using the form</p>
          </div>
        ) : (
          <div className="space-y-4">
            {stories.map((story) => (
              <div key={story.id} className="bg-white rounded-lg shadow p-4">
                <div className="flex items-start justify-between mb-2">
                  <h4 className="font-medium text-gray-900">{story.title}</h4>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => editStory(story)}
                      className="p-1 text-gray-400 hover:text-primary-600"
                      aria-label="Edit story"
                    >
                      <MessageSquare className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => {
                        if (confirm('Delete this story?')) {
                          onDeleteStory(story.id)
                        }
                      }}
                      className="p-1 text-gray-400 hover:text-red-600"
                      aria-label="Delete story"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {story.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1 mb-3">
                    {story.tags.map((tag, index) => (
                      <span
                        key={index}
                        className="px-2 py-0.5 text-xs bg-gray-100 text-gray-600 rounded-full"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                )}

                <div className="space-y-2 text-sm">
                  <div>
                    <span className="font-medium text-blue-600">S:</span>{' '}
                    <span className="text-gray-600">{story.situation.slice(0, 100)}...</span>
                  </div>
                  <div>
                    <span className="font-medium text-green-600">T:</span>{' '}
                    <span className="text-gray-600">{story.task.slice(0, 100)}...</span>
                  </div>
                  <div>
                    <span className="font-medium text-amber-600">A:</span>{' '}
                    <span className="text-gray-600">{story.action.slice(0, 100)}...</span>
                  </div>
                  <div>
                    <span className="font-medium text-purple-600">R:</span>{' '}
                    <span className="text-gray-600">{story.result.slice(0, 100)}...</span>
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
  token: string
  research: CompanyResearch
  onUpdateResearch: (research: CompanyResearch) => void
}

function CompanyResearchTab({ token, research, onUpdateResearch }: CompanyResearchTabProps) {
  const [companyInput, setCompanyInput] = useState(research.companyName)
  const [isGenerating, setIsGenerating] = useState(false)

  const handleGenerateTalkingPoints = async () => {
    if (!companyInput.trim()) return
    setIsGenerating(true)
    try {
      const response = await aiApi.interviewPrep(token, {
        question: `Generate interview talking points and research insights for someone interviewing at ${companyInput}. Include: company background, recent news, culture insights, and suggested questions to ask. Format as bullet points.`,
      })

      const points = (response as InterviewPrepResponse).answer
        .split('\n')
        .filter((line) => line.trim())
        .map((line) => line.replace(/^[-*]\s*/, '').trim())
        .filter((line) => line.length > 0)

      onUpdateResearch({
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

  const toggleChecklistItem = (itemId: string) => {
    const updatedChecklist = research.checklist.map((item) =>
      item.id === itemId ? { ...item, checked: !item.checked } : item
    )
    onUpdateResearch({ ...research, checklist: updatedChecklist })
  }

  const completedCount = research.checklist.filter((item) => item.checked).length

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Research Input */}
      <div className="lg:col-span-2 space-y-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Building2 className="w-5 h-5 text-primary-600" />
            Company Research
          </h3>

          <div className="flex gap-2 mb-4">
            <input
              type="text"
              value={companyInput}
              onChange={(e) => setCompanyInput(e.target.value)}
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="Enter company name..."
            />
            <button
              onClick={handleGenerateTalkingPoints}
              disabled={isGenerating || !companyInput.trim()}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 flex items-center"
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
              <h4 className="text-sm font-medium text-gray-700 flex items-center gap-2">
                <Lightbulb className="w-4 h-4 text-amber-500" />
                AI-Generated Talking Points
              </h4>
              <ul className="space-y-2">
                {research.talkingPoints.map((point, index) => (
                  <li
                    key={index}
                    className="p-3 bg-gray-50 rounded-lg text-sm text-gray-700 flex items-start gap-2"
                  >
                    <Target className="w-4 h-4 text-primary-600 mt-0.5 flex-shrink-0" />
                    {point}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Notes */}
          <div className="mt-6">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Your Research Notes
            </label>
            <textarea
              value={research.notes}
              onChange={(e) => onUpdateResearch({ ...research, notes: e.target.value })}
              rows={6}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="Add your own research notes here..."
            />
          </div>
        </div>
      </div>

      {/* Research Checklist */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <CheckCircle className="w-5 h-5 text-green-600" />
          Research Checklist
        </h3>

        <div className="mb-4">
          <div className="flex justify-between text-sm text-gray-600 mb-1">
            <span>Progress</span>
            <span>
              {completedCount} / {research.checklist.length}
            </span>
          </div>
          <div className="w-full bg-gray-100 rounded-full h-2">
            <div
              className="bg-green-500 h-2 rounded-full transition-all"
              style={{
                width: `${(completedCount / research.checklist.length) * 100}%`,
              }}
            />
          </div>
        </div>

        <ul className="space-y-2">
          {research.checklist.map((item) => (
            <li key={item.id}>
              <label className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 cursor-pointer">
                <input
                  type="checkbox"
                  checked={item.checked}
                  onChange={() => toggleChecklistItem(item.id)}
                  className="w-4 h-4 text-primary-600 rounded border-gray-300 focus:ring-primary-500"
                />
                <span
                  className={cn(
                    'text-sm',
                    item.checked ? 'text-gray-400 line-through' : 'text-gray-700'
                  )}
                >
                  {item.label}
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
  token: string
  resumes: Resume[]
  selectedResume: Resume | null
  jobDescription: string
}

function PracticeModeTab({
  token,
  resumes,
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
    setCurrentQuestion(question)
    setAnswer('')
    setFeedback(null)
    resetTimer()
  }

  const handleGetFeedback = async () => {
    if (!currentQuestion || !answer.trim()) return
    pauseTimer()
    setIsGettingFeedback(true)
    try {
      const response = await aiApi.interviewPrep(token, {
        question: `You are an interview coach. Evaluate this interview answer and provide:
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
        resume_content: selectedResume?.content,
        job_description: jobDescription || undefined,
      })

      const responseText = (response as InterviewPrepResponse).answer

      // Parse the response
      const scoreMatch = responseText.match(/SCORE:\s*(\d+)/i)
      const score = scoreMatch ? parseInt(scoreMatch[1], 10) : 5

      const analysisMatch = responseText.match(/ANALYSIS:\s*([\s\S]*?)(?=SUGGESTIONS:|$)/i)
      const analysis = analysisMatch ? analysisMatch[1].trim() : responseText

      const suggestionsMatch = responseText.match(/SUGGESTIONS:\s*([\s\S]*)/i)
      const suggestionsText = suggestionsMatch ? suggestionsMatch[1] : ''
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
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700">Category:</label>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value as QuestionCategory)}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
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
            className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 flex items-center"
          >
            <Shuffle className="w-5 h-5 mr-2" />
            Random Question
          </button>

          {/* Timer */}
          <div className="flex items-center gap-2 ml-auto">
            <Clock className="w-5 h-5 text-gray-500" />
            <span className="text-xl font-mono font-bold text-gray-900 w-16">
              {formatTime(timer)}
            </span>
            <button
              onClick={isTimerRunning ? pauseTimer : startTimer}
              className="p-2 rounded-lg hover:bg-gray-100"
              aria-label={isTimerRunning ? 'Pause timer' : 'Start timer'}
            >
              {isTimerRunning ? (
                <Pause className="w-5 h-5 text-gray-600" />
              ) : (
                <Play className="w-5 h-5 text-gray-600" />
              )}
            </button>
            <button
              onClick={resetTimer}
              className="p-2 rounded-lg hover:bg-gray-100"
              aria-label="Reset timer"
            >
              <RotateCcw className="w-5 h-5 text-gray-600" />
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
              <div className="bg-white rounded-lg shadow p-6">
                <span
                  className={cn(
                    'inline-block px-2 py-1 text-xs font-medium rounded-full mb-3',
                    CATEGORY_COLORS[currentQuestion.category]
                  )}
                >
                  {currentQuestion.category}
                </span>
                <p className="text-lg font-medium text-gray-900">{currentQuestion.text}</p>
              </div>

              {/* Answer Input */}
              <div className="bg-white rounded-lg shadow p-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Your Answer
                </label>
                <textarea
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                  rows={10}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="Type your answer here... Use the STAR method for behavioral questions."
                />

                <button
                  onClick={handleGetFeedback}
                  disabled={!answer.trim() || isGettingFeedback}
                  className="mt-4 w-full py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 flex items-center justify-center"
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
                <div className="bg-white rounded-lg shadow p-6">
                  <div className="flex items-center gap-4 mb-4">
                    <div
                      className={cn(
                        'w-16 h-16 rounded-full flex items-center justify-center text-2xl font-bold',
                        feedback.score >= 8
                          ? 'bg-green-100 text-green-800'
                          : feedback.score >= 6
                          ? 'bg-amber-100 text-amber-800'
                          : 'bg-red-100 text-red-800'
                      )}
                    >
                      {feedback.score}/10
                    </div>
                    <div>
                      <h4 className="font-semibold text-gray-900">Your Score</h4>
                      <p className="text-sm text-gray-500">
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
                      <h4 className="text-sm font-medium text-gray-700 mb-2">Analysis</h4>
                      <p className="text-sm text-gray-600 whitespace-pre-wrap">{feedback.text}</p>
                    </div>

                    {feedback.suggestions.length > 0 && (
                      <div>
                        <h4 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
                          <AlertCircle className="w-4 h-4 text-amber-500" />
                          Improvement Suggestions
                        </h4>
                        <ul className="space-y-2">
                          {feedback.suggestions.map((suggestion, index) => (
                            <li
                              key={index}
                              className="text-sm text-gray-600 flex items-start gap-2"
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
            <div className="bg-white rounded-lg shadow p-12 text-center">
              <Shuffle className="w-16 h-16 mx-auto mb-4 text-gray-300" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">Ready to Practice?</h3>
              <p className="text-gray-500 mb-4">
                Select a category and click "Random Question" to start practicing
              </p>
              <button
                onClick={getRandomQuestion}
                className="px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 inline-flex items-center"
              >
                <Shuffle className="w-5 h-5 mr-2" />
                Get Started
              </button>
            </div>
          )}
        </div>

        {/* Session Stats */}
        <div className="space-y-4">
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Session Stats</h3>

            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Questions Practiced</span>
                <span className="font-bold text-gray-900">{sessionHistory.length}</span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Average Score</span>
                <span className="font-bold text-gray-900">
                  {sessionHistory.length > 0 ? `${averageScore}/10` : '-'}
                </span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Total Time</span>
                <span className="font-bold text-gray-900">
                  {formatTime(sessionHistory.reduce((sum, s) => sum + s.timeSpent, 0))}
                </span>
              </div>
            </div>
          </div>

          {sessionHistory.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Practice</h3>
              <ul className="space-y-3">
                {sessionHistory
                  .slice(-5)
                  .reverse()
                  .map((session, index) => {
                    const question = SAMPLE_QUESTIONS.find((q) => q.id === session.questionId)
                    return (
                      <li key={index} className="p-3 bg-gray-50 rounded-lg">
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
                                ? 'text-green-600'
                                : (session.score || 0) >= 6
                                ? 'text-amber-600'
                                : 'text-red-600'
                            )}
                          >
                            {session.score}/10
                          </span>
                        </div>
                        <p className="text-xs text-gray-500 truncate">
                          {question?.text.slice(0, 50)}...
                        </p>
                        <p className="text-xs text-gray-400 mt-1">
                          Time: {formatTime(session.timeSpent)}
                        </p>
                      </li>
                    )
                  })}
              </ul>
            </div>
          )}

          {/* Tips Card */}
          <div className="bg-amber-50 rounded-lg border border-amber-200 p-4">
            <h4 className="text-sm font-medium text-amber-800 mb-2 flex items-center gap-2">
              <Lightbulb className="w-4 h-4" />
              Practice Tips
            </h4>
            <ul className="text-sm text-amber-700 space-y-1">
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
// Main Page Component
// ============================================================================

export default function InterviewCenterPage() {
  const { user, tokens, isLoading: authLoading } = useAuth()
  const router = useRouter()

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

  // Auth redirect
  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login')
    }
  }, [user, authLoading, router])

  // Load data
  useEffect(() => {
    if (tokens?.access_token) {
      loadData()
    }
  }, [tokens])

  // Load saved data from localStorage
  useEffect(() => {
    const storedStories = localStorage.getItem('star_stories')
    if (storedStories) {
      setStarStories(JSON.parse(storedStories))
    }

    const storedResearch = localStorage.getItem('company_research')
    if (storedResearch) {
      setCompanyResearch(JSON.parse(storedResearch))
    }
  }, [])

  const loadData = async () => {
    if (!tokens?.access_token) return

    try {
      const resumesData = await resumesApi.list(tokens.access_token)
      setResumes(resumesData as Resume[])
      if ((resumesData as Resume[]).length > 0) {
        setSelectedResume((resumesData as Resume[])[0])
      }
    } catch (error) {
      console.error('Failed to load resumes:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSaveStory = (story: STARStory) => {
    const existingIndex = starStories.findIndex((s) => s.id === story.id)
    let updatedStories: STARStory[]

    if (existingIndex >= 0) {
      updatedStories = [...starStories]
      updatedStories[existingIndex] = story
    } else {
      updatedStories = [...starStories, story]
    }

    setStarStories(updatedStories)
    localStorage.setItem('star_stories', JSON.stringify(updatedStories))
  }

  const handleDeleteStory = (id: string) => {
    const updatedStories = starStories.filter((s) => s.id !== id)
    setStarStories(updatedStories)
    localStorage.setItem('star_stories', JSON.stringify(updatedStories))
  }

  const handleUpdateResearch = (research: CompanyResearch) => {
    setCompanyResearch(research)
    localStorage.setItem('company_research', JSON.stringify(research))
  }

  // Loading state
  if (authLoading || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    )
  }

  const tabs = [
    { id: 'questions' as const, label: 'Question Bank', icon: BookOpen },
    { id: 'star' as const, label: 'STAR Builder', icon: Star },
    { id: 'research' as const, label: 'Company Research', icon: Building2 },
    { id: 'practice' as const, label: 'Practice Mode', icon: Target },
  ]

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Interview Center</h1>
        <p className="text-gray-500">
          Prepare for interviews with AI-powered tools and practice sessions
        </p>
      </div>

      {/* Context Selection */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Select Resume (for personalized answers)
            </label>
            <select
              value={selectedResume?.id || ''}
              onChange={(e) => {
                const resume = resumes.find((r) => r.id === Number(e.target.value))
                setSelectedResume(resume || null)
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
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
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Job Description (optional)
            </label>
            <textarea
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              rows={2}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="Paste job description for more relevant answers..."
            />
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="flex gap-4 -mb-px" aria-label="Tabs">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors',
                activeTab === tab.id
                  ? 'border-primary-600 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              )}
              aria-current={activeTab === tab.id ? 'page' : undefined}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'questions' && (
        <QuestionBankTab
          token={tokens?.access_token || ''}
          resumes={resumes}
          selectedResume={selectedResume}
          jobDescription={jobDescription}
        />
      )}

      {activeTab === 'star' && (
        <STARBuilderTab
          token={tokens?.access_token || ''}
          stories={starStories}
          onSaveStory={handleSaveStory}
          onDeleteStory={handleDeleteStory}
        />
      )}

      {activeTab === 'research' && (
        <CompanyResearchTab
          token={tokens?.access_token || ''}
          research={companyResearch}
          onUpdateResearch={handleUpdateResearch}
        />
      )}

      {activeTab === 'practice' && (
        <PracticeModeTab
          token={tokens?.access_token || ''}
          resumes={resumes}
          selectedResume={selectedResume}
          jobDescription={jobDescription}
        />
      )}
    </div>
  )
}
