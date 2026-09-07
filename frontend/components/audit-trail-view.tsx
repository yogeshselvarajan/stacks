import { AuditEntry } from "@/lib/api/types";
import { TierBadge } from "./tier-badge";
import { RowSkeleton } from "./skeletons";

type Status = "loading" | "ready" | "error";

const TIMESTAMP_STYLE: React.CSSProperties = {
  fontVariantNumeric: "tabular-nums",
  fontFamily: "var(--font-mono)",
};

export function AuditTrailView({
  entries,
  status,
  mode,
}: {
  entries: AuditEntry[];
  status: Status;
  mode: "list" | "trace";
}) {
  if (status === "error") {
    return (
      <p
        role="alert"
        className="rounded-lg border p-4 text-sm"
        style={{ borderColor: "var(--color-border)", background: "var(--color-tier-red-bg)", color: "var(--color-tier-red-text)" }}
      >
        Failed to load the audit trail. Check your connection and refresh to try again.
      </p>
    );
  }

  if (mode === "trace") {
    if (status === "loading") {
      return (
        <ol className="space-y-3 border-l-2 pl-4" style={{ borderColor: "var(--color-border)" }}>
          {Array.from({ length: 3 }).map((_, i) => (
            <li key={i}>
              <div data-testid="skeleton-line" className="mb-1 h-3 w-24 animate-pulse rounded" style={{ background: "var(--color-surface-2)" }} />
              <div data-testid="skeleton-line" className="h-4 w-2/3 animate-pulse rounded" style={{ background: "var(--color-surface-2)" }} />
            </li>
          ))}
        </ol>
      );
    }

    if (entries.length === 0) {
      return (
        <p
          className="rounded-lg border p-4 text-sm"
          style={{ borderColor: "var(--color-border)", background: "var(--color-surface)", color: "var(--color-ink-muted)" }}
        >
          No audit entries match this case yet. Actions taken on it will appear here as soon as the agent or a staff member acts.
        </p>
      );
    }

    // Chronological, regardless of the order the caller passed entries in:
    // the sequence field is the authoritative order within a case trace.
    const chronological = [...entries].sort((a, b) => a.sequence - b.sequence);

    return (
      <ol className="space-y-3 border-l-2 pl-4" style={{ borderColor: "var(--color-border)" }}>
        {chronological.map((e) => (
          <li key={e.auditId}>
            <span className="block text-xs" style={TIMESTAMP_STYLE}>
              {e.timestamp}
            </span>
            <p style={{ color: "var(--color-ink)" }}>
              <strong style={{ fontFamily: "var(--font-mono)" }}>{e.toolName}</strong>: {e.outcome}{" "}
              <span style={{ color: "var(--color-ink-muted)" }}>
                ({e.actor === "HUMAN" ? e.actorIdentity : "agent"})
              </span>
            </p>
            {e.hitlTier && (
              <div className="mt-1">
                <TierBadge tier={e.hitlTier} />
              </div>
            )}
          </li>
        ))}
      </ol>
    );
  }

  return (
    <table className="w-full text-sm" style={{ borderCollapse: "collapse" }}>
      <thead>
        <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
          <th className="px-4 py-2 text-left" style={{ color: "var(--color-ink-muted)" }}>#</th>
          <th className="px-4 py-2 text-left" style={{ color: "var(--color-ink-muted)" }}>Tool</th>
          <th className="px-4 py-2 text-left" style={{ color: "var(--color-ink-muted)" }}>Outcome</th>
          <th className="px-4 py-2 text-left" style={{ color: "var(--color-ink-muted)" }}>Tier</th>
          <th className="px-4 py-2 text-left" style={{ color: "var(--color-ink-muted)" }}>Actor</th>
          <th className="px-4 py-2 text-left" style={{ color: "var(--color-ink-muted)" }}>Timestamp</th>
        </tr>
      </thead>
      <tbody>
        {status === "loading" &&
          Array.from({ length: 3 }).map((_, i) => <RowSkeleton key={i} columns={6} />)}
        {status === "ready" && entries.length === 0 && (
          <tr>
            <td colSpan={6} className="px-4 py-6 text-center" style={{ color: "var(--color-ink-muted)" }}>
              No audit entries match the current filters. Adjust the date range or workflow filter.
            </td>
          </tr>
        )}
        {status === "ready" &&
          entries.map((e) => (
            <tr key={e.auditId} style={{ borderBottom: "1px solid var(--color-border)" }}>
              <td className="px-4 py-2" style={{ fontVariantNumeric: "tabular-nums" }}>{e.sequence}</td>
              <td className="px-4 py-2" style={{ fontFamily: "var(--font-mono)" }}>{e.toolName}</td>
              <td className="px-4 py-2">{e.outcome}</td>
              <td className="px-4 py-2">{e.hitlTier && <TierBadge tier={e.hitlTier} />}</td>
              <td className="px-4 py-2">{e.actor === "HUMAN" ? e.actorIdentity : "Agent"}</td>
              <td className="px-4 py-2" style={TIMESTAMP_STYLE}>{e.timestamp}</td>
            </tr>
          ))}
      </tbody>
    </table>
  );
}
