"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { AppShell } from "@/components/app-shell";
import { ApprovalInboxView } from "@/components/approval-inbox-view";
import { ApprovalQueueProvider, useApprovalQueue } from "@/lib/approval-queue-context";
import { getSession } from "@/lib/api/auth";
import { useRequireSession } from "@/lib/use-require-session";
import { usePolling } from "@/lib/use-polling";

type Role = "circulation_staff" | "room_booking_staff" | "ill_coordinator" | "branch_manager";

function TwoPane({ children }: { children: React.ReactNode }) {
  useRequireSession();
  const { cases, status, resolvingCaseId, refetch } = useApprovalQueue();
  const pathname = usePathname();
  usePolling(refetch, 15000);
  const activeCaseId = pathname.startsWith("/approvals/") ? decodeURIComponent(pathname.slice("/approvals/".length)) : null;
  const [session, setSession] = useState<{ role: string; caseReviewRole: string | null } | null>(null);

  useEffect(() => {
    document.title = "Stacks | Approvals";
  }, []);

  useEffect(() => {
    getSession().then(setSession).catch(() => {});
  }, []);

  return (
    <AppShell
      role={(session?.role ?? "branch_manager") as Role}
      tenantName="Central Branch"
      pendingCounts={{ approvals: cases.length }}
      activeRoute="/approvals"
      caseReviewRole={session?.caseReviewRole ?? null}
    >
      <div className="flex gap-4">
        <div className="w-64 shrink-0 border-r pr-4" style={{ borderColor: "var(--color-border)" }}>
          <ApprovalInboxView cases={cases} status={status} activeCaseId={activeCaseId} resolvingCaseId={resolvingCaseId} />
        </div>
        <div className="flex-1">{children}</div>
      </div>
    </AppShell>
  );
}

export default function ApprovalsLayout({ children }: { children: React.ReactNode }) {
  return (
    <ApprovalQueueProvider>
      <TwoPane>{children}</TwoPane>
    </ApprovalQueueProvider>
  );
}
