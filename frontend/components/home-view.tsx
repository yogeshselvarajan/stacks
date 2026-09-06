import { CardSkeleton } from "./skeletons";

type Status = "loading" | "ready" | "error";
type PendingByTier = { GREEN: number; YELLOW: number; RED: number };

export function HomeView({
  status,
  pendingByTier,
  lastSweepSummary,
}: {
  status: Status;
  pendingByTier: PendingByTier | null;
  lastSweepSummary: string | null;
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
  const green = pendingByTier?.GREEN ?? 0;
  const total = green + yellow + red;

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold" style={{ fontFamily: "var(--font-heading)", color: "var(--color-ink)" }}>
        Welcome back
      </h1>

      {total === 0 ? (
        <p
          className="rounded-lg border p-4 text-sm"
          style={{ borderColor: "var(--color-border)", background: "var(--color-surface)", color: "var(--color-ink-muted)" }}
        >
          All caught up. No pending approvals right now.
        </p>
      ) : (
        <div className="flex gap-4">
          <div
            className="rounded-lg border p-4"
            style={{ borderColor: "var(--color-border)", background: "var(--color-surface)" }}
          >
            <p className="text-xs font-medium uppercase tracking-wide" style={{ color: "var(--color-ink-muted)" }}>
              Yellow tier pending
            </p>
            <p className="text-2xl font-semibold" style={{ color: "var(--color-ink)" }}>{yellow}</p>
          </div>
          <div
            className="rounded-lg border p-4"
            style={{ borderColor: "var(--color-border)", background: "var(--color-surface)" }}
          >
            <p className="text-xs font-medium uppercase tracking-wide" style={{ color: "var(--color-ink-muted)" }}>
              Red tier pending
            </p>
            <p className="text-2xl font-semibold" style={{ color: "var(--color-tier-red-text)" }}>{red}</p>
          </div>
        </div>
      )}

      {lastSweepSummary && (
        <p
          className="rounded-lg border p-4 text-sm"
          style={{ borderColor: "var(--color-border)", background: "var(--color-surface)", color: "var(--color-ink-muted)" }}
        >
          {lastSweepSummary}
        </p>
      )}
    </div>
  );
}
