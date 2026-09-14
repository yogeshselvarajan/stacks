import { ScrollReveal } from "@/components/motion/scroll-reveal";

export function PolicySection() {
  return (
    <section className="px-6 py-24">
      <div className="mx-auto grid max-w-5xl items-center gap-10 lg:grid-cols-2">
        <ScrollReveal>
          <p className="text-sm font-semibold uppercase tracking-wide" style={{ fontFamily: "var(--font-mono)", color: "var(--color-accent)" }}>
            Policy
          </p>
          <h2 className="mt-2 text-3xl" style={{ fontFamily: "var(--font-heading)", color: "var(--color-ink)", fontWeight: 600 }}>
            Stacks doesn&apos;t invent the rule. It cites the rule.
          </h2>
          <p className="mt-4 text-base leading-relaxed" style={{ color: "var(--color-ink-muted)" }}>
            Every resolution names the exact policy clause it applied, verbatim, the same
            clause a staff member sees in the real approval screen. Not a generic
            explanation after the fact: the rationale is required before the tool
            will commit anything.
          </p>
        </ScrollReveal>

        <ScrollReveal>
          <div
            className="rounded-2xl border p-6"
            style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}
          >
            <p className="mb-1 text-xs font-semibold uppercase tracking-wide" style={{ fontFamily: "var(--font-mono)", color: "var(--color-ink-faint)" }}>
              Policy applied
            </p>
            <p className="text-sm" style={{ color: "var(--color-ink-muted)" }}>
              <span style={{ fontFamily: "var(--font-mono)", color: "var(--color-ink)" }}>RBP-1</span>
              {": "}A recurring, library-run program outranks a one-off renter or walk-in
              booking for the same slot.
            </p>
            <p className="mt-4 text-xs" style={{ color: "var(--color-ink-faint)" }}>
              Shown exactly as it appears on a real case in the Stacks console.
            </p>
          </div>
        </ScrollReveal>
      </div>
    </section>
  );
}
