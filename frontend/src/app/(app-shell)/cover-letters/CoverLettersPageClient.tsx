'use client';

import { Mail, Trash2, Wand2 } from 'lucide-react';
import { useEffect, useState, useCallback } from 'react';

import { coverLettersApi, resumesApi, aiApi } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { formatDate } from '@/lib/utils';

import type { CoverLetter, Resume } from '@/types';

export default function CoverLettersPage() {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const [coverLetters, setCoverLetters] = useState<CoverLetter[]>([]);
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showGenerator, setShowGenerator] = useState(false);

  const loadData = useCallback(async () => {
    if (!isAuthenticated) return;
    try {
      const [lettersData, resumesData] = await Promise.all([
        coverLettersApi.list(),
        resumesApi.list(),
      ]);
      setCoverLetters(lettersData);
      setResumes(resumesData);
    } catch (error) {
      console.error('Failed to load data:', error);
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    if (isAuthenticated) {
      void loadData();
    }
  }, [isAuthenticated, loadData]);

  const deleteCoverLetter = async (id: number) => {
    if (!isAuthenticated) return;
    if (!confirm('Are you sure you want to delete this cover letter?')) return;
    try {
      await coverLettersApi.delete(id);
      setCoverLetters(coverLetters.filter(cl => cl.id !== id));
    } catch (error) {
      console.error('Failed to delete cover letter:', error);
    }
  };

  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[var(--accent)]" />
      </div>
    );
  }

  if (!user || !isAuthenticated) {
    return null;
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[var(--accent)]" />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-[var(--ink)] font-display tracking-[-0.02em]">Cover Letters</h1>
          <p className="text-[var(--muted)]">Generate and manage cover letters</p>
        </div>
        <button
          onClick={() => setShowGenerator(true)}
          className="glass-button-primary inline-flex items-center"
        >
          <Wand2 className="w-4 h-4 mr-2" />
          Generate Cover Letter
        </button>
      </div>

      {coverLetters.length === 0 ? (
        <div className="text-center py-12 bg-[var(--surface-strong)] rounded-lg shadow">
          <Mail className="w-12 h-12 mx-auto text-[var(--muted-soft)]" />
          <h3 className="mt-4 text-lg font-medium text-[var(--ink)]">No cover letters yet</h3>
          <p className="mt-2 text-[var(--muted)]">Generate your first cover letter with AI</p>
          <button
            onClick={() => setShowGenerator(true)}
            className="mt-4 glass-button-primary inline-flex items-center"
          >
            <Wand2 className="w-4 h-4 mr-2" />
            Generate Cover Letter
          </button>
        </div>
      ) : (
        <div className="grid gap-4">
          {coverLetters.map((letter) => (
            <div
              key={letter.id}
              className="bg-[var(--surface-strong)] rounded-lg shadow p-6"
            >
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <p className="text-sm text-[var(--muted)]">
                    Created: {formatDate(letter.created_at)}
                  </p>
                </div>
                <button
                  onClick={() => void deleteCoverLetter(letter.id)}
                  className="text-[var(--muted-soft)] hover:text-red-600"
                >
                  <Trash2 className="w-5 h-5" />
                </button>
              </div>

              <p className="mt-4 text-sm text-[var(--ink-secondary)] whitespace-pre-line line-clamp-6">
                {letter.content}
              </p>
            </div>
          ))}
        </div>
      )}

      {showGenerator && (
        <GeneratorModal
          onClose={() => setShowGenerator(false)}
          onGenerate={(newLetter) => {
            setCoverLetters([newLetter, ...coverLetters]);
            setShowGenerator(false);
          }}
          resumes={resumes}
        />
      )}
    </div>
  );
}

function GeneratorModal({
  onClose,
  onGenerate,
  resumes,
}: {
  onClose: () => void;
  onGenerate: (letter: CoverLetter) => void;
  resumes: Resume[];
}) {
  const [formData, setFormData] = useState({
    resume_id: '',
    company_name: '',
    position: '',
    job_description: '',
  });
  const [isGenerating, setIsGenerating] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const selectedResume = resumes.find(r => r.id === Number(formData.resume_id));
    if (!selectedResume) return;

    setIsGenerating(true);
    try {
      const generated = await aiApi.generateCoverLetter(
        selectedResume.content,
        formData.job_description,
        formData.company_name
      );
      // Create the cover letter with the generated content
      const newLetter = await coverLettersApi.create({
        content: generated.content,
      });
      onGenerate(newLetter);
    } catch (error) {
      console.error('Failed to generate cover letter:', error);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-[var(--surface-strong)] rounded-lg shadow-xl max-w-2xl w-full p-6">
        <h2 className="text-xl font-bold mb-4 font-display tracking-[-0.02em]">Generate Cover Letter</h2>

        <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4">
          <div>
            <label htmlFor="select-resume" className="glass-label">Select Resume</label>
            <select
              id="select-resume"
              required
              value={formData.resume_id}
              onChange={(e) => setFormData({ ...formData, resume_id: e.target.value })}
              className="mt-1 block w-full glass-select"
            >
              <option value="">Select a resume...</option>
              {resumes.map((resume) => (
                <option key={resume.id} value={resume.id}>{resume.version_name}</option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="company-name" className="glass-label">Company Name</label>
              <input
                id="company-name"
                type="text"
                required
                value={formData.company_name}
                onChange={(e) => setFormData({ ...formData, company_name: e.target.value })}
                className="mt-1 block w-full glass-input"
              />
            </div>
            <div>
              <label htmlFor="position" className="glass-label">Position</label>
              <input
                id="position"
                type="text"
                required
                value={formData.position}
                onChange={(e) => setFormData({ ...formData, position: e.target.value })}
                className="mt-1 block w-full glass-input"
              />
            </div>
          </div>

          <div>
            <label htmlFor="job-description" className="glass-label">Job Description</label>
            <textarea
              id="job-description"
              required
              rows={6}
              value={formData.job_description}
              onChange={(e) => setFormData({ ...formData, job_description: e.target.value })}
              className="mt-1 block w-full glass-textarea"
              placeholder="Paste the job description here..."
            />
          </div>

          <div className="flex justify-end space-x-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="glass-button-secondary"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isGenerating}
              className="glass-button-primary disabled:opacity-50 flex items-center"
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
      </div>
    </div>
  );
}
