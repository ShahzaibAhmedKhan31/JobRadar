"use client";

import { useQuery } from "@tanstack/react-query";
import { ExternalLink, Link2, Loader2, Timer } from "lucide-react";

import { ArrangementBadge, ExperienceBadge, SourceBadge, StatusBadge } from "@/components/shared/badges";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { getJob } from "@/lib/api";
import { formatDateTime, formatHoursAgo, formatDate } from "@/lib/utils";
import type { Job } from "@/types";

interface JobDetailDialogProps {
  job: Job | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function JobDetailDialog({ job, open, onOpenChange }: JobDetailDialogProps) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["job", job?.id],
    queryFn: () => getJob(job!.id),
    enabled: open && Boolean(job?.id),
  });

  const detail = data ?? job;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        {detail ? (
          <>
            <DialogHeader>
              <DialogTitle className="pr-6">{detail.title}</DialogTitle>
              <DialogDescription>
                {detail.company_name}
                {detail.location ? ` · ${detail.location}` : ""}
              </DialogDescription>
            </DialogHeader>

            <div className="flex flex-wrap items-center gap-2">
              <SourceBadge label={detail.source_label} testData={detail.is_test_data} />
              <ArrangementBadge value={detail.work_arrangement} />
              <ExperienceBadge value={detail.experience_level} />
              {detail.application ? <StatusBadge status={detail.application.status} /> : null}
              {detail.is_shortlisted ? <Badge variant="success">Shortlisted</Badge> : null}
              {detail.possible_duplicate_count > 0 ? (
                <Badge variant="warning">
                  <Link2 className="h-3 w-3" /> {detail.possible_duplicate_count} possible
                  duplicate{detail.possible_duplicate_count === 1 ? "" : "s"}
                </Badge>
              ) : null}
            </div>

            <dl className="grid grid-cols-2 gap-3 rounded-lg border border-border/70 bg-muted/40 p-4 text-xs sm:grid-cols-3">
              <div>
                <dt className="text-muted-foreground">Published</dt>
                <dd className="mt-0.5 font-medium">
                  {detail.published_at ? formatDateTime(detail.published_at) : "Not provided"}
                  {detail.published_at_is_date_only ? (
                    <span className="ml-1 text-[11px] font-normal text-muted-foreground">
                      (date only)
                    </span>
                  ) : null}
                </dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Posting age</dt>
                <dd className="mt-0.5 font-medium">
                  {detail.posting_age_hours !== null
                    ? formatHoursAgo(detail.posting_age_hours)
                    : "Unknown"}
                </dd>
              </div>
              <div>
                <dt className="text-muted-foreground">First discovered</dt>
                <dd className="mt-0.5 font-medium">
                  {formatDateTime(detail.first_seen_at)}
                </dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Last seen</dt>
                <dd className="mt-0.5 font-medium">{formatDateTime(detail.last_seen_at)}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Source ID</dt>
                <dd className="mt-0.5 truncate font-mono text-[11px]">
                  {detail.source_job_id ?? "—"}
                </dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Shortlisted</dt>
                <dd className="mt-0.5 font-medium">
                  {detail.shortlist
                    ? `${detail.shortlist.priority}${detail.application ? "" : ""}`
                    : "No"}
                </dd>
              </div>
            </dl>

            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Description
              </p>
              {isLoading ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" /> Loading full description…
                </div>
              ) : isError ? (
                <p className="text-sm text-muted-foreground">
                  Could not load the full description. The summary is below.
                  <br />
                  {detail.description_snippet}
                </p>
              ) : (
                <div className="max-h-56 overflow-y-auto whitespace-pre-line rounded-lg border border-border/70 bg-card p-4 text-sm leading-relaxed text-foreground/90 scrollbar-thin">
                  {detail.description || detail.description_snippet || "No description stored."}
                </div>
              )}
            </div>

            {detail.possible_duplicates && detail.possible_duplicates.length > 0 ? (
              <div className="rounded-lg border border-amber-200 bg-amber-50/70 p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-amber-800">
                  Same role seen elsewhere
                </p>
                <ul className="mt-2 space-y-2">
                  {detail.possible_duplicates.map((duplicate) => (
                    <li key={duplicate.id} className="flex items-center justify-between gap-3 text-sm">
                      <span className="min-w-0 truncate text-amber-900">
                        {duplicate.source_label} · {duplicate.company_name}
                        {duplicate.published_at
                          ? ` · ${formatDate(duplicate.published_at)}`
                          : ""}
                      </span>
                      <a
                        href={duplicate.job_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="shrink-0 text-xs font-medium text-amber-800 underline-offset-2 hover:underline"
                      >
                        Open
                      </a>
                    </li>
                  ))}
                </ul>
                <p className="mt-2 text-[11px] text-amber-700/80">
                  Records are never merged automatically; each source keeps its own listing and URL.
                </p>
              </div>
            ) : null}

            <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border pt-4">
              <p className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
                <Timer className="h-3.5 w-3.5" />
                Opening the original listing does not mark it as applied.
              </p>
              <Button asChild size="sm">
                <a href={detail.job_url} target="_blank" rel="noopener noreferrer">
                  Open original listing <ExternalLink className="h-3.5 w-3.5" />
                </a>
              </Button>
            </div>
          </>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
