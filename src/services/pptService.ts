export interface PreferredImageUrl {
  slide_number: number;
  url: string;
}

export interface PPTGenerationPayload {
  topic: string;
  content: string;
  num_slides: number;
  subject?: string;
  module?: string;
  preferred_image_urls?: PreferredImageUrl[];
}

export interface PPTGenerateResponse {
  success: boolean;
  message: string;
  presentation_id?: string;
  file_path?: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';

export async function generatePpt(payload: PPTGenerationPayload): Promise<PPTGenerateResponse> {
  const res = await fetch(`${API_BASE}/api/generate-ppt`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || 'Failed to generate PPT');
  }
  return res.json();
}

export async function listPresentations(): Promise<any> {
  const res = await fetch(`${API_BASE}/api/list-presentations`);
  if (!res.ok) throw new Error('Failed to list presentations');
  return res.json();
}

export async function uploadSyllabus(file: File): Promise<{ success: boolean; path: string }> {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${API_BASE}/api/upload-syllabus`, {
    method: 'POST',
    body: form,
  });
  if (!res.ok) throw new Error('Failed to upload syllabus');
  return res.json();
}

export async function downloadPpt(filename: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/download-ppt/${encodeURIComponent(filename)}`);
  if (!res.ok) {
    throw new Error('Failed to download PPT');
  }

  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);

  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();

  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
}

export async function generatePptMulti(topics: string[], subject: string, numSlides?: number): Promise<PPTGenerateResponse> {
  const res = await fetch(`${API_BASE}/api/generate-ppt-multi`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ topics, subject, num_slides: numSlides }),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || 'Failed to generate PPT');
  }
  return res.json();
}