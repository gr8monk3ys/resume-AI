import {
  FileText,
  Briefcase,
  FileEdit,
  Mic,
  Award,
  ArrowRight,
  CheckCircle,
  TrendingUp,
  Target,
} from 'lucide-react'

const landingFeatures = [
  {
    name: 'Resume Hub',
    description: 'Get ATS scores and AI-powered optimization suggestions for your resumes',
    icon: FileText,
    color: 'bg-blue-500',
  },
  {
    name: 'Job Pipeline',
    description: 'Kanban board to track and manage your job applications',
    icon: Briefcase,
    color: 'bg-green-500',
  },
  {
    name: 'Interview Center',
    description: 'Prepare for interviews with AI-powered STAR method responses',
    icon: Mic,
    color: 'bg-purple-500',
  },
  {
    name: 'Document Generator',
    description: 'Generate personalized cover letters and professional documents',
    icon: FileEdit,
    color: 'bg-orange-500',
  },
  {
    name: 'Career Tools',
    description: 'Track your career journal, goals, and professional growth',
    icon: Award,
    color: 'bg-pink-500',
  },
]

export function LandingPage() {
  return (
    <div className="bg-gradient-to-b from-gray-50 to-white">
      <section className="mx-auto max-w-7xl px-4 py-14 sm:px-6 sm:py-24 lg:px-8">
        <div className="text-center">
          <h1 className="text-4xl font-extrabold tracking-tight text-gray-900 sm:text-5xl md:text-6xl">
            <span className="block">ResuBoost AI</span>
            <span className="mt-2 block text-2xl text-primary-600 sm:text-4xl md:text-5xl">
              Your AI-Powered Job Search Toolkit
            </span>
          </h1>
          <p className="mx-auto mt-5 max-w-xl text-base text-gray-500 sm:mt-6 sm:max-w-2xl sm:text-xl">
            Optimize your resume, track applications, generate cover letters, and prepare for interviews, all powered
            by cutting-edge AI technology.
          </p>
          <div className="mt-8 flex flex-col justify-center gap-4 sm:mt-10 sm:flex-row sm:gap-4">
            <a
              href="/register"
              className="inline-flex h-[48px] w-full items-center justify-center rounded-md border border-transparent bg-primary-600 px-8 text-base font-medium leading-none text-white transition-colors hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 sm:h-[56px] sm:w-auto md:px-10 md:text-lg"
            >
              Get Started Free
              <ArrowRight className="ml-2 h-5 w-5" aria-hidden="true" />
            </a>
            <a
              href="/login"
              className="inline-flex h-[48px] w-full items-center justify-center rounded-md border-2 border-primary-600 bg-white px-8 text-base font-medium leading-none text-primary-600 transition-colors hover:bg-primary-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 sm:h-[56px] sm:w-auto md:px-10 md:text-lg"
            >
              Sign In
            </a>
          </div>
        </div>
      </section>

      <section
        className="bg-primary-600 py-12"
        style={{ contentVisibility: 'auto', containIntrinsicSize: '480px' }}
      >
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mb-10 text-center">
            <h2 className="text-3xl font-bold text-white sm:text-4xl">
              Built for the parts of the search that usually break momentum
            </h2>
            <p className="mt-3 text-lg text-primary-100">
              Keep your materials sharp, your pipeline organized, and your next step visible.
            </p>
          </div>
          <div className="grid grid-cols-1 gap-8 text-center md:grid-cols-3">
            <div className="flex flex-col items-center">
              <CheckCircle className="mb-4 h-12 w-12 text-white" aria-hidden="true" />
              <h3 className="text-xl font-semibold text-white">ATS-Optimized</h3>
              <p className="mt-2 text-primary-100">Get your resume past automated screening systems</p>
            </div>
            <div className="flex flex-col items-center">
              <TrendingUp className="mb-4 h-12 w-12 text-white" aria-hidden="true" />
              <h3 className="text-xl font-semibold text-white">AI-Powered</h3>
              <p className="mt-2 text-primary-100">Leverage advanced AI for personalized suggestions</p>
            </div>
            <div className="flex flex-col items-center">
              <Target className="mb-4 h-12 w-12 text-white" aria-hidden="true" />
              <h3 className="text-xl font-semibold text-white">Track Progress</h3>
              <p className="mt-2 text-primary-100">Visualize and manage your entire job search</p>
            </div>
          </div>
        </div>
      </section>

      <section
        className="mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-24 lg:px-8"
        style={{ contentVisibility: 'auto', containIntrinsicSize: '960px' }}
      >
        <div className="mb-12 text-center">
          <h2 className="text-3xl font-bold text-gray-900 sm:text-4xl">Everything You Need to Land Your Dream Job</h2>
          <p className="mt-4 text-lg text-gray-500">A complete toolkit designed to streamline your job search process</p>
        </div>
        <div className="grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-3">
          {landingFeatures.map((feature) => (
            <div
              key={feature.name}
              className="rounded-xl border border-gray-100 bg-white p-6 shadow-md transition-shadow hover:shadow-lg"
            >
              <div className={`${feature.color} flex h-14 w-14 items-center justify-center rounded-xl`}>
                <feature.icon className="h-7 w-7 text-white" aria-hidden="true" />
              </div>
              <h3 className="mt-5 text-xl font-semibold text-gray-900">{feature.name}</h3>
              <p className="mt-3 text-gray-500">{feature.description}</p>
            </div>
          ))}
        </div>
      </section>

      <section
        className="bg-gray-50 py-16"
        style={{ contentVisibility: 'auto', containIntrinsicSize: '360px' }}
      >
        <div className="mx-auto max-w-7xl px-4 text-center sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold text-gray-900">Ready to Boost Your Job Search?</h2>
          <p className="mt-4 text-lg text-gray-500">
            Join thousands of job seekers who have streamlined their search with ResuBoost AI
          </p>
          <div className="mt-8">
            <a
              href="/register"
              className="inline-flex h-[48px] items-center justify-center rounded-md border border-transparent bg-primary-600 px-8 text-base font-medium leading-none text-white transition-colors hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 sm:h-[56px] md:px-10 md:text-lg"
            >
              Create Your Free Account
              <ArrowRight className="ml-2 h-5 w-5" aria-hidden="true" />
            </a>
          </div>
        </div>
      </section>
    </div>
  )
}
