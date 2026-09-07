import { CardSkeleton } from "./skeletons";
import { AuditEntry } from "@/lib/api/types";

type Status = "loading" | "ready" | "error";
type PendingByTier = { GREEN: number; YELLOW: number; RED: number };

function KpiCard({ label, value, valueColor }: { label: string; value: string | number; valueColor?: string }) {
  return (
    <div className="rounded-lg border p-3" style={{ borderColor: "var(--color-border)", background: "var(--color-surface)" }}>
      <p className="text-xs font-medium uppercase tracking-wide" style={{ fontFamily: "var(--font-mono)", color: "var(--color-ink-muted)" }}>
        {label}
      </p>
      <p
        className="text-xl font-semibold"
        style={{ fontFamily: "var(--font-heading)", color: valueColor ?? "var(--color-ink)", fontVariantNumeric: "tabular-nums" }}
      >
        {value}
      </p>
    </div>
  );
}

export function HomeView({
  status,
  pendingByTier,
  lastSweepSummary,
  resolvedTodayCount,
  recentActivity,
}: {
  status: Status;
  pendingByTier: PendingByTier | null;
  lastSweepSummary: string | null;
  resolvedTodayCount: number | null;
  recentActivity: AuditEntry[] | null;
}) {
  if (status === "loading") {
    return <CardSkeleton />;
  }

  if (status === "error") {
    return (
      <p
        role="alert"
        className="rounded-lg border p-4 text-sm"
        style={{ borderColor: "var(--color-border)", color: "var(--color-tier-red-text)", background: "var(--color-tier-red-bg)" }}
      >
        Failed to load your dashboard. Refresh the page to try again.
      </p>
    );
  }

  const yellow = pendingByTier?.YELLOW ?? 0;
  const red = pendingByTier?.RED ?? 0;

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold" style={{ fontFamily: "var(--font-heading)", color: "var(--color-ink)" }}>
        Welcome back
      </h1>

      <div className="grid grid-cols-4 gap-3">
        <KpiCard label="Red pending" value={red} valueColor="var(--color-tier-red-text)" />
        <KpiCard label="Yellow pending" value={yellow} valueColor="var(--color-tier-yellow-text)" />
        <KpiCard label="Resolved today" value={resolvedTodayCount ?? 0} />
        {lastSweepSummary && (
          <div className="rounded-lg border p-3" style={{ borderColor: "var(--color-border)", background: "var(--color-surface)" }}>
            <p className="text-xs font-medium uppercase tracking-wide" style={{ fontFamily: "var(--font-mono)", color: "var(--color-ink-muted)" }}>
              Last overdue sweep
            </p>
            <p className="text-sm" style={{ color: "var(--color-ink)" }}>{lastSweepSummary}</p>
          </div>
        )}
      </div>

      <div className="rounded-lg border p-3" style={{ borderColor: "var(--color-border)", background: "var(--color-surface)" }}>
        <p
          className="mb-2 text-xs font-medium uppercase tracking-wide"
          style={{ fontFamily: "var(--font-mono)", color: "var(--color-ink-muted)" }}
        >
          Activity
        </p>
        {recentActivity && recentActivity.length > 0 ? (
          <ul className="space-y-1.5">
            {recentActivity.map((entry) => (
              <li key={entry.auditId} className="flex items-center gap-2 text-sm">
                <span
                  aria-hidden="true"
                  className="h-1 w-1 shrink-0 rounded-full"
                  style={{ background: entry.actor === "HUMAN" ? "var(--color-accent)" : "var(--color-tier-green-fill)" }}
                />
                <span style={{ color: "var(--color-ink-muted)" }}>
                  <span style={{ fontFamily: "var(--font-mono)", color: "var(--color-ink)" }}>{entry.toolName}</span>: {entry.outcome}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm" style={{ color: "var(--color-ink-muted)" }}>
            No activity yet. Once the agent starts processing cases, you will see them here.
          </p>
        )}
      </div>
    </div>
  );
}
