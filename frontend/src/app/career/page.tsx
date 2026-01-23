'use client'

import { useEffect, useState, useMemo, useCallback } from 'react'
import { useAuth } from '@/lib/auth'
import { useRouter } from 'next/navigation'
import { aiApi, resumesApi } from '@/lib/api'
import type { Resume, AnswerQuestionResponse } from '@/types'
import { cn, formatDate, generateId } from '@/lib/utils'
import {
  Plus,
  Trash2,
  Edit2,
  Search,
  Tag,
  Wand2,
  DollarSign,
  MessageSquare,
  BookOpen,
  Calculator,
  FileText,
  Copy,
  Check,
  ExternalLink,
  Sparkles,
  X,
  Calendar,
  TrendingUp,
  Briefcase,
  Award,
} from 'lucide-react'

// ============================================================================
// Types
// ============================================================================

interface Achievement {
  id: string
  title: string
  description: string
  date: string
  tags: string[]
  enhancedDescription?: string
  createdAt: string
  updatedAt: string
}

interface CompensationData {
  baseSalary: number
  bonusPercentage: number
  stockValue: number
  benefitsValue: number
  otherCompensation: number
}

type NegotiationScenario = 'initial_offer' | 'counter_offer' | 'final_negotiation'

type TabType = 'journal' | 'salary' | 'qa'

// ============================================================================
// Constants
// ============================================================================

const COMMON_TAGS = [
  'Leadership',
  'Technical',
  'Project Management',
  'Communication',
  'Problem Solving',
  'Revenue',
  'Cost Savings',
  'Team Building',
  'Innovation',
  'Customer Success',
]

const NEGOTIATION_SCENARIOS: { value: NegotiationScenario; label: string; description: string }[] = [
  {
    value: 'initial_offer',
    label: 'Initial Offer Response',
    description: 'Responding to a first offer with a counter',
  },
  {
    value: 'counter_offer',
    label: 'Counter Offer',
    description: 'Making a counter offer after initial negotiation',
  },
  {
    value: 'final_negotiation',
    label: 'Final Negotiation',
    description: 'Closing the deal with final terms',
  },
]

const COMMON_QUESTIONS = [
  { value: 'why_company', label: 'Why do you want to work at this company?', type: 'motivation' as const },
  { value: 'why_role', label: 'Why are you interested in this role?', type: 'motivation' as const },
  { value: 'strength', label: 'What is your greatest strength?', type: 'strength' as const },
  { value: 'weakness', label: 'What is your greatest weakness?', type: 'weakness' as const },
  { value: 'tell_me', label: 'Tell me about yourself', type: 'general' as const },
  { value: 'achievement', label: 'Describe your greatest professional achievement', type: 'behavioral' as const },
  { value: 'conflict', label: 'Tell me about a time you resolved a conflict', type: 'behavioral' as const },
  { value: 'failure', label: 'Describe a time you failed and what you learned', type: 'behavioral' as const },
  { value: 'leadership', label: 'Give an example of when you demonstrated leadership', type: 'behavioral' as const },
  { value: 'challenge', label: 'Tell me about a challenging project you completed', type: 'behavioral' as const },
  { value: 'five_years', label: 'Where do you see yourself in 5 years?', type: 'general' as const },
  { value: 'salary', label: 'What are your salary expectations?', type: 'salary' as const },
  { value: 'leaving', label: 'Why are you leaving your current job?', type: 'general' as const },
  { value: 'teamwork', label: 'Describe how you work in a team environment', type: 'behavioral' as const },
  { value: 'pressure', label: 'How do you handle pressure and tight deadlines?', type: 'behavioral' as const },
  { value: 'disagree', label: 'Tell me about a time you disagreed with your manager', type: 'behavioral' as const },
]

const MARKET_RESEARCH_LINKS = [
  { name: 'Levels.fyi', url: 'https://www.levels.fyi', description: 'Tech company compensation data' },
  { name: 'Glassdoor', url: 'https://www.glassdoor.com/Salaries', description: 'Salary reviews and insights' },
  { name: 'PayScale', url: 'https://www.payscale.com', description: 'Salary calculator and research' },
  { name: 'LinkedIn Salary', url: 'https://www.linkedin.com/salary', description: 'Salary insights by role and location' },
  { name: 'Blind', url: 'https://www.teamblind.com', description: 'Anonymous professional network with salary data' },
  { name: 'Comparably', url: 'https://www.comparably.com', description: 'Company culture and compensation' },
]

