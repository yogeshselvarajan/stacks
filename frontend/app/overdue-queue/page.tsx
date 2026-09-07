"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { OverdueQueueView } from "@/components/overdue-queue-view";
import { OverdueCase } from "@/lib/api/types";
import { getOverdueQueue } from "@/lib/api/overdue-queue";

export default function OverdueQueuePage() {
  const [cases, setCases] = useState<OverdueCase[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    getOverdueQueue()
      .then((c) => {
        setCases(c);
        setStatus("ready");
      })
      .catch(() => setStatus("error"));
  }, []);

  return (
    <AppShell role="circulation_staff" tenantName="Central Branch" pendingCounts={{ approvals: 0 }} activeRoute="/overdue-queue">
      <OverdueQueueView cases={cases} status={status} />
    </AppShell>
  );
}
