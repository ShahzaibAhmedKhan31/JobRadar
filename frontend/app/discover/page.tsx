"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { Info, Plus, Radar, Search, Sparkles, Trash2 } from "lucide-react";

import { ImportJobDialog } from "@/components/jobs/import-job-dialog";
import { JobCard } from "@/components/jobs/job-card";
import {
  DEFAULT_FILTERS,
  JobFiltersPanel,
  type DiscoverFilterState,
} from "@/components/jobs/job-filters";
import { PruneJobsDialog } from "@/components/jobs/prune-jobs-dialog";
import { RefreshControl } from "@/components/jobs/refresh-control";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { PageHeader } from "@/components/shared/page-header";
import { Pagination } from "@/components/shared/pagination";
import { JobListSkeleton } from "@/components/shared/skeletons";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { JOB_SORT_OPTIONS } from "@/lib/constants";
import { useJobFacets, useJobs, useSearchSettings, useSources } from "@/lib/hooks";
import { splitLocations, splitTerms } from "@/lib/utils";
import type { JobFilters, JobSort } from "@/types";

const PAGE_SIZE = 10;

export default function DiscoverPage() {
  const [filters, setFilters] = useState<DiscoverFilterState>(DEFAULT_FILTERS);
  const [searchDraft, setSearchDraft] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [sort, setSort] = useState<JobSort>("newest");
  const [page, setPage] = useState(1);
  const [importOpen, setImportOpen] = useState(false);
  const [pruneOpen, setPruneOpen] = useState(false);

  const { data: sourcesData } = useSources();
  const { data: settings } = useSearchSettings();
  const defaultsApplied = useRef(false);

  useEffect(() => {
    if (!settings || defaultsApplied.current) return;
    defaultsApplied.current = true;
    const hasStoredDefaults =
      settings.default_titles ||
      settings.default_keywords ||
      settings.default_location ||
      settings.default_sources.length > 0;
    if (!hasStoredDefaults) return;
    setFilters((current) => ({
      ...current,
      titles: settings.default_titles ?? "",
      keywords: settings.default_keywords ?? "",
      location: settings.default_location ?? "",
      maxAgeHours: settings.default_posting_age_hours ?? 168,
      workArrangement: settings.default_work_arrangement,
      experienceLevel: settings.default_experience_level,
      sources: settings.default_sources,
    }));
  }, [settings]);

  // One place per line; commas stay part of a place ("Karachi, Pakistan").
  const locationList = useMemo(() => splitLocations(filters.location), [filters.location]);

  const apiFilters: JobFilters = useMemo(
    () => ({
      q: searchTerm || undefined,
      titles: splitTerms(filters.titles),
      keywords: splitTerms(filters.keywords),
      locations: locationList,
      max_age_hours: filters.maxAgeHours === "any" ? undefined : filters.maxAgeHours,
      include_unknown_published: filters.includeUnknownPublished,
      work_arrangement:
        filters.workArrangement === "any" ? undefined : filters.workArrangement,
      experience_level:
        filters.experienceLevel === "any" ? undefined : filters.experienceLevel,
      sources: filters.sources.length > 0 ? filters.sources : undefined,
      include_test_data: filters.includeTestData,
      sort,
      page,
      page_size: PAGE_SIZE,
    }),
    [filters, locationList, searchTerm, sort, page],
  );

  const { data, isLoading, isFetching, isError, error, refetch } = useJobs(apiFilters);

  // What is actually stored, ignoring the filters — so an empty page can say why.
  const facetsQuery = useJobFacets({
    sources: filters.sources.length > 0 ? filters.sources : [],
    include_test_data: filters.includeTestData,
  });
  const facets = facetsQuery.data;
  const storedLocations = facets?.locations ?? [];
  // Does *any* stored location share a token with what the user typed? If not,
  // the database is simply full of results from a different search.
  // Does *any* stored location share the tokens of *any* requested place? If
  // none does, the database is simply full of results from a different search.
  const locationAbsentFromStore =
    locationList.length > 0 &&
    storedLocations.length > 0 &&
    !locationList.some((place) => {
      const tokens = place
        .toLowerCase()
        .split(/[\s,]+/)
        .filter((token) => token.length > 1);
      return (
        tokens.length > 0 &&
        storedLocations.some((item) =>
          tokens.every((token) => item.value.toLowerCase().includes(token)),
        )
      );
    });

  const applyFilters = (next: DiscoverFilterState) => {
    setFilters(next);
    setPage(1);
  };

  const resetFilters = () => {
    setFilters(DEFAULT_FILTERS);
    setSearchDraft("");
    setSearchTerm("");
    setSort("newest");
    setPage(1);
  };

  const hasActiveFilters =
    Boolean(searchTerm) ||
    Boolean(filters.titles || filters.keywords || filters.location) ||
    filters.maxAgeHours !== 168 ||
    filters.workArrangement !== "any" ||
    filters.experienceLevel !== "any" ||
    filters.sources.length > 0;

  const showUnknownNotice =
    Boolean(data) &&
    (data?.unknown_published_count ?? 0) > 0 &&
    !filters.includeUnknownPublished &&
    filters.maxAgeHours !== "any";

  const showSampleNotice =
    (data?.items ?? []).some((job) => job.is_test_data) && filters.includeTestData;

  return (
    <div className="space-y-2">
      <PageHeader
        title="Discover jobs"
        description="Filters run against listings already stored in your database. Refresh a source to import the latest postings, then refine your search."
        actions={
          <>
            <RefreshControl
              search={{
                titles: filters.titles,
                keywords: filters.keywords,
                location: filters.location,
                locations: locationList,
                maxAgeHours: filters.maxAgeHours,
              }}
            />
            <Button variant="outline" onClick={() => setImportOpen(true)}>
              <Plus className="h-4 w-4" /> Import job link
            </Button>
          </>
        }
      />

      <div className="grid gap-6 lg:grid-cols-[320px_minmax(0,1fr)]">
        <div className="lg:sticky lg:top-6 lg:self-start">
          <JobFiltersPanel
            value={filters}
            sources={sourcesData?.sources ?? []}
            onApply={applyFilters}
            onReset={resetFilters}
          />
        </div>

        <div className="min-w-0 space-y-4">
          <div className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4 shadow-card sm:flex-row sm:items-center sm:justify-between">
            <form
              className="flex flex-1 items-center gap-2"
              onSubmit={(event) => {
                event.preventDefault();
                setSearchTerm(searchDraft.trim());
                setPage(1);
              }}
            >
              <div className="relative flex-1">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <input
                  value={searchDraft}
                  onChange={(event) => setSearchDraft(event.target.value)}
                  placeholder="Search titles, companies, descriptions…"
                  aria-label="Search jobs"
                  className="h-9 w-full rounded-md border border-input bg-card pl-9 pr-3 text-sm shadow-sm placeholder:text-muted-foreground/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/60"
                />
              </div>
              <Button type="submit" variant="secondary" size="sm">
                Search
              </Button>
            </form>
            <div className="flex items-center gap-2">
              <span className="hidden text-xs text-muted-foreground sm:inline">Sort</span>
              <Select value={sort} onValueChange={(value) => setSort(value as JobSort)}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {JOB_SORT_OPTIONS.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {data ? (
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm text-muted-foreground">
                <span className="font-semibold text-foreground">{data.total}</span> job
                {data.total === 1 ? "" : "s"} match your filters
                {isFetching ? <span className="ml-2 text-xs">updating…</span> : null}
              </p>
              {hasActiveFilters ? (
                <Button variant="ghost" size="sm" onClick={resetFilters}>
                  Clear filters
                </Button>
              ) : null}
            </div>
          ) : null}

          {showUnknownNotice ? (
            <div className="flex flex-col gap-2 rounded-lg border border-sky-200 bg-sky-50/70 p-3 text-sm text-sky-900 sm:flex-row sm:items-center sm:justify-between">
              <p className="flex items-start gap-2">
                <Info className="mt-0.5 h-4 w-4 shrink-0" />
                {data?.unknown_published_count} stored job
                {data?.unknown_published_count === 1 ? " has" : "s have"} no publication
                timestamp, so they are excluded from the posting-age filter.
              </p>
              <Button
                variant="outline"
                size="sm"
                className="border-sky-300 bg-white"
                onClick={() => applyFilters({ ...filters, includeUnknownPublished: true })}
              >
                Include them
              </Button>
            </div>
          ) : null}

          {showSampleNotice ? (
            <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50/70 p-3 text-xs text-amber-900">
              <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              Some results are synthetic sample listings from the bundled demo feed. They are
              labelled “sample” and excluded from dashboard metrics by default.
            </div>
          ) : null}

          {isLoading ? (
            <JobListSkeleton count={4} />
          ) : isError ? (
            <ErrorState error={error} onRetry={() => refetch()} />
          ) : (data?.items.length ?? 0) === 0 ? (
            hasActiveFilters ? (
              <EmptyState
                icon={<Search className="h-5 w-5" />}
                title={
                  (facets?.real_total ?? 0) > 0
                    ? "Nothing stored matches these filters"
                    : "No real listings stored yet"
                }
                description={
                  (facets?.real_total ?? 0) > 0 ? (
                    <>
                      You have <strong>{facets?.real_total}</strong> real listing
                      {facets?.real_total === 1 ? "" : "s"} stored, but none match the current
                      filters. This page only searches what is already in JobRadar — it does not
                      contact LinkedIn by itself.
                      {storedLocations.length > 0 ? (
                        <span className="mt-2 block">
                          Stored locations:{" "}
                          <span className="text-foreground">
                            {storedLocations
                              .slice(0, 4)
                              .map((item) => `${item.value} (${item.count})`)
                              .join(", ")}
                            {storedLocations.length > 4
                              ? ` and ${storedLocations.length - 4} more`
                              : ""}
                          </span>
                        </span>
                      ) : null}
                      {locationAbsentFromStore ? (
                        <span className="mt-2 block">
                          None of them mention{" "}
                          <strong>{locationList.join(" or ")}</strong>. They were most likely
                          fetched by an earlier search that did not include it — LinkedIn
                          answers with a US-wide feed when no location is given.
                        </span>
                      ) : null}
                      <span className="mt-1 block">
                        Adjust a filter, or run this search to fetch more:
                      </span>
                    </>
                  ) : (
                    <>
                      Nothing has been scraped yet. Press the button below to search LinkedIn with
                      these exact criteria — the results are stored, then listed here.
                      {locationList.length > 0 ? null : (
                        <span className="mt-2 block text-amber-700">
                          Tip: add a location such as “Karachi, Pakistan”. An unscoped LinkedIn
                          search returns very little.
                        </span>
                      )}
                    </>
                  )
                }
                action={
                  <div className="flex flex-col items-center gap-2">
                    <div className="flex flex-wrap justify-center gap-2">
                      <RefreshControl
                        compact
                        search={{
                          titles: filters.titles,
                          keywords: filters.keywords,
                          location: filters.location,
                          locations: locationList,
                          maxAgeHours: filters.maxAgeHours,
                        }}
                      />
                      <Button variant="outline" size="sm" onClick={resetFilters}>
                        Clear filters
                      </Button>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-muted-foreground"
                      onClick={() => setPruneOpen(true)}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                      Remove these {facets?.real_total ?? 0} listings
                    </Button>
                  </div>
                }
              />
            ) : (
              <EmptyState
                icon={<Radar className="h-5 w-5" />}
                title="No jobs stored yet"
                description="Press Refresh to scrape LinkedIn using your saved search (titles, location, posting age), or paste a job link you found yourself."
                action={
                  <div className="flex flex-wrap justify-center gap-2">
                    <RefreshControl
                      compact
                      search={{
                        titles: filters.titles,
                        keywords: filters.keywords,
                        location: filters.location,
                        locations: locationList,
                        maxAgeHours: filters.maxAgeHours,
                      }}
                    />
                    <Button variant="outline" size="sm" onClick={() => setImportOpen(true)}>
                      <Plus className="h-3.5 w-3.5" /> Import a link
                    </Button>
                    <Button variant="ghost" size="sm" asChild>
                      <Link href="/settings">Configure sources</Link>
                    </Button>
                  </div>
                }
              />
            )
          ) : (
            <div className="space-y-3">
              {data?.items.map((job) => (
                <JobCard key={job.id} job={job} />
              ))}
            </div>
          )}

          {data && data.total > 0 ? (
            <Pagination
              page={data.page}
              pages={data.pages}
              total={data.total}
              pageSize={data.page_size}
              onPageChange={setPage}
              isFetching={isFetching}
            />
          ) : null}
        </div>
      </div>

      <ImportJobDialog open={importOpen} onOpenChange={setImportOpen} />
      <PruneJobsDialog
        open={pruneOpen}
        onOpenChange={setPruneOpen}
        count={facets?.real_total}
        sources={filters.sources.length > 0 ? filters.sources : undefined}
      />
    </div>
  );
}
