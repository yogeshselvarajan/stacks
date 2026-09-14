import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { LiveDot } from "@/components/motion/live-dot";
import { WorkflowVisualization } from "@/components/marketing/workflow-visualization";

export function Hero() {
  return (
    <section className="relative overflow-hidden px-6 pb-20 pt-36">
      {/* Atmospheric background: one soft radial glow, nothing more --
          content stays dominant per this project's own anti-cyberpunk rule. */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-[560px]"
        style={{ background: "radial-gradient(closest-side, color-mix(in srgb, var(--color-accent) 14%, transparent), transparent)" }}
      />

      <div className="mx-auto grid max-w-6xl items-center gap-12 lg:grid-cols-2">
        <div>
          <span
            className="mb-6 inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wide"
            style={{ borderColor: "var(--color-border)", color: "var(--color-ink-muted)", fontFamily: "var(--font-mono)" }}
          >
            <LiveDot />
            Built on Amazon Bedrock AgentCore
          </span>

          <h1
            className="text-4xl leading-tight sm:text-5xl"
            style={{ fontFamily: "var(--font-heading)", color: "var(--color-ink)", fontWeight: 600 }}
          >
            Give library staff their afternoons back.
          </h1>

          <p className="mt-5 max-w-xl text-lg leading-relaxed" style={{ color: "var(--color-ink-muted)" }}>
            Stacks resolves room-booking conflicts, routes ambiguous interlibrary-loan
            requests, and chases overdue items — automatically when it&apos;s safe, and
            with a staff member in the loop whenever it isn&apos;t.
          </p>

          <div className="mt-8 flex flex-wrap items-center gap-4">
            <Link
              href="/login"
              className="stacks-focus-ring inline-flex items-center gap-2 rounded-md px-5 py-3 text-sm font-semibold transition-colors"
              style={{ background: "var(--color-accent)", color: "var(--color-fill-text)", transitionDuration: "var(--motion-duration-feedback)" }}
            >
              Sign in
              <ArrowRight size={16} aria-hidden="true" />
            </Link>
            <a
              href="#how-it-works"
              className="stacks-focus-ring rounded-md border px-5 py-3 text-sm font-semibold transition-colors"
              style={{ borderColor: "var(--color-border)", color: "var(--color-ink)", transitionDuration: "var(--motion-duration-feedback)" }}
            >
              See how it works
            </a>
          </div>

          <p className="mt-4 text-sm" style={{ color: "var(--color-ink-faint)" }}>
            No setup for staff — real Cognito sign-in, real AWS infrastructure underneath.
          </p>
        </div>

        <div className="flex justify-center lg:justify-end">
          <WorkflowVisualization />
        </div>
      </div>
    </section>
  );
}
