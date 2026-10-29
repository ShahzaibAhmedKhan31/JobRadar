"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { APPLICATION_STATUS_ORDER, STATUS_META } from "@/lib/constants";
import { useCreateApplication, useUpdateApplication } from "@/lib/hooks";
import { toIsoDate } from "@/lib/utils";
import type { ApplicationStatus, Job } from "@/types";

interface TrackApplicationDialogProps {
  job: Job | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function TrackApplicationDialog({ job, open, onOpenChange }: TrackApplicationDialogProps) {
  const existing = job?.application ?? null;
  const createMutation = useCreateApplication();
  const updateMutation = useUpdateApplication();

  const [status, setStatus] = useState<ApplicationStatus>("applied");
  const [applicationDate, setApplicationDate] = useState("");
  const [followUpDate, setFollowUpDate] = useState("");
  const [resume, setResume] = useState("");
  const [notes, setNotes] = useState("");

  useEffect(() => {
    if (!open || !job) return;
    const current = job.application;
    setStatus(current?.status ?? "applied");
    setApplicationDate(current?.application_date ?? toIsoDate(new Date()));
    setFollowUpDate(current?.follow_up_date ?? "");
    setResume(current?.resume_reference ?? "");
    setNotes(job.shortlist?.notes ?? "");
  }, [open, job]);

  const submitting = createMutation.isPending || updateMutation.isPending;

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!job) return;
    const payload = {
      status,
      application_date: applicationDate || null,
      follow_up_date: followUpDate || null,
      resume_reference: resume.trim() ? resume.trim() : null,
      notes: notes.trim() ? notes.trim() : null,
    };
    try {
      if (existing) {
        await updateMutation.mutateAsync({ applicationId: existing.id, ...payload });
      } else {
        await createMutation.mutateAsync({ job_id: job.id, ...payload });
      }
      onOpenChange(false);
    } catch {
      /* toast already shown by the mutation */
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{existing ? "Update application" : "Track an application"}</DialogTitle>
          <DialogDescription>
            {job ? `${job.title} · ${job.company_name}` : ""}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="status">Status</Label>
              <Select value={status} onValueChange={(value) => setStatus(value as ApplicationStatus)}>
                <SelectTrigger id="status">
                  <SelectValue placeholder="Select status" />
                </SelectTrigger>
                <SelectContent>
                  {APPLICATION_STATUS_ORDER.map((value) => (
                    <SelectItem key={value} value={value}>
                      {STATUS_META[value].label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="application-date">Application date</Label>
              <Input
                id="application-date"
                type="date"
                value={applicationDate}
                max={toIsoDate(new Date())}
                onChange={(event) => setApplicationDate(event.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="follow-up">Follow-up date</Label>
              <Input
                id="follow-up"
                type="date"
                value={followUpDate}
                onChange={(event) => setFollowUpDate(event.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="resume">Resume version</Label>
              <Input
                id="resume"
                placeholder="e.g. backend-2026-v3.pdf"
                value={resume}
                onChange={(event) => setResume(event.target.value)}
              />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="notes">Notes</Label>
            <Textarea
              id="notes"
              rows={3}
              placeholder="Recruiter, referral, salary notes, next steps…"
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
            />
          </div>
          <p className="rounded-md bg-muted/60 px-3 py-2 text-[11px] text-muted-foreground">
            This records a tracking entry only. Submitting the actual application stays manual.
          </p>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              {existing ? "Save changes" : "Start tracking"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
