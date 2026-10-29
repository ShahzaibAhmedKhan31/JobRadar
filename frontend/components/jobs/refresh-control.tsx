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
import { useRefreshJobs, useSources } from "@/lib/hooks";

export function RefreshControl({ compact = false }: { compact?: boolean }) {
  const { data } = useSources();
  const refreshMutation = useRefreshJobs();
  const refreshable = (data?.sources ?? []).filter((source) => source.can_refresh);
  const pending = refreshMutation.isPending;

  const refreshAll = () => refreshMutation.mutate({});
  const refreshOne = (source: string) => refreshMutation.mutate({ sources: [source] });

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
        {pending ? "Refreshing…" : "Refresh sources"}
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
        <DropdownMenuContent align="end" className="w-60">
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
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
