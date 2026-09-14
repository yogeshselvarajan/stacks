// frontend/components/ill-queue-view.tsx
"use client";

import { Fragment, useState } from "react";
import { BrainCircuit, ChevronDown, ChevronRight } from "lucide-react";
import { IllRequest } from "@/lib/api/types";
import { TierBadge } from "./tier-badge";
import { RowSkeleton } from "./skeletons";

type Status = "loading" | "ready" | "error" | "forbidden";

// Craft-bar item (frontend_architecture.md section 7.4 / the plan's Global
// Constraint on six-state interactive elements): the row-expand toggle
// needs the full default/hover/focus/active/disabled/loading treatment,
// not just a bare onClick.
// default: EXPAND_TRIGGER_CLASS's base layout/color styling below.
// hover: hover:brightness-90.
// focus (keyboard): stacks-focus-ring (Task 7's shared custom focus ring).
// active/pressed: active:brightness-95.
// disabled: a request with no specialistTrace has nothing to expand into,
// so it renders as a plain, non-interactive <span aria-disabled="true">
// instead of a <button>, mirroring calendar-view's PendingReviewBadge.
// loading: this trigger only ever renders once the table is in its
// "ready" state; while loading, RowSkeleton stands in for the whole row,
// mirroring the same reasoning calendar-view documents for its own link.
const EXPAND_TRIGGER_CLASS =
  "stacks-focus-ring flex w-full items-center gap-1.5 rounded px-1 py-1 text-left transition-all hover:brightness-90 active:brightness-95";
const EXPAND_DISABLED_CLASS = "flex items-center gap-1.5 px-1 py-1 opacity-60";

function formatRequestedDate(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric" }).format(date);
}

const STATUS_LABELS: Record<IllRequest["status"], string> = {
  open: "Open",
  routed: "Routed",
  no_match: "No match found",
};

const STATUS_DOT_COLORS: Record<IllRequest["status"], string> = {
  open: "var(--color-ink-faint)",
  routed: "var(--color-tier-green-fill)",
  no_match: "var(--color-tier-yellow-fill)",
};

