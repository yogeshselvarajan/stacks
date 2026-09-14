import Link from "next/link";
import { AlertTriangle, Bot, CheckCircle2, Inbox, OctagonAlert } from "lucide-react";
import { Reveal } from "@/components/motion/reveal";
import { CardSkeleton } from "./skeletons";
import { AuditEntry } from "@/lib/api/types";

type Status = "loading" | "ready" | "error";
type PendingByTier = { GREEN: number; YELLOW: number; RED: number };

function KpiCard({
  label, value, valueColor, accentColor, Icon,
}: {
  label: string; value: string | number; valueColor?: string; accentColor: string; Icon: typeof OctagonAlert;
}) {
  return (
    <div
      className="relative overflow-hidden rounded-lg border p-4"
      style={{ borderColor: "var(--color-border)", background: "var(--color-surface)" }}
    >
      <div aria-hidden="true" className="absolute inset-x-0 top-0 h-0.5" style={{ background: accentColor }} />
      <div className="flex items-start justify-between">
        <p className="text-xs font-medium uppercase tracking-wide" style={{ fontFamily: "var(--font-mono)", color: "var(--color-ink-muted)" }}>
          {label}
        </p>
        <Icon size={16} aria-hidden="true" style={{ color: accentColor }} />
      </div>
      <p
        className="mt-2 text-3xl font-semibold"
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
  const needsAttention = yellow + red;

  return (
    <div className="space-y-5">
      <Reveal>
        <h1 className="text-2xl font-semibold" style={{ fontFamily: "var(--font-heading)", color: "var(--color-ink)" }}>
          Welcome back
        </h1>
      </Reveal>

      {/* Attention-first: what needs the staff member right now, before any
          secondary metric. A library staff member's actual first question
          is "what needs me", not "what happened" -- so this is the first
          thing on the page, not a KPI card among equals. This is also the
          one deliberate use of --shadow-floating (the design system's own
          named elevation exception) on this page: the single item that
          actually warrants being lifted above everything else. */}
      <Reveal delayMs={40}>
        {needsAttention > 0 ? (
          <Link
            href="/approvals"
            className="stacks-focus-ring flex items-center justify-between rounded-lg border p-4 transition-colors hover:bg-[var(--color-surface-2)]"
            style={{
              borderColor: "var(--color-tier-red-fill)",
              background: "var(--color-tier-red-bg)",
              boxShadow: "var(--shadow-floating)",
              transitionDuration: "var(--motion-duration-feedback)",
            }}
          >
            <span className="flex items-center gap-3">
              <Inbox size={20} aria-hidden="true" style={{ color: "var(--color-tier-red-text)" }} />
              <span>
                <span className="block text-sm font-semibold" style={{ color: "var(--color-tier-red-text)" }}>
                  Needs your attention
                </span>
                <span className="block text-sm" style={{ color: "var(--color-ink-muted)" }}>
                  {red > 0 && `${red} case${red === 1 ? "" : "s"} awaiting review`}
                  {red > 0 && yellow > 0 && ", "}
                  {yellow > 0 && `${yellow} awaiting confirmation`}
                </span>
              </span>
            </span>
            <span className="text-sm font-medium" style={{ color: "var(--color-accent)" }}>
              Open approval inbox &rarr;
            </span>
          </Link>
        ) : (
          <div
            className="flex items-center gap-3 rounded-lg border p-4"
            style={{ borderColor: "var(--color-border)", background: "var(--color-surface)" }}
          >
            <CheckCircle2 size={20} aria-hidden="true" style={{ color: "var(--color-tier-green-text)" }} />
            <div>
              <p className="text-sm font-semibold" style={{ color: "var(--color-ink)" }}>Nothing needs you right now</p>
              <p className="text-sm" style={{ color: "var(--color-ink-muted)" }}>Every case is either resolved or still routine.</p>
            </div>
          </div>
        )}
      </Reveal>

      <Reveal delayMs={80}>
        <div className={lastSweepSummary ? "grid grid-cols-4 gap-3" : "grid grid-cols-3 gap-3"}>
          <KpiCard label="Red pending" value={red} valueColor="var(--color-tier-red-text)" accentColor="var(--color-tier-red-fill)" Icon={OctagonAlert} />
          <KpiCard label="Yellow pending" value={yellow} valueColor="var(--color-tier-yellow-text)" accentColor="var(--color-tier-yellow-fill)" Icon={AlertTriangle} />
          <KpiCard label="Agent actions today" value={resolvedTodayCount ?? 0} accentColor="var(--color-accent)" Icon={Bot} />
          {lastSweepSummary && (
            <div className="rounded-lg border p-4" style={{ borderColor: "var(--color-border)", background: "var(--color-surface)" }}>
              <p className="text-xs font-medium uppercase tracking-wide" style={{ fontFamily: "var(--font-mono)", color: "var(--color-ink-muted)" }}>
                Last overdue sweep
              </p>
              <p className="mt-2 text-sm" style={{ color: "var(--color-ink)" }}>{lastSweepSummary}</p>
            </div>
          )}
        </div>
      </Reveal>

      <Reveal delayMs={120}>
        <div className="rounded-lg border p-4" style={{ borderColor: "var(--color-border)", background: "var(--color-surface)" }}>
          <p
            className="mb-3 text-xs font-medium uppercase tracking-wide"
            style={{ fontFamily: "var(--font-mono)", color: "var(--color-ink-muted)" }}
          >
            Recent activity
          </p>
          {recentActivity && recentActivity.length > 0 ? (
            <ul className="space-y-2">
              {recentActivity.map((entry) => (
                <li key={entry.auditId} className="flex items-center gap-2 text-sm">
                  <span
                    aria-hidden="true"
                    className="h-1.5 w-1.5 shrink-0 rounded-full"
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
      </Reveal>
    </div>
  );
}
