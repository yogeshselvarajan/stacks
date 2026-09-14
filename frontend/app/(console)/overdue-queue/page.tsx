"use client";

import { useCallback, useEffect, useState } from "react";
import { OverdueQueueView } from "@/components/overdue-queue-view";
import { NewOverdueCaseForm } from "@/components/new-overdue-case-form";
import { OverdueCase } from "@/lib/api/types";
import { getOverdueQueue } from "@/lib/api/overdue-queue";

export default function OverdueQueuePage() {
  const [cases, setCases] = useState<OverdueCase[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    document.title = "Stacks | Overdue";
  }, []);

  const refetch = useCallback(() => {
    getOverdueQueue()
      .then((c) => {
        setCases(c);
        setStatus("ready");
      })
      .catch(() => setStatus("error"));
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
