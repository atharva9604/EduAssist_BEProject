const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';

export interface AttendanceSummary {
  roll_no: number;
  name: string;
  total: number;
  present: number;
  percentage: number;
}

export interface AttendanceResponse {
  tool?: string;
  session_id?: number;
  present?: number;
  total?: number;
  summary?: AttendanceSummary[];
  file_path?: string;
  status?: string;
  message?: string;
  error?: string;
  ok?: boolean;
  ask?: any;
}

// Send natural language command to attendance agent
export async function sendAttendanceCommand(message: string): Promise<AttendanceResponse> {
  const res = await fetch(`${API_BASE}/api/attendance/agent`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(errorText || 'Failed to process attendance command');
  }
  return res.json();
}

// Upload student roster (Excel file)
export async function uploadRoster(file: File, classId: number): Promise<{ filename: string; rows_inserted: number; status: string }> {
  const form = new FormData();
  form.append('file', file);
  
  const res = await fetch(`${API_BASE}/api/attendance/upload-roster?class_id=${classId}`, {
    method: 'POST',
    body: form,
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(errorText || 'Failed to upload roster');
  }
  return res.json();
}

// Download exported attendance CSV for a subject
export async function downloadAttendanceCsv(subjectId: number): Promise<void> {
  // First, ensure the CSV is generated/updated
  try {
    await sendAttendanceCommand(`Export CSV for subject ${subjectId}`);
  } catch (e) {
    // Continue even if export command fails - file might already exist
    console.warn("Export command failed, trying direct download:", e);
  }

  // Use direct URL approach - browsers allow this from user-initiated clicks
  const downloadUrl = `${API_BASE}/api/attendance/export-csv/${subjectId}`;
  
  // Create a temporary link and trigger download
  const a = document.createElement("a");
  a.href = downloadUrl;
  a.download = `attendance_summary_subject_${subjectId}.csv`;
  a.style.display = "none";
  document.body.appendChild(a);
  
  // Trigger click - this must be synchronous with user action
  a.click();
  
  // Clean up after a short delay
  setTimeout(() => {
    document.body.removeChild(a);
  }, 100);
}

// Helper function to format date for natural language
export function formatDateForCommand(date: Date | string): string {
  if (typeof date === 'string') {
    return date;
  }
  return date.toISOString().split('T')[0];
}
