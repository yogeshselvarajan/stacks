import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { NewBookingForm } from "./new-booking-form";
import * as calendarApi from "@/lib/api/calendar";

vi.mock("@/lib/api/calendar", async () => {
  const actual = await vi.importActual<typeof calendarApi>("@/lib/api/calendar");
  return { ...actual, createBooking: vi.fn() };
});

describe("NewBookingForm", () => {
  beforeEach(() => {
    vi.mocked(calendarApi.createBooking).mockReset();
  });

  it("starts collapsed, showing only the entry point", () => {
    render(<NewBookingForm />);
    expect(screen.getByRole("button", { name: /new room booking/i })).toBeInTheDocument();
    expect(screen.queryByLabelText("Room")).toBeNull();
  });

  it("expands into a form when the entry point is clicked", () => {
    render(<NewBookingForm />);
    fireEvent.click(screen.getByRole("button", { name: /new room booking/i }));
    expect(screen.getByLabelText("Room")).toBeInTheDocument();
    expect(screen.getByLabelText("Start")).toBeInTheDocument();
    expect(screen.getByLabelText("End")).toBeInTheDocument();
    expect(screen.getByLabelText("Booking type")).toBeInTheDocument();
    expect(screen.getByLabelText("Booked by")).toBeInTheDocument();
  });

  it("submits the entered values and shows a real processing state, not a spinner", async () => {
    vi.mocked(calendarApi.createBooking).mockImplementation(
      () => new Promise(() => {}) // never resolves during this assertion
    );
    render(<NewBookingForm />);
    fireEvent.click(screen.getByRole("button", { name: /new room booking/i }));
    fireEvent.change(screen.getByLabelText("Room"), { target: { value: "room_b" } });
    fireEvent.change(screen.getByLabelText("Start"), { target: { value: "2026-10-01T10:00" } });
    fireEvent.change(screen.getByLabelText("End"), { target: { value: "2026-10-01T11:00" } });
    fireEvent.change(screen.getByLabelText("Booking type"), { target: { value: "walk_in" } });
    fireEvent.change(screen.getByLabelText("Booked by"), { target: { value: "patron_x" } });
    fireEvent.click(screen.getByRole("button", { name: /submit/i }));

    expect(await screen.findByText(/submitting to stacks/i)).toBeInTheDocument();
    expect(calendarApi.createBooking).toHaveBeenCalledWith({
      roomId: "room_b",
      start: "2026-10-01T10:00",
      end: "2026-10-01T11:00",
      bookingType: "walk_in",
      bookedBy: "patron_x",
    });
  });

  it("shows a link into the Approval Inbox when the case lands as pending approval", async () => {
    vi.mocked(calendarApi.createBooking).mockResolvedValue({
      bookingId: "b_abc123",
      status: "pending_approval",
      outcome: null,
      conflictingBookingIds: ["b_zzz", "b_aaa"],
    });
    render(<NewBookingForm />);
    fireEvent.click(screen.getByRole("button", { name: /new room booking/i }));
    fireEvent.change(screen.getByLabelText("Room"), { target: { value: "room_a" } });
    fireEvent.change(screen.getByLabelText("Start"), { target: { value: "2026-10-01T10:00" } });
    fireEvent.change(screen.getByLabelText("End"), { target: { value: "2026-10-01T11:00" } });
    fireEvent.change(screen.getByLabelText("Booked by"), { target: { value: "patron_x" } });
    fireEvent.click(screen.getByRole("button", { name: /submit/i }));

    const link = await screen.findByRole("link", { name: /review in approval inbox/i });
    expect(link).toHaveAttribute("href", "/approvals/b_aaa:b_zzz");
  });

  it("shows a resolved message, not a pending-approval link, when the case auto-resolves", async () => {
    vi.mocked(calendarApi.createBooking).mockResolvedValue({
      bookingId: "b_def456",
      status: "resolved",
      outcome: "committed",
      conflictingBookingIds: ["b_def456"],
    });
    render(<NewBookingForm />);
    fireEvent.click(screen.getByRole("button", { name: /new room booking/i }));
    fireEvent.change(screen.getByLabelText("Room"), { target: { value: "room_a" } });
    fireEvent.change(screen.getByLabelText("Start"), { target: { value: "2026-10-01T10:00" } });
    fireEvent.change(screen.getByLabelText("End"), { target: { value: "2026-10-01T11:00" } });
    fireEvent.change(screen.getByLabelText("Booked by"), { target: { value: "patron_y" } });
    fireEvent.click(screen.getByRole("button", { name: /submit/i }));

    expect(await screen.findByText(/resolved automatically/i)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /review in approval inbox/i })).toBeNull();
  });

  it("shows a needs-attention message when the conflict is created but not resolved automatically", async () => {
    vi.mocked(calendarApi.createBooking).mockResolvedValue({
      bookingId: "b_needs1",
      status: "needs_attention",
      outcome: "blocked_missing_approval",
      conflictingBookingIds: ["b_needs1"],
    });
    render(<NewBookingForm />);
    fireEvent.click(screen.getByRole("button", { name: /new room booking/i }));
    fireEvent.change(screen.getByLabelText("Room"), { target: { value: "room_a" } });
    fireEvent.change(screen.getByLabelText("Start"), { target: { value: "2026-10-01T10:00" } });
    fireEvent.change(screen.getByLabelText("End"), { target: { value: "2026-10-01T11:00" } });
    fireEvent.change(screen.getByLabelText("Booked by"), { target: { value: "patron_x" } });
    fireEvent.click(screen.getByRole("button", { name: /submit/i }));

    expect(
      await screen.findByText(/could not resolve it automatically.*check the calendar/i)
    ).toBeInTheDocument();
  });

  it("shows a could-not-process message when the conflict is created but agent invocation fails", async () => {
    vi.mocked(calendarApi.createBooking).mockResolvedValue({
      bookingId: "b_fail1",
      status: "agent_invocation_failed",
      outcome: null,
      conflictingBookingIds: ["b_fail1"],
    });
    render(<NewBookingForm />);
    fireEvent.click(screen.getByRole("button", { name: /new room booking/i }));
    fireEvent.change(screen.getByLabelText("Room"), { target: { value: "room_a" } });
    fireEvent.change(screen.getByLabelText("Start"), { target: { value: "2026-10-01T10:00" } });
    fireEvent.change(screen.getByLabelText("End"), { target: { value: "2026-10-01T11:00" } });
    fireEvent.change(screen.getByLabelText("Booked by"), { target: { value: "patron_x" } });
    fireEvent.click(screen.getByRole("button", { name: /submit/i }));

    expect(await screen.findByText(/could not process it yet/i)).toBeInTheDocument();
  });

  it("shows a clear no-conflict message when the submitted booking does not overlap anything", async () => {
    vi.mocked(calendarApi.createBooking).mockResolvedValue({
      bookingId: "b_new1", status: "no_conflict", outcome: null, conflictingBookingIds: null,
    });
    render(<NewBookingForm />);
    fireEvent.click(screen.getByRole("button", { name: /new room booking/i }));
    fireEvent.change(screen.getByLabelText("Room"), { target: { value: "room_a" } });
    fireEvent.change(screen.getByLabelText("Start"), { target: { value: "2026-10-01T10:00" } });
    fireEvent.change(screen.getByLabelText("End"), { target: { value: "2026-10-01T11:00" } });
    fireEvent.change(screen.getByLabelText("Booked by"), { target: { value: "patron_x" } });
    fireEvent.click(screen.getByRole("button", { name: /submit/i }));

    expect(await screen.findByText(/no conflict was detected/i)).toBeInTheDocument();
  });

  it("shows a plain-language error and lets the user try again on failure", async () => {
    vi.mocked(calendarApi.createBooking).mockRejectedValue(new Error("network down"));
    render(<NewBookingForm />);
    fireEvent.click(screen.getByRole("button", { name: /new room booking/i }));
    fireEvent.change(screen.getByLabelText("Room"), { target: { value: "room_a" } });
    fireEvent.change(screen.getByLabelText("Start"), { target: { value: "2026-10-01T10:00" } });
    fireEvent.change(screen.getByLabelText("End"), { target: { value: "2026-10-01T11:00" } });
    fireEvent.change(screen.getByLabelText("Booked by"), { target: { value: "patron_z" } });
    fireEvent.click(screen.getByRole("button", { name: /submit/i }));

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(/couldn't submit/i));
  });

  it("calls onCreated after a successful submission", async () => {
    const onCreated = vi.fn();
    vi.mocked(calendarApi.createBooking).mockResolvedValue({
      bookingId: "b_ghi789", status: "resolved", outcome: "committed", conflictingBookingIds: ["b_ghi789"],
    });
    render(<NewBookingForm onCreated={onCreated} />);
    fireEvent.click(screen.getByRole("button", { name: /new room booking/i }));
    fireEvent.change(screen.getByLabelText("Room"), { target: { value: "room_a" } });
    fireEvent.change(screen.getByLabelText("Start"), { target: { value: "2026-10-01T10:00" } });
    fireEvent.change(screen.getByLabelText("End"), { target: { value: "2026-10-01T11:00" } });
    fireEvent.change(screen.getByLabelText("Booked by"), { target: { value: "patron_z" } });
    fireEvent.click(screen.getByRole("button", { name: /submit/i }));

    await waitFor(() => expect(onCreated).toHaveBeenCalled());
  });

  it("resets the draft fields when Cancel is clicked, unlike a stale reopen", () => {
    render(<NewBookingForm />);
    fireEvent.click(screen.getByRole("button", { name: /new room booking/i }));
    fireEvent.change(screen.getByLabelText("Booked by"), { target: { value: "patron_x" } });
    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));

    fireEvent.click(screen.getByRole("button", { name: /new room booking/i }));
    expect(screen.getByLabelText("Booked by")).toHaveValue("");
  });

  it("every input and the submit button carry the shared focus-ring class", () => {
    render(<NewBookingForm />);
    fireEvent.click(screen.getByRole("button", { name: /new room booking/i }));
    expect(screen.getByLabelText("Room").className).toContain("stacks-focus-ring");
    expect(screen.getByLabelText("Start").className).toContain("stacks-focus-ring");
    expect(screen.getByLabelText("End").className).toContain("stacks-focus-ring");
    expect(screen.getByLabelText("Booking type").className).toContain("stacks-focus-ring");
    expect(screen.getByLabelText("Booked by").className).toContain("stacks-focus-ring");
    expect(screen.getByRole("button", { name: /submit/i }).className).toContain("stacks-focus-ring");
  });
});
