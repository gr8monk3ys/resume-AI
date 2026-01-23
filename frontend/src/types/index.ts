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

// Interview Event types for Timeline
export type InterviewEventType =
  | 'phone_screen'
  | 'technical'
  | 'behavioral'
  | 'onsite'
  | 'panel'
  | 'hr'
  | 'final'
  | 'follow_up'
  | 'other';

export type FollowUpUrgency = 'low' | 'medium' | 'high' | 'overdue';

export interface InterviewEvent {
  id: string;
  job_id: number;
  company: string;
  position: string;
  event_type: InterviewEventType;
  scheduled_date: string;
  scheduled_time?: string;
  duration_minutes?: number;
  location?: string;
  meeting_link?: string;
  interviewer_names?: string[];
  notes?: string;
  is_completed: boolean;
  follow_up_date?: string;
  follow_up_done: boolean;
  created_at: string;
}

// Analytics types
export interface WeeklyApplicationData {
  week: string;
  count: number;
}

export interface CompanySuccessRate {
  company: string;
  applications: number;
  offers: number;
  rate: number;
}

export interface JobGoals {
  weekly_target: number;
  monthly_target: number;
  weekly_current: number;
  monthly_current: number;
}

// Analytics types
export type DateRangeOption = '7d' | '30d' | '90d' | 'all' | 'custom';
export type TimelinePeriod = 'daily' | 'weekly' | 'monthly';

export interface AnalyticsOverview {
  total_applications: number;
  response_rate: number;
  response_rate_trend: number;
  interview_rate: number;
  interview_rate_trend: number;
  offer_rate: number;
  offer_rate_trend: number;
  avg_response_time_days: number;
  active_applications: number;
}

export interface TimelineDataPoint {
  date: string;
  count: number;
  label: string;
}

export interface ConversionFunnelStage {
  stage: string;
  count: number;
  percentage: number;
  dropoff_rate: number;
}

export interface SourcePerformance {
  source: string;
  applications: number;
  responses: number;
  interviews: number;
  offers: number;
  response_rate: number;
}

export interface CompanyStats {
  company: string;
  applications: number;
  responses: number;
  interviews: number;
  offers: number;
  response_rate: number;
  avg_response_time_days: number | null;
}

export interface ResumePerformance {
  resume_id: number;
  version_name: string;
  applications: number;
  interviews: number;
  offers: number;
  interview_rate: number;
  ats_score: number | null;
}

export interface ActivityLogEntry {
  id: number;
  timestamp: string;
  type: 'application' | 'status_change' | 'interview' | 'offer';
  description: string;
  company: string;
  position: string;
}

export interface AnalyticsFilters {
  dateRange: DateRangeOption;
  customStartDate?: string;
  customEndDate?: string;
  status?: JobStatus | '';
  source?: string;
}

// Job Filter types
export type CompanyFilterType = 'blacklist' | 'whitelist';

export interface CompanyFilter {
  id: string;
  company_name: string;
  filter_type: CompanyFilterType;
  reason: string | null;
  created_at: string;
}

export type KeywordFilterType = 'exclude' | 'require';
export type KeywordAppliesTo = 'title' | 'description' | 'both';

export interface KeywordFilter {
  id: string;
  keyword: string;
  filter_type: KeywordFilterType;
  applies_to: KeywordAppliesTo;
  created_at: string;
}

export type QuestionTemplateType = 'text' | 'number' | 'select' | 'boolean';
export type QuestionTemplateCategory =
  | 'experience'
  | 'salary'
  | 'availability'
  | 'authorization'
  | 'personal'
  | 'demographics';

export interface QuestionTemplate {
  id: string;
  question_pattern: string;
  answer: string;
  answer_type: QuestionTemplateType;
  category: QuestionTemplateCategory;
  created_at: string;
  updated_at: string;
}

export interface JobCheckResult {
  blocked: boolean;
  required: boolean;
  matched_company_filter: CompanyFilter | null;
  matched_keyword_filters: KeywordFilter[];
}
