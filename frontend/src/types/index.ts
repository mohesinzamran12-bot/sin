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
