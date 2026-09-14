"use client";

import { useEffect, useState } from "react";
import { AuditTrailView } from "@/components/audit-trail-view";
import { AuditEntry } from "@/lib/api/types";
import { getAuditList } from "@/lib/api/audit";

export default function AuditPage() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    document.title = "Stacks | Audit";
  }, []);

  useEffect(() => {
    getAuditList()
      .then((e) => {
        setEntries(e);
        setStatus("ready");
      })
      .catch(() => setStatus("error"));
  }, []);

  return <AuditTrailView entries={entries} status={status} mode="list" />;
}
