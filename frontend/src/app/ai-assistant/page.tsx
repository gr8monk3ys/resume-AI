'use client';

import { useEffect, useState, useCallback } from 'react';
import { useAuth } from '@/lib/auth';
import { useRouter } from 'next/navigation';
import { aiApi, resumesApi } from '@/lib/api';
import type { Resume, TailorResumeResponse, AnswerQuestionResponse, InterviewPrepResponse } from '@/types';
import { Bot, FileText, MessageSquare, Mic } from 'lucide-react';

type Tool = 'tailor' | 'question' | 'interview';

export default function AIAssistantPage() {
  const { user, tokens, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const [selectedTool, setSelectedTool] = useState<Tool>('tailor');
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [selectedResume, setSelectedResume] = useState<Resume | null>(null);
  const [jobDescription, setJobDescription] = useState('');
  const [question, setQuestion] = useState('');
  const [result, setResult] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login');
    }
  }, [user, authLoading, router]);

  const loadResumes = useCallback(async () => {
    if (!tokens?.access_token) return;
    try {
      const data = await resumesApi.list(tokens.access_token);
      setResumes(data as Resume[]);
      if ((data as Resume[]).length > 0) {
        setSelectedResume((data as Resume[])[0]);
      }
    } catch (error) {
      console.error('Failed to load resumes:', error);
    }
  }, [tokens]);

  useEffect(() => {
    if (tokens?.access_token) {
      loadResumes();
    }
  }, [tokens, loadResumes]);

  const handleTailorResume = async () => {
    if (!tokens?.access_token || !selectedResume) return;
    setIsLoading(true);
    setResult('');
    try {
      const response = await aiApi.tailorResume(tokens.access_token, {
        resume_content: selectedResume.content,
        job_description: jobDescription,
      });
      setResult((response as TailorResumeResponse).tailored_resume);
    } catch (error) {
      console.error('Failed to tailor resume:', error);
      setResult('Error: Failed to tailor resume. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleAnswerQuestion = async () => {
    if (!tokens?.access_token) return;
    setIsLoading(true);
    setResult('');
    try {
      const response = await aiApi.answerQuestion(tokens.access_token, {
        question,
        resume_content: selectedResume?.content,
        job_description: jobDescription,
      });
      setResult((response as AnswerQuestionResponse).answer);
    } catch (error) {
      console.error('Failed to answer question:', error);
      setResult('Error: Failed to generate answer. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleInterviewPrep = async () => {
    if (!tokens?.access_token) return;
    setIsLoading(true);
    setResult('');
    try {
      const response = await aiApi.interviewPrep(tokens.access_token, {
        question,
        resume_content: selectedResume?.content,
        job_description: jobDescription,
      });
      setResult((response as InterviewPrepResponse).answer);
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
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    );
  }

  const tools = [
    { id: 'tailor' as Tool, name: 'Resume Tailor', icon: FileText, description: 'Tailor your resume for a specific job' },
    { id: 'question' as Tool, name: 'Question Answerer', icon: MessageSquare, description: 'Get answers for application questions' },
    { id: 'interview' as Tool, name: 'Interview Prep', icon: Mic, description: 'Prepare STAR-method answers' },
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">AI Assistant</h1>
        <p className="text-gray-500">AI-powered tools to help with your job search</p>
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
                : 'border-gray-200 hover:border-gray-300'
            }`}
          >
            <tool.icon className={`w-6 h-6 ${selectedTool === tool.id ? 'text-primary-600' : 'text-gray-400'}`} />
            <h3 className="mt-2 font-medium">{tool.name}</h3>
            <p className="text-sm text-gray-500">{tool.description}</p>
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Input Panel */}
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Select Resume</label>
            <select
              value={selectedResume?.id || ''}
              onChange={(e) => {
                const resume = resumes.find(r => r.id === Number(e.target.value));
                setSelectedResume(resume || null);
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="">Select a resume...</option>
              {resumes.map((resume) => (
                <option key={resume.id} value={resume.id}>{resume.version_name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Job Description</label>
            <textarea
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              rows={6}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              placeholder="Paste the job description here..."
            />
          </div>

          {(selectedTool === 'question' || selectedTool === 'interview') && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {selectedTool === 'question' ? 'Application Question' : 'Interview Question'}
              </label>
              <textarea
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
                placeholder={selectedTool === 'question'
                  ? "e.g., Why do you want to work at our company?"
                  : "e.g., Tell me about a time you faced a challenge at work."
                }
              />
            </div>
          )}

          <button
            onClick={() => {
              if (selectedTool === 'tailor') handleTailorResume();
              else if (selectedTool === 'question') handleAnswerQuestion();
              else handleInterviewPrep();
            }}
            disabled={isLoading || !selectedResume}
            className="w-full py-3 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
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
          <label className="block text-sm font-medium text-gray-700 mb-1">Result</label>
          <div className="bg-white border border-gray-300 rounded-md p-4 min-h-[400px]">
            {result ? (
              <pre className="whitespace-pre-wrap text-sm">{result}</pre>
            ) : (
              <p className="text-gray-400 text-center mt-32">
                Results will appear here
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
