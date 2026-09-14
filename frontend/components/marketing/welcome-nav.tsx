"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Library } from "lucide-react";

const LINKS = [
  { href: "#how-it-works", label: "How it works" },
  { href: "#capabilities", label: "Capabilities" },
  { href: "#built-on-aws", label: "Built on AWS" },
];

export function WelcomeNav() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className="fixed inset-x-0 top-0 z-50 transition-colors"
      style={{
        transitionDuration: "var(--motion-duration-panel)",
        transitionTimingFunction: "var(--motion-ease-feedback)",
        background: scrolled ? "color-mix(in srgb, var(--color-bg) 82%, transparent)" : "transparent",
        borderBottom: scrolled ? "1px solid var(--color-border)" : "1px solid transparent",
        backdropFilter: scrolled ? "blur(10px)" : "none",
      }}
    >
      <nav
        aria-label="Primary"
        className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4"
      >
        <Link href="/welcome" className="stacks-focus-ring flex items-center gap-2 rounded-md">
          <Library size={20} aria-hidden="true" style={{ color: "var(--color-accent)" }} />
          <span className="font-semibold" style={{ fontFamily: "var(--font-heading)", color: "var(--color-ink)" }}>
            Stacks
          </span>
        </Link>

        <ul className="hidden items-center gap-6 md:flex">
          {LINKS.map((link) => (
            <li key={link.href}>
              <a
                href={link.href}
                className="stacks-focus-ring rounded-md text-sm font-medium transition-colors"
                style={{
                  color: "var(--color-ink-muted)",
                  transitionDuration: "var(--motion-duration-feedback)",
                }}
              >
                {link.label}
              </a>
            </li>
          ))}
        </ul>

        <Link
          href="/login"
          className="stacks-focus-ring rounded-md px-4 py-2 text-sm font-semibold transition-colors"
          style={{
            background: "var(--color-accent)",
            color: "var(--color-fill-text)",
            transitionDuration: "var(--motion-duration-feedback)",
          }}
        >
          Sign in
        </Link>
      </nav>
    </header>
  );
}
