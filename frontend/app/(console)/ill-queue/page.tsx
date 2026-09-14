"use client";

import { useCallback, useEffect, useState } from "react";
import { IllQueueView } from "@/components/ill-queue-view";
import { NewIllRequestForm } from "@/components/new-ill-request-form";
import { IllRequest } from "@/lib/api/types";
import { getIllQueue } from "@/lib/api/ill-queue";

export default function IllQueuePage() {
  const [requests, setRequests] = useState<IllRequest[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    document.title = "Stacks | ILL Queue";
  }, []);

  const refetch = useCallback(() => {
    getIllQueue()
      .then((r) => {
        setRequests(r);
        setStatus("ready");
      })
      .catch(() => setStatus("error"));
  }, []);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return (
    <>
      <NewIllRequestForm onCreated={refetch} />
      <IllQueueView requests={requests} status={status} />
    </>
  );
}
