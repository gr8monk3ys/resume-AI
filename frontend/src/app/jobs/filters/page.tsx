'use client'

import { useEffect, useState, useMemo } from 'react'
import { useAuth } from '@/lib/auth'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { filtersApi } from '@/lib/api'
import type {
  CompanyFilter,
  CompanyFilterType,
  KeywordFilter,
  KeywordFilterType,
  KeywordAppliesTo,
  QuestionTemplate,
  QuestionTemplateType,
  QuestionTemplateCategory,
} from '@/types'
import { cn, formatDate } from '@/lib/utils'
import {
  Building2,
  Tag,
  MessageSquare,
  Plus,
  Trash2,
  Search,
  ArrowLeft,
  Upload,
  Download,
  X,
  Check,
  Edit2,
  Eye,
} from 'lucide-react'

// ============================================================================
// Types and Constants
// ============================================================================

type TabType = 'companies' | 'keywords' | 'templates'

const COMMON_EXCLUDE_KEYWORDS = [
  'Security Clearance',
  'TS/SCI',
  'Secret Clearance',
  'On-site only',
  'No Remote',
  'Contract only',
  'C2C',
  'Entry Level',
  'Junior',
  'Internship',
  'Unpaid',
]

const COMMON_REQUIRE_KEYWORDS = [
  'Remote',
  'Hybrid',
  'Full-time',
  'Senior',
  'Lead',
  'Staff',
  'Principal',
]

const TEMPLATE_CATEGORIES: { value: QuestionTemplateCategory; label: string }[] = [
  { value: 'experience', label: 'Experience' },
  { value: 'salary', label: 'Salary' },
  { value: 'availability', label: 'Availability' },
  { value: 'authorization', label: 'Authorization' },
  { value: 'personal', label: 'Personal' },
  { value: 'demographics', label: 'Demographics' },
]

const TEMPLATE_TYPES: { value: QuestionTemplateType; label: string }[] = [
  { value: 'text', label: 'Text' },
  { value: 'number', label: 'Number' },
  { value: 'boolean', label: 'Yes/No' },
  { value: 'select', label: 'Multiple Choice' },
]

// ============================================================================
// Company Filters Tab
// ============================================================================

interface CompanyFiltersTabProps {
  filters: CompanyFilter[]
  onAdd: (data: { company_name: string; filter_type: CompanyFilterType; reason?: string }) => Promise<void>
  onDelete: (id: string) => Promise<void>
  onImport: (companies: string[], filterType: CompanyFilterType, reason?: string) => Promise<void>
}

