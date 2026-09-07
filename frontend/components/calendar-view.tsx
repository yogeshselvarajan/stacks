// frontend/components/calendar-view.tsx
import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { CalendarBooking } from "@/lib/api/types";
import { TierBadge } from "./tier-badge";
import { RowSkeleton } from "./skeletons";

type Status = "loading" | "ready" | "error";

const PENDING_REVIEW_COLORS: Record<"YELLOW" | "RED", { text: string; bg: string }> = {
  YELLOW: { text: "var(--color-tier-yellow-text)", bg: "var(--color-tier-yellow-bg)" },
  RED: { text: "var(--color-tier-red-text)", bg: "var(--color-tier-red-bg)" },
};

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
  if (status === "error") {
    return <p style={{ color: "var(--color-tier-red-text)" }}>Failed to load the calendar. Refresh to try again.</p>;
  }

  return (
    <table className="w-full text-sm" style={{ borderCollapse: "collapse" }}>
      <thead>
        <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
          <th className="px-4 py-2 text-left">Room</th>
          <th className="px-4 py-2 text-left">Start</th>
          <th className="px-4 py-2 text-left">End</th>
          <th className="px-4 py-2 text-left">Status</th>
        </tr>
      </thead>
      <tbody>
        {status === "loading" && Array.from({ length: 3 }).map((_, i) => <RowSkeleton key={i} columns={4} />)}
        {status === "ready" && bookings.length === 0 && (
          <tr><td colSpan={4} className="px-4 py-6 text-center" style={{ color: "var(--color-ink-muted)" }}>No bookings for this room and date range. Try a different room or week.</td></tr>
        )}
        {status === "ready" && bookings.map((b) => (
          <tr
            key={b.bookingId}
            style={{
              borderBottom: "1px solid var(--color-border)",
              backgroundImage:
                b.status === "pending_conflict"
                  ? "repeating-linear-gradient(45deg, var(--color-tier-red-bg), var(--color-tier-red-bg) 4px, transparent 4px, transparent 8px)"
                  : undefined,
            }}
          >
            <td className="px-4 py-2" style={{ fontFamily: "var(--font-mono)" }}>{b.roomId}</td>
            <td className="px-4 py-2" style={{ fontVariantNumeric: "tabular-nums" }}>{b.start}</td>
            <td className="px-4 py-2" style={{ fontVariantNumeric: "tabular-nums" }}>{b.end}</td>
            <td className="px-4 py-2">
              {b.conflictResolution ? (
                <div className="flex items-center gap-2">
                  <TierBadge tier={b.conflictResolution.resolvedTier} />
                  <span style={{ fontFamily: "var(--font-mono)" }}>{b.conflictResolution.policyClauseId}</span>
                </div>
              ) : b.status === "pending_conflict" ? (
                <PendingReviewBadge pendingReview={b.pendingReview} />
              ) : (
                b.status
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
