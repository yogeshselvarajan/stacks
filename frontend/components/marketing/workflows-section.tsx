"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Calendar, BookOpen, Clock3, ChevronDown } from "lucide-react";
import { ScrollReveal } from "@/components/motion/scroll-reveal";
import { TierBadge } from "@/components/tier-badge";
import { DURATION, EASE } from "@/lib/motion-tokens";

const WORKFLOWS = [
  {
    Icon: Calendar,
    title: "Room booking",
    teaser: "Two requests. One room. A policy decides the priority.",
    detail: "Stacks reads the library's own priority policy, resolves which booking yields, proposes an outcome, and cites the clause it applied.",
    tier: "GREEN" as const,
  },
  {
    Icon: BookOpen,
    title: "Interlibrary loan",
    teaser: "Incomplete citation. Multiple candidate editions.",
    detail: "A dedicated specialist agent narrows the ambiguous request to a single confident candidate before the main agent ever commits to a routing decision.",
    tier: "YELLOW" as const,
  },
  {
    Icon: Clock3,
    title: "Overdue escalation",
    teaser: "Not every overdue case is the same.",
    detail: "Context, a hardship flag, a minor's account, a rare item, decides how far the escalation ladder goes, and whether a human reviews it first.",
    tier: "RED" as const,
  },
];

export function WorkflowsSection() {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  return (
    <section id="workflows" className="px-6 py-24" style={{ background: "var(--color-surface)" }}>
      <div className="mx-auto max-w-4xl">
        <ScrollReveal>
          <p className="text-sm font-semibold uppercase tracking-wide" style={{ fontFamily: "var(--font-mono)", color: "var(--color-accent)" }}>
            Three real workflows
          </p>
          <h2 className="mt-2 text-3xl" style={{ fontFamily: "var(--font-heading)", color: "var(--color-ink)", fontWeight: 600 }}>
            Not features. Cases Stacks actually completes.
          </h2>
        </ScrollReveal>

        <ScrollReveal className="mt-8 space-y-3" stagger={0.08}>
          {WORKFLOWS.map((workflow, i) => {
            const open = openIndex === i;
            return (
              <div
                key={workflow.title}
                className="overflow-hidden rounded-2xl border"
                style={{ background: "var(--color-bg)", borderColor: "var(--color-border)" }}
              >
                <button
                  type="button"
                  className="stacks-focus-ring flex w-full items-center justify-between gap-4 p-5 text-left"
                  aria-expanded={open}
                  onClick={() => setOpenIndex(open ? null : i)}
                >
                  <span className="flex items-center gap-3">
                    <span className="flex h-10 w-10 items-center justify-center rounded-lg" style={{ background: "var(--color-surface-2)" }}>
                      <workflow.Icon size={20} aria-hidden="true" style={{ color: "var(--color-accent)" }} />
                    </span>
                    <span>
                      <span className="block text-base font-semibold" style={{ fontFamily: "var(--font-heading)", color: "var(--color-ink)" }}>
                        {workflow.title}
                      </span>
                      <span className="block text-sm" style={{ color: "var(--color-ink-muted)" }}>{workflow.teaser}</span>
                    </span>
                  </span>
                  <motion.span animate={{ rotate: open ? 180 : 0 }} transition={{ duration: DURATION.fast }}>
                    <ChevronDown size={18} aria-hidden="true" style={{ color: "var(--color-ink-faint)" }} />
                  </motion.span>
                </button>
                <AnimatePresence initial={false}>
                  {open && (
                    <motion.div
                      key="detail"
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: DURATION.normal, ease: EASE.ui }}
                    >
                      <div className="flex flex-col gap-3 border-t px-5 py-4 sm:flex-row sm:items-center sm:justify-between" style={{ borderColor: "var(--color-border)" }}>
                        <p className="text-sm" style={{ color: "var(--color-ink-muted)" }}>{workflow.detail}</p>
                        <TierBadge tier={workflow.tier} />
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            );
          })}
        </ScrollReveal>
      </div>
    </section>
  );
}
