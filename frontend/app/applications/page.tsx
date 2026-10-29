"use client";

import { useState } from "react";
import Link from "next/link";
import { Check, ChevronDown, Columns3, Kanban, Plus, Search, Table2 } from "lucide-react";

import { ApplicationBoard } from "@/components/applications/application-board";
import { ApplicationRow } from "@/components/applications/application-row";
import { TrackJobDialog } from "@/components/applications/track-job-dialog";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { PageHeader } from "@/components/shared/page-header";
import { Pagination } from "@/components/shared/pagination";
import { TableSkeleton } from "@/components/shared/skeletons";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { APPLICATION_STATUS_ORDER, STATUS_META } from "@/lib/constants";
import { useApplications } from "@/lib/hooks";
import type { ApplicationFilters, ApplicationSort, ApplicationStatus } from "@/types";

const PAGE_SIZE = 15;
const BOARD_PAGE_SIZE = 100;

export default function ApplicationsPage() {
  const [view, setView] = useState<"table" | "board">("table");
  const [search, setSearch] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [company, setCompany] = useState("");
  const [companyTerm, setCompanyTerm] = useState("");
  const [statuses, setStatuses] = useState<ApplicationStatus[]>([]);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [sort, setSort] = useState<ApplicationSort>("newest");
  const [page, setPage] = useState(1);
  const [trackOpen, setTrackOpen] = useState(false);

  const filters: ApplicationFilters = {
    status: statuses.length > 0 ? statuses : undefined,
    company: companyTerm || undefined,
    search: searchTerm || undefined,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
    sort,
    page: view === "board" ? 1 : page,
    page_size: view === "board" ? BOARD_PAGE_SIZE : PAGE_SIZE,
  };

  const { data, isLoading, isFetching, isError, error, refetch } = useApplications(filters);

  const reset = () => {
    setSearch("");
    setSearchTerm("");
    setCompany("");
    setCompanyTerm("");
    setStatuses([]);
    setDateFrom("");
    setDateTo("");
    setSort("newest");
    setPage(1);
  };

  const toggleStatus = (status: ApplicationStatus) => {
    setStatuses((current) =>
      current.includes(status)
        ? current.filter((entry) => entry !== status)
        : [...current, status],
    );
    setPage(1);
  };

  const activeFilterCount =
    (searchTerm ? 1 : 0) +
    (companyTerm ? 1 : 0) +
    statuses.length +
    (dateFrom ? 1 : 0) +
    (dateTo ? 1 : 0);

  return (
    <div className="space-y-2">
      <PageHeader
        title="Applications"
        description="A manual record of every application you submitted. Update statuses as you hear back — nothing here is changed automatically."
        actions={
          <Button onClick={() => setTrackOpen(true)}>
            <Plus className="h-4 w-4" /> Track a job
          </Button>
        }
      />

      <Card className="p-4">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
          <div className="space-y-1.5 xl:col-span-2">
            <Label htmlFor="application-search">Search</Label>
            <form
              className="relative"
              onSubmit={(event) => {
                event.preventDefault();
                setSearchTerm(search.trim());
                setPage(1);
              }}
            >
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                id="application-search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Role, company, notes…"
                className="pl-9"
              />
            </form>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="application-company">Company</Label>
            <form
              onSubmit={(event) => {
                event.preventDefault();
                setCompanyTerm(company.trim());
                setPage(1);
              }}
            >
              <Input
                id="application-company"
                value={company}
                onChange={(event) => setCompany(event.target.value)}
                placeholder="Filter by company"
              />
            </form>
          </div>
          <div className="space-y-1.5">
            <Label>Status</Label>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" className="w-full justify-between font-normal">
                  {statuses.length === 0
                    ? "All statuses"
                    : `${statuses.length} selected`}
                  <ChevronDown className="h-4 w-4 opacity-50" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" className="w-52">
                <DropdownMenuLabel>Filter by status</DropdownMenuLabel>
                {APPLICATION_STATUS_ORDER.map((status) => (
                  <DropdownMenuItem
                    key={status}
                    onSelect={(event) => {
                      event.preventDefault();
                      toggleStatus(status);
                    }}
                  >
                    <span className="flex h-4 w-4 items-center justify-center">
                      <Checkbox checked={statuses.includes(status)} className="pointer-events-none" />
                    </span>
                    {STATUS_META[status].label}
                  </DropdownMenuItem>
                ))}
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  onSelect={(event) => {
                    event.preventDefault();
                    setStatuses([]);
                    setPage(1);
                  }}
                >
                  Clear status filter
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div className="space-y-1.5">
              <Label htmlFor="applied-from">Applied from</Label>
              <Input
                id="applied-from"
                type="date"
                value={dateFrom}
                onChange={(event) => {
                  setDateFrom(event.target.value);
                  setPage(1);
                }}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="applied-to">Until</Label>
              <Input
                id="applied-to"
                type="date"
                value={dateTo}
                onChange={(event) => {
                  setDateTo(event.target.value);
                  setPage(1);
                }}
              />
            </div>
          </div>
        </div>

        <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <Select
              value={sort}
              onValueChange={(value) => {
                setSort(value as ApplicationSort);
                setPage(1);
              }}
            >
              <SelectTrigger className="w-[180px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="newest">Newest applied</SelectItem>
                <SelectItem value="oldest">Oldest applied</SelectItem>
                <SelectItem value="updated">Recently updated</SelectItem>
                <SelectItem value="company">Company A–Z</SelectItem>
              </SelectContent>
            </Select>
            {activeFilterCount > 0 ? (
              <Button variant="ghost" size="sm" onClick={reset}>
                Clear {activeFilterCount} filter{activeFilterCount === 1 ? "" : "s"}
              </Button>
            ) : null}
          </div>
          <Tabs value={view} onValueChange={(value) => setView(value as "table" | "board")}>
            <TabsList>
              <TabsTrigger value="table">
                <Table2 className="h-3.5 w-3.5" /> Table
              </TabsTrigger>
              <TabsTrigger value="board">
                <Kanban className="h-3.5 w-3.5" /> Board
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </div>
      </Card>

      {isLoading ? (
        <TableSkeleton rows={6} />
      ) : isError ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : (data?.items.length ?? 0) === 0 ? (
        <EmptyState
          icon={<Columns3 className="h-5 w-5" />}
          title={activeFilterCount > 0 ? "No applications match these filters" : "No applications tracked yet"}
          description={
            activeFilterCount > 0
              ? "Try clearing the filters to see every tracked application."
              : "When you submit an application manually, record it here to track its status, follow-ups and notes."
          }
          action={
            activeFilterCount > 0 ? (
              <Button variant="outline" size="sm" onClick={reset}>
                Clear filters
              </Button>
            ) : (
              <div className="flex flex-wrap justify-center gap-2">
                <Button size="sm" onClick={() => setTrackOpen(true)}>
                  <Plus className="h-3.5 w-3.5" /> Track a job
                </Button>
                <Button variant="outline" size="sm" asChild>
                  <Link href="/shortlist">Go to shortlist</Link>
                </Button>
              </div>
            )
          }
        />
      ) : view === "table" ? (
        <>
          <Card className="overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Job</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Applied</TableHead>
                  <TableHead>Follow-up</TableHead>
                  <TableHead>Resume</TableHead>
                  <TableHead>Notes</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.items.map((application) => (
                  <ApplicationRow key={application.id} application={application} />
                ))}
              </TableBody>
            </Table>
          </Card>
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
      ) : (
        <>
          <ApplicationBoard applications={data?.items ?? []} />
          <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
            <p>
              Showing {data?.items.length ?? 0} of {data?.total ?? 0} tracked applications.
            </p>
            {data && data.total > BOARD_PAGE_SIZE ? (
              <p>Board shows the latest {BOARD_PAGE_SIZE}; use filters to narrow the list.</p>
            ) : null}
            <p className="inline-flex items-center gap-1">
              <Check className="h-3.5 w-3.5 text-emerald-600" /> Click a card to edit or move it.
            </p>
          </div>
        </>
      )}

      <TrackJobDialog open={trackOpen} onOpenChange={setTrackOpen} />
    </div>
  );
}
