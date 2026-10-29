"use client";

import Link from "next/link";
import { ArrowUpRight } from "lucide-react";

import { STATUS_META } from "@/lib/constants";
import { formatNumber } from "@/lib/utils";
import type { StatusBreakdownItem } from "@/types";

export function StatusBreakdown({ items }: { items: StatusBreakdownItem[] }) {
  const total = items.reduce((sum, item) => sum + item.count, 0);

  return (
    <div className="space-y-3">
      {items.map((item) => {
        const meta = STATUS_META[item.status];
        const percentage = total > 0 ? Math.round((item.count / total) * 100) : 0;
        return (
          <div key={item.status} className="space-y-1.5">
            <div className="flex items-center justify-between text-sm">
              <span className="flex items-center gap-2 text-foreground/80">
                <span className={`h-2 w-2 rounded-full ${meta.dot}`} />
                {item.label}
              </span>
              <span className="tabular text-xs text-muted-foreground">
                {formatNumber(item.count)}
                {total > 0 ? ` · ${percentage}%` : ""}
              </span>
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
              <div
                className={`h-full rounded-full ${meta.dot}`}
                style={{ width: `${percentage}%` }}
              />
            </div>
          </div>
        );
      })}
      {total === 0 ? (
        <Link
          href="/discover"
          className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
        >
          Start by shortlisting a job <ArrowUpRight className="h-3 w-3" />
        </Link>
      ) : null}
    </div>
  );
}
