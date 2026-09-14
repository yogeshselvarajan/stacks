"use client";

import { useCallback, useEffect, useState } from "react";
import { CalendarView } from "@/components/calendar-view";
import { NewBookingForm } from "@/components/new-booking-form";
import { ApiError, CalendarBooking } from "@/lib/api/types";
import { getCalendar } from "@/lib/api/calendar";

export default function CalendarPage() {
  const [bookings, setBookings] = useState<CalendarBooking[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error" | "forbidden">("loading");

  useEffect(() => {
    document.title = "Stacks | Calendar";
  }, []);

  const refetch = useCallback(() => {
    getCalendar()
      .then((b) => {
        setBookings(b);
        setStatus("ready");
      })
      .catch((err) => setStatus(err instanceof ApiError && err.status === 403 ? "forbidden" : "error"));
  }, []);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return (
    <>
      {status !== "forbidden" && <NewBookingForm onCreated={refetch} />}
      <CalendarView bookings={bookings} status={status} />
    </>
  );
}
