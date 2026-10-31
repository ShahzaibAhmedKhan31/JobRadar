"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { Toaster } from "sonner";

import { ApiError } from "@/lib/api";

/** A refused connection almost always means uvicorn is starting or restarting. */
function isUnreachable(error: unknown): boolean {
  return error instanceof ApiError && error.status === 0;
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 15_000,
            // Real API errors (404/422/500) deserve one retry at most;
            // "connection refused" is transient while the backend boots or
            // reloads, so keep trying for a few seconds instead of painting a
            // dead screen the user has to refresh by hand.
            retry: (failureCount, error) =>
              isUnreachable(error) ? failureCount < 5 : failureCount < 1,
            retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 8000),
            refetchOnWindowFocus: true,
            refetchOnReconnect: true,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <Toaster richColors closeButton position="top-right" />
    </QueryClientProvider>
  );
}
