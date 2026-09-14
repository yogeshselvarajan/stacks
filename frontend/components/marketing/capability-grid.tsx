import { Bot, Split, Clock3, ShieldCheck, Brain, UserCheck } from "lucide-react";
import { Reveal } from "@/components/motion/reveal";

const CAPABILITIES = [
  {
    Icon: Bot,
    title: "Stacks Agent",
    body: "The orchestration layer. Reads each case, calls the right tool, and never invents a resolution the tool itself didn't return.",
    badge: "Powered by Amazon Bedrock (Nova)",
  },
  {
    Icon: Split,
    title: "ILL Disambiguation Specialist",
    body: "A dedicated agent that narrows an ambiguous interlibrary-loan request to a single confident candidate before the main agent ever commits.",
    badge: "Amazon Bedrock, agents-as-tools",
  },
  {
    Icon: Clock3,
    title: "Overdue Escalation Sequencer",
    body: "Runs the nightly reminder ladder as a durable, session-backed process — resumable, never double-sent, never stuck mid-tier.",
    badge: "Bedrock AgentCore Runtime + EventBridge",
  },
  {
    Icon: ShieldCheck,
    title: "Bedrock Guardrails",
    body: "A real, live guardrail policy screens every outbound notification for sensitive content before it reaches a patron.",
    badge: "Amazon Bedrock Guardrails",
  },
  {
    Icon: Brain,
    title: "AgentCore Memory",
    body: "Recalls a patron or requester's real history — prior hardship flags, prior substitutions — so staff see context, not a cold case.",
    badge: "Amazon Bedrock AgentCore Memory",
  },
  {
    Icon: UserCheck,
    title: "HITL Approval Gate",
    body: "A code-governed classifier, never the model itself, decides GREEN, YELLOW, or RED — and RED cannot resolve without a qualified human.",
    badge: "Deterministic, not a model decision",
  },
];

export function CapabilityGrid() {
  return (
    <section id="capabilities" className="px-6 py-24" style={{ background: "var(--color-surface)" }}>
      <div className="mx-auto max-w-6xl">
        <Reveal>
          <p className="text-sm font-semibold uppercase tracking-wide" style={{ fontFamily: "var(--font-mono)", color: "var(--color-accent)" }}>
            The system, end to end
          </p>
          <h2 className="mt-2 text-3xl" style={{ fontFamily: "var(--font-heading)", color: "var(--color-ink)", fontWeight: 600 }}>
            Six real components, working as one
          </h2>
        </Reveal>

        <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {CAPABILITIES.map((cap, i) => (
            <Reveal key={cap.title} delayMs={(i % 3) * 80}>
              <div
                className="group h-full rounded-2xl border p-6 transition-colors"
                style={{
                  background: "var(--color-bg)",
                  borderColor: "var(--color-border)",
                  transitionDuration: "var(--motion-duration-panel)",
                }}
              >
                <span
                  className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg transition-colors"
                  style={{ background: "var(--color-surface-2)", transitionDuration: "var(--motion-duration-panel)" }}
                >
                  <cap.Icon size={20} aria-hidden="true" style={{ color: "var(--color-accent)" }} />
                </span>
                <h3 className="text-base font-semibold" style={{ fontFamily: "var(--font-heading)", color: "var(--color-ink)" }}>
                  {cap.title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed" style={{ color: "var(--color-ink-muted)" }}>
                  {cap.body}
                </p>
                <div
                  className="mt-4 h-px w-full transition-colors group-hover:opacity-100"
                  style={{ background: "var(--color-border)", transitionDuration: "var(--motion-duration-panel)" }}
                  aria-hidden="true"
                />
                <p
                  className="mt-3 text-xs font-medium uppercase tracking-wide transition-colors group-hover:text-[var(--color-accent)]"
                  style={{ fontFamily: "var(--font-mono)", color: "var(--color-ink-faint)", transitionDuration: "var(--motion-duration-panel)" }}
                >
                  {cap.badge}
                </p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
