"use client";

import { useState } from "react";
import { ApprovalCase } from "@/lib/api/types";
import { TierBadge } from "./tier-badge";
import { CardSkeleton } from "./skeletons";

type Status = "loading" | "ready" | "error";
type ResolveAction = "approve" | "decline";

const TIER_ORDER: Record<string, number> = { RED: 0, YELLOW: 1, GREEN: 2 };

const APPROVE_BUTTON_CLASS =
  "stacks-focus-ring rounded px-3 py-1.5 text-sm font-medium transition-all hover:brightness-90 active:brightness-95 disabled:cursor-not-allowed disabled:opacity-60";
const DECLINE_BUTTON_CLASS =
  "stacks-focus-ring rounded border px-3 py-1.5 text-sm font-medium transition-colors hover:bg-[var(--color-bg)] active:bg-[var(--color-border)] disabled:cursor-not-allowed disabled:opacity-60";

export function ApprovalInboxView({
  cases,
  status,
  onResolve,
  resolvingCaseId,
}: {
  cases: ApprovalCase[];
  status: Status;
  onResolve: (caseId: string, action: ResolveAction) => void;
  resolvingCaseId: string | null;
}) {
  // Tracks which action (approve vs. decline) is in flight for the
  // currently-resolving card, so the signature motion's colored trailing
  // edge (section 4.3) and the busy button label match the decision that
  // was actually made, not just "some action is happening."
  const [resolvingAction, setResolvingAction] = useState<ResolveAction | null>(null);

  if (status === "loading") {
    return (
      <div className="space-y-3">
        <CardSkeleton />
        <CardSkeleton />
      </div>
    );
  }

  if (status === "error") {
    return (
      <p
        role="alert"
        className="rounded-lg border p-4 text-sm"
        style={{ borderColor: "var(--color-border)", background: "var(--color-tier-red-bg)", color: "var(--color-tier-red-text)" }}
      >
        Failed to load the approval inbox. Check your connection and refresh to try again.
      </p>
    );
  }

  if (cases.length === 0) {
    return (
      <p
        className="rounded-lg border p-4 text-sm"
        style={{ borderColor: "var(--color-border)", background: "var(--color-surface)", color: "var(--color-ink-muted)" }}
      >
        Your queue is caught up. Nothing is waiting on your review right now.
      </p>
    );
  }

  const sorted = [...cases].sort((a, b) => TIER_ORDER[a.tier] - TIER_ORDER[b.tier]);

  function handleResolve(caseId: string, action: ResolveAction) {
    setResolvingAction(action);
    onResolve(caseId, action);
  }

  return (
    <ul className="space-y-3">
      {sorted.map((c) => {
        const resolving = resolvingCaseId === c.caseId;
        // Default to the "approve" flavor of the animation when a caller
        // drives resolvingCaseId externally without going through
        // handleResolve (e.g. a controlled parent, or this component's
        // own loading-state tests) -- decline is only ever chosen once we
        // actually observed a decline click.
        const isDecline = resolving && resolvingAction === "decline";
        const cardClassName = resolving
          ? `rounded-lg border p-4 approval-card-resolving approval-card-resolving--${isDecline ? "decline" : "approve"}`
          : "rounded-lg border p-4";

        return (
          <li
            key={c.caseId}
            data-testid="approval-card"
            className={cardClassName}
            style={{ borderColor: "var(--color-border)", background: "var(--color-surface)" }}
          >
            <div className="mb-2 flex items-center justify-between">
              <TierBadge tier={c.tier} />
              <span className="text-xs" style={{ color: "var(--color-ink-muted)", fontFamily: "var(--font-mono)" }}>
                {c.ageMinutes} min ago
              </span>
            </div>
            <p className="mb-3 text-sm" style={{ color: "var(--color-ink)" }}>{c.summary}</p>

            {c.tier === "YELLOW" && (
              <label
                data-testid="trust-mode-toggle"
                className="mb-3 flex items-center gap-2 text-sm"
                style={{ color: "var(--color-ink-muted)" }}
              >
                <input type="checkbox" className="stacks-focus-ring" />
                Apply automatically for this tool for the rest of my session
              </label>
            )}

            <div className="flex gap-2">
              <button
                type="button"
                className={APPROVE_BUTTON_CLASS}
                style={{
                  background: "var(--color-tier-green-fill)",
                  color: "var(--color-fill-text)",
                  transitionDuration: "var(--motion-duration-feedback)",
                  transitionTimingFunction: "var(--motion-ease-feedback)",
                }}
                disabled={resolving}
                onClick={() => handleResolve(c.caseId, "approve")}
              >
                {resolving && !isDecline ? "Approving..." : "Approve"}
              </button>
              <button
                type="button"
                className={DECLINE_BUTTON_CLASS}
                style={{
                  borderColor: "var(--color-border)",
                  color: "var(--color-ink)",
                  transitionDuration: "var(--motion-duration-feedback)",
                  transitionTimingFunction: "var(--motion-ease-feedback)",
                }}
                disabled={resolving}
                onClick={() => handleResolve(c.caseId, "decline")}
              >
                {isDecline ? "Declining..." : "Decline"}
              </button>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
