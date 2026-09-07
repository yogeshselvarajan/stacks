"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { AuditTrailView } from "@/components/audit-trail-view";
import { AuditEntry } from "@/lib/api/types";
import { getAuditList } from "@/lib/api/audit";

export default function AuditPage() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    getAuditList()
      .then((e) => {
        setEntries(e);
        setStatus("ready");
      })
      .catch(() => setStatus("error"));
  }, []);

  return (
    <AppShell role="branch_manager" tenantName="Central Branch" pendingCounts={{ approvals: 0 }} activeRoute="/audit">
      <AuditTrailView entries={entries} status={status} mode="list" />
    </AppShell>
  );
}
