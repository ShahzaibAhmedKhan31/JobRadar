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
import { useUpdateApplication } from "@/lib/hooks";
import type { Application, ApplicationStatus } from "@/types";

interface ApplicationEditDialogProps {
  application: Application | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ApplicationEditDialog({
  application,
  open,
  onOpenChange,
}: ApplicationEditDialogProps) {
  const updateMutation = useUpdateApplication();
  const [status, setStatus] = useState<ApplicationStatus>("applied");
  const [applicationDate, setApplicationDate] = useState("");
  const [followUpDate, setFollowUpDate] = useState("");
  const [resume, setResume] = useState("");
  const [notes, setNotes] = useState("");

  useEffect(() => {
    if (!open || !application) return;
    setStatus(application.status);
    setApplicationDate(application.application_date ?? "");
    setFollowUpDate(application.follow_up_date ?? "");
    setResume(application.resume_reference ?? "");
    setNotes(application.notes ?? "");
  }, [open, application]);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!application) return;
    try {
      await updateMutation.mutateAsync({
        applicationId: application.id,
        status,
        application_date: applicationDate || null,
        follow_up_date: followUpDate || null,
        resume_reference: resume.trim() ? resume.trim() : null,
        notes: notes.trim() ? notes.trim() : null,
      });
      onOpenChange(false);
    } catch {
      /* handled by mutation toast */
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit application</DialogTitle>
          <DialogDescription>
            {application ? `${application.job.title} · ${application.job.company_name}` : ""}
          </DialogDescription>
        </DialogHeader>
        <form className="space-y-4" onSubmit={handleSubmit}>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="edit-status">Status</Label>
              <Select value={status} onValueChange={(value) => setStatus(value as ApplicationStatus)}>
                <SelectTrigger id="edit-status">
                  <SelectValue />
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
              <Label htmlFor="edit-applied">Application date</Label>
              <Input
                id="edit-applied"
                type="date"
                value={applicationDate}
                onChange={(event) => setApplicationDate(event.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="edit-follow-up">Follow-up date</Label>
              <Input
                id="edit-follow-up"
                type="date"
                value={followUpDate}
                onChange={(event) => setFollowUpDate(event.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="edit-resume">Resume version</Label>
              <Input
                id="edit-resume"
                value={resume}
                onChange={(event) => setResume(event.target.value)}
                placeholder="e.g. backend-2026-v3.pdf"
              />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="edit-notes">Notes</Label>
            <Textarea
              id="edit-notes"
              rows={4}
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              placeholder="Interviews, contacts, salary discussions…"
            />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={updateMutation.isPending}>
              {updateMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Save changes
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
