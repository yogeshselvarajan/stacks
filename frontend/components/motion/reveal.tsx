"use client";

import { useEffect, useRef, useState } from "react";

/** Fades and lifts children into view the first time they cross the
 * viewport. Pure CSS transition + IntersectionObserver -- no animation
 * library dependency. Renders content immediately (never blocks on JS)
 * and settles to its resting state without a listener if IntersectionObserver
 * is unavailable (SSR/very old browsers).
 */
export function Reveal({
  children,
  delayMs = 0,
  className = "",
}: {
  children: React.ReactNode;
  delayMs?: number;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (!node || typeof IntersectionObserver === "undefined") {
      setVisible(true);
      return;
    }
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { threshold: 0.15 },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className={className}
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? "translateY(0)" : "translateY(12px)",
        transition: `opacity var(--motion-duration-drawer) var(--motion-ease-signature), transform var(--motion-duration-drawer) var(--motion-ease-signature)`,
        transitionDelay: `${delayMs}ms`,
      }}
    >
      {children}
    </div>
  );
}
