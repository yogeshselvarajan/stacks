// frontend/lib/api/calendar.ts
import { CalendarBooking, bffFetch } from "./types";

export function getCalendar(roomId?: string): Promise<CalendarBooking[]> {
  const query = roomId ? `?room_id=${encodeURIComponent(roomId)}` : "";
  return bffFetch<CalendarBooking[]>(`/api/calendar${query}`);
}
