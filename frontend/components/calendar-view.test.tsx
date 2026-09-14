// frontend/components/calendar-view.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CalendarView } from "./calendar-view";
import { CALENDAR_FIXTURE } from "@/lib/fixtures";
import { CalendarBooking } from "@/lib/api/types";

describe("CalendarView", () => {
  it("loading state: renders row skeletons", () => {
    const { container } = render(<CalendarView bookings={[]} status="loading" />);
    expect(container.querySelector("[data-testid='skeleton-cell']")).not.toBeNull();
  });

  it("populated state: a resolved conflict shows its tier badge and the cited policy clause", () => {
    render(<CalendarView bookings={CALENDAR_FIXTURE} status="ready" />);
    expect(screen.getByText("RBP-1")).toBeInTheDocument();
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("populated state: shows the room's human-readable name, never its raw internal id", () => {
    render(<CalendarView bookings={CALENDAR_FIXTURE} status="ready" />);
    expect(screen.getByText("Story Room")).toBeInTheDocument();
    expect(screen.queryByText("room_a")).not.toBeInTheDocument();
  });

  it("empty state: names the room/date filter as why nothing shows", () => {
    render(<CalendarView bookings={[]} status="ready" />);
    expect(screen.getByText(/no bookings for this room and date range/i)).toBeInTheDocument();
  });

  it("error state: a specific, retry-oriented message", () => {
    render(<CalendarView bookings={[]} status="error" />);
    expect(screen.getByText(/failed to load the calendar/i)).toBeInTheDocument();
  });

  it("shows a clear access-denied message when status is forbidden, not the generic failure message", () => {
    render(<CalendarView bookings={[]} status="forbidden" />);
    expect(screen.getByText("You do not have access to this workflow.")).toBeInTheDocument();
  });

  // Craft-bar coverage (frontend_architecture.md section 7.4 / the plan's
  // Global Constraint on six-state interactive elements): a pending
  // conflict's "awaiting review" badge is a real drill-in link into the
  // Approval Inbox, not a plain status string, so it needs the same
  // default/hover/focus/active/disabled treatment as any other
  // interactive element in the app.
  it("pending conflict: renders an awaiting-review link into the Approval Inbox with hover, focus, and active styling", () => {
    render(<CalendarView bookings={CALENDAR_FIXTURE} status="ready" />);
    const link = screen.getByRole("link", { name: /awaiting review/i });
    expect(link).toHaveAttribute("href", "/approvals/b_recurring_c%3Ab_walkin_c");
    expect(link.className).toContain("stacks-focus-ring");
    expect(link.className).toContain("hover:");
    expect(link.className).toContain("active:");
  });

  it("pending conflict: falls back to a disabled badge (not a link) when no case id is available", () => {
    const bookings: CalendarBooking[] = [
      {
        bookingId: "b_orphan", roomId: "room_z", roomName: "room_z", start: "2026-09-05T10:00:00Z", end: "2026-09-05T11:00:00Z",
        bookingType: "one_off", status: "pending_conflict",
      },
    ];
    render(<CalendarView bookings={bookings} status="ready" />);
    expect(screen.queryByRole("link", { name: /awaiting review/i })).toBeNull();
    const disabled = screen.getByTestId("pending-review-disabled");
    expect(disabled).toHaveTextContent(/awaiting review/i);
    expect(disabled).toHaveAttribute("aria-disabled", "true");
  });
});

describe("CalendarView conflict rows", () => {
  it("a pending-conflict row gets the diagonal-hatch background pattern, not just a badge color", () => {
    render(<CalendarView bookings={CALENDAR_FIXTURE} status="ready" />);
    const conflictRow = screen.getByText("Community Room B").closest("tr");
    expect(conflictRow?.style.backgroundImage).toContain("repeating-linear-gradient");
  });
});
