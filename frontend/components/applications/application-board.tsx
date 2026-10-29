"use client";

import { useState } from "react";
import { ExternalLink, Pencil } from "lucide-react";

import { ApplicationEditDialog } from "@/components/applications/application-edit-dialog";
import { StatusBadge } from "@/components/shared/badges";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { APPLICATION_STATUS_ORDER, STATUS_META } from "@/lib/constants";
import { formatDate } from "@/lib/utils";
import type { Application } from "@/types";

export function ApplicationBoard({ applications }: { applications: Application[] }) {
  const [editing, setEditing] = useState<Application | null>(null);
  const [editOpen, setEditOpen] = useState(false);

  return (
    <>
      <div className="grid gap-4 overflow-x-auto md:grid-cols-2 xl:grid-cols-4 2xl:grid-cols-7">
        {APPLICATION_STATUS_ORDER.map((status) => {
          const items = applications.filter((entry) => entry.status === status);
          const meta = STATUS_META[status];
          return (
            <div
              key={status}
              className="flex min-w-[220px] flex-col rounded-xl border border-border bg-card/70"
            >
              <div className="flex items-center justify-between border-b border-border px-3 py-2.5">
                <div className="flex items-center gap-2">
                  <span className={`h-2 w-2 rounded-full ${meta.dot}`} />
                  <p className="text-xs font-semibold uppercase tracking-wide text-foreground/80">
                    {meta.label}
                  </p>
                </div>
                <span className="rounded-full bg-muted px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
                  {items.length}
                </span>
              </div>
              <div className="flex flex-1 flex-col gap-2 p-2">
                {items.length === 0 ? (
                  <p className="px-2 py-6 text-center text-xs text-muted-foreground">
                    Nothing here yet
                  </p>
                ) : (
                  items.map((application) => (
                    <Card key={application.id} className="space-y-2 p-3 shadow-none">
                      <button
                        type="button"
                        className="line-clamp-2 text-left text-sm font-medium hover:text-primary"
                        onClick={() => {
                          setEditing(application);
                          setEditOpen(true);
                        }}
                      >
                        {application.job.title}
                      </button>
                      <p className="truncate text-xs text-muted-foreground">
                        {application.job.company_name}
                      </p>
                      <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-muted-foreground">
                        {application.application_date ? (
                          <span>Applied {formatDate(application.application_date)}</span>
                        ) : (
                          <span>Not applied yet</span>
                        )}
                        {application.follow_up_date ? (
                          <span>· Follow up {formatDate(application.follow_up_date)}</span>
                        ) : null}
                      </div>
                      <div className="flex items-center justify-between gap-2">
                        <StatusBadge status={application.status} />
                        <div className="flex items-center gap-0.5">
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            aria-label="Edit application"
                            onClick={() => {
                              setEditing(application);
                              setEditOpen(true);
                            }}
                          >
                            <Pencil className="h-3.5 w-3.5" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            aria-label="Open original listing"
                            asChild
                          >
                            <a
                              href={application.job.job_url}
                              target="_blank"
                              rel="noopener noreferrer"
                            >
                              <ExternalLink className="h-3.5 w-3.5" />
                            </a>
                          </Button>
                        </div>
                      </div>
                    </Card>
                  ))
                )}
              </div>
            </div>
          );
        })}
      </div>

      <ApplicationEditDialog application={editing} open={editOpen} onOpenChange={setEditOpen} />
    </>
  );
}
