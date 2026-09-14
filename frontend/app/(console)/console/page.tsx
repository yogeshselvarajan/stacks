"use client";

import { useEffect, useState } from "react";
import { HomeView } from "@/components/home-view";
import { getApprovals } from "@/lib/api/approvals";
import { getAuditList } from "@/lib/api/audit";
import { AuditEntry } from "@/lib/api/types";
import { usePolling } from "@/lib/use-polling";

function isToday(timestamp: string): boolean {
  const entryDate = new Date(timestamp);
  const now = new Date();
  return (
    entryDate.getUTCFullYear() === now.getUTCFullYear() &&
    entryDate.getUTCMonth() === now.getUTCMonth() &&
    entryDate.getUTCDate() === now.getUTCDate()
  );
}

export default function ConsolePage() {
  useEffect(() => {
    document.title = "Stacks | Home";
  }, []);

  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [pendingByTier, setPendingByTier] = useState<{ GREEN: number; YELLOW: number; RED: number } | null>(null);
  const [resolvedTodayCount, setResolvedTodayCount] = useState<number | null>(null);
  const [recentActivity, setRecentActivity] = useState<AuditEntry[] | null>(null);

  function fetchHomeData() {
    getApprovals()
      .then((cases) => {
        const counts = { GREEN: 0, YELLOW: 0, RED: 0 };
        for (const c of cases) counts[c.tier] += 1;
        setPendingByTier(counts);
        setStatus("ready");
      })
      .catch(() => setStatus("error"));

    getAuditList()
      .then((audit) => {
        const sorted = [...audit].sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
        setRecentActivity(sorted.slice(0, 5));
        setResolvedTodayCount(audit.filter((e) => isToday(e.timestamp)).length);
      })
      .catch(() => {
        // Supplementary data -- a failure here should not block the page or
        // hide the pending-tier counts, which is the number that actually
        // matters. resolvedTodayCount/recentActivity simply stay null, and
        // HomeView's ready-state rendering already handles null for both.
      });
  }

  useEffect(() => {
    fetchHomeData();
  }, []);

  usePolling(fetchHomeData, 15000);

  return (
    <HomeView
      status={status}
      pendingByTier={pendingByTier}
      lastSweepSummary={null}
      resolvedTodayCount={resolvedTodayCount}
      recentActivity={recentActivity}
    />
  );
}
