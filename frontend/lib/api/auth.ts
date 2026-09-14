// frontend/lib/api/auth.ts
export interface SessionInfo {
  role: string;
  libraryId: string;
  caseReviewRole: string | null;
}

export async function login(username: string, password: string): Promise<SessionInfo> {
  const { bffFetch } = await import("./types");
  return bffFetch<SessionInfo>("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
}

export async function getSession(): Promise<SessionInfo> {
  const { bffFetch } = await import("./types");
  return bffFetch<SessionInfo>("/api/session");
}

export async function logout(): Promise<void> {
  const { bffFetch } = await import("./types");
  await bffFetch<{ status: string }>("/api/auth/logout", { method: "POST" });
}

export type SignupRole = "branch_manager" | "circulation_staff" | "room_booking_staff" | "ill_coordinator";

export async function signup(username: string, password: string, role: SignupRole): Promise<SessionInfo> {
  const { bffFetch } = await import("./types");
  return bffFetch<SessionInfo>("/api/auth/signup", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password, role }),
  });
}
