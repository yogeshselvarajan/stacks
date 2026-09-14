import { ArrowDown } from "lucide-react";
import { ScrollReveal } from "@/components/motion/scroll-reveal";

const FLOW = [
  "Case",
  "Stacks Agent",
  "Amazon Bedrock",
  "Bedrock AgentCore",
  "Policy + Memory",
  "Safety gate",
  "Action",
  "Audit",
];

export function AwsArchitecture() {
  return (
    <section id="built-on-aws" className="px-6 py-24">
      <div className="mx-auto max-w-3xl text-center">
        <ScrollReveal>
          <p className="text-sm font-semibold uppercase tracking-wide" style={{ fontFamily: "var(--font-mono)", color: "var(--color-accent)" }}>
            Built on AWS
          </p>
          <h2 className="mt-2 text-3xl" style={{ fontFamily: "var(--font-heading)", color: "var(--color-ink)", fontWeight: 600 }}>
            Built on AWS for controlled, observable task completion.
          </h2>
        </ScrollReveal>

        <ScrollReveal className="mt-10 flex flex-col items-center gap-2" stagger={0.05}>
          {FLOW.map((step, i) => (
            <div key={step} className="flex flex-col items-center gap-2">
              <span
                className="rounded-lg border px-4 py-2 text-sm"
                style={{
                  borderColor: i === 0 || i === FLOW.length - 1 ? "var(--color-border)" : "var(--color-accent)",
                  color: "var(--color-ink)",
                  fontFamily: "var(--font-mono)",
                }}
              >
                {step}
              </span>
              {i < FLOW.length - 1 && <ArrowDown size={14} aria-hidden="true" style={{ color: "var(--color-ink-faint)" }} />}
            </div>
          ))}
        </ScrollReveal>
      </div>
    </section>
  );
}
