import type {
  ApplicationStatus,
  ExperienceLevel,
  JobSort,
  Priority,
  WorkArrangement,
} from "@/types";

export const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: "layout-dashboard", description: "Overview" },
  { href: "/discover", label: "Discover Jobs", icon: "radar", description: "Search sources" },
  { href: "/shortlist", label: "Shortlist", icon: "bookmark", description: "Saved roles" },
  { href: "/applications", label: "Applications", icon: "kanban", description: "Track progress" },
  { href: "/settings", label: "Search Settings", icon: "settings", description: "Preferences" },
] as const;

export const POSTING_AGE_OPTIONS = [
  { value: 6, label: "Last 6 hours" },
  { value: 12, label: "Last 12 hours" },
  { value: 24, label: "Last 24 hours" },
  { value: 48, label: "Last 48 hours" },
  { value: 168, label: "Last 7 days" },
] as const;

export const RECENT_PERIOD_OPTIONS = [
  { value: 24, label: "Last 24 hours" },
  { value: 72, label: "Last 3 days" },
  { value: 168, label: "Last 7 days" },
  { value: 720, label: "Last 30 days" },
] as const;

export const WORK_ARRANGEMENT_LABELS: Record<WorkArrangement, string> = {
  remote: "Remote",
  hybrid: "Hybrid",
  onsite: "On-site",
  unknown: "Not specified",
};

export const EXPERIENCE_LABELS: Record<ExperienceLevel, string> = {
  entry: "Entry level",
  associate: "Associate",
  mid_senior: "Mid-senior",
  unknown: "Not specified",
};

export const APPLICATION_STATUS_ORDER: ApplicationStatus[] = [
  "saved",
  "applied",
  "assessment",
  "interview",
  "offer",
  "rejected",
  "withdrawn",
];

export const STATUS_META: Record<
  ApplicationStatus,
  { label: string; badge: string; dot: string; column: string }
> = {
  saved: {
    label: "Saved",
    badge: "bg-slate-100 text-slate-700 border-slate-200",
    dot: "bg-slate-400",
    column: "border-slate-200",
  },
  applied: {
    label: "Applied",
    badge: "bg-sky-50 text-sky-700 border-sky-200",
    dot: "bg-sky-500",
    column: "border-sky-200",
  },
  assessment: {
    label: "Assessment",
    badge: "bg-violet-50 text-violet-700 border-violet-200",
    dot: "bg-violet-500",
    column: "border-violet-200",
  },
  interview: {
    label: "Interview",
    badge: "bg-amber-50 text-amber-700 border-amber-200",
    dot: "bg-amber-500",
    column: "border-amber-200",
  },
  offer: {
    label: "Offer",
    badge: "bg-emerald-50 text-emerald-700 border-emerald-200",
    dot: "bg-emerald-500",
    column: "border-emerald-200",
  },
  rejected: {
    label: "Rejected",
    badge: "bg-rose-50 text-rose-700 border-rose-200",
    dot: "bg-rose-500",
    column: "border-rose-200",
  },
  withdrawn: {
    label: "Withdrawn",
    badge: "bg-slate-100 text-slate-600 border-slate-200",
    dot: "bg-slate-400",
    column: "border-slate-200",
  },
};

export const PRIORITY_META: Record<Priority, { label: string; badge: string; dot: string }> = {
  high: {
    label: "High",
    badge: "bg-rose-50 text-rose-700 border-rose-200",
    dot: "bg-rose-500",
  },
  medium: {
    label: "Medium",
    badge: "bg-amber-50 text-amber-700 border-amber-200",
    dot: "bg-amber-500",
  },
  low: {
    label: "Low",
    badge: "bg-slate-100 text-slate-600 border-slate-200",
    dot: "bg-slate-400",
  },
};

export const JOB_SORT_OPTIONS: { value: JobSort; label: string }[] = [
  { value: "newest", label: "Newest postings" },
  { value: "relevant", label: "Best match" },
  { value: "oldest", label: "Oldest postings" },
  { value: "company", label: "Company A–Z" },
];

export const REFRESH_INTERVAL_OPTIONS = [
  { value: 30, label: "Every 30 minutes" },
  { value: 60, label: "Every hour" },
  { value: 180, label: "Every 3 hours" },
  { value: 720, label: "Every 12 hours" },
  { value: 1440, label: "Once a day" },
];

export const MANUAL_IMPORT_SOURCES = [
  { value: "linkedin", label: "LinkedIn" },
  { value: "indeed", label: "Indeed" },
  { value: "manual_import", label: "Other / manual" },
  { value: "other", label: "Other" },
];
