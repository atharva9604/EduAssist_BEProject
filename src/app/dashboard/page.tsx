"use client";

import React, { useEffect, useMemo, useState } from "react";
import { onAuthStateChanged, signOut, User } from "firebase/auth";
import { auth } from "@/lib/firebase";
import { motion } from "framer-motion";
import { X,UserRound, Calendar, ListTodo, BookOpen, Clock, Menu } from "lucide-react";
import { useRouter } from "next/navigation";
import Link from "next/link";

import Subjects from "@/components/subjects";
import TodoList from "@/components/todo-list";
import AdvancedCalendar, { RbcEvent } from "@/components/advacedcalendar";
import OverviewCalendar from "@/components/overviewcalender";
import Sidebar from "@/components/sidebar";
import { uploadTimetable, uploadTimetableFull } from "@/services/calenderService";
import { div } from "framer-motion/client";


export type CalendarEvent = { id: string; date: string; title: string };
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
  const [showSemesterModal, setShowSemesterModal] = useState(false);
  const [semesterStartDate, setSemesterStartDate] = useState("");
  const [semesterEndDate, setSemesterEndDate] = useState("");
  const [syncingSemester, setSyncingSemester] = useState(false);
  const [semesterSyncMsg, setSemesterSyncMsg] = useState("");
  const [subjects, setSubjects] = useState<SubjectItem[]>([]);
  const [todos, setTodos] = useState<TodoItem[]>([]);
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState("");
  const [todayEvents, setTodayEvents] = useState<any[]>([]);
  const [todayTasks, setTodayTasks] = useState<any[]>([]);

  useEffect(() => {
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
      setSemesterSyncMsg("Please choose a CSV file.");
      return;
    }
    if(!semesterStartDate || !semesterEndDate){
      setSemesterSyncMsg("Please select start and end date.");
      return;
    }
    if(semesterStartDate>semesterEndDate){
      setSemesterSyncMsg("Please select valid start date.");
      return;
    }
    setSyncingSemester(true);
    setSemesterSyncMsg("");
    try {
      const res = await uploadTimetableFull(csvFile,semesterStartDate,semesterEndDate);
      setSemesterSyncMsg(`Semester sync complete! Imported ${res.inserted} events. Total: ${res.total_events}.`);
      await refreshEventsFromBackend();
      await fetchTodayOverview();
      setTimeout(()=>{
        setShowSemesterModal(false);
        setSemesterSyncMsg("");
        setSemesterStartDate("");
        setSemesterEndDate("");
      },2000);
    } catch (e: any) {
      setSemesterSyncMsg(e?.message || "Semester sync failed.");
    } finally {
      setSyncingSemester(false);
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

  const loadSubjects = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/subjects`);
      if (!res.ok) return;
      const data = await res.json();
      setSubjects(data.subjects || []);
    } catch (e) {
      console.error("Failed to load subjects:", e);
    }
  };

  const loadTodos = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/simple-todos`);
      if (!res.ok) return;
      const data = await res.json();
      setTodos(data.todos || []);
    } catch (e) {
      console.error("Failed to load todos:", e);
    }
  };

  useEffect(() => {
    // Load all data from database on page load/refresh
    refreshEventsFromBackend();
    fetchTodayOverview();
    loadSubjects();
    loadTodos();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
                      onClick={()=>setShowSemesterModal(true)}
                      disabled={uploading || !csvFile}
                      className="px-4 py-2 bg-gray-700 text-white rounded-lg border border-gray-600 hover:bg-gray-600 transition disabled:opacity-50"
                    >
                      Sync for the Semester
                    </button>
                  </div>
                  {uploadMsg && <p className="text-sm mt-3 text-gray-300">{uploadMsg}</p>}
                  <p className="text-xs text-gray-400 mt-2">CSV columns: title, start, end[, location, description, allDay]</p>
                </div>

                {showSemesterModal && (
                  <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                    <div className="bg-gray-900 border border-white/20 rounded-2xl p-6 max-w-md w-full">
                      <div className="flex items-center justify-between mb-4">
                        <h3 className="text-xl font-semibold text-[#DAA520]">
                          Submit
                        </h3>
                        <button onClick={()=>{
                          setShowSemesterModal(false);
                          setSemesterSyncMsg("");
                          setSemesterStartDate("");
                          setSemesterEndDate("");
                        }}
                        className="text-gray-400 hover:text-white transition"
                        >
                          <X className="h-6 w-6" />
                        </button>
                      </div>
                      <div className="space-y-4">
                        <div>
                          <label className="block text-sm font-medium text-gray-300 mb-2">
                            Semester Start Date
                          </label>
                          <div className="relative">
                          <input type="date" value={semesterStartDate} onChange={(e)=> setSemesterStartDate(e.target.value)} className="w-full px-3 py-2 bg-black/40 border border-white/10 rounded-lg text-white focus:outline-none focus:border-[#DAA520]" required 
                          onClick={(e)=> e.currentTarget.showPicker?.()}
                          />
                          <Calendar className="absolute right-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400 pointer-events-none" />
    
                          </div>
                        </div>
                        <div>
    <label className="block text-sm font-medium text-gray-300 mb-2">
      Semester End Date *
    </label>
    <div className="relative">
      <input 
        type="date" 
        value={semesterEndDate} 
        onChange={(e) => setSemesterEndDate(e.target.value)} 
        className="w-full px-3 py-2 bg-black/40 border border-white/10 rounded-lg text-white focus:outline-none focus:border-[#DAA520] cursor-pointer" 
        required
        onClick={(e) => e.currentTarget.showPicker?.()}  // Force calendar to open
      />
      <Calendar className="absolute right-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400 pointer-events-none" />
    </div>
  </div>
                        {semesterSyncMsg && (
                          <div className={`p-3 rounded-lg text-sm ${
                            semesterSyncMsg.includes("complete") || semesterSyncMsg.includes("Imported") ? "bg-green-500/20 text-green-300" : "bg-red-500/20 text-red-300"
                          }`}>
                            {semesterSyncMsg}
                          </div>
                        )}
                      </div>
                      <div className="flex justify-end gap-2 pt-4">
                        <button onClick={()=>{
                          setShowSemesterModal(false);
                          setSemesterSyncMsg("");
                          setSemesterStartDate("");
                          setSemesterEndDate("");
                        }} className="px-4 py-2 rounded-lg bg-white/5 border border-white/10 text-gray-200 hover:bg-white/10 transition">Cancel</button>
                        <button onClick={handleUploadCsvFull}
                        disabled={syncingSemester || !semesterStartDate || !semesterEndDate}
                        className="px-4 py-2 rounded-lg bg-[#DAA520] text-black font-semibold shadow-[0_0_25px_rgba(218,165,32,0.25)] hover:bg-[#B8860B] transition disabled:opacity-50"
                        >
                          {syncingSemester ? "Syncing…" : "Sync"}
                        </button>
                      </div>
                    </div>
                  </div>
                )}
                
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

              </div>

              <div className="flex flex-col space-y-6 pr-1">
                <div className=" rounded-2xl bg-white/5 border border-white/10 p-5">
                  <Subjects
                    subjects={subjects}
                    onAdd={async (s) => {
                      try {
                        const res = await fetch(`${API_BASE}/api/subjects`, {
                          method: "POST",
                          headers: { "Content-Type": "application/json" },
                          body: JSON.stringify(s),
                        });
                        if (res.ok) {
                          const data = await res.json();
                          setSubjects((p) => [...p, data.subject]);
                        }
                      } catch (e) {
                        console.error("Failed to add subject:", e);
                      }
                    }}
                    onDelete={async (id) => {
                      try {
                        const res = await fetch(`${API_BASE}/api/subjects/${id}`, {
                          method: "DELETE",
                        });
                        if (res.ok) {
                          setSubjects((p) => p.filter((x) => x.id !== id));
                        }
                      } catch (e) {
                        console.error("Failed to delete subject:", e);
                      }
                    }}
                  />
                </div>

                <div className="rounded-2xl bg-white/5 border border-white/10 p-5">
                  <TodoList
                    todos={todos}
                    onAdd={async (t) => {
                      try {
                        const res = await fetch(`${API_BASE}/api/simple-todos`, {
                          method: "POST",
                          headers: { "Content-Type": "application/json" },
                          body: JSON.stringify(t),
                        });
                        if (res.ok) {
                          const data = await res.json();
                          setTodos((p) => [...p, data.todo]);
                        }
                      } catch (e) {
                        console.error("Failed to add todo:", e);
                      }
                    }}
                    onToggle={async (id) => {
                      try {
                        const todo = todos.find((t) => t.id === id);
                        if (!todo) return;
                        const res = await fetch(`${API_BASE}/api/simple-todos/${id}`, {
                          method: "PUT",
                          headers: { "Content-Type": "application/json" },
                          body: JSON.stringify({ ...todo, done: !todo.done }),
                        });
                        if (res.ok) {
                          setTodos((p) => p.map((t) => (t.id === id ? { ...t, done: !t.done } : t)));
                        }
                      } catch (e) {
                        console.error("Failed to toggle todo:", e);
                      }
                    }}
                    onDelete={async (id) => {
                      try {
                        const res = await fetch(`${API_BASE}/api/simple-todos/${id}`, {
                          method: "DELETE",
                        });
                        if (res.ok) {
                          setTodos((p) => p.filter((t) => t.id !== id));
                        }
                      } catch (e) {
                        console.error("Failed to delete todo:", e);
                      }
                    }}
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

            </motion.div>
          )}
        </section>
      </div>
    </main>
  );
}