"use client";

import { useState } from "react";
import {
  Bookmark,
  BookmarkCheck,
  Building2,
  CalendarClock,
  ExternalLink,
  Link2,
  MapPin,
  Timer,
  Trash2,
} from "lucide-react";

import { JobDetailDialog } from "@/components/jobs/job-detail-dialog";
import { TrackApplicationDialog } from "@/components/jobs/track-application-dialog";
import {
  ArrangementBadge,
  ExperienceBadge,
  SourceBadge,
  StatusBadge,
} from "@/components/shared/badges";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useRemoveShortlist, useShortlistJob } from "@/lib/hooks";
import { describePostingAge, relativeFromNow } from "@/lib/utils";
import type { Job } from "@/types";

interface JobCardProps {
  job: Job;
  compact?: boolean;
}

export function JobCard({ job, compact = false }: JobCardProps) {
  const [detailOpen, setDetailOpen] = useState(false);
  const [trackOpen, setTrackOpen] = useState(false);
  const [confirmRemove, setConfirmRemove] = useState(false);
  const shortlistMutation = useShortlistJob();
  const removeMutation = useRemoveShortlist();

  return (
    <>
      <Card className="animate-fade-in p-5 transition-shadow hover:shadow-elevated">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 space-y-1">
            <button
              type="button"
              onClick={() => setDetailOpen(true)}
              className="text-left text-base font-semibold leading-snug text-foreground hover:text-primary"
            >
              {job.title}
            </button>
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">
              <span className="inline-flex items-center gap-1.5">
                <Building2 className="h-3.5 w-3.5" /> {job.company_name}
              </span>
              {job.location ? (
                <span className="inline-flex items-center gap-1.5">
                  <MapPin className="h-3.5 w-3.5" /> {job.location}
                </span>
              ) : null}
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-1">
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label="Open original listing"
              asChild
            >
              <a href={job.job_url} target="_blank" rel="noopener noreferrer">
                <ExternalLink className="h-4 w-4" />
              </a>
            </Button>
            {job.is_shortlisted ? (
              <Button
                variant="ghost"
                size="icon-sm"
                aria-label="Remove from shortlist"
                onClick={() => setConfirmRemove(true)}
              >
                <BookmarkCheck className="h-4 w-4 text-primary" />
              </Button>
            ) : (
              <Button
                variant="ghost"
                size="icon-sm"
                aria-label="Shortlist this job"
                disabled={shortlistMutation.isPending}
                onClick={() => shortlistMutation.mutate({ jobId: job.id })}
              >
                <Bookmark className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-2">
          <SourceBadge label={job.source_label} testData={job.is_test_data} />
          <ArrangementBadge value={job.work_arrangement} />
          <ExperienceBadge value={job.experience_level} />
          {job.possible_duplicate_count > 0 ? (
            <Badge variant="warning">
              <Link2 className="h-3 w-3" />
              {job.possible_duplicate_count} possible duplicate
              {job.possible_duplicate_count === 1 ? "" : "s"}
            </Badge>
          ) : null}
          {job.application ? <StatusBadge status={job.application.status} /> : null}
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1.5">
            <Timer className="h-3.5 w-3.5" />
            {describePostingAge(job.posting_age_hours, job.published_at_is_date_only)}
          </span>
          <span className="inline-flex items-center gap-1.5">
            <CalendarClock className="h-3.5 w-3.5" />
            Discovered {relativeFromNow(job.first_seen_at)}
          </span>
        </div>

        {job.description_snippet ? (
          <p className="mt-3 line-clamp-2 text-sm leading-relaxed text-muted-foreground">
            {job.description_snippet}
          </p>
        ) : null}

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => setDetailOpen(true)}>
            View details
          </Button>
          <Button
            variant={job.application ? "secondary" : "default"}
            size="sm"
            onClick={() => setTrackOpen(true)}
          >
            {job.application ? "Update application" : "Track application"}
          </Button>
          {!compact && job.is_shortlisted && job.shortlist ? (
            <span className="text-xs text-muted-foreground">
              Shortlisted · {job.shortlist.priority} priority
            </span>
          ) : null}
        </div>
      </Card>

      <JobDetailDialog job={job} open={detailOpen} onOpenChange={setDetailOpen} />
      <TrackApplicationDialog job={job} open={trackOpen} onOpenChange={setTrackOpen} />

      <Dialog open={confirmRemove} onOpenChange={setConfirmRemove}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Remove from shortlist?</DialogTitle>
            <DialogDescription>
              {job.title} at {job.company_name} will be removed from your shortlist along with its
              notes and priority. Any application tracking record is kept.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmRemove(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              disabled={removeMutation.isPending}
              onClick={() => {
                removeMutation.mutate(job.id, {
                  onSettled: () => setConfirmRemove(false),
                });
              }}
            >
              <Trash2 className="h-3.5 w-3.5" /> Remove
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
