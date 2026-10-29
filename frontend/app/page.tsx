"use client";

import { useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  BarChart3,
  Bookmark,
  BriefcaseBusiness,
  CalendarCheck,
  ChevronRight,
  CircleDot,
  Clock3,
  FileCheck2,
  Handshake,
  Plus,
  Radar,
  Send,
  Sparkles,
  Target,
} from "lucide-react";

import { ActivityChart } from "@/components/dashboard/activity-chart";
import { StatusBreakdown } from "@/components/dashboard/status-breakdown";
import { ImportJobDialog } from "@/components/jobs/import-job-dialog";
import { RefreshControl } from "@/components/jobs/refresh-control";
import { StatusBadge } from "@/components/shared/badges";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { MetricCard } from "@/components/shared/metric-card";
import { PageHeader } from "@/components/shared/page-header";
import { JobCardSkeleton, MetricsSkeleton } from "@/components/shared/skeletons";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { RECENT_PERIOD_OPTIONS } from "@/lib/constants";
import { useDashboardActivity, useDashboardSummary } from "@/lib/hooks";
import { formatHoursAgo, formatNumber, relativeFromNow } from "@/lib/utils";

const DAYS_OPTIONS = [
  { value: 7, label: "7 days" },
  { value: 14, label: "14 days" },
  { value: 30, label: "30 days" },
];

