"use client";

import { useState } from "react";
import Link from "next/link";
import { Bookmark, Search } from "lucide-react";

import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { PageHeader } from "@/components/shared/page-header";
import { Pagination } from "@/components/shared/pagination";
import { JobListSkeleton } from "@/components/shared/skeletons";
import { ShortlistCard } from "@/components/shortlist/shortlist-card";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useShortlist, useSources } from "@/lib/hooks";
import { PRIORITY_META } from "@/lib/constants";
import type { Priority, ShortlistFilters } from "@/types";

const PAGE_SIZE = 8;

export default function ShortlistPage() {
  const [search, setSearch] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [priority, setPriority] = useState<"any" | Priority>("any");
  const [source, setSource] = useState<string>("any");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [sort, setSort] = useState<"newest" | "oldest" | "priority">("priority");
  const [page, setPage] = useState(1);

  const { data: sourcesData } = useSources();

  const filters: ShortlistFilters = {
    search: searchTerm || undefined,
    priority: priority === "any" ? undefined : priority,
    sources: source === "any" ? undefined : [source],
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
    sort,
    page,
    page_size: PAGE_SIZE,
  };

  const { data, isLoading, isFetching, isError, error, refetch } = useShortlist(filters);

  const reset = () => {
    setSearch("");
    setSearchTerm("");
    setPriority("any");
    setSource("any");
    setDateFrom("");
    setDateTo("");
    setSort("priority");
    setPage(1);
  };

  return (
    <div className="space-y-2">
      <PageHeader
        title="Shortlist"
        description="Roles worth a second look. Notes and priority survive source refreshes, and saving a job never marks it as applied."
        actions={
          <Button variant="outline" asChild>
            <Link href="/discover">
              <Search className="h-4 w-4" /> Find more jobs
            </Link>
          </Button>
        }
      />

      <Card className="p-4">
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-6">
          <div className="space-y-1.5 lg:col-span-2">
            <Label htmlFor="shortlist-search">Search</Label>
            <form
              onSubmit={(event) => {
                event.preventDefault();
                setSearchTerm(search.trim());
                setPage(1);
              }}
            >
              <Input
                id="shortlist-search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Title, company or note"
              />
            </form>
          </div>
          <div className="space-y-1.5">
            <Label>Priority</Label>
            <Select
              value={priority}
              onValueChange={(value) => {
                setPriority(value as "any" | Priority);
                setPage(1);
              }}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="any">Any priority</SelectItem>
                {(Object.keys(PRIORITY_META) as Priority[]).map((value) => (
                  <SelectItem key={value} value={value}>
                    {PRIORITY_META[value].label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label>Source</Label>
            <Select
              value={source}
              onValueChange={(value) => {
                setSource(value);
                setPage(1);
              }}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="any">Any source</SelectItem>
                {(sourcesData?.sources ?? []).map((entry) => (
                  <SelectItem key={entry.key} value={entry.key}>
                    {entry.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="shortlisted-from">Saved from</Label>
            <Input
              id="shortlisted-from"
              type="date"
              value={dateFrom}
              onChange={(event) => {
                setDateFrom(event.target.value);
                setPage(1);
              }}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="shortlisted-to">Saved until</Label>
            <Input
              id="shortlisted-to"
              type="date"
              value={dateTo}
              onChange={(event) => {
                setDateTo(event.target.value);
                setPage(1);
              }}
            />
          </div>
        </div>
        <div className="mt-3 flex items-center justify-between gap-2">
          <Select
            value={sort}
            onValueChange={(value) => {
              setSort(value as "newest" | "oldest" | "priority");
              setPage(1);
            }}
          >
            <SelectTrigger className="w-[170px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="priority">Priority first</SelectItem>
              <SelectItem value="newest">Recently saved</SelectItem>
              <SelectItem value="oldest">Oldest saved</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="ghost" size="sm" onClick={reset}>
            Reset filters
          </Button>
        </div>
      </Card>

      {isLoading ? (
        <JobListSkeleton count={4} />
      ) : isError ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : (data?.items.length ?? 0) === 0 ? (
        <EmptyState
          icon={<Bookmark className="h-5 w-5" />}
          title="Your shortlist is empty"
          description="Shortlist a role from Discover Jobs to keep it here with private notes and a priority."
          action={
            <Button asChild size="sm">
              <Link href="/discover">Browse jobs</Link>
            </Button>
          }
        />
      ) : (
        <>
          <p className="text-sm text-muted-foreground">
            <span className="font-semibold text-foreground">{data?.total}</span> shortlisted
            role{data?.total === 1 ? "" : "s"}
            {isFetching ? <span className="ml-2 text-xs">updating…</span> : null}
          </p>
          <div className="grid gap-4 xl:grid-cols-2">
            {data?.items.map((entry) => (
              <ShortlistCard key={entry.id} entry={entry} />
            ))}
          </div>
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
        </>
      )}
    </div>
  );
}
