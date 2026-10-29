/** Types mirroring the FastAPI response schemas. */

export type WorkArrangement = "remote" | "hybrid" | "onsite" | "unknown";
export type ExperienceLevel = "entry" | "associate" | "mid_senior" | "unknown";
export type Priority = "high" | "medium" | "low";
export type ApplicationStatus =
  | "saved"
  | "applied"
  | "assessment"
  | "interview"
  | "offer"
  | "rejected"
  | "withdrawn";
export type FetchRunStatus = "running" | "success" | "partial" | "failed" | "skipped";
export type RefreshTrigger = "manual" | "scheduled";
export type SourceAvailability = "available" | "unavailable" | "not_configured";
export type JobSort = "newest" | "oldest" | "relevant" | "company";
export type ApplicationSort = "newest" | "oldest" | "updated" | "company";
export type ShortlistSort = "newest" | "oldest" | "priority";

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ShortlistSummary {
  id: string;
  priority: Priority;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ApplicationSummary {
  id: string;
  status: ApplicationStatus;
  application_date: string | null;
  follow_up_date: string | null;
  resume_reference: string | null;
  updated_at: string;
}

export interface DuplicateRef {
  id: string;
  source: string;
  source_label: string;
  title: string;
  company_name: string;
  job_url: string;
  published_at: string | null;
}

export interface Job {
  id: string;
  source: string;
  source_label: string;
  source_job_id: string | null;
  title: string;
  company_name: string;
  location: string | null;
  work_arrangement: WorkArrangement;
  experience_level: ExperienceLevel;
  description_snippet: string | null;
  job_url: string;
  published_at: string | null;
  posting_age_hours: number | null;
  first_seen_at: string;
  discovered_age_hours: number;
  last_seen_at: string;
  is_test_data: boolean;
  is_shortlisted: boolean;
  shortlist: ShortlistSummary | null;
  application: ApplicationSummary | null;
  possible_duplicate_count: number;
  description?: string | null;
  possible_duplicates?: DuplicateRef[];
}

export interface JobPage extends Page<Job> {
  unknown_published_count: number;
  include_test_data: boolean;
}

export interface ShortlistEntry {
  id: string;
  job: Job;
  priority: Priority;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface Application {
  id: string;
  job: Job;
  status: ApplicationStatus;
  application_date: string | null;
  notes: string | null;
  follow_up_date: string | null;
  resume_reference: string | null;
  created_at: string;
  updated_at: string;
}

export interface FetchRun {
  id: string;
  source: string;
  source_label: string;
  trigger: RefreshTrigger;
  status: FetchRunStatus;
  started_at: string;
  finished_at: string | null;
  duration_seconds: number | null;
  fetched_jobs_count: number;
  new_jobs_count: number;
  updated_jobs_count: number;
  unchanged_jobs_count: number;
  error_message: string | null;
  warnings?: string[];
}

export interface RefreshResponse {
  runs: FetchRun[];
  new_jobs: number;
  updated_jobs: number;
  message: string;
}

export interface SourceInfo {
  key: string;
  name: string;
  description: string;
  availability: SourceAvailability;
  availability_reason: string | null;
  supports_refresh: boolean;
  can_refresh: boolean;
  is_test_data: boolean;
  docs_url: string | null;
  required_config: string[];
  stored_jobs_count: number;
  last_run: FetchRun | null;
}

export interface StatusBreakdownItem {
  status: ApplicationStatus;
  label: string;
  count: number;
}

export interface SourceBreakdownItem {
  source: string;
  label: string;
  count: number;
}

export interface DashboardSummary {
  generated_at: string;
  recent_period_hours: number;
  include_test_data: boolean;
  total_jobs: number;
  jobs_discovered_recent: number;
  jobs_published_recent: number;
  unknown_published_jobs: number;
  shortlisted_jobs: number;
  applications_total: number;
  applications_submitted: number;
  applications_in_progress: number;
  saved_count: number;
  applied_count: number;
  assessment_count: number;
  interview_count: number;
  offer_count: number;
  rejected_count: number;
  withdrawn_count: number;
  interviews: number;
  offers: number;
  status_breakdown: StatusBreakdownItem[];
  source_breakdown: SourceBreakdownItem[];
  recent_jobs: Job[];
  latest_refresh: FetchRun | null;
  test_data_jobs: number;
  upcoming_follow_ups: number;
}

export interface ActivityPoint {
  date: string;
  jobs_discovered: number;
  applications_submitted: number;
}

export interface ActivityResponse {
  days: number;
  include_test_data: boolean;
  points: ActivityPoint[];
  jobs_discovered_total: number;
  applications_submitted_total: number;
}

export interface SearchSettings {
  default_titles: string | null;
  default_keywords: string | null;
  default_location: string | null;
  default_work_arrangement: "any" | WorkArrangement;
  default_experience_level: "any" | ExperienceLevel;
  default_posting_age_hours: number;
  default_sources: string[];
  scheduled_refresh_enabled: boolean;
  scheduled_refresh_interval_minutes: number;
  updated_at: string | null;
}

export interface JobFilters {
  q?: string;
  titles?: string[];
  keywords?: string[];
  location?: string;
  work_arrangement?: WorkArrangement;
  experience_level?: ExperienceLevel;
  sources?: string[];
  max_age_hours?: number;
  include_unknown_published?: boolean;
  shortlisted?: boolean;
  application_status?: ApplicationStatus[];
  include_test_data?: boolean;
  sort?: JobSort;
  page?: number;
  page_size?: number;
}

export interface ShortlistFilters {
  sources?: string[];
  priority?: Priority;
  date_from?: string;
  date_to?: string;
  search?: string;
  sort?: ShortlistSort;
  page?: number;
  page_size?: number;
}

export interface ApplicationFilters {
  status?: ApplicationStatus[];
  company?: string;
  search?: string;
  date_from?: string;
  date_to?: string;
  sort?: ApplicationSort;
  page?: number;
  page_size?: number;
}

export interface ManualJobImportInput {
  title: string;
  company_name: string;
  job_url: string;
  source: string;
  location?: string | null;
  work_arrangement?: WorkArrangement;
  experience_level?: ExperienceLevel;
  description?: string | null;
  published_at?: string | null;
  source_job_id?: string | null;
}
