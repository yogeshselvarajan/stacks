import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Reveal } from "@/components/motion/reveal";

export function CtaSection() {
  return (
    <section className="px-6 py-20">
      <Reveal>
        <div
          className="mx-auto flex max-w-4xl flex-col items-center gap-6 rounded-2xl border px-8 py-12 text-center"
          style={{ background: "var(--color-surface-2)", borderColor: "var(--color-border)" }}
        >
          <h2 className="text-2xl" style={{ fontFamily: "var(--font-heading)", color: "var(--color-ink)", fontWeight: 600 }}>
            Your first case is one sign-in away.
          </h2>
          <p className="max-w-xl text-sm" style={{ color: "var(--color-ink-muted)" }}>
            Real Cognito authentication, real AWS infrastructure. See a room-booking
            conflict, an ILL request, or an overdue case resolve the moment it&apos;s safe to.
          </p>
          <Link
            href="/login"
            className="stacks-focus-ring inline-flex items-center gap-2 rounded-md px-6 py-3 text-sm font-semibold transition-colors"
            style={{ background: "var(--color-accent)", color: "var(--color-fill-text)", transitionDuration: "var(--motion-duration-feedback)" }}
          >
            Sign in
            <ArrowRight size={16} aria-hidden="true" />
          </Link>
        </div>
      </Reveal>
    </section>
  );
}
