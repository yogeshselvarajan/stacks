"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { IllQueueView } from "@/components/ill-queue-view";
import { IllRequest } from "@/lib/api/types";
import { getIllQueue } from "@/lib/api/ill-queue";

export default function IllQueuePage() {
  const [requests, setRequests] = useState<IllRequest[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    getIllQueue()
      .then((r) => {
        setRequests(r);
        setStatus("ready");
      })
      .catch(() => setStatus("error"));
  }, []);

  return (
    <AppShell role="ill_coordinator" pendingCounts={{ approvals: 0 }} activeRoute="/ill-queue">
      <IllQueueView requests={requests} status={status} />
    </AppShell>
  );
}
