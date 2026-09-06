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
