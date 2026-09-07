import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import ApprovalsLayout from "./layout";
import { APPROVAL_CASES_FIXTURE } from "@/lib/fixtures";

vi.mock("@/lib/api/approvals", () => ({
  getApprovals: vi.fn(),
}));

import { getApprovals } from "@/lib/api/approvals";

vi.mock("next/navigation", () => ({
  usePathname: () => "/approvals",
}));

describe("ApprovalsLayout", () => {
  beforeEach(() => {
    vi.mocked(getApprovals).mockReset();
    vi.mocked(getApprovals).mockResolvedValue(APPROVAL_CASES_FIXTURE);
  });

  it("renders the persistent case list alongside the routed child content", async () => {
    render(
      <ApprovalsLayout>
        <p>right pane content</p>
      </ApprovalsLayout>
    );
    await waitFor(() => expect(screen.getAllByTestId("approval-row").length).toBe(APPROVAL_CASES_FIXTURE.length));
    expect(screen.getByText("right pane content")).toBeInTheDocument();
  });

  it("shows the live approval count in the shell nav, reflecting the fetched queue", async () => {
    render(
      <ApprovalsLayout>
        <p>right pane content</p>
      </ApprovalsLayout>
    );
    await waitFor(() => {
      const approvalsLink = screen.getByRole("link", { name: /approval inbox/i });
      expect(approvalsLink).toHaveTextContent(String(APPROVAL_CASES_FIXTURE.length));
    });
  });
});
