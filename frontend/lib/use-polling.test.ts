import { renderHook } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { usePolling } from "./use-polling";

describe("usePolling", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    Object.defineProperty(document, "visibilityState", { value: "visible", writable: true, configurable: true });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("calls the callback repeatedly at the given interval while the tab is visible", () => {
    const callback = vi.fn();
    renderHook(() => usePolling(callback, 1000));

    vi.advanceTimersByTime(3500);
    expect(callback).toHaveBeenCalledTimes(3);
  });

  it("does not call the callback while the tab is hidden", () => {
    Object.defineProperty(document, "visibilityState", { value: "hidden", writable: true, configurable: true });
    const callback = vi.fn();
    renderHook(() => usePolling(callback, 1000));

    vi.advanceTimersByTime(5000);
    expect(callback).not.toHaveBeenCalled();
  });

  it("stops polling on unmount", () => {
    const callback = vi.fn();
    const { unmount } = renderHook(() => usePolling(callback, 1000));
    unmount();
    vi.advanceTimersByTime(5000);
    expect(callback).not.toHaveBeenCalled();
  });
});
