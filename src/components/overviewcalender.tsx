"use client";

import React, { useState } from "react";
import dynamic from "next/dynamic";
import { dateFnsLocalizer, Views, View } from "react-big-calendar";
import { format, parse, startOfWeek, getDay } from "date-fns";
import { enUS } from "date-fns/locale";
import { RbcEvent } from "./advacedcalendar";


const BigCalendar = dynamic(() => import("react-big-calendar").then(m => m.Calendar), { ssr: false });

const locales = { "en-US": enUS };
const localizer = dateFnsLocalizer({
  format,
  parse,
  startOfWeek: () => startOfWeek(new Date(), { weekStartsOn: 1 }),
  getDay,
  locales,
});

type Props = { events: RbcEvent[] };

export default function OverviewCalendar({ events }: Props) {
  const [selected, setSelected] = useState<RbcEvent | null>(null);
  const [currentView, setCurrentView] = useState<View>(Views.MONTH);
  const [currentDate, setCurrentDate] = useState<Date>(new Date());

  return (
    <div className="rounded-3xl bg-gradient-to-br from-white/10 via-white/5 to-transparent border border-white/10 p-4">
      <div className="bg-black/30 rounded-xl overflow-hidden">
        <BigCalendar
          localizer={localizer}
          events={events}
          startAccessor={(e: any) => e.start}
          endAccessor={(e: any) => e.end}
          date={currentDate}
          onNavigate={setCurrentDate}
          view={currentView}
          onView={setCurrentView}
          toolbar={true}
          popup
          messages={{ showMore: (total: number) => `+${total}` }}
          selectable={false}
          onSelectEvent={(ev: any) => setSelected(ev as RbcEvent)}
          style={{ height: 360 }}
          eventPropGetter={() => ({
            style: {
              backgroundColor: "transparent",
              borderLeft: "3px solid #DAA520",
              color: "#DAA520",
              padding: "0 6px 0 4px",
              fontSize: 12,
              lineHeight: 1.1,
              fontWeight: 600,
            },
          })}
        />
      </div>
      {/* Small event details modal (restored) */}
      {selected && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-black/60">
          <div className="w-[90vw] max-w-md rounded-2xl bg-[#DAA520] text-black border border-black/20 p-5 shadow-xl">
            <h3 className="text-sm uppercase tracking-wider opacity-80 mb-2">Event Details</h3>
            <div className="space-y-2">
              <p className="text-lg font-semibold break-words">{selected.title}</p>
              <p className="text-sm">
                {format(selected.start, "EEE, dd MMM yyyy • HH:mm")} — {format(selected.end, "HH:mm")}
              </p>
            </div>
            <div className="flex justify-end gap-2 pt-4">
              <button
                onClick={() => setSelected(null)}
                className="px-4 py-2 rounded-lg bg-black/10 text-black font-semibold hover:bg-black/20"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}