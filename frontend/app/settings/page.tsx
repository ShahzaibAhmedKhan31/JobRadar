"use client";

import { useEffect, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Clock3,
  Database,
  Info,
  Loader2,
  Lock,
  RefreshCw,
  Save,
  ShieldCheck,
} from "lucide-react";

import { ErrorState } from "@/components/shared/error-state";
import { PageHeader } from "@/components/shared/page-header";
import { TableSkeleton } from "@/components/shared/skeletons";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import {
  POSTING_AGE_OPTIONS,
  REFRESH_INTERVAL_OPTIONS,
} from "@/lib/constants";
import {
  useRefreshHistory,
  useRefreshJobs,
  useSearchSettings,
  useSources,
  useUpdateSearchSettings,
} from "@/lib/hooks";
import { formatDuration, relativeFromNow } from "@/lib/utils";
import type { SearchSettings } from "@/types";

function statusVariant(status: string) {
  if (status === "success") return "success" as const;
  if (status === "failed") return "destructive" as const;
  if (status === "skipped") return "muted" as const;
  if (status === "partial") return "warning" as const;
  return "secondary" as const;
}

export default function SettingsPage() {
  const settingsQuery = useSearchSettings();
  const sourcesQuery = useSources();
  const historyQuery = useRefreshHistory(10);
  const updateMutation = useUpdateSearchSettings();
  const refreshMutation = useRefreshJobs();

  const [form, setForm] = useState<SearchSettings | null>(null);

  useEffect(() => {
    if (settingsQuery.data && !form) {
      setForm(settingsQuery.data);
    }
  }, [settingsQuery.data, form]);

  if (settingsQuery.isError) {
    return (
      <div className="space-y-4">
        <PageHeader title="Search settings" />
        <ErrorState error={settingsQuery.error} onRetry={() => settingsQuery.refetch()} />
      </div>
    );
  }

  const sources = sourcesQuery.data?.sources ?? [];
  const scrapingSources = sources.filter(
    (source) => source.can_refresh && !source.is_test_data && source.key !== "manual_import",
  );

  const toggleSource = (key: string) => {
    if (!form) return;
    setForm({
      ...form,
      default_sources: form.default_sources.includes(key)
        ? form.default_sources.filter((entry) => entry !== key)
        : [...form.default_sources, key],
    });
  };

  const save = () => {
    if (!form) return;
    updateMutation.mutate({
      default_titles: form.default_titles || null,
      default_keywords: form.default_keywords || null,
      default_location: form.default_location || null,
      default_work_arrangement: form.default_work_arrangement,
      default_experience_level: form.default_experience_level,
      default_posting_age_hours: form.default_posting_age_hours,
      default_sources: form.default_sources,
      scheduled_refresh_enabled: form.scheduled_refresh_enabled,
      scheduled_refresh_interval_minutes: form.scheduled_refresh_interval_minutes,
    });
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Search settings"
        description="Defaults used to prefill job discovery, plus source availability and refresh history."
      />

      <div className="grid gap-4 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader>
            <CardTitle>Default search</CardTitle>
            <CardDescription>
              These values prefill the Discover filters when you open the page. They never apply
              silently to stored data.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {!form ? (
              <div className="space-y-3">
                <TableSkeleton rows={4} />
              </div>
            ) : (
              <div className="space-y-5">
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-1.5">
                    <Label htmlFor="settings-titles">Preferred job titles</Label>
                    <Textarea
                      id="settings-titles"
                      rows={2}
                      value={form.default_titles ?? ""}
                      onChange={(event) =>
                        setForm({ ...form, default_titles: event.target.value })
                      }
                      placeholder="Backend Engineer, Data Engineer"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="settings-keywords">Skills &amp; keywords</Label>
                    <Textarea
                      id="settings-keywords"
                      rows={2}
                      value={form.default_keywords ?? ""}
                      onChange={(event) =>
                        setForm({ ...form, default_keywords: event.target.value })
                      }
                      placeholder="Python, PostgreSQL, FastAPI"
                    />
                  </div>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-1.5">
                    <Label htmlFor="settings-location">Preferred location</Label>
                    <Input
                      id="settings-location"
                      value={form.default_location ?? ""}
                      onChange={(event) =>
                        setForm({ ...form, default_location: event.target.value })
                      }
                      placeholder="Karachi, Pakistan"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label>Posting age window</Label>
                    <Select
                      value={String(form.default_posting_age_hours)}
                      onValueChange={(value) =>
                        setForm({ ...form, default_posting_age_hours: Number(value) })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {POSTING_AGE_OPTIONS.map((option) => (
                          <SelectItem key={option.value} value={String(option.value)}>
                            {option.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1.5">
                    <Label>Work arrangement</Label>
                    <Select
                      value={form.default_work_arrangement}
                      onValueChange={(value) =>
                        setForm({
                          ...form,
                          default_work_arrangement: value as SearchSettings["default_work_arrangement"],
                        })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="any">Any arrangement</SelectItem>
                        <SelectItem value="remote">Remote</SelectItem>
                        <SelectItem value="hybrid">Hybrid</SelectItem>
                        <SelectItem value="onsite">On-site</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1.5">
                    <Label>Experience level</Label>
                    <Select
                      value={form.default_experience_level}
                      onValueChange={(value) =>
                        setForm({
                          ...form,
                          default_experience_level:
                            value as SearchSettings["default_experience_level"],
                        })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="any">Any level</SelectItem>
                        <SelectItem value="entry">Entry level</SelectItem>
                        <SelectItem value="associate">Associate</SelectItem>
                        <SelectItem value="mid_senior">Mid-senior</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>Default sources</Label>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {sources.map((source) => (
                      <label
                        key={source.key}
                        className="flex cursor-pointer items-center gap-2.5 rounded-md border border-border/70 px-3 py-2 text-sm hover:bg-muted/40"
                      >
                        <Checkbox
                          checked={form.default_sources.includes(source.key)}
                          onCheckedChange={() => toggleSource(source.key)}
                        />
                        <span className="flex-1">
                          {source.name}
                          {source.is_test_data ? (
                            <span className="ml-2 text-[10px] uppercase text-amber-600">
                              sample
                            </span>
                          ) : null}
                        </span>
                      </label>
                    ))}
                  </div>
                </div>

                <div className="space-y-3 rounded-lg border border-border bg-muted/30 p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="space-y-1">
                      <p className="text-sm font-medium">Automatic refresh</p>
                      <p className="text-xs text-muted-foreground">
                        While the API is running, refresh available sources on a fixed interval.
                        The first automatic run waits for one full interval after startup.
                      </p>
                    </div>
                    <Switch
                      checked={form.scheduled_refresh_enabled}
                      onCheckedChange={(value) =>
                        setForm({ ...form, scheduled_refresh_enabled: value })
                      }
                      aria-label="Enable automatic refresh"
                    />
                  </div>
                  <div className="flex flex-wrap items-end gap-3">
                    <div className="space-y-1.5">
                      <Label>Interval</Label>
                      <Select
                        value={String(form.scheduled_refresh_interval_minutes)}
                        onValueChange={(value) =>
                          setForm({
                            ...form,
                            scheduled_refresh_interval_minutes: Number(value),
                          })
                        }
                        disabled={!form.scheduled_refresh_enabled}
                      >
                        <SelectTrigger className="w-[190px]">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {REFRESH_INTERVAL_OPTIONS.map((option) => (
                            <SelectItem key={option.value} value={String(option.value)}>
                              {option.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <p className="flex items-center gap-1.5 pb-2 text-xs text-muted-foreground">
                      <Clock3 className="h-3.5 w-3.5" />
                      {form.scheduled_refresh_enabled
                        ? "Scheduler on"
                        : "Scheduler off — refresh manually from any page"}
                    </p>
                  </div>
                </div>

                <div className="flex items-center justify-between border-t border-border pt-4">
                  <p className="text-xs text-muted-foreground">
                    {form.updated_at
                      ? `Last saved ${relativeFromNow(form.updated_at)}`
                      : "Not saved yet"}
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      onClick={() => setForm(settingsQuery.data ?? null)}
                      disabled={updateMutation.isPending}
                    >
                      Reset
                    </Button>
                    <Button onClick={save} disabled={updateMutation.isPending}>
                      {updateMutation.isPending ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Save className="h-4 w-4" />
                      )}
                      Save settings
                    </Button>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>How job sources work</CardTitle>
            <CardDescription>Authorized access only</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <div className="flex gap-3 rounded-lg bg-muted/50 p-3">
              <Lock className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
              <div>
                <p className="font-medium">
                  {scrapingSources.length > 0
                    ? `Scraping is on for ${scrapingSources.map((source) => source.name).join(", ")}`
                    : "LinkedIn & Indeed need an opt-in"}
                </p>
                <p className="text-xs text-muted-foreground">
                  {scrapingSources.length > 0 ? (
                    <>
                      Listings come from the board&apos;s public guest search pages through
                      python-jobspy. Automated access may breach the board&apos;s terms of service
                      and can be throttled or blocked at any time — JobRadar never bypasses a
                      block, and a blocked run shows up as <em>failed</em> with the provider
                      message. Keep refreshes manual: each saved title is one request, with a{" "}
                      {""}
                      short delay in between.
                    </>
                  ) : (
                    <>
                      Neither platform offers a self-serve job-search API, so nothing is fetched
                      until you install the optional{" "}
                      <code className="font-mono text-[11px]">python-jobspy</code> extra and opt in
                      through <code className="font-mono text-[11px]">JOBSPY_SITES</code>. “Import
                      job link” always works without it.
                    </>
                  )}
                </p>
              </div>
            </div>
            <div className="flex gap-3 rounded-lg bg-muted/50 p-3">
              <Database className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
              <div>
                <p className="font-medium">Refresh imports, then filters work</p>
                <p className="text-xs text-muted-foreground">
                  Discovery only searches what is already stored. Refresh a source first, then
                  filter by posting age or keywords.
                </p>
              </div>
            </div>
            <div className="flex gap-3 rounded-lg bg-muted/50 p-3">
              <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
              <div>
                <p className="font-medium">Applications stay manual</p>
                <p className="text-xs text-muted-foreground">
                  Opening a listing never marks it as applied. Tracking records are created only
                  when you confirm them.
                </p>
              </div>
            </div>
            <div className="flex gap-3 rounded-lg bg-amber-50 p-3 text-amber-900">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <div>
                <p className="font-medium">Sample feed</p>
                <p className="text-xs">
                  The “Sample job feed” contains synthetic roles for demos. It is excluded from
                  dashboard metrics by default.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Job sources</CardTitle>
          <CardDescription>
            Provider availability, stored listings and last import result.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {sourcesQuery.isError ? (
            <ErrorState error={sourcesQuery.error} onRetry={() => sourcesQuery.refetch()} />
          ) : sourcesQuery.isLoading ? (
            <TableSkeleton rows={3} />
          ) : (
            <div className="grid gap-3 lg:grid-cols-2">
              {sources.map((source) => (
                <div
                  key={source.key}
                  className="flex flex-col gap-3 rounded-lg border border-border/80 p-4"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-sm font-semibold">{source.name}</p>
                        <Badge
                          variant={
                            source.availability === "available"
                              ? "success"
                              : source.availability === "not_configured"
                                ? "warning"
                                : "muted"
                          }
                        >
                          {source.availability === "available"
                            ? "Available"
                            : source.availability === "not_configured"
                              ? "Opt-in required"
                              : "Unavailable"}
                        </Badge>
                        {source.is_test_data ? <Badge variant="warning">Sample data</Badge> : null}
                      </div>
                      <p className="mt-1 text-xs text-muted-foreground">{source.description}</p>
                    </div>
                    {source.can_refresh ? (
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={refreshMutation.isPending}
                        onClick={() => refreshMutation.mutate({ sources: [source.key] })}
                      >
                        {refreshMutation.isPending ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <RefreshCw className="h-3.5 w-3.5" />
                        )}
                        {source.is_test_data ? "Load samples" : "Refresh"}
                      </Button>
                    ) : null}
                  </div>
                  {source.availability_reason ? (
                    <p className="rounded-md bg-muted/50 p-2.5 text-xs text-muted-foreground">
                      {source.availability_reason}
                    </p>
                  ) : null}
                  {source.setup_command ? (
                    <div className="rounded-md border border-dashed border-border bg-background p-2.5">
                      <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                        How to enable
                      </p>
                      <code className="mt-1 block break-all font-mono text-[11px] text-foreground">
                        {source.setup_command}
                      </code>
                    </div>
                  ) : null}
                  <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
                    <span className="inline-flex items-center gap-1.5">
                      <Database className="h-3.5 w-3.5" /> {source.stored_jobs_count} jobs stored
                    </span>
                    {source.last_run ? (
                      <span className="inline-flex items-center gap-1.5">
                        <RefreshCw className="h-3.5 w-3.5" /> Last run{" "}
                        {relativeFromNow(source.last_run.started_at)} ·{" "}
                        <Badge variant={statusVariant(source.last_run.status)}>
                          {source.last_run.status}
                        </Badge>
                      </span>
                    ) : (
                      <span>No refreshes yet</span>
                    )}
                    {source.supports_refresh ? null : (
                      <span className="inline-flex items-center gap-1">
                        <Info className="h-3.5 w-3.5" /> Manual entry
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Scraping guard-rails</CardTitle>
          <CardDescription>
            What JobRadar does — and refuses to do — when scraping LinkedIn or Indeed.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 text-sm md:grid-cols-2">
          <div className="rounded-lg border border-border/80 p-3">
            <p className="flex items-center gap-2 font-medium">
              <ShieldCheck className="h-4 w-4 text-primary" /> Opt-in only
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              Nothing contacts a board unless the optional{" "}
              <code className="font-mono text-[11px]">python-jobspy</code> package is installed and
              the site is listed in <code className="font-mono text-[11px]">JOBSPY_SITES</code>.
              <code className="font-mono text-[11px]"> JOBSPY_ENABLED=false</code> switches it off
              completely.
            </p>
          </div>
          <div className="rounded-lg border border-border/80 p-3">
            <p className="flex items-center gap-2 font-medium">
              <Clock3 className="h-4 w-4 text-primary" /> Deliberately slow
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              One request per saved search term with a configurable delay between calls, and a
              capped result count. Scheduled refresh is off by default; keep it at one hour or
              longer if you turn it on.
            </p>
          </div>
          <div className="rounded-lg border border-border/80 p-3">
            <p className="flex items-center gap-2 font-medium">
              <AlertTriangle className="h-4 w-4 text-amber-600" /> Blocks are reported
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              A throttle, block or empty response is recorded in refresh history as{" "}
              <em>failed</em> or <em>partial</em> with the provider message. JobRadar never
              fabricates listings to fill the gap and never solves a CAPTCHA.
            </p>
          </div>
          <div className="rounded-lg border border-border/80 p-3">
            <p className="flex items-center gap-2 font-medium">
              <Info className="h-4 w-4 text-primary" /> Date-only timestamps
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              LinkedIn only exposes the posting date, so those cards say &ldquo;date only&rdquo;
              and freshness filters treat the whole day as inside the window instead of inventing
              an hour.
            </p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Refresh history</CardTitle>
          <CardDescription>Newest runs first, with counts and errors.</CardDescription>
        </CardHeader>
        <CardContent>
          {historyQuery.isError ? (
            <ErrorState error={historyQuery.error} onRetry={() => historyQuery.refetch()} />
          ) : historyQuery.isLoading ? (
            <TableSkeleton rows={4} />
          ) : (historyQuery.data?.items.length ?? 0) === 0 ? (
            <p className="py-6 text-center text-sm text-muted-foreground">
              No refresh runs recorded yet. Use “Refresh sources” to import listings.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Source</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Started</TableHead>
                  <TableHead>Duration</TableHead>
                  <TableHead>Fetched</TableHead>
                  <TableHead>New</TableHead>
                  <TableHead>Updated</TableHead>
                  <TableHead>Details</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {historyQuery.data?.items.map((run) => (
                  <TableRow key={run.id}>
                    <TableCell className="text-sm font-medium">{run.source_label}</TableCell>
                    <TableCell>
                      <Badge variant={statusVariant(run.status)}>{run.status}</Badge>
                    </TableCell>
                    <TableCell className="whitespace-nowrap text-xs text-muted-foreground">
                      {relativeFromNow(run.started_at)}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {formatDuration(run.duration_seconds)}
                    </TableCell>
                    <TableCell className="text-sm tabular">{run.fetched_jobs_count}</TableCell>
                    <TableCell className="text-sm tabular">{run.new_jobs_count}</TableCell>
                    <TableCell className="text-sm tabular">{run.updated_jobs_count}</TableCell>
                    <TableCell className="max-w-[280px] text-xs text-muted-foreground">
                      {run.error_message ? (
                        <span
                          className="line-clamp-2 text-amber-800"
                          title={run.error_message}
                        >
                          {run.error_message}
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-emerald-700">
                          <CheckCircle2 className="h-3.5 w-3.5" /> Completed
                        </span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
