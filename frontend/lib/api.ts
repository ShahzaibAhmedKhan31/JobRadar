import type {
  ActivityResponse,
  Application,
  ApplicationFilters,
  DashboardSummary,
  FetchRun,
  Job,
  JobFilters,
  JobPage,
  ManualJobImportInput,
  Page,
  RefreshResponse,
  SearchSettings,
  ShortlistEntry,
  ShortlistFilters,
  SourceInfo,
} from "@/types";

export class ApiError extends Error {
  status: number;
  detail?: string;
  code?: string;

  constructor(message: string, status: number, detail?: string, code?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.code = code;
  }
}

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

type QueryValue =
  | string
  | number
  | boolean
  | null
  | undefined
  | (string | number)[];

/**
 * Serialize a typed filter object into a query string. Arrays become repeated
 * parameters (`sources=a&sources=b`), matching FastAPI's list handling.
 */
export function toQueryString(params: object): string {
  const search = new URLSearchParams();
  Object.entries(params as Record<string, QueryValue>).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    if (Array.isArray(value)) {
      value.forEach((entry) => {
        if (entry !== undefined && entry !== null && entry !== "") {
          search.append(key, String(entry));
        }
      });
      return;
    }
    search.set(key, String(value));
  });
  const serialized = search.toString();
  return serialized ? `?${serialized}` : "";
}

function extractMessage(payload: unknown, fallback: string): { message: string; detail?: string } {
  if (typeof payload === "object" && payload !== null) {
    const record = payload as Record<string, unknown>;
    const detail = record.detail;
    if (typeof detail === "string") {
      return { message: detail, detail };
    }
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as Record<string, unknown>;
      const msg = typeof first?.msg === "string" ? first.msg : fallback;
      const location = Array.isArray(first?.loc) ? first.loc.join(".") : undefined;
      return {
        message: location ? `${msg} (${location})` : msg,
        detail: msg,
      };
    }
  }
  return { message: fallback };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
      cache: "no-store",
    });
  } catch {
    throw new ApiError(
      "Cannot reach the JobRadar API. Is the FastAPI server running on port 8000?",
      0,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();
  let payload: unknown = undefined;
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = text;
    }
  }

  if (!response.ok) {
    const { message, detail } = extractMessage(
      payload,
      `Request failed with status ${response.status}`,
    );
    const code =
      typeof payload === "object" && payload !== null
        ? ((payload as Record<string, unknown>).code as string | undefined)
        : undefined;
    throw new ApiError(message, response.status, detail, code);
  }
  return payload as T;
}

/* ---------------------------------------------------------------- Jobs */

export function getJobs(filters: JobFilters): Promise<JobPage> {
  return request<JobPage>(`/api/jobs${toQueryString(filters)}`);
}

export function getJob(jobId: string): Promise<Job> {
  return request<Job>(`/api/jobs/${jobId}`);
}

export function refreshJobs(payload: {
  sources?: string[];
  titles?: string[];
  keywords?: string[];
  location?: string;
  max_age_hours?: number;
  limit?: number;
}): Promise<RefreshResponse> {
  return request<RefreshResponse>("/api/jobs/refresh", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getRefreshHistory(params: {
  page?: number;
  page_size?: number;
  source?: string;
}): Promise<Page<FetchRun>> {
  return request<Page<FetchRun>>(`/api/jobs/refresh-history${toQueryString(params)}`);
}

export function importJob(payload: ManualJobImportInput): Promise<{
  job: Job;
  created: boolean;
  message: string;
}> {
  return request("/api/jobs/import", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/* ----------------------------------------------------------- Shortlist */

export function getShortlist(filters: ShortlistFilters): Promise<Page<ShortlistEntry>> {
  return request<Page<ShortlistEntry>>(`/api/shortlist${toQueryString(filters)}`);
}

export function addToShortlist(
  jobId: string,
  payload: { priority?: string; notes?: string | null },
): Promise<ShortlistEntry> {
  return request<ShortlistEntry>(`/api/shortlist/${jobId}`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateShortlistEntry(
  jobId: string,
  payload: { priority?: string; notes?: string | null },
): Promise<ShortlistEntry> {
  return request<ShortlistEntry>(`/api/shortlist/${jobId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function removeShortlistEntry(jobId: string): Promise<void> {
  return request<void>(`/api/shortlist/${jobId}`, { method: "DELETE" });
}

/* -------------------------------------------------------- Applications */

export function getApplications(
  filters: ApplicationFilters,
): Promise<Page<Application>> {
  return request<Page<Application>>(`/api/applications${toQueryString(filters)}`);
}

export function createApplication(payload: {
  job_id: string;
  status?: string;
  application_date?: string | null;
  notes?: string | null;
  follow_up_date?: string | null;
  resume_reference?: string | null;
}): Promise<Application> {
  return request<Application>("/api/applications", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateApplication(
  applicationId: string,
  payload: {
    status?: string;
    application_date?: string | null;
    notes?: string | null;
    follow_up_date?: string | null;
    resume_reference?: string | null;
  },
): Promise<Application> {
  return request<Application>(`/api/applications/${applicationId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteApplication(applicationId: string): Promise<void> {
  return request<void>(`/api/applications/${applicationId}`, { method: "DELETE" });
}

/* ----------------------------------------------------------- Dashboard */

export function getDashboardSummary(params: {
  recent_period_hours?: number;
  include_test_data?: boolean;
}): Promise<DashboardSummary> {
  return request<DashboardSummary>(`/api/dashboard/summary${toQueryString(params)}`);
}

export function getDashboardActivity(params: {
  days?: number;
  include_test_data?: boolean;
}): Promise<ActivityResponse> {
  return request<ActivityResponse>(`/api/dashboard/activity${toQueryString(params)}`);
}

/* ------------------------------------------------------------ Settings */

export function getSearchSettings(): Promise<SearchSettings> {
  return request<SearchSettings>("/api/settings");
}

export function updateSearchSettings(
  payload: Partial<SearchSettings>,
): Promise<SearchSettings> {
  return request<SearchSettings>("/api/settings", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function getSources(): Promise<{ sources: SourceInfo[] }> {
  return request<{ sources: SourceInfo[] }>("/api/sources");
}

export function getHealth(): Promise<{
  status: string;
  database: string;
  version: string;
}> {
  return request("/health");
}
