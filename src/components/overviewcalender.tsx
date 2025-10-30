"use client";

import React, { useState } from "react";
import dynamic from "next/dynamic";
import { dateFnsLocalizer, Views } from "react-big-calendar";
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

  return (
    <div className="rounded-3xl bg-gradient-to-br from-white/10 via-white/5 to-transparent border border-white/10 p-4">
      <div className="bg-black/30 rounded-xl overflow-hidden">
        <BigCalendar
          localizer={localizer}
          events={events}
          startAccessor="start"
          endAccessor="end"
          view={Views.MONTH}
          toolbar={true}
          popup
          selectable={false}
          onSelectEvent={(ev: any) => setSelected(ev as RbcEvent)}
        
          eventPropGetter={() => ({
            style: {
              backgroundColor: "rgba(218,165,32,0.25)",
              border: "1px solid rgba(218,165,32,0.35)",
              color: "#fff",
              borderRadius: 8,
              padding: "2px 6px",
              fontSize: 12
            },
          })}
        />
      </div>

      {selected && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-black/60">
          <div className="w-[90vw] max-w-md rounded-2xl bg-gray-900 border border-white/10 p-5">
            <h3 className="text-sm uppercase tracking-wider text-gray-400 mb-2">Event Details</h3>
            <div className="space-y-2">
              <p className="text-lg font-semibold">{selected.title}</p>
              <p className="text-sm text-gray-300">
                {format(selected.start, "EEE, dd MMM yyyy • HH:mm")} — {format(selected.end, "HH:mm")}
              </p>
            </div>
            <div className="flex justify-end gap-2 pt-4">
              <button
                onClick={() => setSelected(null)}
                className="px-4 py-2 rounded-lg bg-[#DAA520] text-black font-semibold"
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