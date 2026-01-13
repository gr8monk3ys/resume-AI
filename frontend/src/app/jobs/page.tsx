'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/lib/auth';
import { useRouter } from 'next/navigation';
import { jobsApi } from '@/lib/api';
import type { JobApplication, JobStatus } from '@/types';
import { cn, getStatusColor, formatDate } from '@/lib/utils';
import { Plus, ExternalLink, Trash2 } from 'lucide-react';

const COLUMNS: JobStatus[] = [
  'Bookmarked',
  'Applied',
  'Phone Screen',
  'Interview',
  'Offer',
  'Rejected',
];

export default function JobsPage() {
  const { user, tokens, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const [jobs, setJobs] = useState<JobApplication[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login');
    }
  }, [user, authLoading, router]);

  useEffect(() => {
    if (tokens?.access_token) {
      loadJobs();
    }
  }, [tokens]);

  const loadJobs = async () => {
    if (!tokens?.access_token) return;
    try {
      const data = await jobsApi.list(tokens.access_token);
      setJobs(data as JobApplication[]);
    } catch (error) {
      console.error('Failed to load jobs:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const updateJobStatus = async (jobId: number, newStatus: JobStatus) => {
    if (!tokens?.access_token) return;
    try {
      await jobsApi.updateStatus(tokens.access_token, jobId, newStatus);
      setJobs(jobs.map(job =>
        job.id === jobId ? { ...job, status: newStatus } : job
      ));
    } catch (error) {
      console.error('Failed to update job status:', error);
    }
  };

  const deleteJob = async (jobId: number) => {
    if (!tokens?.access_token) return;
    if (!confirm('Are you sure you want to delete this job application?')) return;
    try {
      await jobsApi.delete(tokens.access_token, jobId);
      setJobs(jobs.filter(job => job.id !== jobId));
    } catch (error) {
      console.error('Failed to delete job:', error);
    }
  };

  if (authLoading || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    );
  }

  const jobsByStatus = COLUMNS.reduce((acc, status) => {
    acc[status] = jobs.filter(job => job.status === status);
    return acc;
  }, {} as Record<JobStatus, JobApplication[]>);

  return (
    <div className="max-w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Job Tracker</h1>
          <p className="text-gray-500">Track your job applications</p>
        </div>
        <button
          onClick={() => setShowAddForm(true)}
          className="inline-flex items-center px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700"
        >
          <Plus className="w-4 h-4 mr-2" />
          Add Job
        </button>
      </div>

      {/* Kanban Board */}
      <div className="flex gap-4 overflow-x-auto pb-4">
        {COLUMNS.map((status) => (
          <div
            key={status}
            className="flex-shrink-0 w-72 bg-gray-100 rounded-lg p-4"
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-medium text-gray-900">{status}</h3>
              <span className="bg-gray-200 text-gray-600 text-sm px-2 py-1 rounded">
                {jobsByStatus[status].length}
              </span>
            </div>

            <div className="space-y-3">
              {jobsByStatus[status].map((job) => (
                <div
                  key={job.id}
                  className="bg-white rounded-lg shadow p-4 cursor-pointer hover:shadow-md transition-shadow"
                >
                  <div className="flex justify-between items-start">
                    <div className="flex-1 min-w-0">
                      <h4 className="font-medium text-gray-900 truncate">{job.position}</h4>
                      <p className="text-sm text-gray-500 truncate">{job.company}</p>
                    </div>
                    {job.job_url && (
                      <a
                        href={job.job_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-gray-400 hover:text-primary-600"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <ExternalLink className="w-4 h-4" />
                      </a>
                    )}
                  </div>

                  {job.location && (
                    <p className="text-xs text-gray-400 mt-2">{job.location}</p>
                  )}

                  {job.application_date && (
                    <p className="text-xs text-gray-400 mt-1">
                      Applied: {formatDate(job.application_date)}
                    </p>
                  )}

                  <div className="mt-3 flex items-center justify-between">
                    <select
                      value={job.status}
                      onChange={(e) => updateJobStatus(job.id, e.target.value as JobStatus)}
                      className="text-xs border rounded px-2 py-1"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {COLUMNS.map((s) => (
                        <option key={s} value={s}>{s}</option>
                      ))}
                    </select>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteJob(job.id);
                      }}
                      className="text-gray-400 hover:text-red-600"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Add Job Modal */}
      {showAddForm && (
        <AddJobModal
          onClose={() => setShowAddForm(false)}
          onAdd={(newJob) => {
            setJobs([newJob, ...jobs]);
            setShowAddForm(false);
          }}
          token={tokens?.access_token || ''}
        />
      )}
    </div>
  );
}

function AddJobModal({
  onClose,
  onAdd,
  token,
}: {
  onClose: () => void;
  onAdd: (job: JobApplication) => void;
  token: string;
}) {
  const [formData, setFormData] = useState({
    company: '',
    position: '',
    job_url: '',
    location: '',
    status: 'Bookmarked' as JobStatus,
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      const newJob = await jobsApi.create(token, formData) as JobApplication;
      onAdd(newJob);
    } catch (error) {
      console.error('Failed to create job:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
        <h2 className="text-xl font-bold mb-4">Add Job Application</h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Company</label>
            <input
              type="text"
              required
              value={formData.company}
              onChange={(e) => setFormData({ ...formData, company: e.target.value })}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Position</label>
            <input
              type="text"
              required
              value={formData.position}
              onChange={(e) => setFormData({ ...formData, position: e.target.value })}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Job URL</label>
            <input
              type="url"
              value={formData.job_url}
              onChange={(e) => setFormData({ ...formData, job_url: e.target.value })}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Location</label>
            <input
              type="text"
              value={formData.location}
              onChange={(e) => setFormData({ ...formData, location: e.target.value })}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Status</label>
            <select
              value={formData.status}
              onChange={(e) => setFormData({ ...formData, status: e.target.value as JobStatus })}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              {COLUMNS.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
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
              {isSubmitting ? 'Adding...' : 'Add Job'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
