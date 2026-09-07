import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import ApprovalsLayout from "./layout";
import { APPROVAL_CASES_FIXTURE } from "@/lib/fixtures";

vi.mock("@/lib/api/approvals", () => ({
  getApprovals: vi.fn(),
}));

import { getApprovals } from "@/lib/api/approvals";

const mockUsePathname = vi.fn(() => "/approvals");
vi.mock("next/navigation", () => ({
  usePathname: () => mockUsePathname(),
}));

describe("ApprovalsLayout", () => {
  beforeEach(() => {
    mockUsePathname.mockReturnValue("/approvals");
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

  it("highlights the active case row when pathname contains a URL-encoded case id", async () => {
    const activeCaseId = APPROVAL_CASES_FIXTURE[0].caseId;
    mockUsePathname.mockReturnValue(`/approvals/${encodeURIComponent(activeCaseId)}`);
    render(
      <ApprovalsLayout>
        <p>right pane content</p>
      </ApprovalsLayout>
    );
    await waitFor(() => expect(screen.getAllByTestId("approval-row").length).toBe(APPROVAL_CASES_FIXTURE.length));
    const rows = screen.getAllByTestId("approval-row");
    const activeRow = rows.find((r) => r.getAttribute("href") === `/approvals/${encodeURIComponent(activeCaseId)}`);
    expect(activeRow?.style.background).toBe("var(--color-surface-2)");
  });
});
