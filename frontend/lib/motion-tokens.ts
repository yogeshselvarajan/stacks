// frontend/lib/motion-tokens.ts
// One shared vocabulary for every animation on /welcome. Values chosen so
// there is exactly one place to tune pacing, never a scattered literal
// duration in a component. Named per this project's own motion-language
// convention (frontend/app/globals.css's --motion-duration-* tokens),
// extended here with the longer, more editorial durations a cinematic
// scroll experience needs that the console's own restrained --motion-*
// tokens deliberately don't cover.
export const DURATION = {
  fast: 0.18,
  normal: 0.35,
  emphasis: 0.6,
  cinematic: 1.0,
} as const;

export const EASE = {
  // UI feedback: springy, physical.
  ui: [0.16, 1, 0.3, 1] as const,
  // Editorial typography reveals: smooth, no overshoot.
  editorial: [0.22, 1, 0.36, 1] as const,
  // Operational/instrument state changes: slightly mechanical, precise.
  instrument: "power2.out",
};

export function prefersReducedMotion(): boolean {
  return typeof window !== "undefined" && typeof window.matchMedia === "function"
    ? window.matchMedia("(prefers-reduced-motion: reduce)").matches
    : false;
}
