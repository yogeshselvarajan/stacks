"use client";

import { useEffect, useRef } from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { LiveDot } from "@/components/motion/live-dot";
import { WorkflowVisualization } from "@/components/marketing/workflow-visualization";
import { getGsap, SplitText } from "@/lib/gsap-client";
import { DURATION, EASE, prefersReducedMotion } from "@/lib/motion-tokens";

export function Hero() {
  const eyebrowRef = useRef<HTMLSpanElement>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const subheadRef = useRef<HTMLParagraphElement>(null);
  const microcopyRef = useRef<HTMLParagraphElement>(null);
  const ctaRef = useRef<HTMLDivElement>(null);
  const noteRef = useRef<HTMLParagraphElement>(null);
  const visualRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const nodes = [eyebrowRef, headingRef, subheadRef, microcopyRef, ctaRef, noteRef, visualRef].map((r) => r.current);
    if (nodes.some((n) => n === null)) return;

    if (prefersReducedMotion()) {
      return; // Final state is the element's own natural, already-visible layout.
    }

    // A one-time entrance sequence, never looped -- the page settles into
    // idle (the WorkflowVisualization's own restrained, already-throttled
    // cycle) once this timeline finishes. Wrapped defensively: a failure
    // splitting/animating text must never leave the hero invisible.
    try {
      const gsap = getGsap();
      // SplitText rewrites the heading into one wrapper span per word,
      // which is how a screen reader ends up reading "afternoonsback"
      // instead of "afternoons back" -- the space is a text node SplitText
      // discards when it rebuilds the DOM. Capture the real sentence as
      // aria-label first (the accessible name always wins over a
      // element's visible children), so assistive tech gets the correct
      // text regardless of how the visual split reconstructs spacing.
      headingRef.current!.setAttribute("aria-label", headingRef.current!.textContent ?? "");
      const split = new SplitText(headingRef.current!, { type: "words" });

      gsap.set([eyebrowRef.current, subheadRef.current, microcopyRef.current, ctaRef.current, noteRef.current], {
        opacity: 0, y: 16,
      });
      gsap.set(split.words, { opacity: 0, y: 20 });
      gsap.set(visualRef.current, { opacity: 0, y: 24, scale: 0.98 });

      const tl = gsap.timeline({ defaults: { ease: EASE.instrument } });
      tl.to(eyebrowRef.current, { opacity: 1, y: 0, duration: DURATION.normal })
        .to(split.words, { opacity: 1, y: 0, duration: DURATION.emphasis, stagger: 0.04 }, "-=0.1")
        .to(subheadRef.current, { opacity: 1, y: 0, duration: DURATION.normal }, "-=0.2")
        .to(microcopyRef.current, { opacity: 1, y: 0, duration: DURATION.normal }, "-=0.15")
        .to(ctaRef.current, { opacity: 1, y: 0, duration: DURATION.normal }, "-=0.15")
        .to(noteRef.current, { opacity: 1, y: 0, duration: DURATION.fast }, "-=0.1")
        .to(visualRef.current, { opacity: 1, y: 0, scale: 1, duration: DURATION.cinematic }, "-=0.3");

      // Live-observed on the deployed Amplify build, 2026-09-14: the
      // timeline above was constructed successfully (no exception, so the
      // try/catch's own safety net never fired) but never visibly played
      // in that specific environment, leaving every element stuck at the
      // gsap.set(..., opacity:0) initial state indefinitely. Root cause
      // not fully isolated (Turbopack's production chunking is a
      // suspected factor, not confirmed). Rather than leave a
      // half-understood animation as the only path to a visible hero, a
      // hard timeout forces the same end state GSAP would have reached on
      // its own, on every environment, regardless of whether the
      // timeline actually ran.
      const safetyTimeout = window.setTimeout(() => {
        gsap.set([eyebrowRef.current, ...split.words, subheadRef.current, microcopyRef.current, ctaRef.current, noteRef.current, visualRef.current], {
          clearProps: "opacity,transform",
        });
      }, 2000);

      return () => {
        window.clearTimeout(safetyTimeout);
        tl.kill();
        split.revert();
      };
    } catch {
      // Any environment where GSAP/SplitText can't operate (an
      // unsupported browser, a test renderer, a plugin registration
      // failure specific to one deployment) falls back to the element's
      // own static, already-legible markup -- never a blank hero. This
      // reset is required, not just the early return: gsap.set(...,
      // {opacity: 0}) above may have already applied before the failure
      // point, and without explicitly clearing it back to 1 the hero
      // stays permanently invisible -- a real, live-observed bug (the
      // deployed Amplify build rendered a blank hero with every element
      // stuck at opacity:0), not a hypothetical one.
      getGsap().set([eyebrowRef.current, headingRef.current, subheadRef.current, microcopyRef.current, ctaRef.current, noteRef.current, visualRef.current], {
        clearProps: "opacity,transform",
      });
      return;
    }
  }, []);

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
            ref={eyebrowRef}
            className="mb-6 inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wide"
            style={{ borderColor: "var(--color-border)", color: "var(--color-ink-muted)", fontFamily: "var(--font-mono)" }}
          >
            <LiveDot />
            A task-completion agent for library operations
          </span>

          <h1
            ref={headingRef}
            className="text-4xl leading-tight sm:text-5xl"
            style={{ fontFamily: "var(--font-heading)", color: "var(--color-ink)", fontWeight: 600 }}
          >
            Give library staff their afternoons back.
          </h1>

          <p ref={subheadRef} className="mt-5 max-w-xl text-lg leading-relaxed" style={{ color: "var(--color-ink-muted)" }}>
            Stacks resolves room-booking conflicts, routes ambiguous interlibrary-loan
            requests, and chases overdue items, automatically when it&apos;s safe, and
            with a staff member in the loop whenever it isn&apos;t.
          </p>

          <p ref={microcopyRef} className="mt-3 max-w-xl text-base" style={{ color: "var(--color-ink-faint)" }}>
            Your systems already flag the hard cases. Stacks is what works the queue they flag them into.
          </p>

          <div ref={ctaRef} className="mt-8 flex flex-wrap items-center gap-4">
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

          <p ref={noteRef} className="mt-4 text-sm" style={{ color: "var(--color-ink-faint)" }}>
            No setup for staff. Real Cognito sign-in, real AWS infrastructure underneath, built on Amazon Bedrock AgentCore.
          </p>
        </div>

        <div ref={visualRef} className="flex justify-center lg:justify-end">
          <WorkflowVisualization />
        </div>
      </div>
    </section>
  );
}
