"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState, ReactNode } from "react";
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
  // I3 (final review fix round): the Approvals page's 15-second poll
  // (usePolling(refetch, 15000) in approvals/layout.tsx) can race the
  // real post-decision refetch a decision's own submit() triggers. If an
  // older poll's GET /api/approvals is still in flight when a newer
  // refetch (e.g. right after approving a case) already applied its own
  // response, the older response can land afterward and resurrect the
  // just-resolved case for up to 15 seconds. This sequence-number guard
  // ensures only the most-recently-INITIATED fetch's response is ever
  // applied, no matter what order the responses actually arrive in.
  const latestSequenceRef = useRef(0);

  const refetch = useCallback(() => {
    const sequence = ++latestSequenceRef.current;
    return getApprovals()
      .then((c) => {
        if (sequence !== latestSequenceRef.current) return;
        setCases(c);
        setStatus("ready");
      })
      .catch(() => {
        if (sequence !== latestSequenceRef.current) return;
        setStatus("error");
      });
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
