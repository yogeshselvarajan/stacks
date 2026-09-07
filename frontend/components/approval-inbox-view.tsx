import Link from "next/link";
import { ApprovalCase, Tier } from "@/lib/api/types";
import { ListRowSkeleton } from "./skeletons";

type Status = "loading" | "ready" | "error";

const TIER_ORDER: Record<string, number> = { RED: 0, YELLOW: 1, GREEN: 2 };
const TIER_DOT_COLOR: Record<Tier, string> = {
  RED: "var(--color-tier-red-fill)",
  YELLOW: "var(--color-tier-yellow-fill)",
  GREEN: "var(--color-tier-green-fill)",
};

const ROW_CLASS =
  "stacks-focus-ring flex items-center gap-2 rounded-md px-3 py-2.5 text-sm transition-colors hover:bg-[var(--color-surface-2)] active:bg-[var(--color-border)]";

export function ApprovalInboxView({
  cases,
  status,
  activeCaseId,
  resolvingCaseId,
}: {
  cases: ApprovalCase[];
  status: Status;
  activeCaseId: string | null;
  resolvingCaseId: string | null;
}) {
  if (status === "loading") {
    return (
      <div className="space-y-0.5">
        <ListRowSkeleton />
        <ListRowSkeleton />
        <ListRowSkeleton />
      </div>
    );
  }

  if (status === "error") {
    return (
      <p
        role="alert"
        className="rounded-lg border p-3 text-sm"
        style={{ borderColor: "var(--color-border)", background: "var(--color-tier-red-bg)", color: "var(--color-tier-red-text)" }}
      >
        Failed to load the approval inbox. Refresh to try again.
      </p>
    );
  }

  if (cases.length === 0) {
    return (
      <p
        className="rounded-lg border p-3 text-sm"
        style={{ borderColor: "var(--color-border)", color: "var(--color-ink-muted)" }}
      >
        Your queue is caught up. Nothing is waiting on your review right now.
      </p>
    );
  }

  const sorted = [...cases].sort((a, b) => TIER_ORDER[a.tier] - TIER_ORDER[b.tier]);

  return (
    <ul className="space-y-0.5">
      {sorted.map((c) => {
        const active = activeCaseId === c.caseId;
        const resolving = resolvingCaseId === c.caseId;
        const className = resolving ? `${ROW_CLASS} approval-row-collapsing` : ROW_CLASS;

        return (
          <li key={c.caseId}>
            <Link
              href={`/approvals/${encodeURIComponent(c.caseId)}`}
              data-testid="approval-row"
              className={className}
              style={{
                transitionDuration: "var(--motion-duration-feedback)",
                transitionTimingFunction: "var(--motion-ease-feedback)",
                color: "var(--color-ink)",
                background: active ? "var(--color-surface-2)" : "transparent",
              }}
            >
              <span
                data-testid="tier-dot"
                aria-hidden="true"
                className="h-1.5 w-1.5 shrink-0 rounded-full"
                style={{ background: TIER_DOT_COLOR[c.tier] }}
              />
              <span className="sr-only">
                {c.tier === "RED" ? "Requires review" : c.tier === "YELLOW" ? "Awaiting confirmation" : "Auto-executed"}
              </span>
              <span className="truncate">{c.summary}</span>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
