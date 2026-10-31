"use client";

import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { toast } from "sonner";

import {
  addToShortlist,
  ApiError,
  createApplication,
  deleteApplication,
  getApplications,
  getDashboardActivity,
  getDashboardSummary,
  getJobFacets,
  getJobs,
  getRefreshHistory,
  getSearchSettings,
  getShortlist,
  getSources,
  importJob,
  pruneJobs,
  refreshJobs,
  removeShortlistEntry,
  updateApplication,
  updateSearchSettings,
  updateShortlistEntry,
} from "@/lib/api";
import type {
  ApplicationFilters,
  ApplicationStatus,
  JobFilters,
  ManualJobImportInput,
  Priority,
  SearchSettings,
  ShortlistFilters,
} from "@/types";

export const queryKeys = {
  jobs: (filters: JobFilters) => ["jobs", filters] as const,
  jobFacets: (params: { sources: string[]; include_test_data: boolean }) =>
    ["jobs", "facets", params] as const,
  job: (id: string) => ["job", id] as const,
  shortlist: (filters: ShortlistFilters) => ["shortlist", filters] as const,
  applications: (filters: ApplicationFilters) => ["applications", filters] as const,
  summary: (params: { recent_period_hours: number; include_test_data: boolean }) =>
    ["dashboard", "summary", params] as const,
  activity: (params: { days: number; include_test_data: boolean }) =>
    ["dashboard", "activity", params] as const,
  sources: ["sources"] as const,
  settings: ["settings"] as const,
  refreshHistory: ["refresh-history"] as const,
};

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Something went wrong";
}

export function useApiErrorToast() {
  return (error: unknown) => toast.error(errorMessage(error));
}

/* ------------------------------------------------------------- Queries */

export function useJobs(filters: JobFilters) {
  return useQuery({
    queryKey: queryKeys.jobs(filters),
    queryFn: () => getJobs(filters),
    placeholderData: keepPreviousData,
  });
}

/**
 * What is stored, ignoring the current filters. Used to explain an empty list:
 * "you have 25 LinkedIn jobs, none in Karachi" is actionable, a blank page is not.
 */
export function useJobFacets(params: { sources: string[]; include_test_data: boolean }) {
  return useQuery({
    queryKey: queryKeys.jobFacets(params),
    queryFn: () => getJobFacets(params),
    placeholderData: keepPreviousData,
  });
}

export function useShortlist(filters: ShortlistFilters) {
  return useQuery({
    queryKey: queryKeys.shortlist(filters),
    queryFn: () => getShortlist(filters),
    placeholderData: keepPreviousData,
  });
}

export function useApplications(filters: ApplicationFilters) {
  return useQuery({
    queryKey: queryKeys.applications(filters),
    queryFn: () => getApplications(filters),
    placeholderData: keepPreviousData,
  });
}

export function useDashboardSummary(params: {
  recent_period_hours: number;
  include_test_data: boolean;
}) {
  return useQuery({
    queryKey: queryKeys.summary(params),
    queryFn: () => getDashboardSummary(params),
  });
}

export function useDashboardActivity(params: {
  days: number;
  include_test_data: boolean;
}) {
  return useQuery({
    queryKey: queryKeys.activity(params),
    queryFn: () => getDashboardActivity(params),
  });
}

export function useSources() {
  return useQuery({ queryKey: queryKeys.sources, queryFn: getSources });
}

export function useSearchSettings() {
  return useQuery({ queryKey: queryKeys.settings, queryFn: getSearchSettings });
}

export function useRefreshHistory(limit = 10) {
  return useQuery({
    queryKey: [...queryKeys.refreshHistory, limit],
    queryFn: () => getRefreshHistory({ page_size: limit }),
  });
}

/* ----------------------------------------------------------- Mutations */

function useInvalidateTrackerData() {
  const queryClient = useQueryClient();
  return () => {
    void queryClient.invalidateQueries({ queryKey: ["jobs"] });
    void queryClient.invalidateQueries({ queryKey: ["job"] });
    void queryClient.invalidateQueries({ queryKey: ["shortlist"] });
    void queryClient.invalidateQueries({ queryKey: ["applications"] });
    void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    void queryClient.invalidateQueries({ queryKey: ["sources"] });
    void queryClient.invalidateQueries({ queryKey: ["refresh-history"] });
  };
}

