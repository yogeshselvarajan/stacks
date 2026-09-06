"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { HomeView } from "@/components/home-view";
import { getApprovals } from "@/lib/api/approvals";

export default function HomePage() {
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [pendingByTier, setPendingByTier] = useState<{ GREEN: number; YELLOW: number; RED: number } | null>(null);

  useEffect(() => {
    getApprovals()
      .then((cases) => {
        const counts = { GREEN: 0, YELLOW: 0, RED: 0 };
        for (const c of cases) counts[c.tier] += 1;
        setPendingByTier(counts);
        setStatus("ready");
      })
      .catch(() => setStatus("error"));
  }, []);

  return (
    <AppShell
      role="branch_manager"
      pendingCounts={{ approvals: (pendingByTier?.YELLOW ?? 0) + (pendingByTier?.RED ?? 0) }}
      activeRoute="/"
    >
      <HomeView status={status} pendingByTier={pendingByTier} lastSweepSummary={null} />
    </AppShell>
  );
}
