"use client";

import { useState } from "react";
import { ApprovalCase } from "@/lib/api/types";
import { TierBadge } from "./tier-badge";

type ActionStatus = "idle" | "submitting" | "error";

const WHY_THIS_NEEDS_REVIEW: Record<ApprovalCase["tier"], string> = {
  RED: "This action affects a sensitive record or an external recipient and cannot be automated. A qualified reviewer must decide before anything commits.",
  YELLOW: "Stacks prepared this action and is waiting for your confirmation before it commits.",
  GREEN: "Stacks resolved this automatically. It is shown here only for reference.",
};

const EYEBROW_STYLE: React.CSSProperties = {
  fontFamily: "var(--font-mono)",
  color: "var(--color-ink-faint)",
};

const PRIMARY_BUTTON_CLASS =
  "stacks-focus-ring rounded px-4 py-2 text-sm font-medium transition-all hover:brightness-90 active:brightness-95 disabled:cursor-not-allowed disabled:opacity-60";
const SECONDARY_BUTTON_CLASS =
  "stacks-focus-ring rounded border px-4 py-2 text-sm font-medium transition-colors hover:bg-[var(--color-surface-2)] active:bg-[var(--color-border)] disabled:cursor-not-allowed disabled:opacity-60";

export function ApprovalCaseDetail({
  case: theCase,
  onApprove,
  onDecline,
  onEdit,
  actionStatus,
  resolving,
}: {
  case: ApprovalCase;
  onApprove: (caseId: string) => void;
  onDecline: (caseId: string, reason: string) => void;
  onEdit: (caseId: string, editedValue: string) => void;
  actionStatus: ActionStatus;
  resolving: boolean;
}) {
  const [mode, setMode] = useState<"view" | "edit" | "decline">("view");
  const [editedValue, setEditedValue] = useState(theCase.candidates?.[0]?.id ?? "");
  const [declineReason, setDeclineReason] = useState("");
  const submitting = actionStatus === "submitting";

  return (
    <div className={resolving ? "space-y-4 approval-detail-resolving" : "space-y-4"}>
      <div className="flex items-center justify-between">
        <TierBadge tier={theCase.tier} />
        <span className="text-xs uppercase tracking-wide" style={EYEBROW_STYLE}>Case {theCase.caseId}</span>
      </div>

      <div>
        <p className="mb-1 text-xs font-semibold uppercase tracking-wide" style={EYEBROW_STYLE}>Why this needs review</p>
        <p className="text-sm" style={{ color: "var(--color-ink-muted)" }}>{WHY_THIS_NEEDS_REVIEW[theCase.tier]}</p>
      </div>

      <div>
        <p className="mb-1 text-xs font-semibold uppercase tracking-wide" style={EYEBROW_STYLE}>Proposed action</p>
        <p className="text-sm" style={{ color: "var(--color-ink)" }}>{theCase.summary}</p>
      </div>

      {theCase.tier === "YELLOW" && (
        <label
          data-testid="trust-mode-toggle"
          className="flex items-center gap-2 text-sm"
          style={{ color: "var(--color-ink-muted)" }}
        >
          <input
            type="checkbox"
            className="stacks-focus-ring transition-colors hover:brightness-90 active:brightness-95 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={submitting}
          />
          Apply automatically for this tool for the rest of my session
        </label>
      )}

      {theCase.candidates && (
        <ul className="list-inside list-disc text-sm" style={{ color: "var(--color-ink)" }}>
          {theCase.candidates.map((candidate) => (
            <li key={candidate.id}>{candidate.label}</li>
          ))}
        </ul>
      )}

      {theCase.recallSummary && (
        <div className="rounded-lg border p-3" style={{ borderColor: "var(--color-border)", background: "var(--color-surface-2)" }}>
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide" style={EYEBROW_STYLE}>Context recalled</p>
          <p className="text-sm" style={{ color: "var(--color-ink-muted)" }}>{theCase.recallSummary}</p>
        </div>
      )}

      {actionStatus === "error" && (
        <p
          role="alert"
          className="rounded-lg border p-3 text-sm"
          style={{ borderColor: "var(--color-border)", background: "var(--color-tier-red-bg)", color: "var(--color-tier-red-text)" }}
        >
          Could not submit your decision. Check your connection and try again.
        </p>
      )}

      {mode === "edit" && theCase.candidates && (
        <div className="space-y-2">
          <div>
            <label htmlFor="edit-select" className="mb-1 block text-sm font-medium" style={{ color: "var(--color-ink)" }}>
              Choose a different outcome
            </label>
            <select
              id="edit-select"
              className="stacks-focus-ring w-full rounded border px-3 py-2 text-sm"
              style={{ borderColor: "var(--color-border)", background: "var(--color-surface)", color: "var(--color-ink)" }}
              value={editedValue}
              onChange={(e) => setEditedValue(e.target.value)}
            >
              {theCase.candidates.map((candidate) => (
                <option key={candidate.id} value={candidate.id}>{candidate.label}</option>
              ))}
            </select>
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              className={PRIMARY_BUTTON_CLASS}
              style={{ background: "var(--color-accent)", color: "var(--color-fill-text)" }}
              disabled={submitting}
              onClick={() => onEdit(theCase.caseId, editedValue)}
            >
              {submitting ? "Submitting..." : "Confirm edit"}
            </button>
            <button type="button" className={SECONDARY_BUTTON_CLASS} style={{ borderColor: "var(--color-border)", color: "var(--color-ink)" }} disabled={submitting} onClick={() => setMode("view")}>
              Cancel
            </button>
          </div>
        </div>
      )}

      {mode === "decline" && (
        <div className="space-y-2">
          <div>
            <label htmlFor="decline-reason" className="mb-1 block text-sm font-medium" style={{ color: "var(--color-ink)" }}>
              Reason for declining
            </label>
            <input
              id="decline-reason"
              className="stacks-focus-ring w-full rounded border px-3 py-2 text-sm"
              style={{ borderColor: "var(--color-border)", background: "var(--color-surface)", color: "var(--color-ink)" }}
              value={declineReason}
              onChange={(e) => setDeclineReason(e.target.value)}
            />
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              className={PRIMARY_BUTTON_CLASS}
              style={{ background: "var(--color-tier-red-fill)", color: "var(--color-fill-text)" }}
              disabled={submitting || !declineReason}
              onClick={() => onDecline(theCase.caseId, declineReason)}
            >
              {submitting ? "Submitting..." : "Confirm decline"}
            </button>
            <button type="button" className={SECONDARY_BUTTON_CLASS} style={{ borderColor: "var(--color-border)", color: "var(--color-ink)" }} disabled={submitting} onClick={() => setMode("view")}>
              Cancel
            </button>
          </div>
        </div>
      )}

      {mode === "view" && (
        <div className="flex gap-2">
          <button
            type="button"
            className={PRIMARY_BUTTON_CLASS}
            style={{ background: "var(--color-tier-green-fill)", color: "var(--color-fill-text)" }}
            disabled={submitting}
            onClick={() => onApprove(theCase.caseId)}
          >
            {submitting ? "Approving..." : "Approve"}
          </button>
          <button
            type="button"
            className={SECONDARY_BUTTON_CLASS}
            style={{ borderColor: "var(--color-border)", color: "var(--color-ink)" }}
            disabled={submitting}
            onClick={() => setMode("decline")}
          >
            Decline
          </button>
          {theCase.candidates && (
            <button
              type="button"
              className={SECONDARY_BUTTON_CLASS}
              style={{ borderColor: "var(--color-border)", color: "var(--color-ink)" }}
              disabled={submitting}
              onClick={() => setMode("edit")}
            >
              Edit
            </button>
          )}
        </div>
      )}
    </div>
  );
}
