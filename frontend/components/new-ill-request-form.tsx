"use client";

import { useState } from "react";
import Link from "next/link";
import { createIllRequest, CreateIllRequestResult } from "@/lib/api/ill-queue";

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

export function NewIllRequestForm({ onCreated }: { onCreated?: () => void }) {
  const [phase, setPhase] = useState<Phase>("collapsed");
  const [title, setTitle] = useState("");
  const [editionHint, setEditionHint] = useState("");
  const [patronId, setPatronId] = useState("");
  const [result, setResult] = useState<CreateIllRequestResult | null>(null);

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
        + New request
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
            Case created. Stacks needs a human decision before it routes.{" "}
            <Link
              href={`/approvals/${result.illRequestId}`}
              className="stacks-focus-ring rounded-sm underline-offset-4 hover:underline"
              style={{ color: "var(--color-accent)", fontWeight: 600 }}
            >
              Review in Approval Inbox
            </Link>
          </p>
        ) : result.status === "resolved" ? (
          <p style={{ color: "var(--color-ink)" }}>Resolved automatically. No human review was needed.</p>
        ) : (
          <p style={{ color: "var(--color-tier-red-text)" }}>
            Case created, but Stacks could not process it yet. Try again shortly.
          </p>
        )}
        <button
          type="button"
          onClick={() => {
            setPhase("collapsed");
            setTitle("");
            setEditionHint("");
            setPatronId("");
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
          const created = await createIllRequest({
            requestedTitle: title,
            requestedEditionHint: editionHint || undefined,
            requesterPatronId: patronId,
          });
          setResult(created);
          setPhase("done");
          onCreated?.();
        } catch {
          setPhase("error");
        }
      }}
    >
      <label htmlFor="new-ill-title" className="mb-1 block text-sm font-medium" style={{ color: "var(--color-ink)" }}>
        Title
      </label>
      <input
        id="new-ill-title"
        required
        className={INPUT_CLASS}
        style={INPUT_STYLE}
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        disabled={busy}
      />

      <label htmlFor="new-ill-edition" className="mb-1 block text-sm font-medium" style={{ color: "var(--color-ink)" }}>
        Edition hint (optional)
      </label>
      <input
        id="new-ill-edition"
        className={INPUT_CLASS}
        style={INPUT_STYLE}
        value={editionHint}
        onChange={(e) => setEditionHint(e.target.value)}
        disabled={busy}
      />

      <label htmlFor="new-ill-patron" className="mb-1 block text-sm font-medium" style={{ color: "var(--color-ink)" }}>
        Requester patron ID
      </label>
      <input
        id="new-ill-patron"
        required
        className={INPUT_CLASS}
        style={INPUT_STYLE}
        value={patronId}
        onChange={(e) => setPatronId(e.target.value)}
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
            onClick={() => setPhase("collapsed")}
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
