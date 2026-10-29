"use client";

import { useState } from "react";
import {
  ExternalLink,
  MoreHorizontal,
  Pencil,
  Trash2,
} from "lucide-react";

import { ApplicationEditDialog } from "@/components/applications/application-edit-dialog";
import { StatusBadge } from "@/components/shared/badges";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { TableCell, TableRow } from "@/components/ui/table";
import { APPLICATION_STATUS_ORDER, STATUS_META } from "@/lib/constants";
import { useDeleteApplication, useUpdateApplication } from "@/lib/hooks";
import { formatDate } from "@/lib/utils";
import type { Application, ApplicationStatus } from "@/types";

export function ApplicationRow({ application }: { application: Application }) {
  const [editOpen, setEditOpen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const updateMutation = useUpdateApplication();
  const deleteMutation = useDeleteApplication();

  return (
    <>
      <TableRow>
        <TableCell className="min-w-[240px]">
          <p className="font-medium text-foreground">{application.job.title}</p>
          <p className="text-xs text-muted-foreground">
            {application.job.company_name}
            {application.job.location ? ` · ${application.job.location}` : ""}
          </p>
        </TableCell>
        <TableCell>
          <div className="flex items-center gap-2">
            <StatusBadge status={application.status} />
            <Select
              value={application.status}
              onValueChange={(value) =>
                updateMutation.mutate({
                  applicationId: application.id,
                  status: value as ApplicationStatus,
                })
              }
            >
              <SelectTrigger
                className="h-7 w-7 border-none bg-transparent p-0 shadow-none [&>svg]:h-3.5 [&>svg]:w-3.5"
                aria-label="Change status"
              >
                <SelectValue className="sr-only" />
              </SelectTrigger>
              <SelectContent align="end">
                {APPLICATION_STATUS_ORDER.map((value) => (
                  <SelectItem key={value} value={value}>
                    {STATUS_META[value].label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </TableCell>
        <TableCell className="whitespace-nowrap text-sm">
          {formatDate(application.application_date)}
        </TableCell>
        <TableCell className="whitespace-nowrap text-sm">
          {formatDate(application.follow_up_date)}
        </TableCell>
        <TableCell className="max-w-[140px] truncate text-xs text-muted-foreground">
          {application.resume_reference ?? "—"}
        </TableCell>
        <TableCell className="max-w-[220px]">
          <p className="truncate text-xs text-muted-foreground" title={application.notes ?? ""}>
            {application.notes || "—"}
          </p>
        </TableCell>
        <TableCell className="text-right">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon-sm" aria-label="Application actions">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => setEditOpen(true)}>
                <Pencil className="h-3.5 w-3.5" /> Edit details
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <a href={application.job.job_url} target="_blank" rel="noopener noreferrer">
                  <ExternalLink className="h-3.5 w-3.5" /> Open listing
                </a>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem destructive onClick={() => setConfirmDelete(true)}>
                <Trash2 className="h-3.5 w-3.5" /> Delete record
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </TableCell>
      </TableRow>

      <ApplicationEditDialog application={application} open={editOpen} onOpenChange={setEditOpen} />

      <Dialog open={confirmDelete} onOpenChange={setConfirmDelete}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Delete tracking record?</DialogTitle>
            <DialogDescription>
              This removes your application notes and history for {application.job.title}. The job
              listing itself is kept.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmDelete(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              disabled={deleteMutation.isPending}
              onClick={() =>
                deleteMutation.mutate(application.id, {
                  onSettled: () => setConfirmDelete(false),
                })
              }
            >
              <Trash2 className="h-3.5 w-3.5" /> Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
