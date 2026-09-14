// frontend/components/ill-queue-view.test.tsx
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { IllQueueView } from "./ill-queue-view";
import { ILL_QUEUE_FIXTURE } from "@/lib/fixtures";
import { IllRequest } from "@/lib/api/types";

describe("IllQueueView", () => {
  it("loading state: renders row skeletons", () => {
    const { container } = render(<IllQueueView requests={[]} status="loading" />);
    expect(container.querySelector("[data-testid='skeleton-cell']")).not.toBeNull();
  });

  it("populated state: expanding a row reveals the specialist's own trace, labeled distinctly", () => {
    render(<IllQueueView requests={ILL_QUEUE_FIXTURE} status="ready" />);
    fireEvent.click(screen.getByText("The Left Hand of Darkness"));
    expect(screen.getByText(/specialist's reasoning/i)).toBeInTheDocument();
    expect(screen.getByText("hold_2a")).toBeInTheDocument();
  });

  it("populated state: shows the requester's real name and a formatted request date, never the raw patron id or ISO string", () => {
    render(<IllQueueView requests={ILL_QUEUE_FIXTURE} status="ready" />);
    expect(screen.getByText("Devi Kapoor")).toBeInTheDocument();
    expect(screen.getByText("Aug 20, 2026")).toBeInTheDocument();
    expect(screen.queryByText("2026-08-20T09:00:00+00:00")).not.toBeInTheDocument();
  });

  it("empty state: names the filter as why nothing shows", () => {
    render(<IllQueueView requests={[]} status="ready" />);
    expect(screen.getByText(/no ill requests match/i)).toBeInTheDocument();
  });

  it("error state: a specific, retry-oriented message", () => {
    render(<IllQueueView requests={[]} status="error" />);
    expect(screen.getByText(/failed to load the ill queue/i)).toBeInTheDocument();
  });

  it("shows a clear access-denied message when status is forbidden, not the generic failure message", () => {
    render(<IllQueueView requests={[]} status="forbidden" />);
    expect(screen.getByText("You do not have access to this workflow.")).toBeInTheDocument();
  });

  it("expanding a second time collapses the row again (toggle)", () => {
    render(<IllQueueView requests={ILL_QUEUE_FIXTURE} status="ready" />);
    const trigger = screen.getByText("The Left Hand of Darkness");
    fireEvent.click(trigger);
    expect(screen.getByText(/specialist's reasoning/i)).toBeInTheDocument();
    fireEvent.click(trigger);
    expect(screen.queryByText(/specialist's reasoning/i)).toBeNull();
  });

  it("a memory recall summary renders as a distinctly labeled indicator, separate from the specialist trace", () => {
    render(<IllQueueView requests={ILL_QUEUE_FIXTURE} status="ready" />);
    fireEvent.click(screen.getByText("The Left Hand of Darkness"));
    const indicator = screen.getByTestId("memory-recall-indicator");
    expect(indicator).toBeInTheDocument();
    expect(screen.getByText(/memory recall:/i)).toBeInTheDocument();
  });

  it("a request with no memory recall renders the trace without a recall indicator", () => {
    const noRecall: IllRequest[] = [
      {
        illRequestId: "ill_req_999",
        requestedTitle: "Kindred",
        requesterName: "Octavia Brooks",
        requestedAt: "2026-08-15T12:00:00+00:00",
        status: "open",
        tier: "YELLOW",
        specialistTrace: { narrowedCandidateId: "hold_9z", confidence: 0.5, stillAmbiguous: false },
      },
    ];
    render(<IllQueueView requests={noRecall} status="ready" />);
    fireEvent.click(screen.getByText("Kindred"));
    expect(screen.getByText(/specialist's reasoning/i)).toBeInTheDocument();
    expect(screen.queryByTestId("memory-recall-indicator")).toBeNull();
  });

  // Craft-bar coverage (frontend_architecture.md section 7.4 / the plan's
  // Global Constraint on six-state interactive elements): the row-expand
  // trigger needs the same default/hover/focus/active/disabled treatment as
  // any other interactive element in the app, and toggling it must be
  // reflected via aria-expanded for keyboard and assistive-tech users.
  it("expand trigger: has hover, focus, and active styling, and toggles aria-expanded", () => {
    render(<IllQueueView requests={ILL_QUEUE_FIXTURE} status="ready" />);
    const trigger = screen.getByRole("button", { name: /the left hand of darkness/i });
    expect(trigger.className).toContain("stacks-focus-ring");
    expect(trigger.className).toContain("hover:");
    expect(trigger.className).toContain("active:");
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(trigger);
    expect(trigger).toHaveAttribute("aria-expanded", "true");
  });

  it("expand trigger: a request with no specialist trace renders a disabled, non-interactive row (no button)", () => {
    const noTrace: IllRequest[] = [
      {
        illRequestId: "ill_req_no_trace", requestedTitle: "Unrouted Title",
        requesterName: "Priya Nair", requestedAt: "2026-08-10T08:00:00+00:00",
        status: "no_match", tier: null,
      },
    ];
    render(<IllQueueView requests={noTrace} status="ready" />);
    expect(screen.queryByRole("button", { name: /unrouted title/i })).toBeNull();
    const disabled = screen.getByTestId("expand-disabled");
    expect(disabled).toHaveAttribute("aria-disabled", "true");
    expect(disabled).toHaveTextContent("Unrouted Title");
  });

  it("the expanded detail row uses the surface-2 nested-fill token, not the canvas background token", () => {
    render(<IllQueueView requests={ILL_QUEUE_FIXTURE} status="ready" />);
    fireEvent.click(screen.getByRole("button", { name: /Left Hand of Darkness/ }));
    const detailCell = screen.getByText("The specialist's reasoning").closest("td");
    expect(detailCell?.style.background).toBe("var(--color-surface-2)");
  });
});
