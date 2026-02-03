'use client';

import { Bot, FileText, MessageSquare, Mic } from 'lucide-react';
import { useEffect, useState, useCallback } from 'react';

import { AIMarkdown } from '@/components/AIMarkdown';
import { aiApi, resumesApi } from '@/lib/api';
import { useAuth } from '@/lib/auth';

import type { Resume } from '@/types';


type Tool = 'tailor' | 'question' | 'interview';

export default function AIAssistantPage() {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const [selectedTool, setSelectedTool] = useState<Tool>('tailor');
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [selectedResume, setSelectedResume] = useState<Resume | null>(null);
  const [jobDescription, setJobDescription] = useState('');
  const [question, setQuestion] = useState('');
  const [result, setResult] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const loadResumes = useCallback(async () => {
    if (!isAuthenticated) return;
    try {
      const data = await resumesApi.list();
      setResumes(data);
      if ((data).length > 0) {
        setSelectedResume((data)[0] ?? null);
      }
    } catch (error) {
      console.error('Failed to load resumes:', error);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    if (isAuthenticated) {
      void loadResumes()
    }
  }, [isAuthenticated, loadResumes])

  const handleTailorResume = async () => {
    if (!isAuthenticated || !selectedResume) return;
    setIsLoading(true);
    setResult('');
    try {
      const response = await aiApi.tailorResume(
        selectedResume.content,
        jobDescription
      );
      setResult((response).tailored_resume);
    } catch (error) {
      console.error('Failed to tailor resume:', error);
      setResult('Error: Failed to tailor resume. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleAnswerQuestion = async () => {
    if (!isAuthenticated) return;
    setIsLoading(true);
    setResult('');
    try {
      const response = await aiApi.answerQuestion(
        question,
        `Resume: ${selectedResume?.content || ''}\n\nJob Description: ${jobDescription}`
      );
      setResult((response).answer);
    } catch (error) {
      console.error('Failed to answer question:', error);
      setResult('Error: Failed to generate answer. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleInterviewPrep = async () => {
    if (!isAuthenticated) return;
    setIsLoading(true);
    setResult('');
    try {
      const response = await aiApi.interviewPrep(
        question,
        selectedResume?.content,
        jobDescription
      );
      setResult((response).answer);
    } catch (error) {
      console.error('Failed to prepare interview answer:', error);
      setResult('Error: Failed to generate answer. Please try again.');
    } finally {
      setIsLoading(false);
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

  const tools = [
    { id: 'tailor' as Tool, name: 'Resume Tailor', icon: FileText, description: 'Tailor your resume for a specific job' },
    { id: 'question' as Tool, name: 'Question Answerer', icon: MessageSquare, description: 'Get answers for application questions' },
    { id: 'interview' as Tool, name: 'Interview Prep', icon: Mic, description: 'Prepare STAR-method answers' },
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-[var(--ink)] font-display tracking-[-0.02em]">AI Assistant</h1>
        <p className="text-[var(--muted)]">AI-powered tools to help with your job search</p>
      </div>

      {/* Tool Selection */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        {tools.map((tool) => (
          <button
            key={tool.id}
            onClick={() => {
              setSelectedTool(tool.id);
              setResult('');
            }}
            className={`p-4 rounded-lg border-2 transition-all ${
              selectedTool === tool.id
                ? 'border-primary-600 bg-primary-50'
                : 'border-[var(--line)] hover:border-[var(--line-strong)]'
            }`}
          >
            <tool.icon className={`w-6 h-6 ${selectedTool === tool.id ? 'text-primary-600' : 'text-[var(--muted-soft)]'}`} />
            <h3 className="mt-2 font-medium">{tool.name}</h3>
            <p className="text-sm text-[var(--muted)]">{tool.description}</p>
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Input Panel */}
        <div className="space-y-4">
          <div>
            <label htmlFor="resume-select" className="glass-label mb-1">Select Resume</label>
            <select
              id="resume-select"
              value={selectedResume?.id || ''}
              onChange={(e) => {
                const resume = resumes.find(r => r.id === Number(e.target.value));
                setSelectedResume(resume || null);
              }}
              className="w-full glass-select"
            >
              <option value="">Select a resume...</option>
              {resumes.map((resume) => (
                <option key={resume.id} value={resume.id}>{resume.version_name}</option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="job-description" className="glass-label mb-1">Job Description</label>
            <textarea
              id="job-description"
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              rows={6}
              className="w-full glass-textarea"
              placeholder="Paste the job description here..."
            />
          </div>

          {(selectedTool === 'question' || selectedTool === 'interview') && (
            <div>
              <label htmlFor="question-input" className="glass-label mb-1">
                {selectedTool === 'question' ? 'Application Question' : 'Interview Question'}
              </label>
              <textarea
                id="question-input"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                rows={3}
                className="w-full glass-textarea"
                placeholder={selectedTool === 'question'
                  ? "e.g., Why do you want to work at our company?"
                  : "e.g., Tell me about a time you faced a challenge at work."
                }
              />
            </div>
          )}

          <button
            onClick={() => {
              if (selectedTool === 'tailor') void handleTailorResume()
              else if (selectedTool === 'question') void handleAnswerQuestion()
              else void handleInterviewPrep()
            }}
            disabled={isLoading || !selectedResume}
            className="w-full glass-button-primary disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
          >
            {isLoading ? (
              <>
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2" />
                Generating...
              </>
            ) : (
              <>
                <Bot className="w-5 h-5 mr-2" />
                Generate
              </>
            )}
          </button>
        </div>

        {/* Output Panel */}
        <div>
          <label htmlFor="result-output" className="glass-label mb-1">Result</label>
          <div id="result-output" role="region" aria-live="polite" className="bg-[var(--surface-strong)] border border-[var(--line-strong)] rounded-md p-4 min-h-[400px]">
            {result ? (
              <AIMarkdown content={result} />
            ) : (
              <p className="text-[var(--muted-soft)] text-center mt-32">
                Results will appear here
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
