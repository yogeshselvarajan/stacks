import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { useRequireSession } from "./use-require-session";

const mockRouterPush = vi.fn();
const mockUsePathname = vi.fn(() => "/console");
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockRouterPush }),
  usePathname: () => mockUsePathname(),
}));

vi.mock("@/lib/api/auth", () => ({
  getSession: vi.fn(),
}));

import { getSession } from "@/lib/api/auth";

describe("useRequireSession", () => {
  beforeEach(() => {
    mockRouterPush.mockReset();
    mockUsePathname.mockReturnValue("/console");
    vi.mocked(getSession).mockReset();
  });

  it("does not redirect when a session is present", async () => {
    vi.mocked(getSession).mockResolvedValue({ role: "branch_manager", libraryId: "lib-1", caseReviewRole: null });
    renderHook(() => useRequireSession());
    await waitFor(() => expect(getSession).toHaveBeenCalled());
    expect(mockRouterPush).not.toHaveBeenCalled();
  });

  it("redirects to /login with the current path preserved when no session exists", async () => {
    mockUsePathname.mockReturnValue("/overdue-queue");
    vi.mocked(getSession).mockRejectedValue(new Error("401"));
    renderHook(() => useRequireSession());
    await waitFor(() => expect(mockRouterPush).toHaveBeenCalledWith("/login?redirect=%2Foverdue-queue"));
  });
});
