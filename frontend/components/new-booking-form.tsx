"use client";

import { useState } from "react";
import Link from "next/link";
import { createBooking, CreateBookingInput, CreateBookingResult } from "@/lib/api/calendar";

type Phase = "collapsed" | "form" | "submitting" | "done" | "error";

const INPUT_CLASS =
  "stacks-focus-ring mb-3 w-full rounded border px-3 py-2 text-sm transition-colors disabled:cursor-not-allowed disabled:opacity-60";
const INPUT_STYLE = {
  borderColor: "var(--color-border)",
  background: "var(--color-surface-2)",
  color: "var(--color-ink)",
  transitionDuration: "var(--motion-duration-feedback)",
  transitionTimingFunction: "var(--motion-ease-feedback)",
} as const;

export function NewBookingForm({ onCreated }: { onCreated?: () => void }) {
  const [phase, setPhase] = useState<Phase>("collapsed");
  const [roomId, setRoomId] = useState<CreateBookingInput["roomId"]>("room_a");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [bookingType, setBookingType] = useState<CreateBookingInput["bookingType"]>("recurring_program");
  const [bookedBy, setBookedBy] = useState("");
  const [result, setResult] = useState<CreateBookingResult | null>(null);

  if (phase === "collapsed") {
    return (
      <button
        type="button"
        onClick={() => setPhase("form")}
        className="stacks-focus-ring mb-4 rounded-md px-3 py-2 text-sm font-medium transition-colors hover:bg-[var(--color-surface-2)] active:bg-[var(--color-border)]"
        style={{
          color: "var(--color-accent)",
          transitionDuration: "var(--motion-duration-feedback)",
          transitionTimingFunction: "var(--motion-ease-feedback)",
        }}
      >
        + New room booking
      </button>
    );
  }

  if (phase === "done" && result) {
    return (
      <div
        className="mb-4 rounded-lg border p-4 text-sm"
        style={{ borderColor: "var(--color-border)", background: "var(--color-surface)" }}
      >
        {result.status === "no_conflict" ? (
          <p style={{ color: "var(--color-ink)" }}>No conflict was detected. The booking was created as confirmed.</p>
        ) : result.status === "pending_approval" ? (
          <p style={{ color: "var(--color-ink)" }}>
            Conflict detected. Stacks needs a human decision before it resolves.{" "}
            <Link
              href={`/approvals/${result.conflictingBookingIds?.slice().sort().join(":")}`}
              className="stacks-focus-ring rounded-sm underline-offset-4 hover:underline"
              style={{ color: "var(--color-accent)", fontWeight: 600 }}
            >
              Review in Approval Inbox
            </Link>
          </p>
        ) : result.status === "resolved" ? (
          <p style={{ color: "var(--color-ink)" }}>Resolved automatically. No human review was needed.</p>
        ) : result.status === "needs_attention" ? (
          <p style={{ color: "var(--color-tier-red-text)" }}>
            Conflict created, but Stacks could not resolve it automatically. A team member should check the
            Calendar.
          </p>
        ) : (
          <p style={{ color: "var(--color-tier-red-text)" }}>
            Conflict detected, but Stacks could not process it yet. Try again shortly.
          </p>
        )}
        <button
          type="button"
          onClick={() => {
            setPhase("collapsed");
            setRoomId("room_a");
            setStart("");
            setEnd("");
            setBookingType("recurring_program");
            setBookedBy("");
            setResult(null);
          }}
          className="stacks-focus-ring mt-2 rounded-md px-2 py-1 text-xs font-medium transition-colors hover:bg-[var(--color-surface-2)] active:bg-[var(--color-border)]"
          style={{ color: "var(--color-ink-muted)" }}
        >
          Create another
        </button>
      </div>
    );
  }

  const busy = phase === "submitting";

  return (
    <form
      className="mb-4 w-96 rounded-lg border p-4"
      style={{ borderColor: "var(--color-border)", background: "var(--color-surface)" }}
      onSubmit={async (e) => {
        e.preventDefault();
        if (busy) return;
        setPhase("submitting");
        try {
          const created = await createBooking({ roomId, start, end, bookingType, bookedBy });
          setResult(created);
          setPhase("done");
          onCreated?.();
        } catch {
          setPhase("error");
        }
      }}
    >
      <label htmlFor="new-booking-room" className="mb-1 block text-sm font-medium" style={{ color: "var(--color-ink)" }}>
        Room
      </label>
      <select
        id="new-booking-room"
        required
        className={INPUT_CLASS}
        style={INPUT_STYLE}
        value={roomId}
        onChange={(e) => setRoomId(e.target.value as CreateBookingInput["roomId"])}
        disabled={busy}
      >
        <option value="room_a">Community Room A</option>
        <option value="room_b">Community Room B</option>
      </select>

      <label htmlFor="new-booking-start" className="mb-1 block text-sm font-medium" style={{ color: "var(--color-ink)" }}>
        Start
      </label>
      <input
        id="new-booking-start"
        type="datetime-local"
        required
        className={INPUT_CLASS}
        style={INPUT_STYLE}
        value={start}
        onChange={(e) => setStart(e.target.value)}
        disabled={busy}
      />

      <label htmlFor="new-booking-end" className="mb-1 block text-sm font-medium" style={{ color: "var(--color-ink)" }}>
        End
      </label>
      <input
        id="new-booking-end"
        type="datetime-local"
        required
        className={INPUT_CLASS}
        style={INPUT_STYLE}
        value={end}
        onChange={(e) => setEnd(e.target.value)}
        disabled={busy}
      />

      <label htmlFor="new-booking-type" className="mb-1 block text-sm font-medium" style={{ color: "var(--color-ink)" }}>
        Booking type
      </label>
      <select
        id="new-booking-type"
        required
        className={INPUT_CLASS}
        style={INPUT_STYLE}
        value={bookingType}
        onChange={(e) => setBookingType(e.target.value as CreateBookingInput["bookingType"])}
        disabled={busy}
      >
        <option value="recurring_program">Recurring program</option>
        <option value="one_off_renter">One-off renter</option>
        <option value="staff_internal">Staff internal</option>
        <option value="walk_in">Walk-in</option>
      </select>

      <label htmlFor="new-booking-booked-by" className="mb-1 block text-sm font-medium" style={{ color: "var(--color-ink)" }}>
        Booked by
      </label>
      <input
        id="new-booking-booked-by"
        required
        className={INPUT_CLASS}
        style={INPUT_STYLE}
        value={bookedBy}
        onChange={(e) => setBookedBy(e.target.value)}
        disabled={busy}
      />

      {phase === "error" && (
        <p
          role="alert"
          className="mb-3 rounded px-3 py-2 text-sm"
          style={{ color: "var(--color-tier-red-text)", background: "var(--color-tier-red-bg)" }}
        >
          Couldn&apos;t submit this request. Check your connection and try again.
        </p>
      )}

      <div className="flex items-center gap-2">
        <button
          type="submit"
          disabled={busy}
          className="stacks-focus-ring rounded px-4 py-2 text-sm font-medium transition-colors hover:bg-[var(--color-accent-hover)] active:bg-[var(--color-accent-hover)] disabled:cursor-not-allowed disabled:opacity-60"
          style={{
            background: "var(--color-accent)",
            color: "var(--color-fill-text)",
            transitionDuration: "var(--motion-duration-feedback)",
            transitionTimingFunction: "var(--motion-ease-feedback)",
          }}
        >
          {busy ? "Submitting to Stacks..." : "Submit"}
        </button>
        {!busy && (
          <button
            type="button"
            onClick={() => {
              setPhase("collapsed");
              setRoomId("room_a");
              setStart("");
              setEnd("");
              setBookingType("recurring_program");
              setBookedBy("");
            }}
            className="stacks-focus-ring rounded px-3 py-2 text-sm"
            style={{ color: "var(--color-ink-muted)" }}
          >
            Cancel
          </button>
        )}
      </div>
    </form>
  );
}
