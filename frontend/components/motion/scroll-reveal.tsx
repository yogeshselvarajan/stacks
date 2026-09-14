"use client";

import { useEffect, useRef } from "react";
import { getGsap, ScrollTrigger } from "@/lib/gsap-client";
import { DURATION, EASE, prefersReducedMotion } from "@/lib/motion-tokens";

/** GSAP-driven scroll reveal for content that benefits from staggered
 * children (unlike the simpler IntersectionObserver-based Reveal
 * primitive, used where a single block just needs to fade in). Animates
 * once, the first time the section crosses the viewport; settles to its
 * final state immediately under prefers-reduced-motion.
 */
export function ScrollReveal({
  children,
  className = "",
  stagger = 0.08,
}: {
  children: React.ReactNode;
  className?: string;
  stagger?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;

    const items = Array.from(node.children);
    if (prefersReducedMotion()) {
      gsapSet(items);
      return;
    }

    const gsap = getGsap();
    gsap.set(items, { opacity: 0, y: 24 });
    const trigger = ScrollTrigger.create({
      trigger: node,
      start: "top 85%",
      once: true,
      onEnter: () => {
        gsap.to(items, {
          opacity: 1,
          y: 0,
          duration: DURATION.emphasis,
          ease: EASE.instrument,
          stagger,
        });
      },
    });

    return () => trigger.kill();
  }, [stagger]);

  return (
    <div ref={ref} className={className}>
      {children}
    </div>
  );
}

function gsapSet(items: Element[]) {
  for (const item of items) {
    (item as HTMLElement).style.opacity = "1";
    (item as HTMLElement).style.transform = "none";
  }
}
