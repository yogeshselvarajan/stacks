"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { CalendarView } from "@/components/calendar-view";
import { CalendarBooking } from "@/lib/api/types";
import { getCalendar } from "@/lib/api/calendar";

export default function CalendarPage() {
  const [bookings, setBookings] = useState<CalendarBooking[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    getCalendar().then((b) => { setBookings(b); setStatus("ready"); }).catch(() => setStatus("error"));
  }, []);

  return (
    <AppShell role="room_booking_staff" pendingCounts={{ approvals: 0 }} activeRoute="/calendar">
      <CalendarView bookings={bookings} status={status} />
    </AppShell>
  );
}
