"use client";

import { useEffect, useState } from "react";
import { CalendarView } from "@/components/calendar-view";
import { CalendarBooking } from "@/lib/api/types";
import { getCalendar } from "@/lib/api/calendar";

export default function CalendarPage() {
  const [bookings, setBookings] = useState<CalendarBooking[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    document.title = "Stacks | Calendar";
  }, []);

  useEffect(() => {
    getCalendar().then((b) => { setBookings(b); setStatus("ready"); }).catch(() => setStatus("error"));
  }, []);

  return <CalendarView bookings={bookings} status={status} />;
}
