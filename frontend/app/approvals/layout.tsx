"use client";

import { usePathname } from "next/navigation";
import { AppShell } from "@/components/app-shell";
import { ApprovalInboxView } from "@/components/approval-inbox-view";
import { ApprovalQueueProvider, useApprovalQueue } from "@/lib/approval-queue-context";

function TwoPane({ children }: { children: React.ReactNode }) {
  const { cases, status, resolvingCaseId } = useApprovalQueue();
  const pathname = usePathname();
  const activeCaseId = pathname.startsWith("/approvals/") ? decodeURIComponent(pathname.slice("/approvals/".length)) : null;

  return (
    <AppShell role="branch_manager" tenantName="Central Branch" pendingCounts={{ approvals: cases.length }} activeRoute="/approvals">
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
