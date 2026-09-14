"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, AlertTriangle } from "lucide-react";
import { LiveDot } from "@/components/motion/live-dot";

type Branch = "GREEN" | "RED";

const COMMON_STEPS = ["Case received", "Evaluating policy", "Memory recall", "Risk assessment"];
const BRANCH_STEP: Record<Branch, string> = { GREEN: "Safe to automate", RED: "Human approval required" };
const BRANCH_OUTCOME: Record<Branch, string> = { GREEN: "Resolved automatically", RED: "Awaiting staff decision" };

const STEP_INTERVAL_MS = 950;

/** The product's own signature visual: case -> policy -> memory -> safety
 * classification -> GREEN (automate) or RED (human approval). Not a
 * generic AI animation -- every label is a real stage this codebase's
 * HITL gate actually evaluates (src/stacks/hitl/classify.py, hitl_gate.py).
 * Cycles between a GREEN and a RED run so the hero communicates both
 * halves of "automation is powerful, but it is bounded" without narration.
 */
export function WorkflowVisualization() {
  const [reducedMotion, setReducedMotion] = useState(() =>
    typeof window !== "undefined" && typeof window.matchMedia === "function"
      ? window.matchMedia("(prefers-reduced-motion: reduce)").matches
      : false,
  );
  const [branch, setBranch] = useState<Branch>("GREEN");
  const [stepIndex, setStepIndex] = useState(0);

  const steps = [...COMMON_STEPS, BRANCH_STEP[branch]];
  const totalSteps = steps.length + 1; // + outcome step

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return;
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    const onChange = () => setReducedMotion(query.matches);
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, []);

  useEffect(() => {
    if (reducedMotion) return;
    const id = setInterval(() => {
      setStepIndex((prev) => {
        const next = prev + 1;
        if (next >= totalSteps) {
          setBranch((b) => (b === "GREEN" ? "RED" : "GREEN"));
          return 0;
        }
        return next;
      });
    }, STEP_INTERVAL_MS);
    return () => clearInterval(id);
  }, [reducedMotion, totalSteps, branch]);

  // Reduced motion: show one settled, legible state -- the GREEN outcome --
  // rather than an empty or half-drawn sequence.
  const effectiveIndex = reducedMotion ? totalSteps - 1 : stepIndex;
  const effectiveBranch: Branch = reducedMotion ? "GREEN" : branch;
  const outcomeReached = effectiveIndex === totalSteps - 1;
  const displaySteps = [...COMMON_STEPS, BRANCH_STEP[effectiveBranch]];

  return (
    <div
      className="w-full max-w-sm rounded-2xl border p-5"
      style={{ background: "var(--color-surface)", borderColor: "var(--color-border)", boxShadow: "var(--shadow-floating)" }}
      role="status"
      aria-live="polite"
      aria-label={`Stacks case workflow: ${outcomeReached ? BRANCH_OUTCOME[effectiveBranch] : displaySteps[effectiveIndex]}`}
    >
      <p className="mb-4 text-xs font-semibold uppercase tracking-wide" style={{ fontFamily: "var(--font-mono)", color: "var(--color-ink-faint)" }}>
        Live case walkthrough
      </p>
      <ol className="space-y-3">
        {displaySteps.map((label, i) => {
          const isDone = i < effectiveIndex || outcomeReached;
          const isActive = i === effectiveIndex && !outcomeReached;
          const isBranchStep = i === displaySteps.length - 1;
          const branchColor = effectiveBranch === "GREEN" ? "var(--color-tier-green-text)" : "var(--color-tier-red-text)";
          return (
            <li key={label} className="flex items-center gap-3">
              <span className="flex h-5 w-5 shrink-0 items-center justify-center">
                {isDone ? (
                  <CheckCircle2
                    size={18}
                    aria-hidden="true"
                    style={{ color: isBranchStep ? branchColor : "var(--color-accent)" }}
                  />
                ) : isActive ? (
                  <LiveDot color={isBranchStep ? branchColor : "var(--color-accent)"} />
                ) : (
                  <span className="h-1.5 w-1.5 rounded-full" style={{ background: "var(--color-ink-faint)" }} />
                )}
              </span>
              <span
                className="text-sm"
                style={{
                  color: isDone || isActive ? "var(--color-ink)" : "var(--color-ink-faint)",
                  fontWeight: isDone && isBranchStep ? 600 : 400,
                }}
              >
                {label}
              </span>
            </li>
          );
        })}
      </ol>

      <div
        className="mt-4 flex items-center gap-2 rounded-lg px-3 py-2.5 transition-opacity"
        style={{
          transitionDuration: "var(--motion-duration-panel)",
          opacity: outcomeReached ? 1 : 0.35,
          background: effectiveBranch === "GREEN" ? "var(--color-tier-green-bg)" : "var(--color-tier-red-bg)",
        }}
      >
        {effectiveBranch === "GREEN" ? (
          <CheckCircle2 size={16} aria-hidden="true" style={{ color: "var(--color-tier-green-text)" }} />
        ) : (
          <AlertTriangle size={16} aria-hidden="true" style={{ color: "var(--color-tier-red-text)" }} />
        )}
        <span
          className="text-sm font-semibold"
          style={{ color: effectiveBranch === "GREEN" ? "var(--color-tier-green-text)" : "var(--color-tier-red-text)" }}
        >
          {BRANCH_OUTCOME[effectiveBranch]}
        </span>
      </div>
    </div>
  );
}
