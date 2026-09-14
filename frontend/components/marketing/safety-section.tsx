import { ArrowDown } from "lucide-react";
import { ScrollReveal } from "@/components/motion/scroll-reveal";
import { TierBadge } from "@/components/tier-badge";

export function SafetySection() {
  return (
    <section id="safety" className="px-6 py-24" style={{ background: "var(--color-surface)" }}>
      <div className="mx-auto max-w-4xl">
        <ScrollReveal>
          <p className="text-sm font-semibold uppercase tracking-wide" style={{ fontFamily: "var(--font-mono)", color: "var(--color-accent)" }}>
            Safety
          </p>
          <h2 className="mt-2 max-w-2xl text-3xl" style={{ fontFamily: "var(--font-heading)", color: "var(--color-ink)", fontWeight: 600 }}>
            The model doesn&apos;t choose its own safety tier.
          </h2>
          <p className="mt-4 max-w-2xl text-base leading-relaxed" style={{ color: "var(--color-ink-muted)" }}>
            A plain, deterministic classifier, ordinary code with no model call in it,
            decides GREEN, YELLOW, or RED for every case. The agent cannot argue with it,
            and it cannot be prompted around.
          </p>
        </ScrollReveal>

        <ScrollReveal className="mt-10 flex flex-col items-center gap-3" stagger={0.1}>
          <span
            className="rounded-lg border px-4 py-2 text-sm"
            style={{ borderColor: "var(--color-border)", color: "var(--color-ink)", fontFamily: "var(--font-mono)" }}
          >
            Case + sensitivity signals
          </span>
          <ArrowDown size={16} aria-hidden="true" style={{ color: "var(--color-ink-faint)" }} />
          <span
            className="rounded-lg border-2 px-4 py-2 text-sm font-semibold"
            style={{ borderColor: "var(--color-accent)", color: "var(--color-accent)" }}
          >
            Code-governed gate
          </span>
          <ArrowDown size={16} aria-hidden="true" style={{ color: "var(--color-ink-faint)" }} />
          <div className="flex flex-wrap items-center justify-center gap-3">
            <TierBadge tier="GREEN" />
            <TierBadge tier="YELLOW" />
            <TierBadge tier="RED" />
          </div>
        </ScrollReveal>
      </div>
    </section>
  );
}
