"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { AppShell } from "@/components/app-shell";
import { ApprovalCaseDetail } from "@/components/approval-case-detail";
import { ApprovalCase } from "@/lib/api/types";
import { getApprovalCase, submitDecision } from "@/lib/api/approvals";

export default function ApprovalCaseDetailPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const router = useRouter();
  const [theCase, setCase] = useState<ApprovalCase | null>(null);
  const [actionStatus, setActionStatus] = useState<"idle" | "submitting" | "error">("idle");

  useEffect(() => {
    getApprovalCase(caseId).then(setCase);
  }, [caseId]);

  if (!theCase) return null;

  async function submit(action: "approve" | "decline" | "edit", extra?: { editedValue?: string; declineReason?: string }) {
    setActionStatus("submitting");
    try {
      await submitDecision(caseId, { action, ...extra });
      router.push("/approvals");
    } catch {
      setActionStatus("error");
    }
  }

  return (
    <AppShell role="branch_manager" pendingCounts={{ approvals: 0 }} activeRoute="/approvals">
      <ApprovalCaseDetail
        case={theCase}
        actionStatus={actionStatus}
        onApprove={() => submit("approve")}
        onDecline={(_id, reason) => submit("decline", { declineReason: reason })}
        onEdit={(_id, editedValue) => submit("edit", { editedValue })}
      />
    </AppShell>
  );
}
