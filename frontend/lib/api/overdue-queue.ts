// frontend/lib/api/overdue-queue.ts
import { OverdueCase, bffFetch } from "./types";

export function getOverdueQueue(): Promise<OverdueCase[]> {
  return bffFetch<OverdueCase[]>("/api/overdue-queue");
}
