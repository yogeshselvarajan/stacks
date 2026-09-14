import { ArrowRight, MessageCircle, Workflow } from "lucide-react";
import { ScrollReveal } from "@/components/motion/scroll-reveal";

export function ActionVsAnswer() {
  return (
    <section className="px-6 py-24">
      <div className="mx-auto max-w-5xl">
        <ScrollReveal>
          <p className="text-sm font-semibold uppercase tracking-wide" style={{ fontFamily: "var(--font-mono)", color: "var(--color-accent)" }}>
            It doesn&apos;t just answer
          </p>
          <h2 className="mt-2 max-w-2xl text-3xl" style={{ fontFamily: "var(--font-heading)", color: "var(--color-ink)", fontWeight: 600 }}>
            Library chatbots inform. Stacks completes the case.
          </h2>
          <p className="mt-4 max-w-2xl text-base leading-relaxed" style={{ color: "var(--color-ink-muted)" }}>
            Library AI assistants such as USF LINK and SJSU KingbotGPT are genuinely useful,
            information-oriented systems: they help patrons find services, collections, and
            spaces. Neither is built to take a transactional action on a case. That is a
            different job, and it is the one Stacks does.
          </p>
        </ScrollReveal>

        <ScrollReveal className="mt-10 grid gap-6 md:grid-cols-2">
          <div className="rounded-2xl border p-6" style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}>
            <MessageCircle size={20} aria-hidden="true" style={{ color: "var(--color-ink-faint)" }} />
            <p className="mt-3 text-xs font-semibold uppercase tracking-wide" style={{ fontFamily: "var(--font-mono)", color: "var(--color-ink-faint)" }}>
              Library chatbot
            </p>
            <div className="mt-3 flex items-center gap-2 text-sm" style={{ color: "var(--color-ink-muted)" }}>
              <span>Question</span>
              <ArrowRight size={14} aria-hidden="true" />
              <span>Answer</span>
            </div>
          </div>

          <div className="rounded-2xl border p-6" style={{ background: "var(--color-surface)", borderColor: "var(--color-accent)" }}>
            <Workflow size={20} aria-hidden="true" style={{ color: "var(--color-accent)" }} />
            <p className="mt-3 text-xs font-semibold uppercase tracking-wide" style={{ fontFamily: "var(--font-mono)", color: "var(--color-accent)" }}>
              Stacks
            </p>
            <div className="mt-3 flex flex-wrap items-center gap-2 text-sm" style={{ color: "var(--color-ink)" }}>
              <span>Case</span>
              <ArrowRight size={14} aria-hidden="true" style={{ color: "var(--color-ink-faint)" }} />
              <span>Context</span>
              <ArrowRight size={14} aria-hidden="true" style={{ color: "var(--color-ink-faint)" }} />
              <span>Decision</span>
              <ArrowRight size={14} aria-hidden="true" style={{ color: "var(--color-ink-faint)" }} />
              <span>Action</span>
              <ArrowRight size={14} aria-hidden="true" style={{ color: "var(--color-ink-faint)" }} />
              <span>Outcome</span>
            </div>
          </div>
        </ScrollReveal>
      </div>
    </section>
  );
}
