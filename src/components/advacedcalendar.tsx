"use client";

import React, { useMemo, useState } from "react";
import { Calendar as BigCalendar, dateFnsLocalizer, View, SlotInfo, Views } from "react-big-calendar";
import { format, parse, startOfWeek, getDay } from "date-fns";
import { enUS } from "date-fns/locale";

const locales = { "en-US": enUS };
const localizer = dateFnsLocalizer({ format, parse, startOfWeek: () => startOfWeek(new Date(), { weekStartsOn: 1 }), getDay, locales });

export type RbcEvent = {
  id: string;
  title: string;
  start: Date;
  end: Date;
  allDay?: boolean;
};

type Props = {
  events: RbcEvent[];
  onCreateEvent: (ev: RbcEvent) => void;
};

export default function AdvancedCalendar({ events, onCreateEvent }: Props) {
  const [currentView, setCurrentView] = useState<View>(Views.MONTH);
  const [currentDate, setCurrentDate] = useState(new Date());
  const [modalOpen, setModalOpen] = useState(false);
  const [modalDate, setModalDate] = useState<Date | null>(null);
  const [title, setTitle] = useState("");
  const [hour, setHour] = useState<number>(9);

  const views = useMemo(() => ({ month: true, week: true, day: true } as const), []);

  const openModalForDay = (date: Date) => {
    setModalDate(date);
    setHour(new Date().getHours());
    setTitle("");
    setModalOpen(true);
  };

  const handleSelectSlot = (slotInfo: SlotInfo) => {
    // Month view: clicking a day gives a range for that day; Week/Day gives time range
    const start = new Date(slotInfo.start);
    if (currentView === Views.MONTH) {
      openModalForDay(start);
    } else {
      // prefill hour based on the clicked time grid
      openModalForDay(start);
      setHour(start.getHours());
    }
  };

  const handleCreate = () => {
    if (!modalDate || !title.trim()) return;
    const start = new Date(modalDate);
    start.setHours(hour, 0, 0, 0);
    const end = new Date(start);
    end.setHours(hour + 1, 0, 0, 0);

    onCreateEvent({ id: crypto.randomUUID(), title: title.trim(), start, end });
    setModalOpen(false);
  };

  return (
    <div className="rounded-2xl bg-white/5 border border-white/10 p-3">
      <div className="flex items-center justify-between px-2 pb-2">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth(), 1))}
            className="px-2 py-1 text-xs rounded bg-black/40 border border-white/10"
          >
            Today
          </button>
          <div className="text-sm text-gray-300">
            {format(currentDate, "MMMM yyyy")}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setCurrentDate(prev => new Date(prev.getFullYear(), prev.getMonth() - 1, 1))} className="px-2 py-1 text-xs rounded bg-black/40 border border-white/10">Prev</button>
          <button onClick={() => setCurrentDate(prev => new Date(prev.getFullYear(), prev.getMonth() + 1, 1))} className="px-2 py-1 text-xs rounded bg-black/40 border border-white/10">Next</button>
          <select
            value={currentView}
            onChange={(e) => setCurrentView(e.target.value as View)}
            className="px-2 py-1 text-xs rounded bg-black/40 border border-white/10"
          >
            <option value={Views.MONTH}>Month</option>
            <option value={Views.WEEK}>Week</option>
            <option value={Views.DAY}>Day</option>
          </select>
        </div>
      </div>

      <div className="bg-black/30 rounded-xl overflow-hidden">
        <BigCalendar
          localizer={localizer}
          events={events}
          startAccessor="start"
          endAccessor="end"
          date={currentDate}
          onNavigate={setCurrentDate}
          view={currentView}
          onView={setCurrentView}
          selectable
          onSelectSlot={handleSelectSlot}
          popup
          messages={{ showMore: (total: number) => `+${total}` }}
          style={{ height: 360 }}
          eventPropGetter={() => ({
            style: {
              backgroundColor: "transparent",
              borderLeft: "3px solid #DAA520",
              color: "#DAA520",
              padding: "0 6px 0 4px",
              fontSize: 12,
              lineHeight: 1.1,
            },
          })}
          dayPropGetter={() => ({
            style: {
              background: "transparent",
            },
          })}
        />
      </div>

      {modalOpen && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-black/60">
          <div className="w-[90vw] max-w-md rounded-2xl bg-gray-900 border border-white/10 p-4">
            <h3 className="text-sm uppercase tracking-wider text-gray-400 mb-3">Add Event</h3>
            <div className="space-y-3">
              <div>
                <label className="text-xs text-gray-400">Date</label>
                <input
                  type="date"
                  value={modalDate ? format(modalDate, "yyyy-MM-dd") : ""}
                  onChange={(e) => setModalDate(e.target.value ? new Date(e.target.value) : modalDate)}
                  className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 outline-none focus:border-[#DAA520]"
                />
              </div>
              <div>
                <label className="text-xs text-gray-400">Title</label>
                <input
                  placeholder="Event title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 outline-none focus:border-[#DAA520]"
                />
              </div>
              <div>
                <label className="text-xs text-gray-400">Hour (0–23)</label>
                <select
                  value={hour}
                  onChange={(e) => setHour(parseInt(e.target.value, 10))}
                  className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 outline-none focus:border-[#DAA520]"
                >
                  {Array.from({ length: 24 }).map((_, i) => (
                    <option key={i} value={i}>
                      {i.toString().padStart(2, "0")}:00
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  onClick={() => setModalOpen(false)}
                  className="px-4 py-2 rounded-lg bg-white/5 border border-white/10 text-gray-200"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreate}
                  className="px-4 py-2 rounded-lg bg-[#DAA520] text-black font-semibold shadow-[0_0_25px_rgba(218,165,32,0.25)]"
                >
                  Add Event
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}