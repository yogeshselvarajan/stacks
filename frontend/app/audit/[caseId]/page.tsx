"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { AppShell } from "@/components/app-shell";
import { AuditTrailView } from "@/components/audit-trail-view";
import { AuditEntry } from "@/lib/api/types";
import { getAuditTrace } from "@/lib/api/audit";

export default function AuditTracePage() {
  const { caseId } = useParams<{ caseId: string }>();
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    getAuditTrace(caseId)
      .then((e) => {
        setEntries(e);
        setStatus("ready");
      })
      .catch(() => setStatus("error"));
  }, [caseId]);

  return (
    <AppShell role="branch_manager" tenantName="Central Branch" pendingCounts={{ approvals: 0 }} activeRoute="/audit">
      <AuditTrailView entries={entries} status={status} mode="trace" />
    </AppShell>
  );
}
