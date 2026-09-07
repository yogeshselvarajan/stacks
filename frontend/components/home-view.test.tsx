import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { HomeView } from "./home-view";
import { AUDIT_FIXTURE } from "@/lib/fixtures";

describe("HomeView", () => {
  it("loading state: renders a card-shaped skeleton, not a spinner", () => {
    const { container } = render(
      <HomeView status="loading" pendingByTier={null} lastSweepSummary={null} resolvedTodayCount={null} recentActivity={null} />
    );
    expect(container.querySelector("[data-testid='skeleton-line']")).not.toBeNull();
  });

  it("populated state: shows RED and YELLOW pending as distinct KPI cards", () => {
    render(
      <HomeView
        status="ready"
        pendingByTier={{ GREEN: 9, YELLOW: 2, RED: 1 }}
        lastSweepSummary={null}
        resolvedTodayCount={17}
        recentActivity={[]}
      />
    );
    expect(screen.getByText("Red pending")).toBeInTheDocument();
    expect(screen.getByText("Yellow pending")).toBeInTheDocument();
  });

  it("populated state: shows the resolved-today count as its own KPI card", () => {
    render(
      <HomeView
        status="ready"
        pendingByTier={{ GREEN: 9, YELLOW: 2, RED: 1 }}
        lastSweepSummary={null}
        resolvedTodayCount={17}
        recentActivity={[]}
      />
    );
    expect(screen.getByText("Resolved today")).toBeInTheDocument();
    expect(screen.getByText("17")).toBeInTheDocument();
  });

  it("populated state: shows the last-sweep summary when present", () => {
    render(
      <HomeView
        status="ready"
        pendingByTier={{ GREEN: 9, YELLOW: 2, RED: 1 }}
        lastSweepSummary="Last night's sweep: 14 cases processed, 2 pending your review."
        resolvedTodayCount={17}
        recentActivity={[]}
      />
    );
    expect(screen.getByText(/14 cases processed/)).toBeInTheDocument();
  });

  it("populated state: renders the activity feed entries", () => {
    render(
      <HomeView
        status="ready"
        pendingByTier={{ GREEN: 9, YELLOW: 2, RED: 1 }}
        lastSweepSummary={null}
        resolvedTodayCount={17}
        recentActivity={AUDIT_FIXTURE}
      />
    );
    expect(screen.getByText(/resolve_room_conflict/)).toBeInTheDocument();
    expect(screen.getByText(/notify_parties/)).toBeInTheDocument();
  });

  it("empty activity feed: a specific, instructive message, not a blank area", () => {
    render(
      <HomeView status="ready" pendingByTier={{ GREEN: 0, YELLOW: 0, RED: 0 }} lastSweepSummary={null} resolvedTodayCount={0} recentActivity={[]} />
    );
    expect(screen.getByText(/no activity yet/i)).toBeInTheDocument();
  });

  it("error state: shows a specific retry-oriented message", () => {
    render(<HomeView status="error" pendingByTier={null} lastSweepSummary={null} resolvedTodayCount={null} recentActivity={null} />);
    expect(screen.getByText(/failed to load/i)).toBeInTheDocument();
  });
});
