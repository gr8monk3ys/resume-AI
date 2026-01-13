'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/lib/auth';
import { useRouter } from 'next/navigation';
import { resumesApi } from '@/lib/api';
import type { Resume } from '@/types';
import { formatDate } from '@/lib/utils';
import { Plus, FileText, Trash2, BarChart3 } from 'lucide-react';

export default function ResumesPage() {
  const { user, tokens, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login');
    }
  }, [user, authLoading, router]);

  useEffect(() => {
    if (tokens?.access_token) {
      loadResumes();
    }
  }, [tokens]);

  const loadResumes = async () => {
    if (!tokens?.access_token) return;
    try {
      const data = await resumesApi.list(tokens.access_token);
      setResumes(data as Resume[]);
    } catch (error) {
      console.error('Failed to load resumes:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const deleteResume = async (id: number) => {
    if (!tokens?.access_token) return;
    if (!confirm('Are you sure you want to delete this resume?')) return;
    try {
      await resumesApi.delete(tokens.access_token, id);
      setResumes(resumes.filter(r => r.id !== id));
    } catch (error) {
      console.error('Failed to delete resume:', error);
    }
  };

  if (authLoading || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">My Resumes</h1>
          <p className="text-gray-500">Manage your resume versions</p>
        </div>
        <button
          onClick={() => setShowAddForm(true)}
          className="inline-flex items-center px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700"
        >
          <Plus className="w-4 h-4 mr-2" />
          Add Resume
        </button>
      </div>

      {resumes.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg shadow">
          <FileText className="w-12 h-12 mx-auto text-gray-400" />
          <h3 className="mt-4 text-lg font-medium text-gray-900">No resumes yet</h3>
          <p className="mt-2 text-gray-500">Add your first resume to get started</p>
          <button
            onClick={() => setShowAddForm(true)}
            className="mt-4 inline-flex items-center px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700"
          >
            <Plus className="w-4 h-4 mr-2" />
            Add Resume
          </button>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {resumes.map((resume) => (
            <div
              key={resume.id}
              className="bg-white rounded-lg shadow p-6 hover:shadow-md transition-shadow"
            >
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <h3 className="font-medium text-gray-900">{resume.version_name}</h3>
                  <p className="text-sm text-gray-500 mt-1">
                    Updated: {formatDate(resume.updated_at)}
                  </p>
                </div>
                {resume.ats_score !== null && (
                  <div className="flex items-center bg-primary-50 text-primary-700 px-2 py-1 rounded">
                    <BarChart3 className="w-4 h-4 mr-1" />
                    <span className="text-sm font-medium">{resume.ats_score}</span>
                  </div>
                )}
              </div>

              <p className="mt-4 text-sm text-gray-600 line-clamp-3">
                {resume.content.slice(0, 200)}...
              </p>

              <div className="mt-4 flex justify-end">
                <button
                  onClick={() => deleteResume(resume.id)}
                  className="text-gray-400 hover:text-red-600"
                >
                  <Trash2 className="w-5 h-5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showAddForm && (
        <AddResumeModal
          onClose={() => setShowAddForm(false)}
          onAdd={(newResume) => {
            setResumes([newResume, ...resumes]);
            setShowAddForm(false);
          }}
          token={tokens?.access_token || ''}
        />
      )}
    </div>
  );
}

function AddResumeModal({
  onClose,
  onAdd,
  token,
}: {
  onClose: () => void;
  onAdd: (resume: Resume) => void;
  token: string;
}) {
  const [formData, setFormData] = useState({
    version_name: '',
    content: '',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      const newResume = await resumesApi.create(token, formData) as Resume;
      onAdd(newResume);
    } catch (error) {
      console.error('Failed to create resume:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full p-6">
        <h2 className="text-xl font-bold mb-4">Add Resume</h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Version Name</label>
            <input
              type="text"
              required
              value={formData.version_name}
              onChange={(e) => setFormData({ ...formData, version_name: e.target.value })}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
              placeholder="e.g., Software Engineer - Google"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Resume Content</label>
            <textarea
              required
              rows={12}
              value={formData.content}
              onChange={(e) => setFormData({ ...formData, content: e.target.value })}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md font-mono text-sm"
              placeholder="Paste your resume content here..."
            />
          </div>

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
              {isSubmitting ? 'Saving...' : 'Save Resume'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
