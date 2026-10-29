"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { ActivityPoint } from "@/types";

function formatLabel(value: string): string {
  const date = new Date(`${value}T00:00:00Z`);
  return new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "short" }).format(date);
}

export function ActivityChart({ points }: { points: ActivityPoint[] }) {
  const data = points.map((point) => ({
    ...point,
    label: formatLabel(point.date),
  }));

  return (
    <div className="h-[260px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
          <defs>
            <linearGradient id="jobs-gradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#0f766e" stopOpacity={0.28} />
              <stop offset="100%" stopColor="#0f766e" stopOpacity={0.02} />
            </linearGradient>
            <linearGradient id="applications-gradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#0284c7" stopOpacity={0.22} />
              <stop offset="100%" stopColor="#0284c7" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
          <XAxis
            dataKey="label"
            tickLine={false}
            axisLine={false}
            tick={{ fontSize: 11, fill: "#64748b" }}
            interval="preserveStartEnd"
            minTickGap={16}
          />
          <YAxis
            allowDecimals={false}
            tickLine={false}
            axisLine={false}
            tick={{ fontSize: 11, fill: "#64748b" }}
            width={40}
          />
          <Tooltip
            contentStyle={{
              borderRadius: 10,
              border: "1px solid #e2e8f0",
              boxShadow: "0 12px 30px -16px rgba(15,23,42,.4)",
              fontSize: 12,
            }}
            labelStyle={{ fontWeight: 600, color: "#0f172a" }}
          />
          <Area
            type="monotone"
            dataKey="jobs_discovered"
            name="Jobs discovered"
            stroke="#0f766e"
            strokeWidth={2}
            fill="url(#jobs-gradient)"
            dot={false}
            activeDot={{ r: 3 }}
          />
          <Area
            type="monotone"
            dataKey="applications_submitted"
            name="Applications submitted"
            stroke="#0284c7"
            strokeWidth={2}
            fill="url(#applications-gradient)"
            dot={false}
            activeDot={{ r: 3 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
