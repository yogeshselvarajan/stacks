import { ScrollReveal } from "@/components/motion/scroll-reveal";
import { TierBadge } from "@/components/tier-badge";

// Illustrative of a real case's shape (matches AuditTrailView's own trace
// rendering exactly), not a live feed -- labeled as such below.
const ENTRIES = [
  { time: "09:41:02", label: "Case received", tier: null },
  { time: "09:41:03", label: "Policy evaluated", tier: null },
  { time: "09:41:03", label: "Context recalled", tier: null },
  { time: "09:41:04", label: "ILL specialist consulted", tier: null },
  { time: "09:41:05", label: "Safety classified", tier: "GREEN" as const },
  { time: "09:41:05", label: "Route committed", tier: null },
];

export function AuditPreview() {
  return (
    <section className="px-6 py-24" style={{ background: "var(--color-surface)" }}>
      <div className="mx-auto max-w-3xl">
        <ScrollReveal>
          <p className="text-sm font-semibold uppercase tracking-wide" style={{ fontFamily: "var(--font-mono)", color: "var(--color-accent)" }}>
            Audit
          </p>
          <h2 className="mt-2 text-3xl" style={{ fontFamily: "var(--font-heading)", color: "var(--color-ink)", fontWeight: 600 }}>
            Every case leaves a record, not a mystery.
          </h2>
          <p className="mt-4 max-w-2xl text-base leading-relaxed" style={{ color: "var(--color-ink-muted)" }}>
            A staff member can always answer &quot;why did Stacks do that&quot; from structured
            evidence, policy matched, context used, specialist consulted, safety classified,
            action taken, never from exposed model reasoning.
          </p>
        </ScrollReveal>

        <ScrollReveal className="mt-8 space-y-3 border-l-2 pl-4" stagger={0.06}>
          {ENTRIES.map((entry) => (
            <div key={entry.time + entry.label}>
              <span className="block text-xs" style={{ fontVariantNumeric: "tabular-nums", fontFamily: "var(--font-mono)", color: "var(--color-ink-faint)" }}>
                {entry.time}
              </span>
              <p className="text-sm" style={{ color: "var(--color-ink)" }}>{entry.label}</p>
              {entry.tier && (
                <div className="mt-1">
                  <TierBadge tier={entry.tier} />
                </div>
              )}
            </div>
          ))}
        </ScrollReveal>

        <p className="mt-6 text-xs" style={{ color: "var(--color-ink-faint)" }}>
          Illustrative sequence for a single ILL case. Real audit records are DynamoDB-backed and per-tool-call.
        </p>
      </div>
    </section>
  );
}
