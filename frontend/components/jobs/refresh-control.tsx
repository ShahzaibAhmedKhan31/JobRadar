"use client";

import { ChevronDown, Loader2, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { RefreshJobsPayload } from "@/lib/api";
import { useRefreshJobs, useSources } from "@/lib/hooks";
import { splitTerms } from "@/lib/utils";

/**
 * Search hints taken from whatever the user is currently looking at.
 *
 * Scraping LinkedIn without keywords returns a generic feed, so "Refresh" must
 * send the filters on screen instead of silently falling back to an empty
 * query. Providers receive the same shape the standalone jobspy script uses:
 * one search term per request, plus location and posting age.
 */
export interface RefreshSearchHints {
  titles?: string;
  keywords?: string;
  location?: string;
  maxAgeHours?: number | "any";
}

const MAX_TERMS = 5;

export function buildRefreshPayload(
  hints: RefreshSearchHints = {},
  extra: RefreshJobsPayload = {},
): RefreshJobsPayload {
  const titles = splitTerms(hints.titles, MAX_TERMS);
  const keywords = splitTerms(hints.keywords, MAX_TERMS);
  const location = hints.location?.trim();
  return {
    ...extra,
    ...(titles.length > 0 ? { titles } : {}),
    ...(keywords.length > 0 ? { keywords } : {}),
    ...(location ? { location } : {}),
    ...(typeof hints.maxAgeHours === "number" ? { max_age_hours: hints.maxAgeHours } : {}),
  };
}

export function RefreshControl({
  compact = false,
  search,
}: {
  compact?: boolean;
  search?: RefreshSearchHints;
}) {
  const { data } = useSources();
  const refreshMutation = useRefreshJobs();
  const refreshable = (data?.sources ?? []).filter((source) => source.can_refresh);
  const pending = refreshMutation.isPending;
  const payload = buildRefreshPayload(search);

  const refreshAll = () => refreshMutation.mutate(payload);
  const refreshOne = (source: string) =>
    refreshMutation.mutate({ ...payload, sources: [source] });

  return (
    <div className="flex items-center">
      <Button
        onClick={refreshAll}
        disabled={pending}
        size={compact ? "sm" : "default"}
        className="rounded-r-none"
      >
        {pending ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <RefreshCw className="h-4 w-4" />
        )}
        {pending ? "Searching…" : "Refresh sources"}
      </Button>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            size={compact ? "sm" : "default"}
            className="rounded-l-none border-l border-primary-foreground/20 px-2"
            aria-label="Choose source to refresh"
            disabled={pending}
          >
            <ChevronDown className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-64">
          <DropdownMenuLabel>Refresh a single source</DropdownMenuLabel>
          {refreshable.length === 0 ? (
            <DropdownMenuItem disabled>No refreshable sources</DropdownMenuItem>
          ) : (
            refreshable.map((source) => (
              <DropdownMenuItem key={source.key} onClick={() => refreshOne(source.key)}>
                <span className="flex-1">{source.name}</span>
                <span className="text-xs text-muted-foreground">{source.stored_jobs_count}</span>
              </DropdownMenuItem>
            ))
          )}
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={refreshAll}>Refresh all sources</DropdownMenuItem>
          <p className="px-2 pb-1 pt-2 text-[11px] leading-snug text-muted-foreground">
            {payload.titles?.length || payload.keywords?.length ? (
              <>
                Searches{" "}
                <span className="font-medium text-foreground">
                  {[...(payload.titles ?? []), ...(payload.keywords ?? [])].join(", ")}
                </span>
                {payload.location ? ` in ${payload.location}` : " (no location)"}
                {payload.max_age_hours ? ` · last ${payload.max_age_hours}h` : ""}.
              </>
            ) : (
              <>
                No titles or location set, so the scrape would run against an unfiltered feed.
                Add them on this page or in Search Settings.
              </>
            )}
          </p>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
