import "@testing-library/jest-dom/vitest";

// jsdom has never implemented matchMedia. Several components already guard
// for its absence directly (workflow-visualization.tsx), but GSAP's own
// ScrollTrigger plugin calls window.matchMedia unconditionally the moment
// it registers, with no such guard -- crashing every test that renders a
// component using ScrollReveal. A minimal, always-not-matching stub is the
// standard fix (used by Motion/GSAP's own test suites for the same jsdom
// gap) rather than degrading real reduced-motion/scroll behavior in every
// consuming component just to keep tests running.
if (typeof window !== "undefined" && typeof window.matchMedia !== "function") {
  window.matchMedia = (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }) as MediaQueryList;
}
