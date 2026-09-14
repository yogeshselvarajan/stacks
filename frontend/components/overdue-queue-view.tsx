// frontend/components/overdue-queue-view.tsx
import { CheckCircle2, Clock, AlertTriangle, BrainCircuit } from "lucide-react";
import { OverdueCase } from "@/lib/api/types";
import { CardSkeleton } from "./skeletons";

type Status = "loading" | "ready" | "error" | "forbidden";
type StepStatus = OverdueCase["tierHistory"][number]["status"];

// frontend_architecture.md section 7.6: "Tier 1 sent -> Tier 2 pending -> ..."
// or, for a flagged case, "Tier 1 sent -> held for review (RED)". Each step
// is rendered as label + status in separate elements (not one flat status
// string) so the tier progression is legible step by step, not collapsed
// into a single word.
const STEP_CONFIG: Record<StepStatus, { text: string; Icon: typeof CheckCircle2; colorVar: string }> = {
  sent: { text: "sent", Icon: CheckCircle2, colorVar: "var(--color-tier-green-text)" },
  pending: { text: "pending", Icon: Clock, colorVar: "var(--color-ink-muted)" },
  held_for_review: { text: "held for review", Icon: AlertTriangle, colorVar: "var(--color-tier-red-text)" },
};

export function OverdueQueueView({ cases, status }: { cases: OverdueCase[]; status: Status }) {
  if (status === "loading") {
    return (
      <div className="space-y-3">
        <CardSkeleton />
        <CardSkeleton />
      </div>
    );
  }

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
        Failed to load the overdue queue. Refresh to try again.
      </p>
    );
  }

  if (cases.length === 0) {
    return (
      <p className="rounded-lg border p-4 text-sm" style={{ borderColor: "var(--color-border)", color: "var(--color-ink-muted)" }}>
        No overdue cases right now.
      </p>
    );
  }

  return (
    <ul className="space-y-3">
      {cases.map((c) => (
        <li key={c.circulationRecordId} className="rounded-lg border p-4" style={{ borderColor: "var(--color-border)" }}>
          <p className="font-medium" style={{ color: "var(--color-ink)" }}>
            {c.itemTitle} &middot; {c.patronName}
          </p>
          <p className="mb-3 font-mono text-xs" style={{ color: "var(--color-ink-muted)" }}>
            {c.circulationRecordId}
          </p>

          {/* The Sequencer's own per-case tier_history, rendered as a
              step-tracker (not a plain status string). */}
          <ol className="flex flex-wrap items-center gap-x-1.5 gap-y-1.5 text-sm" aria-label="Escalation tier history">
            {c.tierHistory.map((step, i) => {
              const config = STEP_CONFIG[step.status];
              const Icon = config.Icon;
              return (
                <li key={step.tierIndex} className="flex items-center gap-1.5">
                  <span className="flex items-center gap-1.5 rounded px-2 py-1" style={{ background: "var(--color-surface-2)" }}>
                    <Icon size={14} aria-hidden="true" style={{ color: config.colorVar, flexShrink: 0 }} />
                    <span className="font-medium" style={{ color: "var(--color-ink)" }}>
                      {step.label}
                    </span>
                    <span style={{ color: config.colorVar }}>{config.text}</span>
                  </span>
                  {i < c.tierHistory.length - 1 && (
                    <span aria-hidden="true" style={{ color: "var(--color-ink-muted)" }}>
                      &rarr;
                    </span>
                  )}
                </li>
              );
            })}
          </ol>

          {c.recallSummary && (
            <div
              data-testid="memory-recall-indicator"
              className="mt-3 flex items-start gap-1.5 rounded-lg border p-2 text-sm"
              style={{ borderColor: "var(--color-border)", background: "var(--color-surface)", color: "var(--color-ink-muted)" }}
            >
              <BrainCircuit size={14} aria-hidden="true" style={{ marginTop: 2, flexShrink: 0 }} />
              <p>
                <span className="font-semibold" style={{ color: "var(--color-ink)" }}>
                  Memory recall:{" "}
                </span>
                {c.recallSummary}
              </p>
            </div>
          )}
        </li>
      ))}
    </ul>
  );
}