export function IllQueueView({ requests, status }: { requests: IllRequest[]; status: Status }) {
  const [expanded, setExpanded] = useState<string | null>(null);

  if (status === "forbidden") {
    return (
      <p
        role="alert"
        className="rounded-lg border p-4 text-sm"
        style={{ borderColor: "var(--color-border)", background: "var(--color-tier-red-bg)", color: "var(--color-tier-red-text)" }}
      >
        You do not have access to this workflow.
      </p>
    );
  }

  if (status === "error") {
    return (
      <p
        role="alert"
        className="rounded-lg border p-4 text-sm"
        style={{ borderColor: "var(--color-border)", background: "var(--color-tier-red-bg)", color: "var(--color-tier-red-text)" }}
      >
        Failed to load the ILL queue. Refresh to try again.
      </p>
    );
  }

  return (
    <table className="w-full text-sm" style={{ borderCollapse: "collapse" }}>
      <thead>
        <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
          <th className="px-4 py-2 text-left" style={{ color: "var(--color-ink-muted)" }}>Title</th>
          <th className="px-4 py-2 text-left" style={{ color: "var(--color-ink-muted)" }}>Requester</th>
          <th className="px-4 py-2 text-left" style={{ color: "var(--color-ink-muted)" }}>Requested</th>
          <th className="px-4 py-2 text-left" style={{ color: "var(--color-ink-muted)" }}>Status</th>
        </tr>
      </thead>
      <tbody>
        {status === "loading" && Array.from({ length: 3 }).map((_, i) => <RowSkeleton key={i} columns={4} />)}
        {status === "ready" && requests.length === 0 && (
          <tr>
            <td colSpan={4} className="px-4 py-6 text-center" style={{ color: "var(--color-ink-muted)" }}>
              No ILL requests match the current filter. Try a different status.
            </td>
          </tr>
        )}
        {status === "ready" &&
          requests.map((r) => {
            const isExpanded = expanded === r.illRequestId;
            const canExpand = Boolean(r.specialistTrace);
            const detailId = `ill-detail-${r.illRequestId}`;

            return (
              <Fragment key={r.illRequestId}>
                <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
                  <td className="px-4 py-2">
                    {canExpand ? (
                      <button
                        type="button"
                        className={EXPAND_TRIGGER_CLASS}
                        style={{
                          color: "var(--color-ink)",
                          transitionDuration: "var(--motion-duration-feedback)",
                          transitionTimingFunction: "var(--motion-ease-feedback)",
                        }}
                        aria-expanded={isExpanded}
                        aria-controls={detailId}
                        onClick={() => setExpanded(isExpanded ? null : r.illRequestId)}
                      >
                        {isExpanded ? (
                          <ChevronDown size={16} aria-hidden="true" />
                        ) : (
                          <ChevronRight size={16} aria-hidden="true" />
                        )}
                        {r.requestedTitle}
                      </button>
                    ) : (
                      <span data-testid="expand-disabled" aria-disabled="true" className={EXPAND_DISABLED_CLASS}>
                        <ChevronRight size={16} aria-hidden="true" style={{ opacity: 0.5 }} />
                        {r.requestedTitle}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2" style={{ color: "var(--color-ink)" }}>{r.requesterName}</td>
                  <td className="px-4 py-2" style={{ fontVariantNumeric: "tabular-nums", color: "var(--color-ink-muted)" }}>
                    {formatRequestedDate(r.requestedAt)}
                  </td>
                  <td className="px-4 py-2">
                    {r.tier ? (
                      <TierBadge tier={r.tier} />
                    ) : (
                      <span className="inline-flex items-center gap-1.5">
                        <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full" style={{ background: STATUS_DOT_COLORS[r.status] }} />
                        <span style={{ color: "var(--color-ink-muted)" }}>{STATUS_LABELS[r.status]}</span>
                      </span>
                    )}
                  </td>
                </tr>
                {isExpanded && r.specialistTrace && (
                  <tr id={detailId}>
                    <td colSpan={4} className="px-4 py-3" style={{ background: "var(--color-surface-2)" }}>
                      {/* frontend_architecture.md section 7.5: the specialist's own
                          reasoning trace is a distinctly labeled block, never folded
                          silently into a top-level rationale. */}
                      <p className="mb-2 text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--color-ink-muted)" }}>
                        The specialist&apos;s reasoning
                      </p>
                      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm" style={{ fontFamily: "var(--font-mono)" }}>
                        <dt style={{ color: "var(--color-ink-muted)" }}>narrowed_candidate_id</dt>
                        <dd>{r.specialistTrace.narrowedCandidateId ?? "none"}</dd>
                        <dt style={{ color: "var(--color-ink-muted)" }}>confidence</dt>
                        <dd>{r.specialistTrace.confidence ?? "n/a"}</dd>
                        <dt style={{ color: "var(--color-ink-muted)" }}>still_ambiguous</dt>
                        <dd>{r.specialistTrace.stillAmbiguous ? "true" : "false"}</dd>
                      </dl>

                      {r.recallSummary && (
                        <div
                          data-testid="memory-recall-indicator"
                          className="mt-3 flex items-start gap-1.5 rounded-lg border p-2 text-sm"
                          style={{ borderColor: "var(--color-border)", background: "var(--color-surface)", color: "var(--color-ink-muted)" }}
                        >
                          <BrainCircuit size={14} aria-hidden="true" style={{ marginTop: 2, flexShrink: 0 }} />
                          <p>
                            <span className="font-semibold" style={{ color: "var(--color-ink)" }}>Memory recall: </span>
                            {r.recallSummary}
                          </p>
                        </div>
                      )}
                    </td>
                  </tr>
                )}
              </Fragment>
            );
          })}
      </tbody>
    </table>
  );
}
