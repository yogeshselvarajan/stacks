// frontend/lib/gsap-client.ts
// Single registration point for GSAP's plugins. GSAP owns scroll
// choreography (ScrollTrigger) and text reveals (SplitText) on this page;
// Motion for React owns component-level entrance/hover/tap/state
// transitions. Never both animating the same element -- one owner per
// interaction, per this project's own motion-system rule.
"use client";

import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { SplitText } from "gsap/SplitText";

let registered = false;

export function getGsap() {
  if (!registered && typeof window !== "undefined") {
    gsap.registerPlugin(ScrollTrigger, SplitText);
    registered = true;
  }
  return gsap;
}

export { ScrollTrigger, SplitText };
