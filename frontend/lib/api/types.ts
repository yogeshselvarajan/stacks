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
  policyClause?: { clauseId: string; clauseText: string } | null;
}

export interface CalendarBooking {
  bookingId: string;
  roomId: string;
  roomName: string;
  start: string;
  end: string;
  bookingType: string;
  status: "confirmed" | "cancelled" | "pending_conflict";
  conflictResolution?: { resolvedTier: Tier; policyClauseId: string; yieldingBookingId: string };
  pendingReview?: { caseId: string; tier: "YELLOW" | "RED" };
}

export interface IllRequest {
  illRequestId: string;
  requestedTitle: string;
  requesterName: string;
  requestedAt: string;
  status: "open" | "routed" | "no_match";
  tier: Tier | null;
  specialistTrace?: { narrowedCandidateId: string | null; confidence: number | null; stillAmbiguous: boolean };
  recallSummary?: string;
}

export interface OverdueCase {
  circulationRecordId: string;
  patronId: string;
  patronName: string;
  itemTitle: string;
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

// Double-submit CSRF cookie (bff/csrf.py): the BFF issues this cookie,
// readable by JS on purpose, on login. Every mutating request must echo
// its value back as a header the BFF compares against the cookie it
// received on the same request -- a cross-site form can't read this
// cookie to also set the header, so it can't produce a match.
//
// On this deployment the frontend (Amplify) and the BFF (a separate
// Lambda Function URL) are different origins, so document.cookie here
// can never see a cookie that belongs to the BFF's origin -- the browser
// still attaches it to requests, but this page's own JS cannot read its
// value. The BFF hands the value back in the login/session response
// bodies instead (readable cross-origin, since it's the fetch response
// this page itself made); setCsrfToken stores it in memory for
// csrfHeaders to echo back on every mutating request.
const CSRF_HEADER_NAME = "X-Stacks-CSRF-Token";

let inMemoryCsrfToken: string | null = null;

export function setCsrfToken(token: string | null): void {
  inMemoryCsrfToken = token;
}

export function csrfHeaders(): Record<string, string> {
  return inMemoryCsrfToken ? { [CSRF_HEADER_NAME]: inMemoryCsrfToken } : {};
}
