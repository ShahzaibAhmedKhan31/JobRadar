"use client";

import { useState } from "react";
import { Loader2, Search } from "lucide-react";

import { TrackApplicationDialog } from "@/components/jobs/track-application-dialog";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { StatusBadge } from "@/components/shared/badges";
import { useJobs } from "@/lib/hooks";
import type { Job } from "@/types";

interface TrackJobDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function TrackJobDialog({ open, onOpenChange }: TrackJobDialogProps) {
  const [search, setSearch] = useState("");
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [trackOpen, setTrackOpen] = useState(false);

  const { data, isLoading } = useJobs({
    q: search.trim() || undefined,
    page_size: 8,
    sort: "newest",
    include_test_data: true,
  });

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Track an existing job</DialogTitle>
            <DialogDescription>
              Pick a stored listing, then record the application details. Only choose jobs you have
              actually applied to.
            </DialogDescription>
          </DialogHeader>
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              autoFocus
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search stored jobs by title or company"
              className="pl-9"
            />
          </div>
          <div className="max-h-72 space-y-2 overflow-y-auto">
            {isLoading ? (
              <div className="flex items-center justify-center gap-2 py-6 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" /> Searching…
              </div>
            ) : (data?.items.length ?? 0) === 0 ? (
              <p className="py-6 text-center text-sm text-muted-foreground">
                No stored jobs found. Discover or import a listing first.
              </p>
            ) : (
              data?.items.map((job) => (
                <button
                  key={job.id}
                  type="button"
                  className="flex w-full items-center justify-between gap-3 rounded-lg border border-border px-3 py-2.5 text-left transition-colors hover:border-primary/40 hover:bg-muted/40"
                  onClick={() => {
                    setSelectedJob(job);
                    setTrackOpen(true);
                    onOpenChange(false);
                  }}
                >
                  <span className="min-w-0">
                    <span className="block truncate text-sm font-medium">{job.title}</span>
                    <span className="block truncate text-xs text-muted-foreground">
                      {job.company_name} · {job.source_label}
                    </span>
                  </span>
                  {job.application ? <StatusBadge status={job.application.status} /> : null}
                </button>
              ))
            )}
          </div>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
        </DialogContent>
      </Dialog>

      <TrackApplicationDialog job={selectedJob} open={trackOpen} onOpenChange={setTrackOpen} />
    </>
  );
}
