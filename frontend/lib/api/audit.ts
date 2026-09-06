// frontend/lib/api/audit.ts
import { AuditEntry, bffFetch } from "./types";

export function getAuditList(): Promise<AuditEntry[]> {
  return bffFetch<AuditEntry[]>("/api/audit");
}

export function getAuditTrace(caseId: string): Promise<AuditEntry[]> {
  return bffFetch<AuditEntry[]>(`/api/audit/${encodeURIComponent(caseId)}`);
}
