// frontend/lib/fixtures/index.ts
/* Representative sample data for every screen's loading/populated/empty
   states, imported by both component tests and (until Task 16's BFF read
   endpoints are live) any manual local exploration of the UI. Never
   imported by BFF or agent code, frontend-only. */
import { ApprovalCase, AuditEntry, CalendarBooking, IllRequest, OverdueCase } from "../api/types";

export const APPROVAL_CASES_FIXTURE: ApprovalCase[] = [
  {
    caseId: "b_recurring_b:b_walkin_b", workflow: "room_booking", tier: "RED", tool: "resolve_room_conflict",
    summary: "Room 204, Thursday 2-4pm: recurring Book Club vs. one-off community meeting.",
    ageMinutes: 14, candidates: [{ id: "b_recurring_b", label: "Book Club (recurring)" }, { id: "b_walkin_b", label: "Community meeting (one-off)" }],
    policyClause: { clauseId: "RBP-1", clauseText: "A recurring, library-run program outranks a one-off renter or walk-in booking for the same slot." },
  },
  {
    caseId: "ill_req_123", workflow: "ill_routing", tier: "YELLOW", tool: "route_ill_request",
    summary: "Ambiguous edition match for \"The Left Hand of Darkness\".", ageMinutes: 40,
    recallSummary: "This requester has accepted a substitute edition without escalating on 3 prior occasions.",
  },
];

export const EMPTY_APPROVAL_CASES_FIXTURE: ApprovalCase[] = [];

export const CALENDAR_FIXTURE: CalendarBooking[] = [
  {
    bookingId: "b_recurring_a", roomId: "room_a", roomName: "Story Room", start: "2026-09-01T14:00:00Z", end: "2026-09-01T16:00:00Z",
    bookingType: "recurring_program", status: "confirmed",
    conflictResolution: { resolvedTier: "GREEN", policyClauseId: "RBP-1", yieldingBookingId: "b_oneoff_a" },
  },
  {
    bookingId: "b_walkin_c", roomId: "room_b", roomName: "Community Room B", start: "2026-09-03T10:00:00Z", end: "2026-09-03T11:00:00Z",
    bookingType: "one_off", status: "pending_conflict",
    pendingReview: { caseId: "b_recurring_c:b_walkin_c", tier: "YELLOW" },
  },
];

export const ILL_QUEUE_FIXTURE: IllRequest[] = [
  {
    illRequestId: "ill_req_123", requestedTitle: "The Left Hand of Darkness",
    requesterName: "Devi Kapoor", requestedAt: "2026-08-20T09:00:00+00:00",
    status: "open", tier: "YELLOW",
    specialistTrace: { narrowedCandidateId: "hold_2a", confidence: 0.72, stillAmbiguous: false },
    recallSummary: "This requester has accepted a substitute edition without escalating on 3 prior occasions.",
  },
];

export const OVERDUE_QUEUE_FIXTURE: OverdueCase[] = [
  {
    circulationRecordId: "circ_1", patronId: "patron_1", patronName: "Maria Chen", itemTitle: "The Great Gatsby",
    tierHistory: [
      { tierIndex: 0, label: "Informational", status: "sent" },
      { tierIndex: 1, label: "Fee mention", status: "held_for_review" },
    ],
    recallSummary: "Hardship flag on file from a cycle approximately 3 months ago.",
  },
];

export const AUDIT_FIXTURE: AuditEntry[] = [
  { auditId: "a1", sequence: 1, toolName: "resolve_room_conflict", outcome: "committed", actor: "AGENT", actorIdentity: null, timestamp: "2026-09-01T14:05:00Z", hitlTier: "GREEN" },
  { auditId: "a2", sequence: 2, toolName: "notify_parties", outcome: "sent", actor: "AGENT", actorIdentity: null, timestamp: "2026-09-01T14:05:02Z", hitlTier: null },
];
