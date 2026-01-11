"use client";

import React, { useEffect, useMemo, useState } from "react";
import { onAuthStateChanged, signOut, User } from "firebase/auth";
import { auth } from "@/lib/firebase";
import { motion } from "framer-motion";
import { UserRound, Calendar, ListTodo, BookOpen, Clock, Menu } from "lucide-react";
import { useRouter } from "next/navigation";
import Link from "next/link";

import Timetable from "@/components/time-table";
import Subjects from "@/components/subjects";
import TodoList from "@/components/todo-list";
import AdvancedCalendar, { RbcEvent } from "@/components/advacedcalendar";
import OverviewCalendar from "@/components/overviewcalender";
import Sidebar from "@/components/sidebar";
import { uploadTimetable, uploadTimetableFull } from "@/services/calenderService";

export type CalendarEvent = { id: string; date: string; title: string };
export type TimetableEntry = {
  id: string;
  day: string;
  time: string;
  subject: string;
  classroom?: string;
};
export type SubjectItem = { id: string; name: string; code?: string };
export type TodoItem = { id: string; text: string; done: boolean };

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "edit">("overview");
  const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarActiveTab, setSidebarActiveTab] = useState("home");

  const [teacherName, setTeacherName] = useState("");
  const [avatar, setAvatar] = useState("");
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [eventsFull, setEventsFull] = useState<any[]>([]);
  const [entries, setEntries] = useState<TimetableEntry[]>([]);
  const [subjects, setSubjects] = useState<SubjectItem[]>([]);
  const [todos, setTodos] = useState<TodoItem[]>([]);
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState("");
  const [todayEvents, setTodayEvents] = useState<any[]>([]);
  const [todayTasks, setTodayTasks] = useState<any[]>([]);

  useEffect(() => {
    if (!auth) {
      // Firebase not configured, set default user
      setTeacherName("Teacher");
      setAvatar("/assets/add.png");
      return;
    }
    const unsub = onAuthStateChanged(auth, (u) => {
      setUser(u);
      if (u) {
        const fallback = u.email?.split("@")[0] || "Teacher";
        setTeacherName(u.displayName || fallback);
        setAvatar(u.photoURL || "/assets/add.png");
      }
    });
    return () => unsub();
  }, []);

  const stats = useMemo(() => {
    const today = new Date().toISOString().slice(0, 10);
    const upcoming = events.filter((e) => e.date >= today).slice(0, 3);
    const completedTodos = todos.filter((t) => t.done).length;
    return { upcoming, completedTodos };
  }, [events, todos]);

  const rbcEvents = useMemo<RbcEvent[]>(
    () => {
      const backendEvents: RbcEvent[] = (eventsFull || []).map((ev: any) => ({
        id: ev.id,
        title: ev.title,
        start: new Date(ev.start),
        end: new Date(ev.end),
      }));
      const localEvents: RbcEvent[] = events.map((e) => {
        const d = new Date(e.date);
        const start = new Date(d);
        start.setHours(9, 0, 0, 0);
        const end = new Date(d);
        end.setHours(10, 0, 0, 0);
        return { id: e.id, title: e.title, start, end };
      });
      const byId = new Map<string, RbcEvent>();
      [...backendEvents, ...localEvents].forEach((ev) => {
        if (!byId.has(ev.id)) byId.set(ev.id, ev);
      });
      return Array.from(byId.values());
    },
    [eventsFull, events]
  );

  const getUserName = () => {
    if (!user) return "User";
    return teacherName || user.displayName || user.email?.split("@")[0] || "User";
  };

  const handleLogout = async () => {
    if (!auth) {
      router.push("/");
      return;
    }
    try {
      await signOut(auth);
      router.push("/");
    } catch (err) {
      console.error("Logout failed:", err);
    }
  };

  const refreshEventsFromBackend = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/events`);
      if (!res.ok) return;
      const data = await res.json();
      setEventsFull(data.events || []);
      const mapped: CalendarEvent[] = (data.events || []).map((ev: any) => ({
        id: ev.id,
        title: ev.title,
        date: (ev.start || "").slice(0, 10),
      }));
      setEvents(mapped);
    } catch (e) {
      // ignore
    }
  };

  const handleUploadCsv = async () => {
    if (!csvFile) {
      setUploadMsg("Please choose a CSV file.");
      return;
    }
    setUploading(true);
    setUploadMsg("");
    try {
      const res = await uploadTimetable(csvFile);
      setUploadMsg(`Imported ${res.inserted} events. Total: ${res.total_events}.`);
      await refreshEventsFromBackend();
      await fetchTodayOverview();
    } catch (e: any) {
      setUploadMsg(e?.message || "Upload failed.");
    } finally {
      setUploading(false);
    }
  };

  const handleUploadCsvFull = async () => {
    if (!csvFile) {
      setUploadMsg("Please choose a CSV file.");
      return;
    }
    setUploading(true);
    setUploadMsg("");
    try {
      const res = await uploadTimetableFull(csvFile);
      setUploadMsg(`Full sync: imported ${res.inserted} events. Total: ${res.total_events}.`);
      await refreshEventsFromBackend();
      await fetchTodayOverview();
    } catch (e: any) {
      setUploadMsg(e?.message || "Upload failed.");
    } finally {
      setUploading(false);
    }
  };

  const fetchTodayOverview = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/today-overview`);
      if (!res.ok) return;
      const data = await res.json();
      setTodayEvents(data.events || []);
      setTodayTasks(data.tasks || []);
    } catch (e) {
      // ignore
    }
  };

  useEffect(() => {
    fetchTodayOverview();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [events, todos]);

  const handleSidebarTabChange = (tab: string) => {
    setSidebarActiveTab(tab);
    if (tab === "home") {
      router.push("/dashboard");
    } else if (tab === "profile") {
      router.push("/profile");
    } else if (tab === "settings") {
      router.push("/settings");
    } else {
      router.push("/mainpage");
    }
  };

  return (
    <main className="min-h-screen flex bg-gradient-to-br from-gray-950 via-black to-gray-900 text-gray-100">
      <Sidebar
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
        onLogout={handleLogout}
        userName={getUserName()}
        activeTab={sidebarActiveTab}
        onTabChange={handleSidebarTabChange}
      />

      <div className="flex-1 flex flex-col">
        <header className="sticky top-0 z-20 backdrop-blur bg-black/40 border-b border-white/10">
          <div className="px-6 py-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="p-2 hover:bg-white/10 rounded-lg transition lg:hidden"
              >
                <Menu />
              </button>

              <Link href="/">
                <div className="h-10 w-10 rounded-xl bg-[#DAA520] grid place-items-center shadow-[0_0_25px_rgba(218,165,32,0.35)] cursor-pointer">
                  <span className="text-black font-extrabold">E</span>
                </div>
              </Link>

              <div>
                <p className="text-sm text-gray-400">Welcome back</p>
                <h1 className="text-lg font-semibold">{teacherName || "Teacher"}</h1>
              </div>
            </div>

            <div className="flex items-center gap-2 bg-white/5 border border-white/10 rounded-full p-1">
              <button
                onClick={() => setActiveTab("overview")}
                className={`px-4 py-2 rounded-full text-sm transition ${
                  activeTab === "overview" ? "bg-[#DAA520] text-black" : "text-gray-300 hover:text-white"
                }`}
              >
                Overview
              </button>
              <button
                onClick={() => setActiveTab("edit")}
                className={`px-4 py-2 rounded-full text-sm transition ${
                  activeTab === "edit" ? "bg-[#DAA520] text-black" : "text-gray-300 hover:text-white"
                }`}
              >
                Edit
              </button>
            </div>

            <div className="flex items-center gap-3">
              <div className="text-right hidden sm:block">
                <p className="text-xs text-gray-400">Signed in as</p>
                <p className="text-sm">{user?.email || "guest@eduassist"}</p>
              </div>
              <img
                src={avatar || "/assets/add.png"}
                alt="profile"
                className="h-10 w-10 rounded-full ring-2 ring-white/20 object-cover"
                referrerPolicy="no-referrer"
              />
            </div>
          </div>
        </header>

        <section className="max-w-7xl mx-auto px-6 py-8 w-full">
          {activeTab === "edit" ? (
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2 space-y-6">
                <div className="rounded-2xl bg-white/5 border border-white/10 p-5">
                  <h2 className="text-sm uppercase tracking-wider text-gray-400 mb-3">Profile</h2>
                  <div className="grid sm:grid-cols-[auto,1fr] gap-4 items-center">
                    <img
                      src={avatar || "/assets/add.png"}
                      alt="profile"
                      className="h-16 w-16 rounded-full ring-2 ring-white/20 object-cover"
                      referrerPolicy="no-referrer"
                    />
                    <div className="grid sm:grid-cols-2 gap-3">
                      <input
                        value={teacherName}
                        onChange={(e) => setTeacherName(e.target.value)}
                        placeholder="Teacher name"
                        className="bg-black/40 border border-white/10 rounded-lg px-3 py-2 outline-none focus:border-[#DAA520]"
                      />
                      <input
                        value={avatar}
                        onChange={(e) => setAvatar(e.target.value)}
                        placeholder="Avatar URL"
                        className="bg-black/40 border border-white/10 rounded-lg px-3 py-2 outline-none focus:border-[#DAA520]"
                      />
                    </div>
                  </div>
                </div>

                <div className="rounded-2xl bg-white/5 border border-white/10 p-5">
                  <h2 className="text-sm uppercase tracking-wider text-gray-400 mb-3">Upload Timetable (CSV)</h2>
                  <div className="flex gap-3 items-center">
                    <input
                      type="file"
                      accept=".csv,text/csv"
                      onChange={(e) => setCsvFile(e.target.files?.[0] || null)}
                      className="flex-1 p-2 rounded-lg bg-gray-700 text-white border border-gray-600"
                    />
                    <button
                      onClick={handleUploadCsv}
                      disabled={uploading || !csvFile}
                      className="px-4 py-2 bg-[#DAA520] text-black rounded-lg font-semibold hover:bg-[#B8860B] transition disabled:opacity-50"
                    >
                      {uploading ? "Uploading…" : "Upload"}
                    </button>
                    <button
                      onClick={handleUploadCsvFull}
                      disabled={uploading || !csvFile}
                      className="px-4 py-2 bg-gray-700 text-white rounded-lg border border-gray-600 hover:bg-gray-600 transition disabled:opacity-50"
                    >
                      {uploading ? "Syncing…" : "Sync Full Week"}
                    </button>
                  </div>
                  {uploadMsg && <p className="text-sm mt-3 text-gray-300">{uploadMsg}</p>}
                  <p className="text-xs text-gray-400 mt-2">CSV columns: title, start, end[, location, description, allDay]</p>
                </div>

                <div className="rounded-2xl bg-white/5 border border-white/10 p-5">
                  <h2 className="text-sm uppercase tracking-wider text-gray-400 mb-3">Calendar </h2>
                  <AdvancedCalendar
                      events={rbcEvents}
                      onCreateEvent={(ev) =>
                        setEvents((prev) => [
                          ...prev,
                          { id: ev.id, title: ev.title, date: ev.start.toISOString().slice(0, 10) },
                        ])
                      }
                  />
                </div>

                <div className="rounded-2xl bg-white/5 border border-white/10 p-5">
                  <Timetable
                    entries={entries}
                    onAdd={(entry) => setEntries((p) => [...p, entry])}
                    onDelete={(id) => setEntries((p) => p.filter((e) => e.id !== id))}
                  />
                </div>
              </div>

              <div className="flex flex-col space-y-6 pr-1">
                <div className=" rounded-2xl bg-white/5 border border-white/10 p-5">
                  <Subjects
                    subjects={subjects}
                    onAdd={(s) => setSubjects((p) => [...p, s])}
                    onDelete={(id) => setSubjects((p) => p.filter((x) => x.id !== id))}
                  />
                </div>

                <div className="rounded-2xl bg-white/5 border border-white/10 p-5">
                  <TodoList
                    todos={todos}
                    onAdd={(t) => setTodos((p) => [...p, t])}
                    onToggle={(id) =>
                      setTodos((p) => p.map((t) => (t.id === id ? { ...t, done: !t.done } : t)))
                    }
                    onDelete={(id) => setTodos((p) => p.filter((t) => t.id !== id))}
                  />
                </div>
              </div>
            </motion.div>
          ) : (
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
              <div className="grid grid-cols-1 lg:grid-cols-[2fr,1fr] gap-6">
                <div className="rounded-3xl bg-gradient-to-br from-white/10 via-white/5 to-transparent border border-white/10 p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <img
                        src={avatar || "/assets/add.png"}
                        className="h-14 w-14 rounded-2xl ring-2 ring-white/20 object-cover"
                        alt="profile"
                        referrerPolicy="no-referrer"
                      />
                      <div>
                        <h2 className="text-xl font-semibold">{teacherName}</h2>
                        <p className="text-xs text-gray-400">{user?.email}</p>
                      </div>
                    </div>
                    <div className="grid grid-cols-3 gap-3">
                      <div className="bg-black/40 border border-white/10 rounded-xl px-4 py-3">
                        <div className="flex items-center gap-2 text-gray-400 text-xs">
                          <Calendar className="h-4 w-4" /> Events
                        </div>
                        <p className="text-lg font-semibold">{events.length}</p>
                      </div>
                      <div className="bg-black/40 border border-white/10 rounded-xl px-4 py-3">
                        <div className="flex items-center gap-2 text-gray-400 text-xs">
                          <ListTodo className="h-4 w-4" /> Done
                        </div>
                        <p className="text-lg font-semibold">{stats.completedTodos}</p>
                      </div>
                      <div className="bg-black/40 border border-white/10 rounded-xl px-4 py-3">
                        <div className="flex items-center gap-2 text-gray-400 text-xs">
                          <BookOpen className="h-4 w-4" /> Subjects
                        </div>
                        <p className="text-lg font-semibold">{subjects.length}</p>
                      </div>
                    </div>
                  </div>

                  <div className="grid sm:grid-cols-2 gap-4">
                    <div className="bg-black/40 border border-white/10 rounded-xl p-4">
                      <div className="flex items-center gap-2 text-gray-300 mb-2">
                        <Clock className="h-4 w-4" />
                        <span className="text-sm">Today’s Schedule</span>
                      </div>
                      <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
                        {todayEvents.length === 0 ? (
                          <p className="text-xs text-gray-500">No events today.</p>
                        ) : (
                          todayEvents.map((e: any) => (
                            <div
                              key={e.id}
                              className="flex items-center justify-between bg-white/5 border border-white/10 rounded-lg px-3 py-2"
                            >
                              <span className="text-sm">{e.title}</span>
                              <span className="text-xs text-gray-400">
                                {new Date(e.start).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                -{new Date(e.end).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                              </span>
                            </div>
                          ))
                        )}
                      </div>
                    </div>

                    <div className="bg-black/40 border border-white/10 rounded-xl p-4">
                      <div className="flex items-center gap-2 text-gray-300 mb-2">
                        <UserRound className="h-4 w-4" />
                        <span className="text-sm">Subjects</span>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {subjects.length === 0 ? (
                          <p className="text-xs text-gray-500">No subjects added.</p>
                        ) : (
                          subjects.map((s) => (
                            <span
                              key={s.id}
                              className="text-xs px-3 py-1 rounded-full bg-white/10 border border-white/10"
                            >
                              {s.name}
                              {s.code ? <span className="text-gray-400"> • {s.code}</span> : null}
                            </span>
                          ))
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="rounded-3xl bg-gradient-to-br from-white/10 via-white/5 to-transparent border border-white/10 p-6">
                  <h3 className="text-sm uppercase tracking-wider text-gray-400 mb-3">To‑Do</h3>
                  <div className="space-y-2">
                    {todos.length === 0 ? (
                      <p className="text-sm text-gray-500">No tasks yet.</p>
                    ) : (
                      todos.map((t) => (
                        <div
                          key={t.id}
                          className="flex items-center justify-between bg-white/5 border border-white/10 rounded-lg px-3 py-2"
                        >
                          <span className={`text-sm ${t.done ? "line-through text-gray-500" : "text-gray-200"}`}>
                            {t.text}
                          </span>
                          <span
                            className={`text-[10px] px-2 py-0.5 rounded-full ${
                              t.done ? "bg-emerald-500/20 text-emerald-300" : "bg-yellow-500/20 text-yellow-300"
                            }`}
                          >
                            {t.done ? "Done" : "Pending"}
                          </span>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>

              <div className="rounded-3xl bg-gradient-to-br from-white/10 via-white/5 to-transparent border border-white/10 p-6">
                <h3 className="text-sm uppercase tracking-wider text-gray-400 mb-3">Calendar</h3>
                <OverviewCalendar events={rbcEvents} />
              </div>

              <div className="rounded-3xl bg-gradient-to-br from-white/10 via-white/5 to-transparent border border-white/10 p-6">
                <h3 className="text-sm uppercase tracking-wider text-gray-400 mb-3">Timetable</h3>
                <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
                  {entries.length === 0 ? (
                    <p className="text-sm text-gray-500">No timetable entries.</p>
                  ) : (
                    entries.map((e) => (
                      <div key={e.id} className="bg-white/5 border border-white/10 rounded-xl p-3">
                        <p className="text-xs text-gray-400">
                          {e.day} • {e.time}
                        </p>
                        <p className="text-sm font-medium">{e.subject}</p>
                        {e.classroom ? <p className="text-xs text-gray-400">{e.classroom}</p> : null}
                      </div>
                    ))
                  )}
                </div>
              </div>
            </motion.div>
          )}
        </section>
      </div>
    </main>
  );
}