export function useShortlistJob() {
  const invalidate = useInvalidateTrackerData();
  return useMutation({
    mutationFn: ({
      jobId,
      priority,
      notes,
    }: {
      jobId: string;
      priority?: Priority;
      notes?: string | null;
    }) => addToShortlist(jobId, { priority, notes }),
    onSuccess: (_, variables) => {
      invalidate();
      toast.success("Job shortlisted");
      void variables;
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useUpdateShortlist() {
  const invalidate = useInvalidateTrackerData();
  return useMutation({
    mutationFn: ({
      jobId,
      priority,
      notes,
    }: {
      jobId: string;
      priority?: Priority;
      notes?: string | null;
    }) => updateShortlistEntry(jobId, { priority, notes }),
    onSuccess: () => {
      invalidate();
      toast.success("Shortlist updated");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useRemoveShortlist() {
  const invalidate = useInvalidateTrackerData();
  return useMutation({
    mutationFn: (jobId: string) => removeShortlistEntry(jobId),
    onSuccess: () => {
      invalidate();
      toast.success("Removed from shortlist");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useCreateApplication() {
  const invalidate = useInvalidateTrackerData();
  return useMutation({
    mutationFn: createApplication,
    onSuccess: () => {
      invalidate();
      toast.success("Application tracking started");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useUpdateApplication() {
  const invalidate = useInvalidateTrackerData();
  return useMutation({
    mutationFn: ({
      applicationId,
      ...payload
    }: {
      applicationId: string;
      status?: ApplicationStatus | string;
      application_date?: string | null;
      notes?: string | null;
      follow_up_date?: string | null;
      resume_reference?: string | null;
    }) => updateApplication(applicationId, payload),
    onSuccess: () => {
      invalidate();
      toast.success("Application updated");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useDeleteApplication() {
  const invalidate = useInvalidateTrackerData();
  return useMutation({
    mutationFn: (applicationId: string) => deleteApplication(applicationId),
    onSuccess: () => {
      invalidate();
      toast.success("Tracking record deleted");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useRefreshJobs() {
  const invalidate = useInvalidateTrackerData();
  return useMutation({
    mutationFn: refreshJobs,
    onSuccess: (data) => {
      invalidate();
      const details: string[] = [];
      if (data.applied_query && data.new_jobs === 0) {
        const query = data.applied_query;
        const terms =
          query.terms.length > 0
            ? query.terms.map((term) => `"${term}"`).join(", ")
            : "an unfiltered feed";
        const where = query.location ? ` in ${query.location}` : " (no location)";
        const age = query.max_age_hours ? ` · last ${query.max_age_hours}h` : "";
        details.push(`Searched ${terms}${where}${age}`);
      }
      data.runs.forEach((run) => {
        const error = run.error_message
          ? ` — ${run.error_message.slice(0, 140)}${run.error_message.length > 140 ? "…" : ""}`
          : "";
        details.push(`${run.source_label}: ${run.status}${error}`);
      });
      toast.success(data.message, {
        description: details.length > 0 ? details.join(" · ") : undefined,
        duration: data.new_jobs === 0 ? 9000 : 5000,
      });
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function usePruneJobs() {
  const invalidate = useInvalidateTrackerData();
  return useMutation({
    mutationFn: (payload: { sources?: string[]; include_test_data?: boolean }) =>
      pruneJobs(payload),
    onSuccess: (data) => {
      invalidate();
      if (data.deleted > 0) {
        toast.success(data.message);
      } else {
        toast.info(data.message);
      }
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useImportJob() {
  const invalidate = useInvalidateTrackerData();
  return useMutation({
    mutationFn: (payload: ManualJobImportInput) => importJob(payload),
    onSuccess: (data) => {
      invalidate();
      toast.success(data.message);
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useUpdateSearchSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: Partial<SearchSettings>) => updateSearchSettings(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.settings });
      toast.success("Search settings saved");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export { errorMessage };
