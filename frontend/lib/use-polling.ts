"use client";

import { useEffect, useRef } from "react";

// Deliberately polling, not a persistent connection (SSE/WebSocket). Given
// the deadline this project is built under, a small interval-based refresh
// paused while the tab is hidden is the lower-risk choice that still meets
// the real requirement (no manual reload needed to see a new approval or
// a resolved case) without introducing new server-side streaming infra
// this close to submission.
export function usePolling(callback: () => void, intervalMs: number): void {
  const callbackRef = useRef(callback);

  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  useEffect(() => {
    const tick = () => {
      if (document.visibilityState === "visible") callbackRef.current();
    };
    const id = setInterval(tick, intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);
}
