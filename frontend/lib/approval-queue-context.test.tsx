import { render, screen, waitFor, act } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { ApprovalQueueProvider, useApprovalQueue } from "./approval-queue-context";
import { APPROVAL_CASES_FIXTURE } from "@/lib/fixtures";

vi.mock("@/lib/api/approvals", () => ({
  getApprovals: vi.fn(),
}));

import { getApprovals } from "@/lib/api/approvals";

function Probe() {
  const { cases, status, resolvingCaseId, setResolvingCaseId, refetch } = useApprovalQueue();
  return (
    <div>
      <span data-testid="status">{status}</span>
      <span data-testid="count">{cases.length}</span>
      <span data-testid="resolving">{resolvingCaseId ?? "none"}</span>
      <button onClick={() => setResolvingCaseId(APPROVAL_CASES_FIXTURE[0].caseId)}>set-resolving</button>
      <button onClick={() => refetch()}>refetch</button>
    </div>
  );
}

describe("ApprovalQueueProvider / useApprovalQueue", () => {
  beforeEach(() => {
    vi.mocked(getApprovals).mockReset();
  });

  it("fetches the queue on mount and exposes it as ready", async () => {
    vi.mocked(getApprovals).mockResolvedValue(APPROVAL_CASES_FIXTURE);
    render(
      <ApprovalQueueProvider>
        <Probe />
      </ApprovalQueueProvider>
    );
    expect(screen.getByTestId("status")).toHaveTextContent("loading");
    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("ready"));
    expect(screen.getByTestId("count")).toHaveTextContent(String(APPROVAL_CASES_FIXTURE.length));
  });

  it("exposes an error status when the fetch rejects", async () => {
    vi.mocked(getApprovals).mockRejectedValue(new Error("network"));
    render(
      <ApprovalQueueProvider>
        <Probe />
      </ApprovalQueueProvider>
    );
    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("error"));
  });

  it("refetch re-runs getApprovals and updates the cases", async () => {
    vi.mocked(getApprovals).mockResolvedValue(APPROVAL_CASES_FIXTURE);
    render(
      <ApprovalQueueProvider>
        <Probe />
      </ApprovalQueueProvider>
    );
    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("ready"));
    vi.mocked(getApprovals).mockResolvedValue([]);
    await act(async () => {
      screen.getByText("refetch").click();
    });
    await waitFor(() => expect(screen.getByTestId("count")).toHaveTextContent("0"));
    expect(getApprovals).toHaveBeenCalledTimes(2);
  });

  it("setResolvingCaseId updates the shared resolving id", async () => {
    vi.mocked(getApprovals).mockResolvedValue(APPROVAL_CASES_FIXTURE);
    render(
      <ApprovalQueueProvider>
        <Probe />
      </ApprovalQueueProvider>
    );
    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("ready"));
    expect(screen.getByTestId("resolving")).toHaveTextContent("none");
    await act(async () => {
      screen.getByText("set-resolving").click();
    });
    expect(screen.getByTestId("resolving")).toHaveTextContent(APPROVAL_CASES_FIXTURE[0].caseId);
  });

  it("throws a clear error when useApprovalQueue is called outside the provider", () => {
    function Bare() {
      useApprovalQueue();
      return null;
    }
    // Suppress the expected React error-boundary console.error noise for this one assertion.
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(<Bare />)).toThrow("useApprovalQueue must be used within an ApprovalQueueProvider");
    spy.mockRestore();
  });
});
