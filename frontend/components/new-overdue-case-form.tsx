"use client";

import { useState } from "react";
import Link from "next/link";
import { createOverdueCase, CreateOverdueCaseResult } from "@/lib/api/overdue-queue";

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

export function NewOverdueCaseForm({ onCreated }: { onCreated?: () => void }) {
  const [phase, setPhase] = useState<Phase>("collapsed");
  const [patronId, setPatronId] = useState("");
  const [itemId, setItemId] = useState("");
  const [itemType, setItemType] = useState("");
  const [daysOverdue, setDaysOverdue] = useState("");
  const [sensitivityFlag, setSensitivityFlag] = useState(false);
  const [result, setResult] = useState<CreateOverdueCaseResult | null>(null);

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
        + New overdue case
      </button>
    );
  }

  if (phase === "done" && result) {
    return (
      <div
        className="mb-4 rounded-lg border p-4 text-sm"
        style={{ borderColor: "var(--color-border)", background: "var(--color-surface)" }}
      >
        {result.status === "pending_approval" ? (
          <p style={{ color: "var(--color-ink)" }}>
            Case created. Stacks needs a human decision before it escalates.{" "}
            <Link
              href={`/approvals/${result.circulationRecordId}`}
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
            Case created, but Stacks could not complete it automatically. A team member should check the Overdue
            Queue.
          </p>
        ) : (
          <p style={{ color: "var(--color-tier-red-text)" }}>
            Case created, but Stacks could not process it yet. Try again shortly.
          </p>
        )}
        <button
          type="button"
          onClick={() => {
            setPhase("collapsed");
            setPatronId("");
            setItemId("");
            setItemType("");
            setDaysOverdue("");
            setSensitivityFlag(false);
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
          const created = await createOverdueCase({
            patronId,
            itemId,
            itemType,
            daysOverdue: Number(daysOverdue),
            sensitivityFlag,
          });
          setResult(created);
          setPhase("done");
          onCreated?.();
        } catch {
          setPhase("error");
        }
      }}
    >
      <label htmlFor="new-overdue-patron" className="mb-1 block text-sm font-medium" style={{ color: "var(--color-ink)" }}>
        Patron ID
      </label>
      <input
        id="new-overdue-patron"
        required
        className={INPUT_CLASS}
        style={INPUT_STYLE}
        value={patronId}
        onChange={(e) => setPatronId(e.target.value)}
        disabled={busy}
      />

      <label htmlFor="new-overdue-item" className="mb-1 block text-sm font-medium" style={{ color: "var(--color-ink)" }}>
        Item ID
      </label>
      <input
        id="new-overdue-item"
        required
        className={INPUT_CLASS}
        style={INPUT_STYLE}
        value={itemId}
        onChange={(e) => setItemId(e.target.value)}
        disabled={busy}
      />

      <label htmlFor="new-overdue-item-type" className="mb-1 block text-sm font-medium" style={{ color: "var(--color-ink)" }}>
        Item type
      </label>
      <input
        id="new-overdue-item-type"
        required
        className={INPUT_CLASS}
        style={INPUT_STYLE}
        value={itemType}
        onChange={(e) => setItemType(e.target.value)}
        disabled={busy}
      />

      <label htmlFor="new-overdue-days" className="mb-1 block text-sm font-medium" style={{ color: "var(--color-ink)" }}>
        Days overdue
      </label>
      <input
        id="new-overdue-days"
        type="number"
        required
        min="1"
        className={INPUT_CLASS}
        style={INPUT_STYLE}
        value={daysOverdue}
        onChange={(e) => setDaysOverdue(e.target.value)}
        disabled={busy}
      />

      <div className="mb-3 flex items-center gap-2">
        <input
          id="new-overdue-sensitivity"
          type="checkbox"
          className="stacks-focus-ring"
          checked={sensitivityFlag}
          onChange={(e) => setSensitivityFlag(e.target.checked)}
          disabled={busy}
        />
        <label htmlFor="new-overdue-sensitivity" className="text-sm font-medium" style={{ color: "var(--color-ink)" }}>
          Flag as a sensitive account (e.g. a minor)
        </label>
      </div>

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
              setPatronId("");
              setItemId("");
              setItemType("");
              setDaysOverdue("");
              setSensitivityFlag(false);
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
