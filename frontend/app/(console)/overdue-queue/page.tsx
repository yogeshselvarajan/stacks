"use client";

import { useCallback, useEffect, useState } from "react";
import { OverdueQueueView } from "@/components/overdue-queue-view";
import { NewOverdueCaseForm } from "@/components/new-overdue-case-form";
import { ApiError, OverdueCase } from "@/lib/api/types";
import { getOverdueQueue } from "@/lib/api/overdue-queue";

export default function OverdueQueuePage() {
  const [cases, setCases] = useState<OverdueCase[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error" | "forbidden">("loading");

  useEffect(() => {
    document.title = "Stacks | Overdue";
  }, []);

  const refetch = useCallback(() => {
    getOverdueQueue()
      .then((c) => {
        setCases(c);
        setStatus("ready");
      })
      .catch((err) => setStatus(err instanceof ApiError && err.status === 403 ? "forbidden" : "error"));
  }, []);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return (
    <>
      <NewOverdueCaseForm onCreated={refetch} />
      <OverdueQueueView cases={cases} status={status} />
    </>
  );
}
