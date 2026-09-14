"use client";

import { useEffect, useState } from "react";
import { IllQueueView } from "@/components/ill-queue-view";
import { IllRequest } from "@/lib/api/types";
import { getIllQueue } from "@/lib/api/ill-queue";

export default function IllQueuePage() {
  const [requests, setRequests] = useState<IllRequest[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    document.title = "Stacks | ILL Queue";
  }, []);

  useEffect(() => {
    getIllQueue()
      .then((r) => {
        setRequests(r);
        setStatus("ready");
      })
      .catch(() => setStatus("error"));
  }, []);

  return <IllQueueView requests={requests} status={status} />;
}
