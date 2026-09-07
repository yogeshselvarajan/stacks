"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ApprovalCaseDetail } from "@/components/approval-case-detail";
import { ApprovalCase } from "@/lib/api/types";
import { getApprovalCase, submitDecision } from "@/lib/api/approvals";
import { useApprovalQueue } from "@/lib/approval-queue-context";

export default function ApprovalCaseDetailPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const router = useRouter();
  const { setResolvingCaseId, resolvingCaseId, refetch } = useApprovalQueue();
  const [theCase, setCase] = useState<ApprovalCase | null>(null);
  const [actionStatus, setActionStatus] = useState<"idle" | "submitting" | "error">("idle");

  useEffect(() => {
    // Clear the previous case immediately so a navigation from case A to
    // case B never leaves A's data on screen (and submittable) while B is
    // still loading. Synchronous within the effect on purpose -- this is
    // not derived state, it's discarding stale state before a new fetch.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setCase(null);
    getApprovalCase(caseId).then(setCase);
  }, [caseId]);

  if (!theCase) return null;

  async function submit(action: "approve" | "decline" | "edit", extra?: { editedValue?: string; declineReason?: string }) {
    setActionStatus("submitting");
    setResolvingCaseId(caseId);
    try {
      await submitDecision(caseId, { action, ...extra });
      await refetch();
      router.push("/approvals");
    } catch {
      setActionStatus("error");
    } finally {
      setResolvingCaseId(null);
    }
  }

  return (
    <ApprovalCaseDetail
      case={theCase}
      actionStatus={actionStatus}
      resolving={resolvingCaseId === caseId}
      onApprove={() => submit("approve")}
      onDecline={(_id, reason) => submit("decline", { declineReason: reason })}
      onEdit={(_id, editedValue) => submit("edit", { editedValue })}
    />
  );
}
