"use client";

import { useCallback, useEffect, useState } from "react";
import { CalendarView } from "@/components/calendar-view";
import { NewBookingForm } from "@/components/new-booking-form";
import { CalendarBooking } from "@/lib/api/types";
import { getCalendar } from "@/lib/api/calendar";

export default function CalendarPage() {
  const [bookings, setBookings] = useState<CalendarBooking[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    document.title = "Stacks | Calendar";
  }, []);

  const refetch = useCallback(() => {
    getCalendar()
      .then((b) => {
        setBookings(b);
        setStatus("ready");
      })
      .catch(() => setStatus("error"));
  }, []);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return (
    <>
      <NewBookingForm onCreated={refetch} />
      <CalendarView bookings={bookings} status={status} />
    </>
  );
}
