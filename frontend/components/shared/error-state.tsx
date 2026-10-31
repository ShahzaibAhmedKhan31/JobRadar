"use client";

import { AlertTriangle, RotateCcw, ServerCrash } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";
import { errorMessage } from "@/lib/hooks";

interface ErrorStateProps {
  error: unknown;
  onRetry?: () => void;
  title?: string;
}

/** True when the browser never reached the API (backend down, wrong port). */
function isUnreachable(error: unknown): boolean {
  return error instanceof ApiError && error.status === 0;
}

function backendHint() {
  return (
    <div className="mt-3 space-y-2 rounded-lg border border-rose-200 bg-white/70 p-3">
      <p className="text-xs font-medium text-rose-900">
        The frontend is running, but FastAPI is not answering on port 8000. Start it in a
        second terminal:
      </p>
      <pre className="overflow-x-auto rounded-md bg-rose-950/90 px-3 py-2 font-mono text-[11px] leading-relaxed text-rose-50">
{`cd backend
.\\.venv\\Scripts\\Activate.ps1
uvicorn app.main:app --reload --port 8000`}
      </pre>
      <p className="text-[11px] text-rose-800/90">
        If it exits immediately, run{" "}
        <code className="rounded bg-rose-100 px-1 py-0.5 font-mono">
          python scripts\\preflight.py
        </code>{" "}
        from the repository root — it checks the database, migrations and port 8000 for you.
      </p>
    </div>
  );
}

export function ErrorState({ error, onRetry, title = "Could not load data" }: ErrorStateProps) {
  const unreachable = isUnreachable(error);
  return (
    <div className="flex flex-col items-start gap-3 rounded-xl border border-rose-200 bg-rose-50/60 p-5">
      <div className="flex items-start gap-3">
        {unreachable ? (
          <ServerCrash className="mt-0.5 h-5 w-5 shrink-0 text-rose-600" />
        ) : (
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-rose-600" />
        )}
        <div className="min-w-0 space-y-1">
          <p className="text-sm font-semibold text-rose-900">
            {unreachable ? "Backend not reachable" : title}
          </p>
          <p className="text-sm text-rose-800/80">{errorMessage(error)}</p>
        </div>
      </div>
      {unreachable ? backendHint() : null}
      {onRetry ? (
        <Button size="sm" variant="outline" onClick={onRetry}>
          <RotateCcw className="h-3.5 w-3.5" /> Try again
        </Button>
      ) : null}
    </div>
  );
}
