const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';

export async function uploadTimetable(file: File): Promise<{ success: boolean; inserted: number; total_events: number }> {
  const form = new FormData();
  form.append('file', file);
  // scope=today imports only today's column; mode=replace clears today's events to avoid duplicates
  const res = await fetch(`${API_BASE}/api/upload-timetable?scope=today&mode=replace`, { method: 'POST', body: form });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function uploadTimetableFull(file: File, start_date: string, end_date: string): Promise<{ success: boolean; inserted: number; total_events: number }> {
  const form = new FormData();
  form.append('file', file);
  // Full sync for all weekdays to upcoming dates
  const res = await fetch(`${API_BASE}/api/upload-timetable?start_date=${start_date}&end_date=${end_date}&mode=replace`, { method: 'POST', body: form });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}