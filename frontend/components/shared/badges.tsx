import { Badge } from "@/components/ui/badge";
import { EXPERIENCE_LABELS, PRIORITY_META, STATUS_META, WORK_ARRANGEMENT_LABELS } from "@/lib/constants";
import { cn } from "@/lib/utils";
import type { ApplicationStatus, ExperienceLevel, Priority, WorkArrangement } from "@/types";

export function SourceBadge({ label, testData }: { label: string; testData?: boolean }) {
  return (
    <Badge variant="outline" className="gap-1 border-border/80 text-foreground/70">
      {label}
      {testData ? <span className="text-[10px] uppercase text-amber-600">sample</span> : null}
    </Badge>
  );
}

export function ArrangementBadge({ value }: { value: WorkArrangement }) {
  if (value === "unknown") return null;
  return <Badge variant="muted">{WORK_ARRANGEMENT_LABELS[value]}</Badge>;
}

export function ExperienceBadge({ value }: { value: ExperienceLevel }) {
  if (value === "unknown") return null;
  return (
    <Badge variant="secondary" className="font-normal">
      {EXPERIENCE_LABELS[value]}
    </Badge>
  );
}

export function StatusBadge({ status }: { status: ApplicationStatus }) {
  const meta = STATUS_META[status];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium",
        meta.badge,
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", meta.dot)} />
      {meta.label}
    </span>
  );
}

export function PriorityBadge({ priority }: { priority: Priority }) {
  const meta = PRIORITY_META[priority];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium",
        meta.badge,
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", meta.dot)} />
      {meta.label}
    </span>
  );
}
