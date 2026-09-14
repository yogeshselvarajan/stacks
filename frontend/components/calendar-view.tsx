// frontend/components/calendar-view.tsx
import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { CalendarBooking } from "@/lib/api/types";
import { TierBadge } from "./tier-badge";
import { RowSkeleton } from "./skeletons";

type Status = "loading" | "ready" | "error" | "forbidden";

const PENDING_REVIEW_COLORS: Record<"YELLOW" | "RED", { text: string; bg: string }> = {
  YELLOW: { text: "var(--color-tier-yellow-text)", bg: "var(--color-tier-yellow-bg)" },
  RED: { text: "var(--color-tier-red-text)", bg: "var(--color-tier-red-bg)" },
};

const STATUS_LABELS: Record<CalendarBooking["status"], string> = {
  confirmed: "Confirmed",
  cancelled: "Cancelled",
  pending_conflict: "Pending conflict",
};

const STATUS_DOT_COLORS: Record<CalendarBooking["status"], string> = {
  confirmed: "var(--color-tier-green-fill)",
  cancelled: "var(--color-ink-faint)",
  pending_conflict: "var(--color-tier-yellow-fill)",
};

function formatDateRange(start: string, end: string): string {
  const startDate = new Date(start);
  const endDate = new Date(end);
  if (Number.isNaN(startDate.getTime()) || Number.isNaN(endDate.getTime())) {
    return `${start} - ${end}`;
  }
  const dateFormatter = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric" });
  const timeFormatter = new Intl.DateTimeFormat("en-US", { hour: "numeric", minute: "2-digit" });
  return `${dateFormatter.format(startDate)} · ${timeFormatter.format(startDate)} – ${timeFormatter.format(endDate)}`;
}

// Craft-bar item 1 (frontend_architecture.md section 7.4): a pending
// conflict's badge is a real drill-in link into the Approval Inbox, so it
// needs all six interactive states, not just a default/hover pair.
// default: PENDING_REVIEW_LINK_CLASS's base layout/color styling below.
// hover: hover:brightness-90.
// focus (keyboard): stacks-focus-ring (Task 7's shared custom focus ring).
// active/pressed: active:brightness-95.
// disabled: when no case id is available yet, this renders as a
// non-interactive <span aria-disabled="true"> instead of a <Link>, so it
// cannot be tabbed to or clicked (a genuine disabled state, not a stub).
// loading: this link only ever renders once the table itself is in its
// "ready" state; while the calendar is loading, RowSkeleton stands in for
// the whole row (including where this link will appear), so the link has
// no independent loading state of its own, mirroring Task 7's app-shell
// nav links, which document the same reasoning for the same reason.
const PENDING_REVIEW_LINK_CLASS =
  "stacks-focus-ring inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-sm font-medium transition-all hover:brightness-90 active:brightness-95";
const PENDING_REVIEW_DISABLED_CLASS =
  "inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-sm font-medium opacity-60";

function PendingReviewBadge({ pendingReview }: { pendingReview?: CalendarBooking["pendingReview"] }) {
  const colors = PENDING_REVIEW_COLORS[pendingReview?.tier ?? "YELLOW"];

  if (!pendingReview) {
    return (
      <span
        data-testid="pending-review-disabled"
        aria-disabled="true"
        className={PENDING_REVIEW_DISABLED_CLASS}
        style={{ color: colors.text, backgroundColor: colors.bg, cursor: "not-allowed" }}
      >
        Awaiting review
        <ArrowUpRight size={14} aria-hidden="true" />
      </span>
    );
  }

  return (
    <Link
      href={`/approvals/${encodeURIComponent(pendingReview.caseId)}`}
      className={PENDING_REVIEW_LINK_CLASS}
      style={{
        color: colors.text,
        backgroundColor: colors.bg,
        transitionDuration: "var(--motion-duration-feedback)",
        transitionTimingFunction: "var(--motion-ease-feedback)",
      }}
    >
      Awaiting review
      <ArrowUpRight size={14} aria-hidden="true" />
    </Link>
  );
}

export function CalendarView({ bookings, status }: { bookings: CalendarBooking[]; status: Status }) {
  if (status === "forbidden") {
    return <p style={{ color: "var(--color-tier-red-text)" }}>You do not have access to this workflow.</p>;
  }

  if (status === "error") {
    return <p style={{ color: "var(--color-tier-red-text)" }}>Failed to load the calendar. Refresh to try again.</p>;
  }

  return (
    <table className="w-full text-sm" style={{ borderCollapse: "collapse" }}>
      <thead>
        <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
          <th className="px-4 py-2 text-left">Room</th>
          <th className="px-4 py-2 text-left">When</th>
          <th className="px-4 py-2 text-left">Status</th>
        </tr>
      </thead>
      <tbody>
        {status === "loading" && Array.from({ length: 3 }).map((_, i) => <RowSkeleton key={i} columns={3} />)}
        {status === "ready" && bookings.length === 0 && (
          <tr><td colSpan={3} className="px-4 py-6 text-center" style={{ color: "var(--color-ink-muted)" }}>No bookings for this room and date range. Try a different room or week.</td></tr>
        )}
        {status === "ready" && bookings.map((b) => (
          <tr
            key={b.bookingId}
            data-testid="calendar-row"
            data-room-id={b.roomId}
            style={{
              borderBottom: "1px solid var(--color-border)",
              backgroundImage:
                b.status === "pending_conflict"
                  ? "repeating-linear-gradient(45deg, color-mix(in srgb, var(--color-tier-red-fill) 25%, transparent), color-mix(in srgb, var(--color-tier-red-fill) 25%, transparent) 4px, transparent 4px, transparent 8px)"
                  : undefined,
            }}
          >
            <td className="px-4 py-2" style={{ color: "var(--color-ink)" }}>{b.roomName}</td>
            <td className="px-4 py-2" style={{ fontVariantNumeric: "tabular-nums", color: "var(--color-ink-muted)" }}>
              {formatDateRange(b.start, b.end)}
            </td>
            <td className="px-4 py-2">
              {b.conflictResolution ? (
                <div className="flex items-center gap-2">
                  <TierBadge tier={b.conflictResolution.resolvedTier} />
                  <span style={{ fontFamily: "var(--font-mono)" }}>{b.conflictResolution.policyClauseId}</span>
                </div>
              ) : b.status === "pending_conflict" ? (
                <PendingReviewBadge pendingReview={b.pendingReview} />
              ) : (
                <span className="inline-flex items-center gap-1.5">
                  <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full" style={{ background: STATUS_DOT_COLORS[b.status] }} />
                  <span style={{ color: "var(--color-ink-muted)" }}>{STATUS_LABELS[b.status]}</span>
                </span>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