function CompanyFiltersTab({ filters, onAdd, onDelete, onImport }: CompanyFiltersTabProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [filterType, setFilterType] = useState<CompanyFilterType | ''>('')
  const [showAddForm, setShowAddForm] = useState(false)
  const [showImportModal, setShowImportModal] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const [newCompany, setNewCompany] = useState('')
  const [newType, setNewType] = useState<CompanyFilterType>('blacklist')
  const [newReason, setNewReason] = useState('')

  const filteredFilters = useMemo(() => {
    let result = [...filters]

    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      result = result.filter(
        (f) =>
          f.company_name.toLowerCase().includes(query) ||
          (f.reason && f.reason.toLowerCase().includes(query))
      )
    }

    if (filterType) {
      result = result.filter((f) => f.filter_type === filterType)
    }

    return result.sort((a, b) => a.company_name.localeCompare(b.company_name))
  }, [filters, searchQuery, filterType])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newCompany.trim()) return

    setIsSubmitting(true)
    try {
      await onAdd({
        company_name: newCompany.trim(),
        filter_type: newType,
        reason: newReason.trim() || undefined,
      })
      setNewCompany('')
      setNewReason('')
      setShowAddForm(false)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header Actions */}
      <div className="flex flex-wrap gap-4 items-center justify-between">
        <div className="flex flex-wrap gap-4 items-center flex-1">
          <div className="relative flex-1 min-w-[200px] max-w-md">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search companies..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value as CompanyFilterType | '')}
            className="border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
            aria-label="Filter by type"
          >
            <option value="">All Types</option>
            <option value="blacklist">Blacklist</option>
            <option value="whitelist">Whitelist</option>
          </select>
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => setShowImportModal(true)}
            className="inline-flex items-center px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            <Upload className="w-4 h-4 mr-2" />
            Import
          </button>
          <button
            onClick={() => setShowAddForm(true)}
            className="inline-flex items-center px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          >
            <Plus className="w-4 h-4 mr-2" />
            Add Company
          </button>
        </div>
      </div>

      {/* Add Form */}
      {showAddForm && (
        <form onSubmit={handleSubmit} className="bg-gray-50 rounded-lg p-4 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Company Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                required
                value={newCompany}
                onChange={(e) => setNewCompany(e.target.value)}
                placeholder="e.g., Acme Corp"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Filter Type
              </label>
              <select
                value={newType}
                onChange={(e) => setNewType(e.target.value as CompanyFilterType)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value="blacklist">Blacklist (Block)</option>
                <option value="whitelist">Whitelist (Prefer)</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Reason (Optional)
              </label>
              <input
                type="text"
                value={newReason}
                onChange={(e) => setNewReason(e.target.value)}
                placeholder="e.g., Poor reviews"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setShowAddForm(false)}
              className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !newCompany.trim()}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
            >
              {isSubmitting ? 'Adding...' : 'Add Filter'}
            </button>
          </div>
        </form>
      )}

      {/* Table */}
      <div className="overflow-x-auto rounded-lg border border-gray-200">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">
                Company
              </th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">
                Type
              </th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">
                Reason
              </th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">
                Added
              </th>
              <th className="px-4 py-3 text-right text-sm font-medium text-gray-700 w-20">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {filteredFilters.map((filter) => (
              <tr key={filter.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-medium text-gray-900">
                  {filter.company_name}
                </td>
                <td className="px-4 py-3">
                  <span
                    className={cn(
                      'text-xs font-medium px-2 py-1 rounded-full',
                      filter.filter_type === 'blacklist'
                        ? 'bg-red-100 text-red-800'
                        : 'bg-green-100 text-green-800'
                    )}
                  >
                    {filter.filter_type === 'blacklist' ? 'Blacklist' : 'Whitelist'}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-500 text-sm">
                  {filter.reason || '-'}
                </td>
                <td className="px-4 py-3 text-gray-500 text-sm">
                  {formatDate(filter.created_at, 'short')}
                </td>
                <td className="px-4 py-3 text-right">
                  <button
                    onClick={() => onDelete(filter.id)}
                    className="p-1 text-gray-400 hover:text-red-600"
                    aria-label="Delete filter"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {filteredFilters.length === 0 && (
          <div className="text-center py-12 text-gray-500">
            {filters.length === 0
              ? 'No company filters yet. Add your first filter above.'
              : 'No companies match your search criteria.'}
          </div>
        )}
      </div>

      {/* Stats */}
      <div className="flex gap-4 text-sm text-gray-500">
        <span>
          Total: {filters.length} filters
        </span>
        <span>
          Blacklist: {filters.filter((f) => f.filter_type === 'blacklist').length}
        </span>
        <span>
          Whitelist: {filters.filter((f) => f.filter_type === 'whitelist').length}
        </span>
      </div>

      {/* Import Modal */}
      {showImportModal && (
        <ImportCompaniesModal
          onClose={() => setShowImportModal(false)}
          onImport={onImport}
        />
      )}
    </div>
  )
}

// ============================================================================
// Import Companies Modal
// ============================================================================

interface ImportCompaniesModalProps {
  onClose: () => void
  onImport: (companies: string[], filterType: CompanyFilterType, reason?: string) => Promise<void>
}

function ImportCompaniesModal({ onClose, onImport }: ImportCompaniesModalProps) {
  const [text, setText] = useState('')
  const [filterType, setFilterType] = useState<CompanyFilterType>('blacklist')
  const [reason, setReason] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const companies = useMemo(() => {
    return text
      .split(/[,\n]/)
      .map((s) => s.trim())
      .filter((s) => s.length > 0)
  }, [text])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (companies.length === 0) return

    setIsSubmitting(true)
    try {
      await onImport(companies, filterType, reason.trim() || undefined)
      onClose()
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-lg w-full">
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-xl font-bold text-gray-900">Import Companies</h2>
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
              Company Names
            </label>
            <textarea
              rows={6}
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Enter company names separated by commas or new lines:&#10;&#10;Acme Corp&#10;Evil Inc&#10;BadCompany LLC"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
            <p className="mt-1 text-sm text-gray-500">
              {companies.length} companies detected
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Filter Type
            </label>
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value as CompanyFilterType)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="blacklist">Blacklist (Block)</option>
              <option value="whitelist">Whitelist (Prefer)</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Reason (Optional)
            </label>
            <input
              type="text"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g., Imported from list"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
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
              disabled={isSubmitting || companies.length === 0}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
            >
              {isSubmitting ? 'Importing...' : `Import ${companies.length} Companies`}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ============================================================================
// Keyword Filters Tab
// ============================================================================

interface KeywordFiltersTabProps {
  filters: KeywordFilter[]
  onAdd: (data: { keyword: string; filter_type: KeywordFilterType; applies_to: KeywordAppliesTo }) => Promise<void>
  onDelete: (id: string) => Promise<void>
}

function KeywordFiltersTab({ filters, onAdd, onDelete }: KeywordFiltersTabProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [filterType, setFilterType] = useState<KeywordFilterType | ''>('')
  const [showAddForm, setShowAddForm] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const [newKeyword, setNewKeyword] = useState('')
  const [newType, setNewType] = useState<KeywordFilterType>('exclude')
  const [newAppliesTo, setNewAppliesTo] = useState<KeywordAppliesTo>('both')

  const filteredFilters = useMemo(() => {
    let result = [...filters]

    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      result = result.filter((f) => f.keyword.toLowerCase().includes(query))
    }

    if (filterType) {
      result = result.filter((f) => f.filter_type === filterType)
    }

    return result.sort((a, b) => a.keyword.localeCompare(b.keyword))
  }, [filters, searchQuery, filterType])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newKeyword.trim()) return

    setIsSubmitting(true)
    try {
      await onAdd({
        keyword: newKeyword.trim(),
        filter_type: newType,
        applies_to: newAppliesTo,
      })
      setNewKeyword('')
      setShowAddForm(false)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleQuickAdd = async (keyword: string, type: KeywordFilterType) => {
    await onAdd({
      keyword,
      filter_type: type,
      applies_to: 'both',
    })
  }

  return (
    <div className="space-y-6">
      {/* Header Actions */}
      <div className="flex flex-wrap gap-4 items-center justify-between">
        <div className="flex flex-wrap gap-4 items-center flex-1">
          <div className="relative flex-1 min-w-[200px] max-w-md">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search keywords..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value as KeywordFilterType | '')}
            className="border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
            aria-label="Filter by type"
          >
            <option value="">All Types</option>
            <option value="exclude">Exclude</option>
            <option value="require">Require</option>
          </select>
        </div>

        <button
          onClick={() => setShowAddForm(true)}
          className="inline-flex items-center px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
        >
          <Plus className="w-4 h-4 mr-2" />
          Add Keyword
        </button>
      </div>

      {/* Quick Add Buttons */}
      <div className="space-y-3">
        <h3 className="text-sm font-medium text-gray-700">Quick Add - Exclude Keywords:</h3>
        <div className="flex flex-wrap gap-2">
          {COMMON_EXCLUDE_KEYWORDS.filter(
            (kw) => !filters.some((f) => f.keyword.toLowerCase() === kw.toLowerCase())
          ).map((keyword) => (
            <button
              key={keyword}
              onClick={() => handleQuickAdd(keyword, 'exclude')}
              className="inline-flex items-center px-3 py-1 text-sm bg-red-50 text-red-700 rounded-full hover:bg-red-100 border border-red-200"
            >
              <Plus className="w-3 h-3 mr-1" />
              {keyword}
            </button>
          ))}
        </div>

        <h3 className="text-sm font-medium text-gray-700">Quick Add - Require Keywords:</h3>
        <div className="flex flex-wrap gap-2">
          {COMMON_REQUIRE_KEYWORDS.filter(
            (kw) => !filters.some((f) => f.keyword.toLowerCase() === kw.toLowerCase())
          ).map((keyword) => (
            <button
              key={keyword}
              onClick={() => handleQuickAdd(keyword, 'require')}
              className="inline-flex items-center px-3 py-1 text-sm bg-green-50 text-green-700 rounded-full hover:bg-green-100 border border-green-200"
            >
              <Plus className="w-3 h-3 mr-1" />
              {keyword}
            </button>
          ))}
        </div>
      </div>

      {/* Add Form */}
      {showAddForm && (
        <form onSubmit={handleSubmit} className="bg-gray-50 rounded-lg p-4 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Keyword <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                required
                value={newKeyword}
                onChange={(e) => setNewKeyword(e.target.value)}
                placeholder="e.g., Security Clearance"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Filter Type
              </label>
              <select
                value={newType}
                onChange={(e) => setNewType(e.target.value as KeywordFilterType)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value="exclude">Exclude (Block)</option>
                <option value="require">Require (Prefer)</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Applies To
              </label>
              <select
                value={newAppliesTo}
                onChange={(e) => setNewAppliesTo(e.target.value as KeywordAppliesTo)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value="both">Title and Description</option>
                <option value="title">Title Only</option>
                <option value="description">Description Only</option>
              </select>
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setShowAddForm(false)}
              className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !newKeyword.trim()}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
            >
              {isSubmitting ? 'Adding...' : 'Add Filter'}
            </button>
          </div>
        </form>
      )}

      {/* Table */}
      <div className="overflow-x-auto rounded-lg border border-gray-200">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">
                Keyword
              </th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">
                Type
              </th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">
                Applies To
              </th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">
                Added
              </th>
              <th className="px-4 py-3 text-right text-sm font-medium text-gray-700 w-20">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {filteredFilters.map((filter) => (
              <tr key={filter.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-medium text-gray-900">
                  {filter.keyword}
                </td>
                <td className="px-4 py-3">
                  <span
                    className={cn(
                      'text-xs font-medium px-2 py-1 rounded-full',
                      filter.filter_type === 'exclude'
                        ? 'bg-red-100 text-red-800'
                        : 'bg-green-100 text-green-800'
                    )}
                  >
                    {filter.filter_type === 'exclude' ? 'Exclude' : 'Require'}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-500 text-sm capitalize">
                  {filter.applies_to === 'both' ? 'Title & Desc' : filter.applies_to}
                </td>
                <td className="px-4 py-3 text-gray-500 text-sm">
                  {formatDate(filter.created_at, 'short')}
                </td>
                <td className="px-4 py-3 text-right">
                  <button
                    onClick={() => onDelete(filter.id)}
                    className="p-1 text-gray-400 hover:text-red-600"
                    aria-label="Delete filter"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {filteredFilters.length === 0 && (
          <div className="text-center py-12 text-gray-500">
            {filters.length === 0
              ? 'No keyword filters yet. Add your first filter above.'
              : 'No keywords match your search criteria.'}
          </div>
        )}
      </div>

      {/* Stats */}
      <div className="flex gap-4 text-sm text-gray-500">
        <span>
          Total: {filters.length} filters
        </span>
        <span>
          Exclude: {filters.filter((f) => f.filter_type === 'exclude').length}
        </span>
        <span>
          Require: {filters.filter((f) => f.filter_type === 'require').length}
        </span>
      </div>
    </div>
  )
}

// ============================================================================
// Answer Templates Tab
// ============================================================================

interface AnswerTemplatesTabProps {
  templates: QuestionTemplate[]
  onAdd: (data: { question_pattern: string; answer: string; answer_type: QuestionTemplateType; category: QuestionTemplateCategory }) => Promise<void>
  onUpdate: (id: string, data: Partial<QuestionTemplate>) => Promise<void>
  onDelete: (id: string) => Promise<void>
  onImportDefaults: () => Promise<void>
}

function AnswerTemplatesTab({ templates, onAdd, onUpdate, onDelete, onImportDefaults }: AnswerTemplatesTabProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [categoryFilter, setCategoryFilter] = useState<QuestionTemplateCategory | ''>('')
  const [showAddForm, setShowAddForm] = useState(false)
  const [editingTemplate, setEditingTemplate] = useState<QuestionTemplate | null>(null)
  const [previewTemplate, setPreviewTemplate] = useState<QuestionTemplate | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const [formData, setFormData] = useState({
    question_pattern: '',
    answer: '',
    answer_type: 'text' as QuestionTemplateType,
    category: 'experience' as QuestionTemplateCategory,
  })

  const filteredTemplates = useMemo(() => {
    let result = [...templates]

    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      result = result.filter(
        (t) =>
          t.question_pattern.toLowerCase().includes(query) ||
          t.answer.toLowerCase().includes(query)
      )
    }

    if (categoryFilter) {
      result = result.filter((t) => t.category === categoryFilter)
    }

    return result.sort((a, b) => {
      // Sort by category first, then by pattern
      const catCompare = a.category.localeCompare(b.category)
      if (catCompare !== 0) return catCompare
      return a.question_pattern.localeCompare(b.question_pattern)
    })
  }, [templates, searchQuery, categoryFilter])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.question_pattern.trim() || !formData.answer.trim()) return

    setIsSubmitting(true)
    try {
      if (editingTemplate) {
        await onUpdate(editingTemplate.id, formData)
        setEditingTemplate(null)
      } else {
        await onAdd(formData)
      }
      setFormData({
        question_pattern: '',
        answer: '',
        answer_type: 'text',
        category: 'experience',
      })
      setShowAddForm(false)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleEdit = (template: QuestionTemplate) => {
    setEditingTemplate(template)
    setFormData({
      question_pattern: template.question_pattern,
      answer: template.answer,
      answer_type: template.answer_type,
      category: template.category,
    })
    setShowAddForm(true)
  }

  const handleCancelEdit = () => {
    setEditingTemplate(null)
    setFormData({
      question_pattern: '',
      answer: '',
      answer_type: 'text',
      category: 'experience',
    })
    setShowAddForm(false)
  }

  const getCategoryColor = (category: QuestionTemplateCategory): string => {
    const colors: Record<QuestionTemplateCategory, string> = {
      experience: 'bg-blue-100 text-blue-800',
      salary: 'bg-green-100 text-green-800',
      availability: 'bg-purple-100 text-purple-800',
      authorization: 'bg-amber-100 text-amber-800',
      personal: 'bg-pink-100 text-pink-800',
      demographics: 'bg-gray-100 text-gray-800',
    }
    return colors[category]
  }

  return (
    <div className="space-y-6">
      {/* Header Actions */}
      <div className="flex flex-wrap gap-4 items-center justify-between">
        <div className="flex flex-wrap gap-4 items-center flex-1">
          <div className="relative flex-1 min-w-[200px] max-w-md">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search templates..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value as QuestionTemplateCategory | '')}
            className="border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
            aria-label="Filter by category"
          >
            <option value="">All Categories</option>
            {TEMPLATE_CATEGORIES.map((cat) => (
              <option key={cat.value} value={cat.value}>
                {cat.label}
              </option>
            ))}
          </select>
        </div>

        <div className="flex gap-2">
          <button
            onClick={onImportDefaults}
            className="inline-flex items-center px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            <Download className="w-4 h-4 mr-2" />
            Import Defaults
          </button>
          <button
            onClick={() => setShowAddForm(true)}
            className="inline-flex items-center px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          >
            <Plus className="w-4 h-4 mr-2" />
            Add Template
          </button>
        </div>
      </div>

      {/* Add/Edit Form */}
      {showAddForm && (
        <form onSubmit={handleSubmit} className="bg-gray-50 rounded-lg p-4 space-y-4">
          <h3 className="font-medium text-gray-900">
            {editingTemplate ? 'Edit Template' : 'Add New Template'}
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Question Pattern <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                required
                value={formData.question_pattern}
                onChange={(e) => setFormData({ ...formData, question_pattern: e.target.value })}
                placeholder="e.g., years of experience"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
              <p className="mt-1 text-xs text-gray-500">
                Use | for multiple patterns: salary|compensation|pay
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Answer <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                required
                value={formData.answer}
                onChange={(e) => setFormData({ ...formData, answer: e.target.value })}
                placeholder="e.g., 5"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Answer Type
              </label>
              <select
                value={formData.answer_type}
                onChange={(e) => setFormData({ ...formData, answer_type: e.target.value as QuestionTemplateType })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                {TEMPLATE_TYPES.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Category
              </label>
              <select
                value={formData.category}
                onChange={(e) => setFormData({ ...formData, category: e.target.value as QuestionTemplateCategory })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                {TEMPLATE_CATEGORIES.map((cat) => (
                  <option key={cat.value} value={cat.value}>
                    {cat.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={handleCancelEdit}
              className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !formData.question_pattern.trim() || !formData.answer.trim()}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
            >
              {isSubmitting ? 'Saving...' : editingTemplate ? 'Update Template' : 'Add Template'}
            </button>
          </div>
        </form>
      )}

      {/* Table */}
      <div className="overflow-x-auto rounded-lg border border-gray-200">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">
                Question Pattern
              </th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">
                Answer
              </th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">
                Type
              </th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">
                Category
              </th>
              <th className="px-4 py-3 text-right text-sm font-medium text-gray-700 w-28">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {filteredTemplates.map((template) => (
              <tr key={template.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-medium text-gray-900">
                  <code className="text-sm bg-gray-100 px-1 py-0.5 rounded">
                    {template.question_pattern}
                  </code>
                </td>
                <td className="px-4 py-3 text-gray-700 max-w-xs truncate">
                  {template.answer}
                </td>
                <td className="px-4 py-3">
                  <span className="text-xs text-gray-500 capitalize">
                    {template.answer_type}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span
                    className={cn(
                      'text-xs font-medium px-2 py-1 rounded-full capitalize',
                      getCategoryColor(template.category)
                    )}
                  >
                    {template.category}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="flex items-center justify-end gap-1">
                    <button
                      onClick={() => setPreviewTemplate(template)}
                      className="p-1 text-gray-400 hover:text-primary-600"
                      aria-label="Preview template"
                    >
                      <Eye className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleEdit(template)}
                      className="p-1 text-gray-400 hover:text-primary-600"
                      aria-label="Edit template"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => onDelete(template.id)}
                      className="p-1 text-gray-400 hover:text-red-600"
                      aria-label="Delete template"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {filteredTemplates.length === 0 && (
          <div className="text-center py-12 text-gray-500">
            {templates.length === 0 ? (
              <div>
                <p>No answer templates yet.</p>
                <button
                  onClick={onImportDefaults}
                  className="mt-2 text-primary-600 hover:text-primary-700 font-medium"
                >
                  Import default templates
                </button>
              </div>
            ) : (
              'No templates match your search criteria.'
            )}
          </div>
        )}
      </div>

      {/* Stats by Category */}
      <div className="flex flex-wrap gap-4 text-sm text-gray-500">
        <span>Total: {templates.length} templates</span>
        {TEMPLATE_CATEGORIES.map((cat) => {
          const count = templates.filter((t) => t.category === cat.value).length
          return count > 0 ? (
            <span key={cat.value}>
              {cat.label}: {count}
            </span>
          ) : null
        })}
      </div>

      {/* Preview Modal */}
      {previewTemplate && (
        <PreviewTemplateModal
          template={previewTemplate}
          onClose={() => setPreviewTemplate(null)}
        />
      )}
    </div>
  )
}

// ============================================================================
// Preview Template Modal
// ============================================================================

interface PreviewTemplateModalProps {
  template: QuestionTemplate
  onClose: () => void
}

function PreviewTemplateModal({ template, onClose }: PreviewTemplateModalProps) {
  const exampleQuestions = useMemo(() => {
    const patterns = template.question_pattern.split('|').map((p) => p.trim())
    return patterns.map((p) => {
      // Generate example question from pattern
      if (p.includes('experience')) return 'How many years of experience do you have?'
      if (p.includes('salary')) return 'What are your salary expectations?'
      if (p.includes('authorized')) return 'Are you authorized to work in the US?'
      if (p.includes('sponsorship')) return 'Do you require visa sponsorship?'
      if (p.includes('start')) return 'When can you start?'
      if (p.includes('relocate')) return 'Are you willing to relocate?'
      if (p.includes('remote')) return 'What is your preferred work arrangement?'
      if (p.includes('gender')) return 'What is your gender?'
      if (p.includes('veteran')) return 'Are you a veteran?'
      if (p.includes('disability')) return 'Do you have a disability?'
      return `Question containing "${p}"?`
    })
  }, [template])

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-lg w-full">
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-xl font-bold text-gray-900">Template Preview</h2>
          <button
            onClick={onClose}
            className="p-1 text-gray-400 hover:text-gray-600"
            aria-label="Close modal"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        <div className="p-4 space-y-4">
          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-1">Pattern</h3>
            <code className="block bg-gray-100 px-3 py-2 rounded text-sm">
              {template.question_pattern}
            </code>
          </div>

          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-1">Answer</h3>
            <div className="bg-primary-50 border border-primary-200 px-3 py-2 rounded">
              <p className="text-primary-800 font-medium">{template.answer}</p>
              <p className="text-xs text-primary-600 mt-1">
                Type: {template.answer_type} | Category: {template.category}
              </p>
            </div>
          </div>

          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-2">Example Questions This Matches:</h3>
            <ul className="space-y-2">
              {exampleQuestions.map((q, i) => (
                <li key={i} className="flex items-start gap-2 text-sm">
                  <Check className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" />
                  <span className="text-gray-700">{q}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="flex justify-end p-4 border-t">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

// ============================================================================
// Main Page Component
// ============================================================================

export default function JobFiltersPage() {
  const { user, isLoading: authLoading } = useAuth()
  const router = useRouter()

  // State
  const [activeTab, setActiveTab] = useState<TabType>('companies')
  const [isLoading, setIsLoading] = useState(true)
  const [companyFilters, setCompanyFilters] = useState<CompanyFilter[]>([])
  const [keywordFilters, setKeywordFilters] = useState<KeywordFilter[]>([])
  const [questionTemplates, setQuestionTemplates] = useState<QuestionTemplate[]>([])

  // Auth redirect
  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login')
    }
  }, [user, authLoading, router])

  // Load data
  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [companies, keywords, templates] = await Promise.all([
        filtersApi.getCompanyFilters(),
        filtersApi.getKeywordFilters(),
        filtersApi.getQuestionTemplates(),
      ])
      setCompanyFilters(companies)
      setKeywordFilters(keywords)
      setQuestionTemplates(templates)
    } catch (error) {
      console.error('Failed to load filters:', error)
    } finally {
      setIsLoading(false)
    }
  }

  // Company filter handlers
  const handleAddCompanyFilter = async (data: { company_name: string; filter_type: CompanyFilterType; reason?: string }) => {
    const newFilter = await filtersApi.createCompanyFilter(data)
    setCompanyFilters([...companyFilters, newFilter])
  }

  const handleDeleteCompanyFilter = async (id: string) => {
    if (!confirm('Are you sure you want to delete this filter?')) return
    await filtersApi.deleteCompanyFilter(id)
    setCompanyFilters(companyFilters.filter((f) => f.id !== id))
  }

  const handleImportCompanyFilters = async (companies: string[], filterType: CompanyFilterType, reason?: string) => {
    const newFilters = await filtersApi.importCompanyFilters(companies, filterType, reason)
    setCompanyFilters([...companyFilters, ...newFilters])
  }

  // Keyword filter handlers
  const handleAddKeywordFilter = async (data: { keyword: string; filter_type: KeywordFilterType; applies_to: KeywordAppliesTo }) => {
    const newFilter = await filtersApi.createKeywordFilter(data)
    setKeywordFilters([...keywordFilters, newFilter])
  }

  const handleDeleteKeywordFilter = async (id: string) => {
    if (!confirm('Are you sure you want to delete this filter?')) return
    await filtersApi.deleteKeywordFilter(id)
    setKeywordFilters(keywordFilters.filter((f) => f.id !== id))
  }

  // Question template handlers
  const handleAddQuestionTemplate = async (data: { question_pattern: string; answer: string; answer_type: QuestionTemplateType; category: QuestionTemplateCategory }) => {
    const newTemplate = await filtersApi.createQuestionTemplate(data)
    setQuestionTemplates([...questionTemplates, newTemplate])
  }

  const handleUpdateQuestionTemplate = async (id: string, data: Partial<QuestionTemplate>) => {
    const updated = await filtersApi.updateQuestionTemplate(id, data)
    setQuestionTemplates(questionTemplates.map((t) => (t.id === id ? updated : t)))
  }

  const handleDeleteQuestionTemplate = async (id: string) => {
    if (!confirm('Are you sure you want to delete this template?')) return
    await filtersApi.deleteQuestionTemplate(id)
    setQuestionTemplates(questionTemplates.filter((t) => t.id !== id))
  }

  const handleImportDefaults = async () => {
    const newTemplates = await filtersApi.importDefaults()
    if (newTemplates.length === 0) {
      alert('All default templates are already imported.')
    } else {
      setQuestionTemplates([...questionTemplates, ...newTemplates])
      alert(`Imported ${newTemplates.length} new templates.`)
    }
  }

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
      <div className="flex items-center gap-4 mb-6">
        <Link
          href="/jobs"
          className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
          aria-label="Back to jobs"
        >
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Job Filters</h1>
          <p className="text-gray-500">
            Manage company filters, keyword filters, and answer templates
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="flex gap-4 -mb-px" aria-label="Tabs">
          {[
            { id: 'companies' as const, label: 'Company Filters', icon: Building2, count: companyFilters.length },
            { id: 'keywords' as const, label: 'Keyword Filters', icon: Tag, count: keywordFilters.length },
            { id: 'templates' as const, label: 'Answer Templates', icon: MessageSquare, count: questionTemplates.length },
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
              <span
                className={cn(
                  'ml-1 px-2 py-0.5 text-xs rounded-full',
                  activeTab === tab.id
                    ? 'bg-primary-100 text-primary-700'
                    : 'bg-gray-100 text-gray-600'
                )}
              >
                {tab.count}
              </span>
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'companies' && (
        <CompanyFiltersTab
          filters={companyFilters}
          onAdd={handleAddCompanyFilter}
          onDelete={handleDeleteCompanyFilter}
          onImport={handleImportCompanyFilters}
        />
      )}

      {activeTab === 'keywords' && (
        <KeywordFiltersTab
          filters={keywordFilters}
          onAdd={handleAddKeywordFilter}
          onDelete={handleDeleteKeywordFilter}
        />
      )}

      {activeTab === 'templates' && (
        <AnswerTemplatesTab
          templates={questionTemplates}
          onAdd={handleAddQuestionTemplate}
          onUpdate={handleUpdateQuestionTemplate}
          onDelete={handleDeleteQuestionTemplate}
          onImportDefaults={handleImportDefaults}
        />
      )}
    </div>
  )
}
