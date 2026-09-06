// frontend/lib/api/ill-queue.ts
import { IllRequest, bffFetch } from "./types";

export function getIllQueue(): Promise<IllRequest[]> {
  return bffFetch<IllRequest[]>("/api/ill-queue");
}
