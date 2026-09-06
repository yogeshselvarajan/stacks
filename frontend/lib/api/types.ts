// frontend/lib/api/types.ts
export type Tier = "GREEN" | "YELLOW" | "RED";
export type Workflow = "room_booking" | "ill_routing" | "overdue_chase";

export interface ApprovalCase {
  caseId: string;
  workflow: Workflow;
  tier: Tier;
  tool: string;
  summary: string;
  ageMinutes: number;
  candidates?: { id: string; label: string }[];
  recallSummary?: string;
}

export interface CalendarBooking {
  bookingId: string;
  roomId: string;
  start: string;
  end: string;
  bookingType: string;
  status: "confirmed" | "cancelled" | "pending_conflict";
  conflictResolution?: { resolvedTier: Tier; policyClauseId: string; yieldingBookingId: string };
}

export interface IllRequest {
  illRequestId: string;
  requestedTitle: string;
  status: "open" | "routed" | "no_match";
  tier: Tier | null;
  specialistTrace?: { narrowedCandidateId: string | null; confidence: number | null; stillAmbiguous: boolean };
  recallSummary?: string;
}

export interface OverdueCase {
  circulationRecordId: string;
  patronId: string;
  tierHistory: { tierIndex: number; label: string; status: "sent" | "pending" | "held_for_review" }[];
  recallSummary?: string;
}

export interface AuditEntry {
  auditId: string;
  sequence: number;
  toolName: string;
  outcome: string;
  actor: "AGENT" | "HUMAN";
  actorIdentity: string | null;
  timestamp: string;
  hitlTier: Tier | null;
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export const BFF_BASE_URL = process.env.NEXT_PUBLIC_BFF_BASE_URL ?? "http://localhost:8000";

export async function bffFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BFF_BASE_URL}${path}`, { ...init, credentials: "include" });
  if (!response.ok) {
    throw new ApiError(response.status, await response.text());
  }
  return response.json() as Promise<T>;
}
