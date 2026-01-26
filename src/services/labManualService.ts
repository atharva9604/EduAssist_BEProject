const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';

export interface LabManualResponse {
  id: string;
  subject: string;
  course_code?: string;
  prerequisites?: string;
  lab_objectives: string[];
  lab_outcomes: string[];
  manual_content: any;
  created_at?: string;
}

/**
 * Generate a lab manual from a PDF or DOCX file
 * Returns a downloadable PDF file
 */
export async function generateLabManualFromPdf(
  file: File,
  numModules: number = 5
): Promise<void> {
  const form = new FormData();
  form.append('file', file);
  form.append('num_modules', numModules.toString());

  const res = await fetch(`${API_BASE}/api/generate-lab-manual-from-pdf`, {
    method: 'POST',
    body: form,
  });

  if (!res.ok) {
    const errorText = await res.text();
    let errorMessage = 'Failed to generate lab manual';
    try {
      const errorJson = JSON.parse(errorText);
      errorMessage = errorJson.detail || errorMessage;
    } catch {
      errorMessage = errorText || errorMessage;
    }
    throw new Error(errorMessage);
  }

  // Get filename from Content-Disposition header or use default
  const contentDisposition = res.headers.get('Content-Disposition');
  let filename = 'lab_manual.pdf';
  if (contentDisposition) {
    const filenameMatch = contentDisposition.match(/filename="?(.+)"?/);
    if (filenameMatch) {
      filename = filenameMatch[1];
    }
  }
  
  // Ensure filename has .pdf extension
  if (!filename.endsWith('.pdf')) {
    filename = filename.replace(/\.(docx|doc)$/, '.pdf');
    if (!filename.endsWith('.pdf')) {
      filename = `${filename}.pdf`;
    }
  }

  // Download the file
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

/**
 * List all lab manuals for the current user
 */
export async function listLabManuals(): Promise<{ manuals: LabManualResponse[] }> {
  const res = await fetch(`${API_BASE}/api/lab-manuals`);
  if (!res.ok) {
    throw new Error('Failed to list lab manuals');
  }
  return res.json();
}

/**
 * Get a specific lab manual by ID
 */
export async function getLabManual(manualId: number): Promise<{ manual: LabManualResponse }> {
  const res = await fetch(`${API_BASE}/api/lab-manuals/${manualId}`);
  if (!res.ok) {
    throw new Error('Failed to get lab manual');
  }
  return res.json();
}

/**
 * Download a previously generated lab manual as PDF
 */
export async function downloadLabManual(manualId: number): Promise<void> {
  const res = await fetch(`${API_BASE}/api/download-lab-manual/${manualId}`);
  if (!res.ok) {
    throw new Error('Failed to download lab manual');
  }

  // Get filename from Content-Disposition header or use default
  const contentDisposition = res.headers.get('Content-Disposition');
  let filename = `lab_manual_${manualId}.pdf`;
  if (contentDisposition) {
    const filenameMatch = contentDisposition.match(/filename="?(.+)"?/);
    if (filenameMatch) {
      filename = filenameMatch[1];
    }
  }
  
  // Ensure filename has .pdf extension
  if (!filename.endsWith('.pdf')) {
    filename = filename.replace(/\.(docx|doc)$/, '.pdf');
    if (!filename.endsWith('.pdf')) {
      filename = `${filename}.pdf`;
    }
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
