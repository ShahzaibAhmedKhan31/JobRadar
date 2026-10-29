"use client";

import { useState } from "react";
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
import { MANUAL_IMPORT_SOURCES } from "@/lib/constants";
import { useImportJob } from "@/lib/hooks";
import type { ExperienceLevel, WorkArrangement } from "@/types";

interface ImportJobDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const WORK_OPTIONS: { value: WorkArrangement; label: string }[] = [
  { value: "remote", label: "Remote" },
  { value: "hybrid", label: "Hybrid" },
  { value: "onsite", label: "On-site" },
  { value: "unknown", label: "Not specified" },
];

const EXPERIENCE_OPTIONS: { value: ExperienceLevel; label: string }[] = [
  { value: "entry", label: "Entry level" },
  { value: "associate", label: "Associate" },
  { value: "mid_senior", label: "Mid-senior" },
  { value: "unknown", label: "Not specified" },
];

export function ImportJobDialog({ open, onOpenChange }: ImportJobDialogProps) {
  const [title, setTitle] = useState("");
  const [company, setCompany] = useState("");
  const [url, setUrl] = useState("");
  const [source, setSource] = useState("linkedin");
  const [location, setLocation] = useState("");
  const [workArrangement, setWorkArrangement] = useState<WorkArrangement>("unknown");
  const [experienceLevel, setExperienceLevel] = useState<ExperienceLevel>("unknown");
  const [publishedAt, setPublishedAt] = useState("");
  const [description, setDescription] = useState("");
  const importMutation = useImportJob();

  function reset() {
    setTitle("");
    setCompany("");
    setUrl("");
    setSource("linkedin");
    setLocation("");
    setWorkArrangement("unknown");
    setExperienceLevel("unknown");
    setPublishedAt("");
    setDescription("");
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    try {
      await importMutation.mutateAsync({
        title: title.trim(),
        company_name: company.trim(),
        job_url: url.trim(),
        source,
        location: location.trim() || null,
        work_arrangement: workArrangement,
        experience_level: experienceLevel,
        description: description.trim() || null,
        published_at: publishedAt ? `${publishedAt}T00:00:00Z` : null,
      });
      reset();
      onOpenChange(false);
    } catch {
      /* toast already handled */
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>Import a job link</DialogTitle>
          <DialogDescription>
            LinkedIn and Indeed don&apos;t permit automated retrieval, so paste the details of a
            listing you found yourself. Only add roles you actually opened.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="import-title">Job title *</Label>
              <Input
                id="import-title"
                required
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                placeholder="Senior Backend Engineer"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="import-company">Company *</Label>
              <Input
                id="import-company"
                required
                value={company}
                onChange={(event) => setCompany(event.target.value)}
                placeholder="Northwind Analytics"
              />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="import-url">Listing URL *</Label>
            <Input
              id="import-url"
              required
              type="url"
              value={url}
              onChange={(event) => setUrl(event.target.value)}
              placeholder="https://www.linkedin.com/jobs/view/…"
            />
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="space-y-1.5">
              <Label htmlFor="import-source">Found on</Label>
              <Select value={source} onValueChange={setSource}>
                <SelectTrigger id="import-source">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {MANUAL_IMPORT_SOURCES.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="import-published">Posted on</Label>
              <Input
                id="import-published"
                type="date"
                value={publishedAt}
                onChange={(event) => setPublishedAt(event.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="import-location">Location</Label>
              <Input
                id="import-location"
                value={location}
                onChange={(event) => setLocation(event.target.value)}
                placeholder="Karachi, Pakistan"
              />
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="import-work">Work arrangement</Label>
              <Select
                value={workArrangement}
                onValueChange={(value) => setWorkArrangement(value as WorkArrangement)}
              >
                <SelectTrigger id="import-work">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {WORK_OPTIONS.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="import-experience">Experience level</Label>
              <Select
                value={experienceLevel}
                onValueChange={(value) => setExperienceLevel(value as ExperienceLevel)}
              >
                <SelectTrigger id="import-experience">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {EXPERIENCE_OPTIONS.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="import-description">Description / notes</Label>
            <Textarea
              id="import-description"
              rows={3}
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="Paste the key responsibilities so filters can match this role."
            />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={importMutation.isPending}>
              {importMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Import job
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
