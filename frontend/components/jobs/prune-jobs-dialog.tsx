"use client";

import { Loader2, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { usePruneJobs } from "@/lib/hooks";

/**
 * Removing scraped listings that turned out to be irrelevant.
 *
 * Listings a provider delivered are not the user's work — but a shortlist entry
 * or an application is, so the API keeps those rows whatever the scope. Say so
 * before deleting, and never make this a one-click accident.
 */
export function PruneJobsDialog({
  open,
  onOpenChange,
  count,
  sources,
  includeTestData = false,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** How many listings the current view says are stored. */
  count?: number;
  /** Limit the cleanup to these sources (default: every source). */
  sources?: string[];
  includeTestData?: boolean;
}) {
  const pruneMutation = usePruneJobs();

  const remove = () => {
    pruneMutation.mutate(
      {
        ...(sources && sources.length > 0 ? { sources } : {}),
        include_test_data: includeTestData,
      },
      { onSuccess: () => onOpenChange(false) },
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Remove stored listings?</DialogTitle>
          <DialogDescription>
            This permanently deletes{" "}
            {count ? (
              <>
                <strong>{count}</strong> stored listing{count === 1 ? "" : "s"}
              </>
            ) : (
              "the stored listings"
            )}{" "}
            that do not match your current filters. Listings you shortlisted or applied to
            are always kept, and a later refresh can fetch the rest again.
          </DialogDescription>
        </DialogHeader>
        <p className="rounded-lg border border-amber-200 bg-amber-50/70 p-3 text-xs text-amber-900">
          Use this when the database holds results from a different search — for example a
          US-wide feed from before a location was configured. Sample rows are not touched here.
        </p>
        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)} disabled={pruneMutation.isPending}>
            Cancel
          </Button>
          <Button variant="destructive" onClick={remove} disabled={pruneMutation.isPending}>
            {pruneMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Trash2 className="h-4 w-4" />
            )}
            Remove {count ? `${count} ` : ""}listing{count === 1 ? "" : "s"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
