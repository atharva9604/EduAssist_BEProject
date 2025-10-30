"use client";

import React, { useState } from "react";
import type { TodoItem } from "@/app/dashboard/page";

type Props = {
  todos: TodoItem[];
  onAdd: (t: TodoItem) => void;
  onToggle: (id: string) => void;
  onDelete: (id: string) => void;
};

export default function TodoList({ todos, onAdd, onToggle, onDelete }: Props) {
  const [text, setText] = useState("");

  return (
    <div>
      <div className="flex flex-col gap-3 mb-4">
        <h2 className="text-sm uppercase tracking-wider text-gray-400">To‑Do</h2>
        <input
          placeholder="Add a task"
          value={text}
          onChange={(e) => setText(e.target.value)}
          className="flex-1 bg-black/40 border border-white/10 rounded-lg px-3 py-2 outline-none focus:border-[#DAA520]"
        />
        <button
          onClick={() => {
            if (!text.trim()) return;
            onAdd({ id: crypto.randomUUID(), text: text.trim(), done: false });
            setText("");
          }}
          className="px-4 py-2 rounded-lg bg-[#DAA520] text-black font-semibold shadow-[0_0_25px_rgba(218,165,32,0.25)]"
        >
          Add
        </button>
      </div>

      <div className="space-y-2">
        {todos.length === 0 ? (
          <p className="text-sm text-gray-500">No tasks yet.</p>
        ) : (
          todos.map((t) => (
            <div
              key={t.id}
              className="flex items-center justify-between bg-black/40 border border-white/10 rounded-lg px-3 py-2"
            >
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={t.done}
                  onChange={() => onToggle(t.id)}
                />
                <span
                  className={`text-sm ${
                    t.done ? "line-through text-gray-500" : "text-gray-100"
                  }`}
                >
                  {t.text}
                </span>
              </label>
              <button
                onClick={() => onDelete(t.id)}
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