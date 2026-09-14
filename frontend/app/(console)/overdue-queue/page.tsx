"use client";

import { useEffect, useState } from "react";
import { OverdueQueueView } from "@/components/overdue-queue-view";
import { OverdueCase } from "@/lib/api/types";
import { getOverdueQueue } from "@/lib/api/overdue-queue";

export default function OverdueQueuePage() {
  const [cases, setCases] = useState<OverdueCase[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    document.title = "Stacks | Overdue";
  }, []);

  useEffect(() => {
    getOverdueQueue()
      .then((c) => {
        setCases(c);
        setStatus("ready");
      })
      .catch(() => setStatus("error"));
  }, []);

  return <OverdueQueueView cases={cases} status={status} />;
}
