export interface Candidate {
  id: string;
  name: string;
  email: string;
  phone: string | null;
  cv_file_path: string | null;
  cv_parsed_json: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
  preferences: JobPreferences | null;
}

export interface JobPreferences {
  id: string;
  candidate_id: string;
  target_titles: string[];
  target_cities: string[];
  min_salary: number | null;
  max_salary: number | null;
  excluded_companies: string[];
  preferred_industries: string[];
  remote_ok: boolean;
  full_time_only: boolean;
}

export interface Job {
  id: string;
  title: string;
  company_name: string;
  city: string | null;
  salary_range: string | null;
  salary_min: number | null;
  salary_max: number | null;
  description: string | null;
  requirements: string | null;
  url: string | null;
  is_active: boolean;
  source: string;
  created_at: string;
  updated_at: string;
}

export interface JobListResponse {
  items: Job[];
  total: number;
  skip: number;
  limit: number;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface UserInfo {
  email: string;
}

export interface ScoreBreakdown {
  skills: number;
  experience: number;
  salary: number;
  culture: number;
}

export interface JobScore {
  id: string;
  job_id: string;
  candidate_id: string;
  score: number;
  score_breakdown: ScoreBreakdown;
  match_summary: string;
  strengths: string[];
  concerns: string[];
  model_used: string;
  prompt_tokens: number;
  completion_tokens: number;
  scored_at: string;
}

export interface Application {
  id: string;
  job_id: string;
  candidate_id: string;
  status: string;
  draft_message: string | null;
  final_message: string | null;
  approved_at: string | null;
  sent_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ApplicationListResponse {
  items: Application[];
  total: number;
  skip: number;
  limit: number;
}

export interface DashboardStats {
  total_jobs: number;
  active_jobs: number;
  total_applications: number;
  pending_approvals: number;
  total_ai_calls: number;
  total_tokens_today: number;
  estimated_cost_today_usd: number;
}

export interface AIAuditLog {
  id: string;
  event_type: string;
  entity_type: string;
  entity_id: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
  result_summary: string;
  created_at: string;
}

export interface AIAuditLogListResponse {
  items: AIAuditLog[];
  total: number;
  skip: number;
  limit: number;
}

export interface ApprovalQueue {
  id: string;
  application_id: string;
  action: string;
  payload: {
    message: string;
    job_title: string;
    company: string;
    score: number | null;
  };
  status: string;
  reviewer_notes: string | null;
  created_at: string;
  reviewed_at: string | null;
}

export interface ApprovalQueueListResponse {
  items: ApprovalQueue[];
  total: number;
  skip: number;
  limit: number;
}

export interface NotificationSettings {
  telegram_configured: boolean;
  telegram_chat_id: string | null;
}
