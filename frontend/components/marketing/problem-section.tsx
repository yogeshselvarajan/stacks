import { ScrollReveal } from "@/components/motion/scroll-reveal";
import { SourceLink } from "@/components/marketing/source-link";

export function ProblemSection() {
  return (
    <section className="px-6 py-24">
      <ScrollReveal className="mx-auto max-w-3xl">
        <p className="text-sm font-semibold uppercase tracking-wide" style={{ fontFamily: "var(--font-mono)", color: "var(--color-accent)" }}>
          The problem
        </p>
        <h2 className="mt-2 text-3xl" style={{ fontFamily: "var(--font-heading)", color: "var(--color-ink)", fontWeight: 600 }}>
          Every library system has an exception queue.
        </h2>
        <p className="mt-4 text-base leading-relaxed" style={{ color: "var(--color-ink-muted)" }}>
          Room-booking software, interlibrary-loan platforms, and ILS overdue modules already
          automate the routine case well. What they hand back is the case a rule could not
          fire on: an incomplete citation, a genuine policy conflict, a patron history that
          changes what the right action is.
        </p>

        <div className="mt-8 space-y-3" role="img" aria-label="Routine work is mostly automated already; the exception queue is what is left over, unresolved">
          <div>
            <div className="mb-1 flex items-center justify-between text-xs" style={{ fontFamily: "var(--font-mono)", color: "var(--color-ink-faint)" }}>
              <span>ROUTINE, ALREADY AUTOMATED</span>
              <span>~70%</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full" style={{ background: "var(--color-surface-2)" }}>
              <div className="h-full rounded-full" style={{ width: "70%", background: "var(--color-tier-green-fill)" }} />
            </div>
          </div>
          <div>
            <div className="mb-1 flex items-center justify-between text-xs" style={{ fontFamily: "var(--font-mono)", color: "var(--color-ink-faint)" }}>
              <span>EXCEPTION QUEUE, LEFT TO STAFF</span>
              <span>~30%</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full" style={{ background: "var(--color-surface-2)" }}>
              <div className="h-full rounded-full" style={{ width: "30%", background: "var(--color-tier-red-fill)" }} />
            </div>
          </div>
        </div>

        <p className="mt-3 text-xs" style={{ color: "var(--color-ink-faint)" }}>
          Illustrative, not universal:{" "}
          <SourceLink href="https://www.oclc.org/en/member-stories/penn-state.html">
            OCLC&apos;s own Penn State member story
          </SourceLink>
          {" "}documents roughly 30% of ILL borrowing requests staying manual even with
          automation in place. Figures vary by library and workflow.
        </p>
      </ScrollReveal>
    </section>
  );
}
