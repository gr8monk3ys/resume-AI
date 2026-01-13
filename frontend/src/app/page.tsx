'use client';

import { useAuth } from '@/lib/auth';
import Link from 'next/link';
import {
  FileText,
  Briefcase,
  Mail,
  Bot,
  BarChart3,
  Target,
} from 'lucide-react';

const features = [
  {
    name: 'Resume Optimizer',
    description: 'Get ATS scores and AI-powered optimization suggestions',
    href: '/resumes',
    icon: FileText,
    color: 'bg-blue-500',
  },
  {
    name: 'Job Tracker',
    description: 'Kanban board to track your job applications',
    href: '/jobs',
    icon: Briefcase,
    color: 'bg-green-500',
  },
  {
    name: 'Cover Letters',
    description: 'Generate personalized cover letters with AI',
    href: '/cover-letters',
    icon: Mail,
    color: 'bg-purple-500',
  },
  {
    name: 'AI Assistant',
    description: 'Tailor resumes, answer questions, interview prep',
    href: '/ai-assistant',
    icon: Bot,
    color: 'bg-orange-500',
  },
];

export default function HomePage() {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    );
  }

  if (!user) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="text-center">
          <h1 className="text-4xl font-bold tracking-tight text-gray-900 sm:text-5xl md:text-6xl">
            <span className="block">ResuBoost AI</span>
            <span className="block text-primary-600">Your AI Job Search Toolkit</span>
          </h1>
          <p className="mt-3 max-w-md mx-auto text-base text-gray-500 sm:text-lg md:mt-5 md:text-xl md:max-w-3xl">
            Optimize your resume, track applications, generate cover letters, and prepare for interviews - all powered by AI.
          </p>
          <div className="mt-5 max-w-md mx-auto sm:flex sm:justify-center md:mt-8">
            <div className="rounded-md shadow">
              <Link
                href="/login"
                className="w-full flex items-center justify-center px-8 py-3 border border-transparent text-base font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 md:py-4 md:text-lg md:px-10"
              >
                Get Started
              </Link>
            </div>
            <div className="mt-3 rounded-md shadow sm:mt-0 sm:ml-3">
              <Link
                href="/register"
                className="w-full flex items-center justify-center px-8 py-3 border border-transparent text-base font-medium rounded-md text-primary-600 bg-white hover:bg-gray-50 md:py-4 md:text-lg md:px-10"
              >
                Create Account
              </Link>
            </div>
          </div>
        </div>

        <div className="mt-20">
          <h2 className="text-center text-3xl font-bold text-gray-900">Features</h2>
          <div className="mt-10 grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-4">
            {features.map((feature) => (
              <div key={feature.name} className="bg-white rounded-lg shadow-md p-6">
                <div className={`${feature.color} w-12 h-12 rounded-lg flex items-center justify-center`}>
                  <feature.icon className="w-6 h-6 text-white" />
                </div>
                <h3 className="mt-4 text-lg font-medium text-gray-900">{feature.name}</h3>
                <p className="mt-2 text-sm text-gray-500">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // Dashboard for logged-in users
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">
          Welcome back, {user.full_name || user.username}!
        </h1>
        <p className="mt-1 text-gray-500">Here&apos;s your job search dashboard</p>
      </div>

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {features.map((feature) => (
          <Link
            key={feature.name}
            href={feature.href}
            className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow"
          >
            <div className={`${feature.color} w-12 h-12 rounded-lg flex items-center justify-center`}>
              <feature.icon className="w-6 h-6 text-white" />
            </div>
            <h3 className="mt-4 text-lg font-medium text-gray-900">{feature.name}</h3>
            <p className="mt-2 text-sm text-gray-500">{feature.description}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
