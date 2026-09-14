import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { AccountMenu } from "./account-menu";

const mockRouterPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockRouterPush }),
}));

const mockLogout = vi.fn();
vi.mock("@/lib/api/auth", () => ({
  logout: () => mockLogout(),
}));

describe("AccountMenu", () => {
  beforeEach(() => {
    mockRouterPush.mockClear();
    mockLogout.mockClear();
    mockLogout.mockResolvedValue(undefined);
  });

  it("shows the role, human-readable (underscores replaced with spaces)", () => {
    render(<AccountMenu role="room_booking_staff" tenantName="Central Branch" />);
    expect(screen.getByText("room booking staff")).toBeInTheDocument();
  });

  it("the menu is closed by default", () => {
    render(<AccountMenu role="branch_manager" tenantName="Central Branch" />);
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });

  it("clicking the account chip opens the menu, showing role and tenant", () => {
    render(<AccountMenu role="branch_manager" tenantName="Central Branch" />);
    fireEvent.click(screen.getByRole("button", { name: /branch manager/i }));
    expect(screen.getByRole("menu")).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: /sign out/i })).toBeInTheDocument();
  });

  it("clicking the invisible overlay closes the menu", () => {
    render(<AccountMenu role="branch_manager" tenantName="Central Branch" />);
    fireEvent.click(screen.getByRole("button", { name: /branch manager/i }));
    expect(screen.getByRole("menu")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Close menu" }));
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });

  it("clicking Sign out calls logout and redirects to /login", async () => {
    render(<AccountMenu role="branch_manager" tenantName="Central Branch" />);
    fireEvent.click(screen.getByRole("button", { name: /branch manager/i }));
    fireEvent.click(screen.getByRole("menuitem", { name: /sign out/i }));
    await waitFor(() => expect(mockLogout).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(mockRouterPush).toHaveBeenCalledWith("/login"));
  });

  it("still redirects to /login even if the logout call itself fails", async () => {
    mockLogout.mockRejectedValue(new Error("network error"));
    render(<AccountMenu role="branch_manager" tenantName="Central Branch" />);
    fireEvent.click(screen.getByRole("button", { name: /branch manager/i }));
    fireEvent.click(screen.getByRole("menuitem", { name: /sign out/i }));
    await waitFor(() => expect(mockRouterPush).toHaveBeenCalledWith("/login"));
  });
});
