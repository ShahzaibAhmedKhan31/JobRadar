import type { Metadata } from "next";
import "@fontsource-variable/inter";
import "./globals.css";

import { AppShell } from "@/components/layout/app-shell";
import { Providers } from "@/app/providers";

export const metadata: Metadata = {
  title: {
    default: "JobRadar",
    template: "%s · JobRadar",
  },
  description:
    "Personal job discovery and application tracking — filter recent roles, shortlist the best matches and track every application.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-background font-sans text-foreground">
        <Providers>
          <AppShell>{children}</AppShell>
        </Providers>
      </body>
    </html>
  );
}
