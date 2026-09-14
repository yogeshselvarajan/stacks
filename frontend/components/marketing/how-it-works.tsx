import { Inbox, ScanSearch, Split } from "lucide-react";
import { Reveal } from "@/components/motion/reveal";
import { TierBadge } from "@/components/tier-badge";

const STEPS = [
  {
    number: "01",
    Icon: Inbox,
    title: "A case appears",
    body: "A room-booking conflict, an ambiguous interlibrary-loan request, or an overdue item enters Stacks — the same workload a circulation desk already handles by hand today.",
  },
  {
    number: "02",
    Icon: ScanSearch,
    title: "Stacks evaluates it",
    body: "The agent checks the library's real policy clauses, recalls relevant history from AgentCore Memory, and — for ambiguous ILL requests — consults a specialist agent before deciding anything.",
  },
  {
    number: "03",
    Icon: Split,
    title: "The right action happens",
    body: "A code-governed safety gate, not the model itself, decides what happens next.",
  },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="px-6 py-24">
      <div className="mx-auto max-w-6xl">
        <Reveal>
          <p className="text-sm font-semibold uppercase tracking-wide" style={{ fontFamily: "var(--font-mono)", color: "var(--color-accent)" }}>
            How it works
          </p>
          <h2 className="mt-2 text-3xl" style={{ fontFamily: "var(--font-heading)", color: "var(--color-ink)", fontWeight: 600 }}>
            From a routine case to a resolved one, in three steps
          </h2>
        </Reveal>

        <div className="mt-12 grid gap-6 md:grid-cols-3">
          {STEPS.map((step, i) => (
            <Reveal key={step.number} delayMs={i * 100}>
              <div
                className="h-full rounded-2xl border p-6"
                style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}
              >
                <div className="mb-4 flex items-center justify-between">
                  <span
                    className="flex h-10 w-10 items-center justify-center rounded-lg"
                    style={{ background: "var(--color-surface-2)" }}
                  >
                    <step.Icon size={20} aria-hidden="true" style={{ color: "var(--color-accent)" }} />
                  </span>
                  <span className="text-2xl font-semibold" style={{ fontFamily: "var(--font-mono)", color: "var(--color-ink-faint)" }}>
                    {step.number}
                  </span>
                </div>
                <h3 className="text-lg font-semibold" style={{ fontFamily: "var(--font-heading)", color: "var(--color-ink)" }}>
                  {step.title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed" style={{ color: "var(--color-ink-muted)" }}>
                  {step.body}
                </p>
                {i === 2 && (
                  <div className="mt-4 flex flex-wrap gap-2">
                    <TierBadge tier="GREEN" />
                    <TierBadge tier="YELLOW" />
                    <TierBadge tier="RED" />
                  </div>
                )}
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
