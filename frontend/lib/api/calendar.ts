// frontend/lib/api/calendar.ts
import { CalendarBooking, bffFetch, csrfHeaders } from "./types";

export function getCalendar(roomId?: string): Promise<CalendarBooking[]> {
  const query = roomId ? `?room_id=${encodeURIComponent(roomId)}` : "";
  return bffFetch<CalendarBooking[]>(`/api/calendar${query}`);
}

export interface CreateBookingInput {
  roomId: "room_a" | "room_b";
  start: string;
  end: string;
  bookingType: "recurring_program" | "one_off_renter" | "staff_internal" | "walk_in";
  bookedBy: string;
}

export interface CreateBookingResult {
  bookingId: string;
  status: "resolved" | "needs_attention" | "pending_approval" | "agent_invocation_failed" | "no_conflict";
  outcome: string | null;
  conflictingBookingIds: string[] | null;
  // I4 (final review fix round): the real case id the backend persists,
  // looked up server-side from the pending-approvals record the agent
  // invocation actually created -- never reconstructed client-side from
  // conflictingBookingIds, which is not guaranteed to match the set the
  // agent itself used. Null unless status is "pending_approval" and a
  // matching record was found.
  caseId: string | null;
}

export function createBooking(input: CreateBookingInput): Promise<CreateBookingResult> {
  return bffFetch<CreateBookingResult>("/api/bookings", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...csrfHeaders() },
    body: JSON.stringify(input),
  });
}
