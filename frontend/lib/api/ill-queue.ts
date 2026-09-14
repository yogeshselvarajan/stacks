// frontend/lib/api/ill-queue.ts
import { IllRequest, bffFetch, csrfHeaders } from "./types";

export function getIllQueue(): Promise<IllRequest[]> {
  return bffFetch<IllRequest[]>("/api/ill-queue");
}

export interface CreateIllRequestInput {
  requestedTitle: string;
  requestedEditionHint?: string;
  requesterPatronId: string;
}

export interface CreateIllRequestResult {
  illRequestId: string;
  status: "pending_approval" | "resolved" | "needs_attention" | "agent_invocation_failed";
  outcome: string | null;
}

export function createIllRequest(input: CreateIllRequestInput): Promise<CreateIllRequestResult> {
  return bffFetch<CreateIllRequestResult>("/api/ill-requests", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...csrfHeaders() },
    body: JSON.stringify(input),
  });
}
