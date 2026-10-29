"use client";

import { useEffect, useState } from "react";
import {
  BookmarkX,
  ExternalLink,
  Link2,
  Loader2,
  MapPin,
  Save,
  StickyNote,
  Timer,
  Trash2,
} from "lucide-react";

import { JobDetailDialog } from "@/components/jobs/job-detail-dialog";
import { TrackApplicationDialog } from "@/components/jobs/track-application-dialog";
import {
  ArrangementBadge,
  ExperienceBadge,
  PriorityBadge,
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { PRIORITY_META } from "@/lib/constants";
import { useRemoveShortlist, useUpdateShortlist } from "@/lib/hooks";
import { formatHoursAgo } from "@/lib/utils";
import type { Priority, ShortlistEntry } from "@/types";

export function ShortlistCard({ entry }: { entry: ShortlistEntry }) {
  const { job } = entry;
  const [notes, setNotes] = useState(entry.notes ?? "");
  const [detailOpen, setDetailOpen] = useState(false);
  const [trackOpen, setTrackOpen] = useState(false);
  const [confirmRemove, setConfirmRemove] = useState(false);

  const updateMutation = useUpdateShortlist();
  const removeMutation = useRemoveShortlist();

  useEffect(() => {
    setNotes(entry.notes ?? "");
  }, [entry.notes]);

  const notesDirty = notes.trim() !== (entry.notes ?? "").trim();

  return (
    <>
      <Card className="flex h-full flex-col p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 space-y-1">
            <button
              type="button"
              onClick={() => setDetailOpen(true)}
              className="text-left text-base font-semibold leading-snug hover:text-primary"
            >
              {job.title}
            </button>
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">
              <span>{job.company_name}</span>
              {job.location ? (
                <span className="inline-flex items-center gap-1.5">
                  <MapPin className="h-3.5 w-3.5" /> {job.location}
                </span>
              ) : null}
            </div>
          </div>
          <Button variant="ghost" size="icon-sm" aria-label="Open original listing" asChild>
            <a href={job.job_url} target="_blank" rel="noopener noreferrer">
              <ExternalLink className="h-4 w-4" />
            </a>
          </Button>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-2">
          <SourceBadge label={job.source_label} testData={job.is_test_data} />
          <ArrangementBadge value={job.work_arrangement} />
          <ExperienceBadge value={job.experience_level} />
          <PriorityBadge priority={entry.priority} />
          {job.possible_duplicate_count > 0 ? (
            <Badge variant="warning">
              <Link2 className="h-3 w-3" /> {job.possible_duplicate_count}
            </Badge>
          ) : null}
          {job.application ? <StatusBadge status={job.application.status} /> : null}
        </div>

        <p className="mt-3 inline-flex items-center gap-1.5 text-xs text-muted-foreground">
          <Timer className="h-3.5 w-3.5" />
          {job.posting_age_hours !== null
            ? `Posted ${formatHoursAgo(job.posting_age_hours)}`
            : "Publication time unknown"}
        </p>

        {job.description_snippet ? (
          <p className="mt-3 line-clamp-2 text-sm text-muted-foreground">
            {job.description_snippet}
          </p>
        ) : null}

        <div className="mt-4 flex-1 space-y-2 rounded-lg border border-border/70 bg-muted/30 p-3">
          <div className="flex items-center justify-between gap-2">
            <p className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
              <StickyNote className="h-3.5 w-3.5" /> Your notes
            </p>
            <Select
              value={entry.priority}
              onValueChange={(value) =>
                updateMutation.mutate({ jobId: job.id, priority: value as Priority })
              }
            >
              <SelectTrigger className="h-7 w-[110px] text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(Object.keys(PRIORITY_META) as Priority[]).map((priority) => (
                  <SelectItem key={priority} value={priority}>
                    {PRIORITY_META[priority].label} priority
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Textarea
            rows={2}
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            placeholder="Why is this role interesting? Referral, salary, questions to ask…"
            className="min-h-[62px] bg-card text-sm"
          />
          <div className="flex items-center justify-between gap-2">
            <span className="text-[11px] text-muted-foreground">
              {notesDirty ? "Unsaved changes" : "Synced with your shortlist"}
            </span>
            <Button
              size="sm"
              variant="outline"
              disabled={!notesDirty || updateMutation.isPending}
              onClick={() =>
                updateMutation.mutate({
                  jobId: job.id,
                  notes: notes.trim() ? notes.trim() : null,
                })
              }
            >
              {updateMutation.isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Save className="h-3.5 w-3.5" />
              )}
              Save notes
            </Button>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => setDetailOpen(true)}>
            Details
          </Button>
          <Button variant="default" size="sm" onClick={() => setTrackOpen(true)}>
            {job.application ? "Update application" : "Track application"}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="text-destructive hover:bg-destructive/10"
            onClick={() => setConfirmRemove(true)}
          >
            <BookmarkX className="h-3.5 w-3.5" /> Remove
          </Button>
        </div>
      </Card>

      <JobDetailDialog job={job} open={detailOpen} onOpenChange={setDetailOpen} />
      <TrackApplicationDialog job={job} open={trackOpen} onOpenChange={setTrackOpen} />

      <Dialog open={confirmRemove} onOpenChange={setConfirmRemove}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Remove from shortlist?</DialogTitle>
            <DialogDescription>
              Notes and priority for {job.title} will be deleted. Application tracking records are
              not affected.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmRemove(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              disabled={removeMutation.isPending}
              onClick={() =>
                removeMutation.mutate(job.id, {
                  onSettled: () => setConfirmRemove(false),
                })
              }
            >
              <Trash2 className="h-3.5 w-3.5" /> Remove
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
