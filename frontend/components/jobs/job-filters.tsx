"use client";

import { useEffect, useState } from "react";
import { FilterX, SlidersHorizontal } from "lucide-react";

import { Button } from "@/components/ui/button";
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
import { Textarea } from "@/components/ui/textarea";
import { POSTING_AGE_OPTIONS } from "@/lib/constants";
import type { ExperienceLevel, SourceInfo, WorkArrangement } from "@/types";

export interface DiscoverFilterState {
  titles: string;
  keywords: string;
  location: string;
  maxAgeHours: number | "any";
  workArrangement: "any" | WorkArrangement;
  experienceLevel: "any" | ExperienceLevel;
  sources: string[];
  includeUnknownPublished: boolean;
  includeTestData: boolean;
}

export const DEFAULT_FILTERS: DiscoverFilterState = {
  titles: "",
  keywords: "",
  location: "",
  maxAgeHours: 168,
  workArrangement: "any",
  experienceLevel: "any",
  sources: [],
  includeUnknownPublished: false,
  includeTestData: false,
};

interface JobFiltersPanelProps {
  value: DiscoverFilterState;
  sources: SourceInfo[];
  onApply: (value: DiscoverFilterState) => void;
  onReset: () => void;
}

export function JobFiltersPanel({ value, sources, onApply, onReset }: JobFiltersPanelProps) {
  const [draft, setDraft] = useState<DiscoverFilterState>(value);

  useEffect(() => {
    setDraft(value);
  }, [value]);

  const update = <K extends keyof DiscoverFilterState>(
    key: K,
    next: DiscoverFilterState[K],
  ) => setDraft((current) => ({ ...current, [key]: next }));

  const toggleSource = (key: string) => {
    setDraft((current) => ({
      ...current,
      sources: current.sources.includes(key)
        ? current.sources.filter((entry) => entry !== key)
        : [...current.sources, key],
    }));
  };

  return (
    <div className="rounded-xl border border-border bg-card shadow-card">
      <div className="flex items-center justify-between border-b border-border px-5 py-4">
        <div className="flex items-center gap-2">
          <SlidersHorizontal className="h-4 w-4 text-primary" />
          <h2 className="text-sm font-semibold">Search filters</h2>
        </div>
        <Button variant="ghost" size="sm" onClick={onReset} className="text-muted-foreground">
          <FilterX className="h-3.5 w-3.5" /> Reset
        </Button>
      </div>

      <div className="space-y-5 p-5">
        <div className="space-y-1.5">
          <Label htmlFor="filter-titles">Job titles</Label>
          <Textarea
            id="filter-titles"
            rows={2}
            value={draft.titles}
            onChange={(event) => update("titles", event.target.value)}
            placeholder="Backend Engineer, Data Engineer"
          />
          <p className="text-[11px] text-muted-foreground">Comma separated. Matches titles and descriptions.</p>
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="filter-keywords">Skills &amp; keywords</Label>
          <Input
            id="filter-keywords"
            value={draft.keywords}
            onChange={(event) => update("keywords", event.target.value)}
            placeholder="Python, PostgreSQL, Fintech"
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="filter-location">Location</Label>
          <Input
            id="filter-location"
            value={draft.location}
            onChange={(event) => update("location", event.target.value)}
            placeholder="Karachi, Pakistan or Remote"
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
          <div className="space-y-1.5">
            <Label>Posting age</Label>
            <Select
              value={String(draft.maxAgeHours)}
              onValueChange={(next) =>
                update("maxAgeHours", next === "any" ? "any" : Number(next))
              }
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="any">Any time</SelectItem>
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
              value={draft.workArrangement}
              onValueChange={(next) =>
                update("workArrangement", next as DiscoverFilterState["workArrangement"])
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
              value={draft.experienceLevel}
              onValueChange={(next) =>
                update("experienceLevel", next as DiscoverFilterState["experienceLevel"])
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
          <Label>Job sources</Label>
          <div className="space-y-2">
            {sources.map((source) => (
              <label
                key={source.key}
                className="flex cursor-pointer items-start gap-2.5 rounded-md px-1 py-1 text-sm hover:bg-muted/50"
              >
                <Checkbox
                  checked={draft.sources.includes(source.key)}
                  onCheckedChange={() => toggleSource(source.key)}
                  className="mt-0.5"
                />
                <span className="flex-1">
                  <span className="flex items-center gap-1.5 font-medium text-foreground/90">
                    {source.name}
                    {source.is_test_data ? (
                      <span className="rounded bg-amber-50 px-1.5 py-0.5 text-[10px] font-medium uppercase text-amber-700">
                        sample
                      </span>
                    ) : null}
                  </span>
                  <span className="block text-[11px] text-muted-foreground">
                    {source.availability === "available" ? "Available" : "Auto-import unavailable"}
                    {" · "}
                    {source.stored_jobs_count} stored
                  </span>
                </span>
              </label>
            ))}
          </div>
        </div>

        <div className="space-y-3 rounded-lg border border-border/70 bg-muted/30 p-3">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-xs font-medium text-foreground">Include unknown posting dates</p>
              <p className="text-[11px] text-muted-foreground">
                Listings without a source timestamp are hidden by age filters otherwise.
              </p>
            </div>
            <Switch
              checked={draft.includeUnknownPublished}
              onCheckedChange={(next) => update("includeUnknownPublished", next)}
              disabled={draft.maxAgeHours === "any"}
              aria-label="Include jobs with unknown posting dates"
            />
          </div>
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-xs font-medium text-foreground">Include sample data</p>
              <p className="text-[11px] text-muted-foreground">
                Off by default. Turn on to see the 26 synthetic demo rows; they never
                appear in your real metrics.
              </p>
            </div>
            <Switch
              checked={draft.includeTestData}
              onCheckedChange={(next) => update("includeTestData", next)}
              aria-label="Include sample data"
            />
          </div>
        </div>

        <Button className="w-full" onClick={() => onApply(draft)}>
          Apply filters
        </Button>
      </div>
    </div>
  );
}
