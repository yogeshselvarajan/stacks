// frontend/lib/api/approvals.ts
import { ApprovalCase, bffFetch, csrfHeaders } from "./types";

export function getApprovals(): Promise<ApprovalCase[]> {
  return bffFetch<ApprovalCase[]>("/api/approvals");
}

export function getApprovalCase(caseId: string): Promise<ApprovalCase> {
  return bffFetch<ApprovalCase>(`/api/approvals/${encodeURIComponent(caseId)}`);
}

export type Decision = { action: "approve" | "decline" | "edit"; editedValue?: string; declineReason?: string };

export function submitDecision(caseId: string, decision: Decision): Promise<{ status: string }> {
  return bffFetch<{ status: string }>(`/api/approvals/${encodeURIComponent(caseId)}/decision`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...csrfHeaders() },
    body: JSON.stringify(decision),
  });
}
