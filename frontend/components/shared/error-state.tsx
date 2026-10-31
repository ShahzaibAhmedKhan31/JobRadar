"use client";

import { useEffect, useRef, useState } from "react";
import { AlertTriangle, Loader2, RotateCcw, ServerCrash } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";
import { errorMessage } from "@/lib/hooks";

interface ErrorStateProps {
  error: unknown;
  onRetry?: () => void;
  title?: string;
}

/** Auto-retry cadence while the backend is unreachable. */
const RETRY_INTERVAL_MS = 5_000;
const MAX_AUTO_RETRIES = 24; // ~2 minutes, then leave the manual button

/** True when the browser never reached the API (backend down, wrong port). */
function isUnreachable(error: unknown): boolean {
  return error instanceof ApiError && error.status === 0;
}

function backendHint() {
  return (
    <div className="mt-3 w-full space-y-2 rounded-lg border border-rose-200 bg-white/70 p-3">
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
        Check it independently with{" "}
        <code className="rounded bg-rose-100 px-1 py-0.5 font-mono">
          curl.exe http://127.0.0.1:8000/health
        </code>
        , or run{" "}
        <code className="rounded bg-rose-100 px-1 py-0.5 font-mono">
          python scripts\\preflight.py
        </code>{" "}
        from the repository root to test the database, migrations and port at once.
      </p>
    </div>
  );
}

export function ErrorState({ error, onRetry, title = "Could not load data" }: ErrorStateProps) {
  const unreachable = isUnreachable(error);
  const [attempts, setAttempts] = useState(0);
  const [retrying, setRetrying] = useState(false);

  // Keep the latest callback without restarting the timer on every render.
  const retryRef = useRef(onRetry);
  useEffect(() => {
    retryRef.current = onRetry;
  }, [onRetry]);

  // Heal automatically: when the API was simply not up yet, poll until it
  // answers instead of making the user reload the page.
  useEffect(() => {
    if (!unreachable || !onRetry || attempts >= MAX_AUTO_RETRIES) return;
    const timer = setTimeout(() => {
      setAttempts((count) => count + 1);
      setRetrying(true);
      retryRef.current?.();
      setRetrying(false);
    }, RETRY_INTERVAL_MS);
    return () => clearTimeout(timer);
  }, [unreachable, onRetry, attempts]);

  const autoRetrying = unreachable && attempts < MAX_AUTO_RETRIES;

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
      <div className="flex items-center gap-3">
        {onRetry ? (
          <Button size="sm" variant="outline" onClick={onRetry}>
            <RotateCcw className="h-3.5 w-3.5" /> Try again
          </Button>
        ) : null}
        {autoRetrying ? (
          <span className="inline-flex items-center gap-1.5 text-[11px] text-rose-800/80">
            {retrying ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <Loader2 className="h-3 w-3" />
            )}
            Retrying automatically every {RETRY_INTERVAL_MS / 1000}s — this panel clears as
            soon as the API answers.
          </span>
        ) : null}
      </div>
    </div>
  );
}
