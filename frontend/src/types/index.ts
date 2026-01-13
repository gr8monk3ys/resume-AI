// User types
export interface User {
  id: number;
  username: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
  last_login: string | null;
}

export interface Profile {
  id: number;
  user_id: number | null;
  name: string;
  email: string | null;
  phone: string | null;
  linkedin: string | null;
  github: string | null;
  portfolio: string | null;
  created_at: string;
  updated_at: string;
}

// Auth types
export interface LoginCredentials {
  username: string;
  password: string;
}

export interface RegisterData {
  username: string;
  email: string;
  password: string;
  full_name?: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

// Resume types
export interface Resume {
  id: number;
  profile_id: number;
  version_name: string;
  content: string;
  ats_score: number | null;
  keywords: string | null;
  created_at: string;
  updated_at: string;
}

export interface ATSAnalysis {
  ats_score: number;
  suggestions: string[];
  keyword_matches: string[];
  missing_keywords: string[];
  score_breakdown: Record<string, number>;
}

// Job types
export type JobStatus =
  | 'Bookmarked'
  | 'Applied'
  | 'Phone Screen'
  | 'Interview'
  | 'Offer'
  | 'Rejected';

export interface JobApplication {
  id: number;
  profile_id: number;
  company: string;
  position: string;
  job_description: string | null;
  status: JobStatus;
  application_date: string | null;
  deadline: string | null;
  location: string | null;
  job_url: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface JobStats {
  total: number;
  status_breakdown: Record<string, number>;
  response_rate: number;
  offer_rate: number;
}

// Cover Letter types
export interface CoverLetter {
  id: number;
  profile_id: number;
  job_application_id: number | null;
  content: string;
  created_at: string;
  updated_at: string;
}

// AI types
export interface TailorResumeResponse {
  tailored_resume: string;
  changes_made: string[];
  keywords_added: string[];
}

export interface AnswerQuestionResponse {
  answer: string;
  tips: string[] | null;
}

export interface InterviewPrepResponse {
  answer: string;
  situation: string | null;
  task: string | null;
  action: string | null;
  result: string | null;
  tips: string[];
}
