import { ArrowRight } from "lucide-react";
import { ScrollReveal } from "@/components/motion/scroll-reveal";

const BEFORE_STEPS = ["Request", "Rule", "No match", "Review queue", "Staff"];
const AFTER_STEPS = ["Request", "Context", "Policy", "Specialist", "Safety", "Resolution"];

function FlowColumn({ label, steps, tone }: { label: string; steps: string[]; tone: "muted" | "accent" }) {
  return (
    <div
      className="rounded-2xl border p-6"
      style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}
    >
      <p className="mb-4 text-xs font-semibold uppercase tracking-wide" style={{ fontFamily: "var(--font-mono)", color: "var(--color-ink-faint)" }}>
        {label}
      </p>
      <ol className="space-y-2">
        {steps.map((step, i) => {
          const isLast = i === steps.length - 1;
          const isTerminal = isLast && tone === "muted";
          const isResolution = isLast && tone === "accent";
          return (
            <li key={step} className="flex items-center gap-2">
              <span
                className="rounded-md px-3 py-1.5 text-sm"
                style={{
                  fontFamily: isTerminal || isResolution ? "var(--font-mono)" : undefined,
                  fontWeight: isTerminal || isResolution ? 600 : 400,
                  color: isTerminal ? "var(--color-tier-red-text)" : isResolution ? "var(--color-tier-green-text)" : "var(--color-ink)",
                  background: isTerminal ? "var(--color-tier-red-bg)" : isResolution ? "var(--color-tier-green-bg)" : "var(--color-surface-2)",
                }}
              >
                {step}
              </span>
              {!isLast && <ArrowRight size={14} aria-hidden="true" style={{ color: "var(--color-ink-faint)" }} />}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

export function StartsWhereTheyStop() {
  return (
    <section id="how-it-works" className="px-6 py-24" style={{ background: "var(--color-surface)" }}>
      <div className="mx-auto max-w-5xl">
        <ScrollReveal>
          <p className="text-sm font-semibold uppercase tracking-wide" style={{ fontFamily: "var(--font-mono)", color: "var(--color-accent)" }}>
            The difference
          </p>
          <h2 className="mt-2 max-w-2xl text-3xl" style={{ fontFamily: "var(--font-heading)", color: "var(--color-ink)", fontWeight: 600 }}>
            Stacks starts where the existing system stops.
          </h2>
        </ScrollReveal>

        <ScrollReveal className="mt-10 grid gap-6 md:grid-cols-2" stagger={0.15}>
          <FlowColumn label="Without Stacks" steps={BEFORE_STEPS} tone="muted" />
          <FlowColumn label="With Stacks" steps={AFTER_STEPS} tone="accent" />
        </ScrollReveal>
      </div>
    </section>
  );
}
