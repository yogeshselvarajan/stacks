import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import ConsolePage from "./page";
import { ApiError } from "@/lib/api/types";

vi.mock("@/lib/api/approvals", () => ({
  getApprovals: vi.fn(),
}));

vi.mock("@/lib/api/audit", () => ({
  getAuditList: vi.fn(),
}));

import { getApprovals } from "@/lib/api/approvals";
import { getAuditList } from "@/lib/api/audit";

const mockRouterPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockRouterPush }),
}));

describe("ConsolePage", () => {
  beforeEach(() => {
    mockRouterPush.mockReset();
    vi.mocked(getApprovals).mockReset();
    vi.mocked(getAuditList).mockReset();
    vi.mocked(getAuditList).mockResolvedValue([]);
  });

  // I1 (RBAC plan final review fix round): room_booking_staff, ill_coordinator,
  // and circulation_staff have no case_review_role, so GET /api/approvals
  // correctly 403s for them. That must render a working, non-error Home
  // screen (zero pending counts), not the page-level "Failed to load your
  // dashboard" error -- a 403 here means "no approvals visible to you", not
  // a real failure.
  it("a 403 from the approvals fetch renders a working dashboard, not the error state", async () => {
    vi.mocked(getApprovals).mockRejectedValue(new ApiError(403, "Forbidden"));

    render(<ConsolePage />);

    await waitFor(() => expect(screen.getByText("Nothing needs you right now")).toBeInTheDocument());
    expect(screen.queryByText(/failed to load your dashboard/i)).not.toBeInTheDocument();
    expect(mockRouterPush).not.toHaveBeenCalled();
  });
});