export default function DashboardPage() {
  const [period, setPeriod] = useState(24);
  const [includeTestData, setIncludeTestData] = useState(false);
  const [activityDays, setActivityDays] = useState(14);
  const [importOpen, setImportOpen] = useState(false);

  const summaryQuery = useDashboardSummary({
    recent_period_hours: period,
    include_test_data: includeTestData,
  });
  const activityQuery = useDashboardActivity({
    days: activityDays,
    include_test_data: includeTestData,
  });

  const summary = summaryQuery.data;
  const onlySampleData =
    summary !== undefined && summary.total_jobs === 0 && summary.test_data_jobs > 0;
  const hasNoData =
    summary !== undefined &&
    summary.total_jobs === 0 &&
    (summary.test_data_jobs === 0 || !includeTestData);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        description="A live view of your job search. Metrics come straight from your stored jobs and application records."
        actions={
          <>
            <Select
              value={String(period)}
              onValueChange={(value) => setPeriod(Number(value))}
            >
              <SelectTrigger className="w-[160px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {RECENT_PERIOD_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={String(option.value)}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <RefreshControl />
            <Button variant="outline" onClick={() => setImportOpen(true)}>
              <Plus className="h-4 w-4" /> Import job
            </Button>
          </>
        }
      />

      {summary && summary.test_data_jobs > 0 ? (
        <div className="flex flex-col gap-2 rounded-lg border border-amber-200 bg-amber-50/70 p-3 text-sm text-amber-900 sm:flex-row sm:items-center sm:justify-between">
          <p className="flex items-start gap-2">
            <Sparkles className="mt-0.5 h-4 w-4 shrink-0" />
            {includeTestData
              ? "Sample data is included in these metrics."
              : `${summary.test_data_jobs} synthetic sample listing${
                  summary.test_data_jobs === 1 ? " is" : "s are"
                } stored and hidden from these metrics.`}
          </p>
          <label className="flex shrink-0 items-center gap-2 text-xs font-medium">
            Include sample data
            <Switch
              checked={includeTestData}
              onCheckedChange={setIncludeTestData}
              aria-label="Include sample data in dashboard metrics"
            />
          </label>
        </div>
      ) : null}

      {summaryQuery.isError ? (
        <ErrorState error={summaryQuery.error} onRetry={() => summaryQuery.refetch()} />
      ) : hasNoData ? (
        <Card className="overflow-hidden">
          <div className="grid gap-6 p-6 lg:grid-cols-[1.2fr_1fr] lg:p-8">
            <div className="space-y-4">
              <div className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-xs font-medium text-primary">
                <CircleDot className="h-3 w-3" /> Welcome to JobRadar
              </div>
              <h2 className="text-2xl font-semibold tracking-tight">
                Set up your pipeline in three steps
              </h2>
              <p className="max-w-xl text-sm text-muted-foreground">
                JobRadar stores listings first, then lets you filter, shortlist and track the roles
                you actually apply to. Nothing is applied on your behalf.
              </p>
              <div className="space-y-3">
                {[
                  {
                    step: "1",
                    title: "Import jobs",
                    text: "Refresh the bundled sample feed or paste a link from LinkedIn or Indeed.",
                  },
                  {
                    step: "2",
                    title: "Filter and shortlist",
                    text: "Use posting age, location, arrangement and skill keywords to narrow the list.",
                  },
                  {
                    step: "3",
                    title: "Track applications",
                    text: "Record each manual application and move it through the pipeline as you progress.",
                  },
                ].map((item) => (
                  <div key={item.step} className="flex items-start gap-3">
                    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
                      {item.step}
                    </span>
                    <div>
                      <p className="text-sm font-medium">{item.title}</p>
                      <p className="text-xs text-muted-foreground">{item.text}</p>
                    </div>
                  </div>
                ))}
              </div>
              <div className="flex flex-wrap gap-2 pt-1">
                <RefreshControl compact />
                <Button size="sm" variant="outline" onClick={() => setImportOpen(true)}>
                  <Plus className="h-3.5 w-3.5" /> Import a job link
                </Button>
                {onlySampleData ? (
                  <Button size="sm" variant="secondary" onClick={() => setIncludeTestData(true)}>
                    <Sparkles className="h-3.5 w-3.5" /> Explore the sample data
                  </Button>
                ) : (
                  <Button size="sm" variant="ghost" asChild>
                    <Link href="/settings">Configure sources</Link>
                  </Button>
                )}
              </div>
            </div>
            <div className="rounded-xl border border-border bg-muted/40 p-5">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                How metrics work
              </p>
              <ul className="mt-3 space-y-3 text-sm text-muted-foreground">
                <li className="flex gap-2">
                  <Radar className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                  Totals only count rows in your database — no demo numbers.
                </li>
                <li className="flex gap-2">
                  <Clock3 className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                  Posting age uses the source publication time; unknown dates stay unknown.
                </li>
                <li className="flex gap-2">
                  <Target className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                  Applications count only after you confirm them here.
                </li>
                <li className="flex gap-2">
                  <FileCheck2 className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                  Sample rows are flagged and excluded unless you opt in.
                </li>
              </ul>
            </div>
          </div>
        </Card>
      ) : summaryQuery.isLoading ? (
        <>
          <MetricsSkeleton count={4} />
          <div className="grid gap-4 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <JobCardSkeleton />
            </div>
            <JobCardSkeleton />
          </div>
        </>
      ) : summary ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard
              label="Total jobs discovered"
              value={formatNumber(summary.total_jobs)}
              hint={`${formatNumber(summary.jobs_discovered_recent)} in the selected period`}
              icon={Radar}
              tone="primary"
            />
            <MetricCard
              label="Shortlisted"
              value={formatNumber(summary.shortlisted_jobs)}
              hint="Saved for follow-up"
              icon={Bookmark}
              tone="amber"
            />
            <MetricCard
              label="Applications submitted"
              value={formatNumber(summary.applications_submitted)}
              hint={`${formatNumber(summary.applications_total)} tracking record${
                summary.applications_total === 1 ? "" : "s"
              } in total`}
              icon={Send}
            />
            <MetricCard
              label="In progress"
              value={formatNumber(summary.applications_in_progress)}
              hint="Assessment or interview stage"
              icon={BriefcaseBusiness}
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard
              label="Interviews"
              value={formatNumber(summary.interviews)}
              hint="Scheduled or completed"
              icon={Handshake}
              tone="amber"
            />
            <MetricCard
              label="Offers"
              value={formatNumber(summary.offers)}
              hint="Congratulations when this moves"
              icon={Target}
              tone="emerald"
            />
            <MetricCard
              label="Follow-ups upcoming"
              value={formatNumber(summary.upcoming_follow_ups)}
              hint="Active applications with a follow-up date"
              icon={CalendarCheck}
            />
            <MetricCard
              label="No publication date"
              value={formatNumber(summary.unknown_published_jobs)}
              hint="Excluded from posting-age filters"
              icon={Clock3}
            />
          </div>

          <div className="grid gap-4 xl:grid-cols-3">
            <Card className="xl:col-span-2">
              <CardHeader className="flex-row items-center justify-between space-y-0">
                <div>
                  <CardTitle>Activity</CardTitle>
                  <CardDescription>
                    Jobs discovered vs. applications submitted per day
                  </CardDescription>
                </div>
                <div className="flex items-center gap-1 rounded-lg bg-muted p-1">
                  {DAYS_OPTIONS.map((option) => (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => setActivityDays(option.value)}
                      className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                        activityDays === option.value
                          ? "bg-card text-foreground shadow-sm"
                          : "text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </CardHeader>
              <CardContent>
                {activityQuery.isLoading ? (
                  <div className="h-[260px] animate-pulse rounded-lg bg-muted" />
                ) : activityQuery.isError ? (
                  <ErrorState
                    error={activityQuery.error}
                    onRetry={() => activityQuery.refetch()}
                  />
                ) : (
                  <ActivityChart points={activityQuery.data?.points ?? []} />
                )}
                <div className="mt-3 flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
                  <span className="inline-flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-teal-700" /> Jobs discovered
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-sky-600" /> Applications submitted
                  </span>
                  <span className="ml-auto">
                    {activityQuery.data?.jobs_discovered_total ?? 0} discovered ·{" "}
                    {activityQuery.data?.applications_submitted_total ?? 0} applied
                  </span>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Application statuses</CardTitle>
                <CardDescription>All tracked applications, by stage</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <StatusBreakdown items={summary.status_breakdown} />
                <Button variant="outline" size="sm" className="w-full" asChild>
                  <Link href="/applications">
                    Open tracker <ArrowRight className="h-3.5 w-3.5" />
                  </Link>
                </Button>
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-4 xl:grid-cols-3">
            <Card className="xl:col-span-2">
              <CardHeader className="flex-row items-center justify-between space-y-0">
                <div>
                  <CardTitle>Recently discovered</CardTitle>
                  <CardDescription>Latest listings imported into JobRadar</CardDescription>
                </div>
                <Button variant="ghost" size="sm" asChild>
                  <Link href="/discover">
                    View all <ChevronRight className="h-3.5 w-3.5" />
                  </Link>
                </Button>
              </CardHeader>
              <CardContent className="space-y-2">
                {summary.recent_jobs.length === 0 ? (
                  <EmptyState
                    title="No jobs yet"
                    description="Refresh a source to import listings."
                    className="py-8"
                  />
                ) : (
                  summary.recent_jobs.map((job) => (
                    <div
                      key={job.id}
                      className="flex flex-col gap-2 rounded-lg border border-border/70 px-3 py-2.5 sm:flex-row sm:items-center sm:justify-between"
                    >
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium">{job.title}</p>
                        <p className="truncate text-xs text-muted-foreground">
                          {job.company_name} · {job.source_label}
                          {job.published_at
                            ? ` · posted ${formatHoursAgo(job.posting_age_hours)}`
                            : " · publication time unknown"}
                        </p>
                      </div>
                      <div className="flex shrink-0 items-center gap-2">
                        <Badge variant="muted">{relativeFromNow(job.first_seen_at)}</Badge>
                        {job.application ? (
                          <StatusBadge status={job.application.status} />
                        ) : job.is_shortlisted ? (
                          <Badge variant="success">Shortlisted</Badge>
                        ) : null}
                        <Button variant="ghost" size="icon-sm" asChild>
                          <a href={job.job_url} target="_blank" rel="noopener noreferrer">
                            <ArrowRight className="h-3.5 w-3.5" />
                          </a>
                        </Button>
                      </div>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>

            <div className="space-y-4">
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm">Latest refresh</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                  {summary.latest_refresh ? (
                    <>
                      <div className="flex items-center justify-between">
                        <span className="text-muted-foreground">Source</span>
                        <span className="font-medium">{summary.latest_refresh.source_label}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-muted-foreground">Started</span>
                        <span className="font-medium">
                          {relativeFromNow(summary.latest_refresh.started_at)}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-muted-foreground">Imported</span>
                        <span className="font-medium tabular">
                          {summary.latest_refresh.new_jobs_count} new ·{" "}
                          {summary.latest_refresh.updated_jobs_count} updated
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-muted-foreground">Status</span>
                        <Badge
                          variant={
                            summary.latest_refresh.status === "success"
                              ? "success"
                              : summary.latest_refresh.status === "failed"
                                ? "destructive"
                                : "warning"
                          }
                        >
                          {summary.latest_refresh.status}
                        </Badge>
                      </div>
                      {summary.latest_refresh.error_message ? (
                        <p className="rounded-md bg-amber-50 p-2 text-xs text-amber-800">
                          {summary.latest_refresh.error_message}
                        </p>
                      ) : null}
                    </>
                  ) : (
                    <p className="text-xs text-muted-foreground">
                      No refreshes recorded yet. Refresh a source to see run history.
                    </p>
                  )}
                  <Button variant="outline" size="sm" className="w-full" asChild>
                    <Link href="/settings">Refresh history</Link>
                  </Button>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm">Quick actions</CardTitle>
                </CardHeader>
                <CardContent className="grid gap-2">
                  <Button variant="outline" size="sm" className="justify-between" asChild>
                    <Link href="/discover">
                      <span className="flex items-center gap-2">
                        <Radar className="h-4 w-4 text-primary" /> Discover jobs
                      </span>
                      <ChevronRight className="h-3.5 w-3.5" />
                    </Link>
                  </Button>
                  <Button variant="outline" size="sm" className="justify-between" asChild>
                    <Link href="/shortlist">
                      <span className="flex items-center gap-2">
                        <Bookmark className="h-4 w-4 text-amber-600" /> Review shortlist
                      </span>
                      <ChevronRight className="h-3.5 w-3.5" />
                    </Link>
                  </Button>
                  <Button variant="outline" size="sm" className="justify-between" asChild>
                    <Link href="/applications">
                      <span className="flex items-center gap-2">
                        <BarChart3 className="h-4 w-4 text-sky-600" /> Open applications
                      </span>
                      <ChevronRight className="h-3.5 w-3.5" />
                    </Link>
                  </Button>
                </CardContent>
              </Card>
            </div>
          </div>
        </>
      ) : null}

      <ImportJobDialog open={importOpen} onOpenChange={setImportOpen} />
    </div>
  );
}
