// frontend/lib/api/auth.ts
export interface SessionInfo {
  role: string;
  libraryId: string;
  caseReviewRole: string | null;
}

interface LoginResult {
  status: string;
  csrfToken: string | null;
}

export async function login(username: string, password: string): Promise<void> {
  const { bffFetch, setCsrfToken } = await import("./types");
  const result = await bffFetch<LoginResult>("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  setCsrfToken(result.csrfToken);
}

export async function getSession(): Promise<SessionInfo> {
  const { bffFetch, setCsrfToken } = await import("./types");
  const session = await bffFetch<SessionInfo & { csrfToken: string | null }>("/api/session");
  setCsrfToken(session.csrfToken);
  return session;
}

export async function logout(): Promise<void> {
  const { bffFetch, setCsrfToken } = await import("./types");
  await bffFetch<{ status: string }>("/api/auth/logout", { method: "POST" });
  setCsrfToken(null);
}

export async function judgeLogin(): Promise<void> {
  const { bffFetch, setCsrfToken } = await import("./types");
  const result = await bffFetch<LoginResult>("/api/auth/judge-login", { method: "POST" });
  setCsrfToken(result.csrfToken);
}

export type SignupRole = "branch_manager" | "circulation_staff" | "room_booking_staff" | "ill_coordinator";

export async function signup(username: string, password: string, role: SignupRole): Promise<void> {
  const { bffFetch, setCsrfToken } = await import("./types");
  const result = await bffFetch<LoginResult>("/api/auth/signup", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password, role }),
  });
  setCsrfToken(result.csrfToken);
}
