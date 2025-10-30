"use client";

import React, { useState } from "react";
import type { SubjectItem } from "@/app/dashboard/page";

type Props = {
  subjects: SubjectItem[];
  onAdd: (s: SubjectItem) => void;
  onDelete: (id: string) => void;
};

export default function Subjects({ subjects, onAdd, onDelete }: Props) {
  const [name, setName] = useState("");
  const [code, setCode] = useState("");

  return (
    <div>
      <div className="flex flex-col gap-3 mb-4">
      <h2 className="text-sm uppercase tracking-wider text-gray-400 mb-3">Subjects </h2>
        <input
          placeholder="Subject name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="flex-1 bg-black/40 border border-white/10 rounded-lg px-3 py-2 outline-none focus:border-[#DAA520]"
        />
        <input
          placeholder="Code (optional)"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          className="flex-1 bg-black/40 border border-white/10 rounded-lg px-3 py-2 outline-none focus:border-[#DAA520]"
        />
        <button
          onClick={() => {
            if (!name.trim()) return;
            onAdd({
              id: crypto.randomUUID(),
              name: name.trim(),
              code: code.trim() || undefined,
            });
            setName("");
            setCode("");
          }}
          className="px-4 py-2 rounded-lg bg-[#DAA520] text-black font-semibold shadow-[0_0_25px_rgba(218,165,32,0.25)]"
        >
          Add
        </button>
      </div>

      <div className="space-y-2">
        {subjects.length === 0 ? (
          <p className="text-sm text-gray-500">No subjects yet.</p>
        ) : (
          subjects.map((s) => (
            <div
              key={s.id}
              className="flex items-center justify-between bg-black/40 border border-white/10 rounded-lg px-3 py-2"
            >
              <div className="text-sm">
                <span className="text-gray-100 font-medium">{s.name}</span>
                {s.code ? <span className="text-gray-400"> • {s.code}</span> : null}
              </div>
              <button
                onClick={() => onDelete(s.id)}
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