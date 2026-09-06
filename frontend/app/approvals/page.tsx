"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { ApprovalInboxView } from "@/components/approval-inbox-view";
import { ApprovalCase } from "@/lib/api/types";
import { getApprovals, submitDecision } from "@/lib/api/approvals";

export default function ApprovalsPage() {
  const [cases, setCases] = useState<ApprovalCase[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [resolvingCaseId, setResolvingCaseId] = useState<string | null>(null);

  // Reused for both the mount-time load and the post-decision refetch.
  // Deliberately does not set status to "loading" synchronously (that
  // would fire inside the effect body below and trip
  // react-hooks/set-state-in-effect) -- status only changes inside the
  // resolved/rejected promise callback, same pattern as the Home screen.
  function fetchApprovals() {
    return getApprovals()
      .then((c) => {
        setCases(c);
        setStatus("ready");
      })
      .catch(() => setStatus("error"));
  }

  useEffect(() => {
    fetchApprovals();
  }, []);

  async function handleResolve(caseId: string, action: "approve" | "decline") {
    setResolvingCaseId(caseId);
    try {
      await submitDecision(caseId, { action });
      await fetchApprovals();
    } finally {
      setResolvingCaseId(null);
    }
  }

  return (
    <AppShell role="branch_manager" pendingCounts={{ approvals: cases.length }} activeRoute="/approvals">
      <ApprovalInboxView cases={cases} status={status} onResolve={handleResolve} resolvingCaseId={resolvingCaseId} />
    </AppShell>
  );
}