// ============================================================================
// Storage Utilities
// ============================================================================

const ACHIEVEMENTS_STORAGE_KEY = 'career_achievements'

function getStoredAchievements(): Achievement[] {
  if (typeof window === 'undefined') return []
  try {
    const stored = localStorage.getItem(ACHIEVEMENTS_STORAGE_KEY)
    return stored ? JSON.parse(stored) : []
  } catch {
    return []
  }
}

function setStoredAchievements(achievements: Achievement[]): void {
  if (typeof window === 'undefined') return
  try {
    localStorage.setItem(ACHIEVEMENTS_STORAGE_KEY, JSON.stringify(achievements))
  } catch {
    console.error('Failed to store achievements')
  }
}

// ============================================================================
// Achievement Journal Tab
// ============================================================================

interface AchievementJournalTabProps {
  token: string
}

function AchievementJournalTab({ token }: AchievementJournalTabProps) {
  const [achievements, setAchievements] = useState<Achievement[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedTags, setSelectedTags] = useState<string[]>([])
  const [showAddModal, setShowAddModal] = useState(false)
  const [editingAchievement, setEditingAchievement] = useState<Achievement | null>(null)
  const [enhancingId, setEnhancingId] = useState<string | null>(null)
  const [isBulkEnhancing, setIsBulkEnhancing] = useState(false)

  // Load achievements from localStorage
  useEffect(() => {
    setAchievements(getStoredAchievements())
  }, [])

  // Get all unique tags
  const allTags = useMemo(() => {
    const tagSet = new Set<string>()
    achievements.forEach((a) => a.tags.forEach((t) => tagSet.add(t)))
    return Array.from(tagSet).sort()
  }, [achievements])

  // Filter achievements
  const filteredAchievements = useMemo(() => {
    return achievements.filter((achievement) => {
      // Search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase()
        const matchesSearch =
          achievement.title.toLowerCase().includes(query) ||
          achievement.description.toLowerCase().includes(query) ||
          (achievement.enhancedDescription?.toLowerCase().includes(query) ?? false)
        if (!matchesSearch) return false
      }

      // Tag filter
      if (selectedTags.length > 0) {
        const hasAllTags = selectedTags.every((tag) => achievement.tags.includes(tag))
        if (!hasAllTags) return false
      }

      return true
    })
  }, [achievements, searchQuery, selectedTags])

  const handleAddAchievement = (data: Omit<Achievement, 'id' | 'createdAt' | 'updatedAt'>) => {
    const newAchievement: Achievement = {
      ...data,
      id: generateId(),
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    }
    const updated = [newAchievement, ...achievements]
    setAchievements(updated)
    setStoredAchievements(updated)
    setShowAddModal(false)
  }

  const handleUpdateAchievement = (data: Omit<Achievement, 'id' | 'createdAt' | 'updatedAt'>) => {
    if (!editingAchievement) return
    const updated = achievements.map((a) =>
      a.id === editingAchievement.id
        ? { ...a, ...data, updatedAt: new Date().toISOString() }
        : a
    )
    setAchievements(updated)
    setStoredAchievements(updated)
    setEditingAchievement(null)
  }

  const handleDeleteAchievement = (id: string) => {
    if (!confirm('Are you sure you want to delete this achievement?')) return
    const updated = achievements.filter((a) => a.id !== id)
    setAchievements(updated)
    setStoredAchievements(updated)
  }

  const handleEnhanceAchievement = async (achievement: Achievement) => {
    setEnhancingId(achievement.id)
    try {
      // Use the AI API to enhance the description
      const response = await aiApi.answerQuestion(token, {
        question: `Transform this raw achievement note into a polished, quantified resume bullet point using action verbs. Keep it concise (1-2 sentences max). Original: "${achievement.description}"`,
        question_type: 'general',
        max_length: 200,
      })

      const enhanced = (response as AnswerQuestionResponse).answer
      const updated = achievements.map((a) =>
        a.id === achievement.id
          ? { ...a, enhancedDescription: enhanced, updatedAt: new Date().toISOString() }
          : a
      )
      setAchievements(updated)
      setStoredAchievements(updated)
    } catch (error) {
      console.error('Failed to enhance achievement:', error)
      alert('Failed to enhance achievement. Please try again.')
    } finally {
      setEnhancingId(null)
    }
  }

  const handleBulkEnhance = async () => {
    const toEnhance = achievements.filter((a) => !a.enhancedDescription)
    if (toEnhance.length === 0) {
      alert('All achievements are already enhanced.')
      return
    }

    if (!confirm(`This will enhance ${toEnhance.length} achievement(s). Continue?`)) return

    setIsBulkEnhancing(true)
    let updatedAchievements = [...achievements]

    for (const achievement of toEnhance) {
      try {
        const response = await aiApi.answerQuestion(token, {
          question: `Transform this raw achievement note into a polished, quantified resume bullet point using action verbs. Keep it concise (1-2 sentences max). Original: "${achievement.description}"`,
          question_type: 'general',
          max_length: 200,
        })

        const enhanced = (response as AnswerQuestionResponse).answer
        updatedAchievements = updatedAchievements.map((a) =>
          a.id === achievement.id
            ? { ...a, enhancedDescription: enhanced, updatedAt: new Date().toISOString() }
            : a
        )
      } catch (error) {
        console.error(`Failed to enhance achievement ${achievement.id}:`, error)
      }
    }

    setAchievements(updatedAchievements)
    setStoredAchievements(updatedAchievements)
    setIsBulkEnhancing(false)
  }

  const toggleTag = (tag: string) => {
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    )
  }

  return (
    <div className="space-y-6">
      {/* Header Actions */}
      <div className="flex flex-col sm:flex-row gap-4 justify-between">
        <div className="flex flex-1 gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search achievements..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>
        </div>

        <div className="flex gap-2">
          <button
            onClick={handleBulkEnhance}
            disabled={isBulkEnhancing}
            className="inline-flex items-center px-4 py-2 border border-primary-600 text-primary-600 rounded-lg hover:bg-primary-50 disabled:opacity-50"
          >
            {isBulkEnhancing ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-600 mr-2" />
                Enhancing...
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4 mr-2" />
                Enhance All
              </>
            )}
          </button>
          <button
            onClick={() => setShowAddModal(true)}
            className="inline-flex items-center px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          >
            <Plus className="w-4 h-4 mr-2" />
            Add Achievement
          </button>
        </div>
      </div>

      {/* Tag Filters */}
      {allTags.length > 0 && (
        <div className="flex flex-wrap gap-2">
          <span className="text-sm text-gray-500 flex items-center mr-2">
            <Tag className="w-4 h-4 mr-1" />
            Filter by tag:
          </span>
          {allTags.map((tag) => (
            <button
              key={tag}
              onClick={() => toggleTag(tag)}
              className={cn(
                'px-3 py-1 text-sm rounded-full transition-colors',
                selectedTags.includes(tag)
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              )}
            >
              {tag}
            </button>
          ))}
          {selectedTags.length > 0 && (
            <button
              onClick={() => setSelectedTags([])}
              className="px-3 py-1 text-sm text-gray-500 hover:text-gray-700"
            >
              Clear filters
            </button>
          )}
        </div>
      )}

      {/* Achievements List */}
      {filteredAchievements.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg shadow">
          <Award className="w-12 h-12 mx-auto text-gray-400" />
          <h3 className="mt-4 text-lg font-medium text-gray-900">
            {achievements.length === 0 ? 'No achievements yet' : 'No matching achievements'}
          </h3>
          <p className="mt-2 text-gray-500">
            {achievements.length === 0
              ? 'Start documenting your professional wins'
              : 'Try adjusting your search or filters'}
          </p>
          {achievements.length === 0 && (
            <button
              onClick={() => setShowAddModal(true)}
              className="mt-4 inline-flex items-center px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700"
            >
              <Plus className="w-4 h-4 mr-2" />
              Add Your First Achievement
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          {filteredAchievements.map((achievement) => (
            <div
              key={achievement.id}
              className="bg-white rounded-lg shadow p-6"
            >
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="text-lg font-semibold text-gray-900">
                      {achievement.title}
                    </h3>
                    <span className="text-sm text-gray-500 flex items-center">
                      <Calendar className="w-4 h-4 mr-1" />
                      {formatDate(achievement.date)}
                    </span>
                  </div>

                  <div className="flex flex-wrap gap-2 mb-3">
                    {achievement.tags.map((tag) => (
                      <span
                        key={tag}
                        className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded-full"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>

                  <div className="space-y-3">
                    <div>
                      <p className="text-sm text-gray-500 font-medium mb-1">Original:</p>
                      <p className="text-gray-700">{achievement.description}</p>
                    </div>

                    {achievement.enhancedDescription && (
                      <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                        <p className="text-sm text-green-700 font-medium mb-1 flex items-center">
                          <Sparkles className="w-4 h-4 mr-1" />
                          AI Enhanced:
                        </p>
                        <p className="text-green-800">{achievement.enhancedDescription}</p>
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2 ml-4">
                  <button
                    onClick={() => handleEnhanceAchievement(achievement)}
                    disabled={enhancingId === achievement.id}
                    className={cn(
                      'p-2 rounded hover:bg-purple-50 text-purple-600',
                      enhancingId === achievement.id && 'opacity-50'
                    )}
                    title="AI Enhance"
                    aria-label="Enhance with AI"
                  >
                    {enhancingId === achievement.id ? (
                      <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-purple-600" />
                    ) : (
                      <Wand2 className="w-5 h-5" />
                    )}
                  </button>
                  <button
                    onClick={() => setEditingAchievement(achievement)}
                    className="p-2 text-gray-400 hover:text-primary-600 hover:bg-primary-50 rounded"
                    aria-label="Edit achievement"
                  >
                    <Edit2 className="w-5 h-5" />
                  </button>
                  <button
                    onClick={() => handleDeleteAchievement(achievement.id)}
                    className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded"
                    aria-label="Delete achievement"
                  >
                    <Trash2 className="w-5 h-5" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add/Edit Modal */}
      {(showAddModal || editingAchievement) && (
        <AchievementModal
          achievement={editingAchievement}
          onClose={() => {
            setShowAddModal(false)
            setEditingAchievement(null)
          }}
          onSave={editingAchievement ? handleUpdateAchievement : handleAddAchievement}
        />
      )}
    </div>
  )
}

// ============================================================================
// Achievement Modal
// ============================================================================

interface AchievementModalProps {
  achievement?: Achievement | null
  onClose: () => void
  onSave: (data: Omit<Achievement, 'id' | 'createdAt' | 'updatedAt'>) => void
}

function AchievementModal({ achievement, onClose, onSave }: AchievementModalProps) {
  const [formData, setFormData] = useState({
    title: achievement?.title || '',
    description: achievement?.description || '',
    date: achievement?.date || new Date().toISOString().split('T')[0],
    tags: achievement?.tags || [],
    enhancedDescription: achievement?.enhancedDescription || '',
  })
  const [tagInput, setTagInput] = useState('')

  const handleAddTag = (tag: string) => {
    const trimmedTag = tag.trim()
    if (trimmedTag && !formData.tags.includes(trimmedTag)) {
      setFormData({ ...formData, tags: [...formData.tags, trimmedTag] })
    }
    setTagInput('')
  }

  const handleRemoveTag = (tag: string) => {
    setFormData({ ...formData, tags: formData.tags.filter((t) => t !== tag) })
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSave(formData)
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-xl font-bold text-gray-900">
            {achievement ? 'Edit Achievement' : 'Add Achievement'}
          </h2>
          <button
            onClick={onClose}
            className="p-1 text-gray-400 hover:text-gray-600"
            aria-label="Close modal"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Title <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              required
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              placeholder="e.g., Led migration to cloud infrastructure"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Date <span className="text-red-500">*</span>
            </label>
            <input
              type="date"
              required
              value={formData.date}
              onChange={(e) => setFormData({ ...formData, date: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description <span className="text-red-500">*</span>
            </label>
            <textarea
              required
              rows={4}
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Describe what you did and the impact it had..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
            <p className="mt-1 text-xs text-gray-500">
              Include specific metrics and outcomes when possible
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Tags</label>
            <div className="flex flex-wrap gap-2 mb-2">
              {formData.tags.map((tag) => (
                <span
                  key={tag}
                  className="inline-flex items-center px-3 py-1 bg-primary-100 text-primary-800 rounded-full text-sm"
                >
                  {tag}
                  <button
                    type="button"
                    onClick={() => handleRemoveTag(tag)}
                    className="ml-2 text-primary-600 hover:text-primary-800"
                    aria-label={`Remove ${tag} tag`}
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault()
                    handleAddTag(tagInput)
                  }
                }}
                placeholder="Add a tag..."
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
              <button
                type="button"
                onClick={() => handleAddTag(tagInput)}
                className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
              >
                Add
              </button>
            </div>
            <div className="mt-2 flex flex-wrap gap-1">
              <span className="text-xs text-gray-500">Suggestions:</span>
              {COMMON_TAGS.filter((t) => !formData.tags.includes(t))
                .slice(0, 5)
                .map((tag) => (
                  <button
                    key={tag}
                    type="button"
                    onClick={() => handleAddTag(tag)}
                    className="text-xs text-primary-600 hover:underline"
                  >
                    {tag}
                  </button>
                ))}
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
            >
              {achievement ? 'Save Changes' : 'Add Achievement'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ============================================================================
// Salary Tools Tab
// ============================================================================

interface SalaryToolsTabProps {
  token: string
}

function SalaryToolsTab({ token }: SalaryToolsTabProps) {
  const [compensation, setCompensation] = useState<CompensationData>({
    baseSalary: 100000,
    bonusPercentage: 10,
    stockValue: 20000,
    benefitsValue: 15000,
    otherCompensation: 0,
  })

  const [negotiationData, setNegotiationData] = useState({
    scenario: 'initial_offer' as NegotiationScenario,
    currentOffer: '',
    targetSalary: '',
    leveragePoints: '',
    roleLevel: '',
    companyName: '',
  })

  const [generatedScript, setGeneratedScript] = useState('')
  const [isGenerating, setIsGenerating] = useState(false)

  // Calculate total compensation
  const totalCompensation = useMemo(() => {
    const bonus = compensation.baseSalary * (compensation.bonusPercentage / 100)
    return (
      compensation.baseSalary +
      bonus +
      compensation.stockValue +
      compensation.benefitsValue +
      compensation.otherCompensation
    )
  }, [compensation])

  const handleGenerateScript = async () => {
    if (!negotiationData.currentOffer || !negotiationData.targetSalary) {
      alert('Please fill in the current offer and target salary.')
      return
    }

    setIsGenerating(true)
    try {
      const scenarioLabel = NEGOTIATION_SCENARIOS.find(
        (s) => s.value === negotiationData.scenario
      )?.label

      const prompt = `Generate a professional salary negotiation script for the following scenario:
Scenario: ${scenarioLabel}
Current Offer: $${negotiationData.currentOffer}
Target Salary: $${negotiationData.targetSalary}
${negotiationData.companyName ? `Company: ${negotiationData.companyName}` : ''}
${negotiationData.roleLevel ? `Role Level: ${negotiationData.roleLevel}` : ''}
${negotiationData.leveragePoints ? `Leverage Points: ${negotiationData.leveragePoints}` : ''}

Please provide a professional, confident, and respectful negotiation script that I can adapt for my conversation. Include specific talking points and suggested phrases.`

      const response = await aiApi.answerQuestion(token, {
        question: prompt,
        question_type: 'salary',
        max_length: 1000,
      })

      setGeneratedScript((response as AnswerQuestionResponse).answer)
    } catch (error) {
      console.error('Failed to generate script:', error)
      alert('Failed to generate negotiation script. Please try again.')
    } finally {
      setIsGenerating(false)
    }
  }

  const copyToClipboard = useCallback((text: string) => {
    navigator.clipboard.writeText(text)
  }, [])

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Compensation Calculator */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <Calculator className="w-5 h-5 mr-2 text-primary-600" />
            Total Compensation Calculator
          </h3>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Base Salary
              </label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500">
                  $
                </span>
                <input
                  type="number"
                  min={0}
                  value={compensation.baseSalary}
                  onChange={(e) =>
                    setCompensation({
                      ...compensation,
                      baseSalary: Number(e.target.value),
                    })
                  }
                  className="w-full pl-8 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Bonus Percentage
              </label>
              <div className="relative">
                <input
                  type="number"
                  min={0}
                  max={100}
                  value={compensation.bonusPercentage}
                  onChange={(e) =>
                    setCompensation({
                      ...compensation,
                      bonusPercentage: Number(e.target.value),
                    })
                  }
                  className="w-full pr-8 pl-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
                <span className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-500">
                  %
                </span>
              </div>
              <p className="mt-1 text-xs text-gray-500">
                Bonus: ${(compensation.baseSalary * (compensation.bonusPercentage / 100)).toLocaleString()}
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Stock/Equity Value (Annual)
              </label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500">
                  $
                </span>
                <input
                  type="number"
                  min={0}
                  value={compensation.stockValue}
                  onChange={(e) =>
                    setCompensation({
                      ...compensation,
                      stockValue: Number(e.target.value),
                    })
                  }
                  className="w-full pl-8 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Benefits Value (Health, 401k Match, etc.)
              </label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500">
                  $
                </span>
                <input
                  type="number"
                  min={0}
                  value={compensation.benefitsValue}
                  onChange={(e) =>
                    setCompensation({
                      ...compensation,
                      benefitsValue: Number(e.target.value),
                    })
                  }
                  className="w-full pl-8 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Other Compensation (Signing Bonus, Relocation, etc.)
              </label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500">
                  $
                </span>
                <input
                  type="number"
                  min={0}
                  value={compensation.otherCompensation}
                  onChange={(e) =>
                    setCompensation({
                      ...compensation,
                      otherCompensation: Number(e.target.value),
                    })
                  }
                  className="w-full pl-8 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>
            </div>

            {/* Total */}
            <div className="border-t pt-4 mt-4">
              <div className="flex justify-between items-center">
                <span className="text-lg font-semibold text-gray-900">
                  Total Compensation
                </span>
                <span className="text-2xl font-bold text-primary-600">
                  ${totalCompensation.toLocaleString()}
                </span>
              </div>
              <p className="text-sm text-gray-500 mt-1">
                Monthly: ${Math.round(totalCompensation / 12).toLocaleString()}
              </p>
            </div>
          </div>
        </div>

        {/* Negotiation Scripts */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <MessageSquare className="w-5 h-5 mr-2 text-primary-600" />
            Negotiation Script Generator
          </h3>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Scenario
              </label>
              <select
                value={negotiationData.scenario}
                onChange={(e) =>
                  setNegotiationData({
                    ...negotiationData,
                    scenario: e.target.value as NegotiationScenario,
                  })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                {NEGOTIATION_SCENARIOS.map((scenario) => (
                  <option key={scenario.value} value={scenario.value}>
                    {scenario.label}
                  </option>
                ))}
              </select>
              <p className="mt-1 text-xs text-gray-500">
                {NEGOTIATION_SCENARIOS.find((s) => s.value === negotiationData.scenario)?.description}
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Current Offer
                </label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500">
                    $
                  </span>
                  <input
                    type="number"
                    min={0}
                    value={negotiationData.currentOffer}
                    onChange={(e) =>
                      setNegotiationData({
                        ...negotiationData,
                        currentOffer: e.target.value,
                      })
                    }
                    placeholder="120000"
                    className="w-full pl-8 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Target Salary
                </label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500">
                    $
                  </span>
                  <input
                    type="number"
                    min={0}
                    value={negotiationData.targetSalary}
                    onChange={(e) =>
                      setNegotiationData({
                        ...negotiationData,
                        targetSalary: e.target.value,
                      })
                    }
                    placeholder="140000"
                    className="w-full pl-8 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Company (Optional)
                </label>
                <input
                  type="text"
                  value={negotiationData.companyName}
                  onChange={(e) =>
                    setNegotiationData({
                      ...negotiationData,
                      companyName: e.target.value,
                    })
                  }
                  placeholder="e.g., Google"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Role Level (Optional)
                </label>
                <input
                  type="text"
                  value={negotiationData.roleLevel}
                  onChange={(e) =>
                    setNegotiationData({
                      ...negotiationData,
                      roleLevel: e.target.value,
                    })
                  }
                  placeholder="e.g., Senior Engineer"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Leverage Points (Optional)
              </label>
              <textarea
                rows={2}
                value={negotiationData.leveragePoints}
                onChange={(e) =>
                  setNegotiationData({
                    ...negotiationData,
                    leveragePoints: e.target.value,
                  })
                }
                placeholder="e.g., competing offer, unique skills, market data..."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>

            <button
              onClick={handleGenerateScript}
              disabled={isGenerating}
              className="w-full inline-flex items-center justify-center px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
            >
              {isGenerating ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                  Generating...
                </>
              ) : (
                <>
                  <Wand2 className="w-4 h-4 mr-2" />
                  Generate Script
                </>
              )}
            </button>
          </div>

          {/* Generated Script */}
          {generatedScript && (
            <div className="mt-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
              <div className="flex justify-between items-start mb-2">
                <h4 className="font-medium text-gray-900">Generated Script</h4>
                <button
                  onClick={() => copyToClipboard(generatedScript)}
                  className="text-gray-500 hover:text-primary-600"
                  title="Copy to clipboard"
                >
                  <Copy className="w-4 h-4" />
                </button>
              </div>
              <p className="text-gray-700 whitespace-pre-wrap text-sm">{generatedScript}</p>
            </div>
          )}
        </div>
      </div>

      {/* Market Research Links */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
          <TrendingUp className="w-5 h-5 mr-2 text-primary-600" />
          Market Research Resources
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {MARKET_RESEARCH_LINKS.map((link) => (
            <a
              key={link.name}
              href={link.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-start p-4 border border-gray-200 rounded-lg hover:border-primary-300 hover:bg-primary-50 transition-colors"
            >
              <ExternalLink className="w-5 h-5 text-primary-600 mr-3 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-gray-900">{link.name}</p>
                <p className="text-sm text-gray-500">{link.description}</p>
              </div>
            </a>
          ))}
        </div>
      </div>
    </div>
  )
}

// ============================================================================
// Application Q&A Tab
// ============================================================================

interface ApplicationQATabProps {
  token: string
  resumes: Resume[]
}

function ApplicationQATab({ token, resumes }: ApplicationQATabProps) {
  const [selectedQuestion, setSelectedQuestion] = useState('')
  const [customQuestion, setCustomQuestion] = useState('')
  const [selectedResumeId, setSelectedResumeId] = useState('')
  const [jobDescription, setJobDescription] = useState('')
  const [generatedAnswer, setGeneratedAnswer] = useState('')
  const [tips, setTips] = useState<string[]>([])
  const [isGenerating, setIsGenerating] = useState(false)
  const [copied, setCopied] = useState(false)

  const selectedResume = resumes.find((r) => r.id === Number(selectedResumeId))
  const questionToUse = selectedQuestion === 'custom' ? customQuestion : selectedQuestion

  const selectedQuestionData = COMMON_QUESTIONS.find((q) => q.label === selectedQuestion)

  const handleGenerateAnswer = async () => {
    if (!questionToUse) {
      alert('Please select or enter a question.')
      return
    }

    setIsGenerating(true)
    setGeneratedAnswer('')
    setTips([])

    try {
      const response = await aiApi.answerQuestion(token, {
        question: questionToUse,
        question_type: selectedQuestionData?.type || 'general',
        resume_content: selectedResume?.content,
        job_description: jobDescription || undefined,
        max_length: 500,
      })

      const data = response as AnswerQuestionResponse
      setGeneratedAnswer(data.answer)
      if (data.tips) {
        setTips(data.tips)
      }
    } catch (error) {
      console.error('Failed to generate answer:', error)
      alert('Failed to generate answer. Please try again.')
    } finally {
      setIsGenerating(false)
    }
  }

  const copyToClipboard = useCallback(() => {
    navigator.clipboard.writeText(generatedAnswer)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }, [generatedAnswer])

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Input Section */}
        <div className="space-y-6">
          {/* Question Selection */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
              <FileText className="w-5 h-5 mr-2 text-primary-600" />
              Select a Question
            </h3>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Common Questions
                </label>
                <select
                  value={selectedQuestion}
                  onChange={(e) => setSelectedQuestion(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value="">Select a question...</option>
                  {COMMON_QUESTIONS.map((q) => (
                    <option key={q.value} value={q.label}>
                      {q.label}
                    </option>
                  ))}
                  <option value="custom">Custom question...</option>
                </select>
              </div>

              {selectedQuestion === 'custom' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Your Question
                  </label>
                  <input
                    type="text"
                    value={customQuestion}
                    onChange={(e) => setCustomQuestion(e.target.value)}
                    placeholder="Enter your question..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
              )}
            </div>
          </div>

          {/* Context Section */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
              <Briefcase className="w-5 h-5 mr-2 text-primary-600" />
              Context (Optional)
            </h3>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Select Resume
                </label>
                <select
                  value={selectedResumeId}
                  onChange={(e) => setSelectedResumeId(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value="">No resume (generic answer)</option>
                  {resumes.map((resume) => (
                    <option key={resume.id} value={resume.id}>
                      {resume.version_name}
                    </option>
                  ))}
                </select>
                <p className="mt-1 text-xs text-gray-500">
                  Selecting a resume helps personalize the answer
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Job Description
                </label>
                <textarea
                  rows={4}
                  value={jobDescription}
                  onChange={(e) => setJobDescription(e.target.value)}
                  placeholder="Paste the job description for a more tailored answer..."
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>
            </div>
          </div>

          <button
            onClick={handleGenerateAnswer}
            disabled={isGenerating || !questionToUse}
            className="w-full inline-flex items-center justify-center px-4 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isGenerating ? (
              <>
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2" />
                Generating Answer...
              </>
            ) : (
              <>
                <Wand2 className="w-5 h-5 mr-2" />
                Generate Answer
              </>
            )}
          </button>
        </div>

        {/* Output Section */}
        <div className="space-y-6">
          {generatedAnswer ? (
            <>
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex justify-between items-start mb-4">
                  <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                    <MessageSquare className="w-5 h-5 mr-2 text-primary-600" />
                    Generated Answer
                  </h3>
                  <button
                    onClick={copyToClipboard}
                    className={cn(
                      'inline-flex items-center px-3 py-1 text-sm rounded-lg transition-colors',
                      copied
                        ? 'bg-green-100 text-green-700'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    )}
                  >
                    {copied ? (
                      <>
                        <Check className="w-4 h-4 mr-1" />
                        Copied!
                      </>
                    ) : (
                      <>
                        <Copy className="w-4 h-4 mr-1" />
                        Copy
                      </>
                    )}
                  </button>
                </div>

                <div className="prose prose-sm max-w-none">
                  <p className="text-gray-700 whitespace-pre-wrap">{generatedAnswer}</p>
                </div>
              </div>

              {tips.length > 0 && (
                <div className="bg-amber-50 border border-amber-200 rounded-lg p-6">
                  <h4 className="font-semibold text-amber-800 mb-3 flex items-center">
                    <Sparkles className="w-5 h-5 mr-2" />
                    Tips for Delivery
                  </h4>
                  <ul className="space-y-2">
                    {tips.map((tip, index) => (
                      <li key={index} className="text-amber-700 text-sm flex items-start">
                        <span className="text-amber-500 mr-2">-</span>
                        {tip}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          ) : (
            <div className="bg-white rounded-lg shadow p-12 text-center">
              <MessageSquare className="w-12 h-12 mx-auto text-gray-300" />
              <h3 className="mt-4 text-lg font-medium text-gray-900">
                No Answer Generated Yet
              </h3>
              <p className="mt-2 text-gray-500">
                Select a question and click Generate Answer to get started
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ============================================================================
// Main Page Component
// ============================================================================

export default function CareerToolsPage() {
  const { user, tokens, isLoading: authLoading } = useAuth()
  const router = useRouter()

  const [activeTab, setActiveTab] = useState<TabType>('journal')
  const [resumes, setResumes] = useState<Resume[]>([])
  const [isLoading, setIsLoading] = useState(true)

  // Auth redirect
  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login')
    }
  }, [user, authLoading, router])

  const loadResumes = useCallback(async () => {
    if (!tokens?.access_token) return

    try {
      const resumesData = await resumesApi.list(tokens.access_token)
      setResumes(resumesData as Resume[])
    } catch (error) {
      console.error('Failed to load resumes:', error)
    } finally {
      setIsLoading(false)
    }
  }, [tokens])

  // Load resumes for Q&A tab
  useEffect(() => {
    if (tokens?.access_token) {
      loadResumes()
    }
  }, [tokens, loadResumes])

  // Loading state
  if (authLoading || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Career Tools</h1>
        <p className="text-gray-500">
          Track achievements, research compensation, and prepare application answers
        </p>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="flex gap-4 -mb-px" aria-label="Tabs">
          {[
            { id: 'journal' as const, label: 'Achievement Journal', icon: BookOpen },
            { id: 'salary' as const, label: 'Salary Tools', icon: DollarSign },
            { id: 'qa' as const, label: 'Application Q&A', icon: MessageSquare },
          ].map((tab) => (
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
      {activeTab === 'journal' && tokens?.access_token && (
        <AchievementJournalTab token={tokens.access_token} />
      )}

      {activeTab === 'salary' && tokens?.access_token && (
        <SalaryToolsTab token={tokens.access_token} />
      )}

      {activeTab === 'qa' && tokens?.access_token && (
        <ApplicationQATab token={tokens.access_token} resumes={resumes} />
      )}
    </div>
  )
}
