import Link from "next/link";
import { Compass } from "lucide-react";

import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-5 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-full bg-muted text-muted-foreground">
        <Compass className="h-7 w-7" />
      </div>
      <div className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
          404
        </p>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">
          This page is off the radar
        </h1>
        <p className="mx-auto max-w-md text-sm text-muted-foreground">
          The route you opened does not exist. Head back to the dashboard to review your
          metrics, or jump straight into job discovery.
        </p>
      </div>
      <div className="flex flex-wrap items-center justify-center gap-2">
        <Button asChild>
          <Link href="/">Back to dashboard</Link>
        </Button>
        <Button asChild variant="outline">
          <Link href="/discover">Discover jobs</Link>
        </Button>
      </div>
    </div>
  );
}
