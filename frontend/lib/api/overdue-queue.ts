// frontend/lib/api/overdue-queue.ts
import { OverdueCase, bffFetch, csrfHeaders } from "./types";

export function getOverdueQueue(): Promise<OverdueCase[]> {
  return bffFetch<OverdueCase[]>("/api/overdue-queue");
}

export interface CreateOverdueCaseInput {
  patronId: string;
  itemId: string;
  itemType: string;
  daysOverdue: number;
  sensitivityFlag: boolean;
}

export interface CreateOverdueCaseResult {
  circulationRecordId: string;
  status: "resolved" | "needs_attention" | "pending_approval" | "agent_invocation_failed";
  outcome: string | null;
}

export function createOverdueCase(input: CreateOverdueCaseInput): Promise<CreateOverdueCaseResult> {
  return bffFetch<CreateOverdueCaseResult>("/api/overdue-cases", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...csrfHeaders() },
    body: JSON.stringify(input),
  });
}
