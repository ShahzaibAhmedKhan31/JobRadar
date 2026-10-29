"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  Bookmark,
  Columns3,
  ExternalLink,
  LayoutDashboard,
  Radar,
  Settings2,
} from "lucide-react";

import { getHealth } from "@/lib/api";
import { NAV_ITEMS } from "@/lib/constants";
import { cn } from "@/lib/utils";

const ICONS = {
  "layout-dashboard": LayoutDashboard,
  radar: Radar,
  bookmark: Bookmark,
  kanban: Columns3,
  settings: Settings2,
} as const;

export function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-3">
      <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-teal-400/90 to-emerald-600 text-white shadow-sm">
        <Radar className="h-5 w-5" />
      </div>
      {!compact ? (
        <div className="leading-tight">
          <p className="text-sm font-semibold tracking-tight text-white">JobRadar</p>
          <p className="text-[11px] text-sidebar-muted">Personal job search</p>
        </div>
      ) : null}
    </div>
  );
}

export function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  return (
    <nav className="flex flex-col gap-1">
      {NAV_ITEMS.map((item) => {
        const Icon = ICONS[item.icon];
        const active =
          item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            className={cn(
              "group flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
              active
                ? "bg-white/10 text-white shadow-inner"
                : "text-sidebar-muted hover:bg-white/5 hover:text-white",
            )}
          >
            <Icon
              className={cn(
                "h-4 w-4 shrink-0",
                active ? "text-sidebar-accent" : "text-sidebar-muted group-hover:text-white",
              )}
            />
            <span className="flex-1">{item.label}</span>
            {active ? <span className="h-1.5 w-1.5 rounded-full bg-sidebar-accent" /> : null}
          </Link>
        );
      })}
    </nav>
  );
}

function ApiStatus() {
  const { data, isError, isLoading } = useQuery({
    queryKey: ["health"],
    queryFn: getHealth,
    refetchInterval: 60_000,
    retry: 0,
  });

  const healthy = !isError && data?.status === "ok";
  return (
    <div className="rounded-lg border border-white/10 bg-white/5 px-3 py-2.5">
      <div className="flex items-center gap-2">
        <span
          className={cn(
            "h-2 w-2 rounded-full",
            isLoading ? "bg-slate-400" : healthy ? "bg-emerald-400" : "bg-rose-400",
          )}
        />
        <p className="text-xs font-medium text-white/90">
          {isLoading ? "Checking API…" : healthy ? "API connected" : "API unavailable"}
        </p>
      </div>
      <p className="mt-1 text-[11px] text-sidebar-muted">
        {healthy
          ? `v${data?.version} · PostgreSQL ${data?.database}`
          : "Start FastAPI on port 8000"}
      </p>
    </div>
  );
}

export function Sidebar() {
  return (
    <aside className="sticky top-0 hidden h-screen w-[264px] shrink-0 flex-col justify-between bg-sidebar px-4 py-6 lg:flex">
      <div className="space-y-8">
        <div className="px-2">
          <Brand />
        </div>
        <div className="px-1">
          <p className="mb-2 px-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-sidebar-muted/70">
            Workspace
          </p>
          <NavLinks />
        </div>
      </div>
      <div className="space-y-3">
        <ApiStatus />
        <a
          href="/docs"
          target="_blank"
          rel="noreferrer"
          className="flex items-center justify-between rounded-lg px-3 py-2 text-xs text-sidebar-muted transition-colors hover:bg-white/5 hover:text-white"
        >
          <span className="flex items-center gap-2">
            <Activity className="h-3.5 w-3.5" /> API reference
          </span>
          <ExternalLink className="h-3.5 w-3.5" />
        </a>
        <p className="px-3 text-[10px] text-sidebar-muted/60">
          JobRadar MVP · local-first
        </p>
      </div>
    </aside>
  );
}
