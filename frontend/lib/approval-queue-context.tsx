"use client";

import { createContext, useCallback, useContext, useEffect, useState, ReactNode } from "react";
import { ApprovalCase } from "@/lib/api/types";
import { getApprovals } from "@/lib/api/approvals";

type Status = "loading" | "ready" | "error";

interface ApprovalQueueContextValue {
  cases: ApprovalCase[];
  status: Status;
  resolvingCaseId: string | null;
  setResolvingCaseId: (id: string | null) => void;
  refetch: () => Promise<void>;
}

const ApprovalQueueContext = createContext<ApprovalQueueContextValue | null>(null);

export function ApprovalQueueProvider({ children }: { children: ReactNode }) {
  const [cases, setCases] = useState<ApprovalCase[]>([]);
  const [status, setStatus] = useState<Status>("loading");
  const [resolvingCaseId, setResolvingCaseId] = useState<string | null>(null);

  const refetch = useCallback(() => {
    return getApprovals()
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
    <ApprovalQueueContext.Provider value={{ cases, status, resolvingCaseId, setResolvingCaseId, refetch }}>
      {children}
    </ApprovalQueueContext.Provider>
  );
}

export function useApprovalQueue(): ApprovalQueueContextValue {
  const ctx = useContext(ApprovalQueueContext);
  if (!ctx) {
    throw new Error("useApprovalQueue must be used within an ApprovalQueueProvider");
  }
  return ctx;
}
