import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { NewIllRequestForm } from "./new-ill-request-form";
import * as illQueueApi from "@/lib/api/ill-queue";

vi.mock("@/lib/api/ill-queue", async () => {
  const actual = await vi.importActual<typeof illQueueApi>("@/lib/api/ill-queue");
  return { ...actual, createIllRequest: vi.fn() };
});

describe("NewIllRequestForm", () => {
  beforeEach(() => {
    vi.mocked(illQueueApi.createIllRequest).mockReset();
  });

  it("starts collapsed, showing only the entry point", () => {
    render(<NewIllRequestForm />);
    expect(screen.getByRole("button", { name: /new request/i })).toBeInTheDocument();
    expect(screen.queryByLabelText("Title")).toBeNull();
  });

  it("expands into a form when the entry point is clicked", () => {
    render(<NewIllRequestForm />);
    fireEvent.click(screen.getByRole("button", { name: /new request/i }));
    expect(screen.getByLabelText("Title")).toBeInTheDocument();
    expect(screen.getByLabelText("Requester patron ID")).toBeInTheDocument();
  });

  it("submits the entered values and shows a real processing state, not a spinner", async () => {
    vi.mocked(illQueueApi.createIllRequest).mockImplementation(
      () => new Promise(() => {}) // never resolves during this assertion
    );
    render(<NewIllRequestForm />);
    fireEvent.click(screen.getByRole("button", { name: /new request/i }));
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Middlemarch" } });
    fireEvent.change(screen.getByLabelText("Requester patron ID"), { target: { value: "patron_x" } });
    fireEvent.click(screen.getByRole("button", { name: /submit/i }));

    expect(await screen.findByText(/submitting to stacks/i)).toBeInTheDocument();
    expect(illQueueApi.createIllRequest).toHaveBeenCalledWith({
      requestedTitle: "Middlemarch",
      requestedEditionHint: undefined,
      requesterPatronId: "patron_x",
    });
  });

  it("shows a link into the Approval Inbox when the case lands as pending approval", async () => {
    vi.mocked(illQueueApi.createIllRequest).mockResolvedValue({
      illRequestId: "ill_abc123", status: "pending_approval", outcome: null,
    });
    render(<NewIllRequestForm />);
    fireEvent.click(screen.getByRole("button", { name: /new request/i }));
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Middlemarch" } });
    fireEvent.change(screen.getByLabelText("Requester patron ID"), { target: { value: "patron_x" } });
    fireEvent.click(screen.getByRole("button", { name: /submit/i }));

    const link = await screen.findByRole("link", { name: /review in approval inbox/i });
    expect(link).toHaveAttribute("href", "/approvals/ill_abc123");
  });

  it("shows a resolved message, not a pending-approval link, when the case auto-resolves", async () => {
    vi.mocked(illQueueApi.createIllRequest).mockResolvedValue({
      illRequestId: "ill_def456", status: "resolved", outcome: "committed",
    });
    render(<NewIllRequestForm />);
    fireEvent.click(screen.getByRole("button", { name: /new request/i }));
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "The Hobbit" } });
    fireEvent.change(screen.getByLabelText("Requester patron ID"), { target: { value: "patron_y" } });
    fireEvent.click(screen.getByRole("button", { name: /submit/i }));

    expect(await screen.findByText(/resolved automatically/i)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /review in approval inbox/i })).toBeNull();
  });

  it("shows a plain-language error and lets the user try again on failure", async () => {
    vi.mocked(illQueueApi.createIllRequest).mockRejectedValue(new Error("network down"));
    render(<NewIllRequestForm />);
    fireEvent.click(screen.getByRole("button", { name: /new request/i }));
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Beloved" } });
    fireEvent.change(screen.getByLabelText("Requester patron ID"), { target: { value: "patron_z" } });
    fireEvent.click(screen.getByRole("button", { name: /submit/i }));

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(/couldn't submit/i));
  });

  it("calls onCreated after a successful submission", async () => {
    const onCreated = vi.fn();
    vi.mocked(illQueueApi.createIllRequest).mockResolvedValue({
      illRequestId: "ill_ghi789", status: "resolved", outcome: "committed",
    });
    render(<NewIllRequestForm onCreated={onCreated} />);
    fireEvent.click(screen.getByRole("button", { name: /new request/i }));
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Beloved" } });
    fireEvent.change(screen.getByLabelText("Requester patron ID"), { target: { value: "patron_z" } });
    fireEvent.click(screen.getByRole("button", { name: /submit/i }));

    await waitFor(() => expect(onCreated).toHaveBeenCalled());
  });

  it("shows a could-not-process message when case creation succeeds but agent invocation fails", async () => {
    vi.mocked(illQueueApi.createIllRequest).mockResolvedValue({
      illRequestId: "ill_fail1", status: "agent_invocation_failed", outcome: null,
    });
    render(<NewIllRequestForm />);
    fireEvent.click(screen.getByRole("button", { name: /new request/i }));
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Middlemarch" } });
    fireEvent.change(screen.getByLabelText("Requester patron ID"), { target: { value: "patron_x" } });
    fireEvent.click(screen.getByRole("button", { name: /submit/i }));

    expect(await screen.findByText(/could not process it yet/i)).toBeInTheDocument();
  });

  it("shows a needs-attention message when the case is created but not completed automatically", async () => {
    vi.mocked(illQueueApi.createIllRequest).mockResolvedValue({
      illRequestId: "ill_needs1", status: "needs_attention", outcome: "blocked_missing_approval",
    });
    render(<NewIllRequestForm />);
    fireEvent.click(screen.getByRole("button", { name: /new request/i }));
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Middlemarch" } });
    fireEvent.change(screen.getByLabelText("Requester patron ID"), { target: { value: "patron_x" } });
    fireEvent.click(screen.getByRole("button", { name: /submit/i }));

    expect(
      await screen.findByText(/could not complete it automatically.*check the ill queue/i)
    ).toBeInTheDocument();
  });

  it("resets the draft fields when Cancel is clicked, unlike a stale reopen", () => {
    render(<NewIllRequestForm />);
    fireEvent.click(screen.getByRole("button", { name: /new request/i }));
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Middlemarch" } });
    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));

    fireEvent.click(screen.getByRole("button", { name: /new request/i }));
    expect(screen.getByLabelText("Title")).toHaveValue("");
  });

  it("every input and the submit button carry the shared focus-ring class", () => {
    render(<NewIllRequestForm />);
    fireEvent.click(screen.getByRole("button", { name: /new request/i }));
    expect(screen.getByLabelText("Title").className).toContain("stacks-focus-ring");
    expect(screen.getByLabelText("Requester patron ID").className).toContain("stacks-focus-ring");
    expect(screen.getByRole("button", { name: /submit/i }).className).toContain("stacks-focus-ring");
  });
});
