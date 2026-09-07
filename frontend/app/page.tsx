"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { HomeView } from "@/components/home-view";
import { getApprovals } from "@/lib/api/approvals";
import { getAuditList } from "@/lib/api/audit";
import { AuditEntry } from "@/lib/api/types";

function isToday(timestamp: string): boolean {
  const entryDate = new Date(timestamp);
  const now = new Date();
  return (
    entryDate.getUTCFullYear() === now.getUTCFullYear() &&
    entryDate.getUTCMonth() === now.getUTCMonth() &&
    entryDate.getUTCDate() === now.getUTCDate()
  );
}

export default function HomePage() {
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [pendingByTier, setPendingByTier] = useState<{ GREEN: number; YELLOW: number; RED: number } | null>(null);
  const [resolvedTodayCount, setResolvedTodayCount] = useState<number | null>(null);
  const [recentActivity, setRecentActivity] = useState<AuditEntry[] | null>(null);

  useEffect(() => {
    Promise.all([getApprovals(), getAuditList()])
      .then(([cases, audit]) => {
        const counts = { GREEN: 0, YELLOW: 0, RED: 0 };
        for (const c of cases) counts[c.tier] += 1;
        setPendingByTier(counts);

        const sorted = [...audit].sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
        setRecentActivity(sorted.slice(0, 5));
        setResolvedTodayCount(audit.filter((e) => isToday(e.timestamp)).length);

        setStatus("ready");
      })
      .catch(() => setStatus("error"));
  }, []);

  return (
    <AppShell
      role="branch_manager"
      tenantName="Central Branch"
      pendingCounts={{ approvals: (pendingByTier?.YELLOW ?? 0) + (pendingByTier?.RED ?? 0) }}
      activeRoute="/"
    >
      <HomeView
        status={status}
        pendingByTier={pendingByTier}
        lastSweepSummary={null}
        resolvedTodayCount={resolvedTodayCount}
        recentActivity={recentActivity}
      />
    </AppShell>
  );
}
