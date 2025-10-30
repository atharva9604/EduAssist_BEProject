"use client";

import React, { useState } from "react";
import type { TimetableEntry } from "@/app/dashboard/page";

const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

type Props = {
  entries: TimetableEntry[];
  onAdd: (e: TimetableEntry) => void;
  onDelete: (id: string) => void;
};

export default function TimeTable({ entries, onAdd, onDelete }: Props) {
  const [form, setForm] = useState({
    day: days[0],
    time: "",
    subject: "",
    classroom: "",
  });

  return (
    <div>
      <div className="grid grid-cols-1 md:grid-cols-5 gap-3 mb-4">
        <select
          value={form.day}
          onChange={(e) => setForm((f) => ({ ...f, day: e.target.value }))}
          className="bg-black/40 border border-white/10 rounded-lg px-3 py-2 outline-none focus:border-[#DAA520]"
        >
          {days.map((d) => (
            <option key={d} value={d}>
              {d}
            </option>
          ))}
        </select>
        <input
          placeholder="Time (10:00 - 11:00)"
          value={form.time}
          onChange={(e) => setForm((f) => ({ ...f, time: e.target.value }))}
          className="bg-black/40 border border-white/10 rounded-lg px-3 py-2 outline-none focus:border-[#DAA520]"
        />
        <input
          placeholder="Subject"
          value={form.subject}
          onChange={(e) => setForm((f) => ({ ...f, subject: e.target.value }))}
          className="bg-black/40 border border-white/10 rounded-lg px-3 py-2 outline-none focus:border-[#DAA520]"
        />
        <input
          placeholder="Classroom"
          value={form.classroom}
          onChange={(e) => setForm((f) => ({ ...f, classroom: e.target.value }))}
          className="bg-black/40 border border-white/10 rounded-lg px-3 py-2 outline-none focus:border-[#DAA520]"
        />
        <button
          onClick={() => {
            if (!form.time.trim() || !form.subject.trim()) return;
            onAdd({
              id: crypto.randomUUID(),
              day: form.day,
              time: form.time.trim(),
              subject: form.subject.trim(),
              classroom: form.classroom.trim() || undefined,
            });
            setForm({ day: days[0], time: "", subject: "", classroom: "" });
          }}
          className="px-4 py-2 rounded-lg bg-[#DAA520] text-black font-semibold shadow-[0_0_25px_rgba(218,165,32,0.25)]"
        >
          Add
        </button>
      </div>

      <div className="space-y-2">
        {entries.length === 0 ? (
          <p className="text-sm text-gray-500">No timetable entries yet.</p>
        ) : (
          entries.map((e) => (
            <div
              key={e.id}
              className="flex items-center justify-between bg-black/40 border border-white/10 rounded-lg px-3 py-2"
            >
              <div className="text-sm">
                <span className="text-gray-300">{e.day} • </span>
                <span className="text-gray-300">{e.time} • </span>
                <span className="text-gray-100 font-medium">{e.subject}</span>
                {e.classroom ? (
                  <span className="text-gray-400"> • {e.classroom}</span>
                ) : null}
              </div>
              <button
                onClick={() => onDelete(e.id)}
                className="text-red-400 text-sm hover:text-red-300"
              >
                Delete
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}