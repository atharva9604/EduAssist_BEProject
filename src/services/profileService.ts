const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';

// Academics Types
export interface ContinuousAssessment {
  id: string;
  subject_name: string;
  assessment_type: string;
  marks: number;
  total_marks: number;
  assessment_date?: string;
}

export interface FDP {
  id: string;
  title: string;
  organization: string;
  start_date?: string;
  end_date?: string;
  certificate_path?: string;
}

export interface Lecture {
  id: string;
  title: string;
  venue?: string;
  date?: string;
  description?: string;
}

export interface Certification {
  id: string;
  name: string;
  issuing_organization: string;
  issue_date?: string;
  expiry_date?: string;
  certificate_path?: string;
}

// Research Types
export interface CurrentProject {
  id: string;
  title: string;
  description?: string;
  start_date?: string;
  status: string;
}

export interface ResearchProposal {
  id: string;
  title: string;
  description?: string;
  submission_date?: string;
  status: string;
  proposal_file_path?: string;
}

// Continuous Assessments
export async function getContinuousAssessments(): Promise<{ assessments: ContinuousAssessment[] }> {
  const res = await fetch(`${API_BASE}/api/continuous-assessments`);
  if (!res.ok) throw new Error('Failed to fetch continuous assessments');
  return res.json();
}

export async function addContinuousAssessment(data: Omit<ContinuousAssessment, 'id'>): Promise<any> {
  const res = await fetch(`${API_BASE}/api/continuous-assessments`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to add continuous assessment');
  return res.json();
}

export async function deleteContinuousAssessment(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/continuous-assessments/${id}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to delete continuous assessment');
}

// FDPs
export async function getFDPs(): Promise<{ fdps: FDP[] }> {
  const res = await fetch(`${API_BASE}/api/fdps`);
  if (!res.ok) throw new Error('Failed to fetch FDPs');
  return res.json();
}

export async function addFDP(data: Omit<FDP, 'id'>): Promise<any> {
  const res = await fetch(`${API_BASE}/api/fdps`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to add FDP');
  return res.json();
}

export async function deleteFDP(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/fdps/${id}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to delete FDP');
}

// Lectures
export async function getLectures(): Promise<{ lectures: Lecture[] }> {
  const res = await fetch(`${API_BASE}/api/lectures`);
  if (!res.ok) throw new Error('Failed to fetch lectures');
  return res.json();
}

export async function addLecture(data: Omit<Lecture, 'id'>): Promise<any> {
  const res = await fetch(`${API_BASE}/api/lectures`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to add lecture');
  return res.json();
}

export async function deleteLecture(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/lectures/${id}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to delete lecture');
}

// Certifications
export async function getCertifications(): Promise<{ certifications: Certification[] }> {
  const res = await fetch(`${API_BASE}/api/certifications`);
  if (!res.ok) throw new Error('Failed to fetch certifications');
  return res.json();
}

export async function uploadCertificate(file: File): Promise<{ success: boolean; path: string; filename: string }> {
  const form = new FormData();
  form.append('file', file);
  
  const res = await fetch(`${API_BASE}/api/upload-certificate`, {
    method: 'POST',
    body: form,
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(errorText || 'Failed to upload certificate');
  }
  return res.json();
}

export async function addCertification(data: Omit<Certification, 'id'>): Promise<any> {
  const res = await fetch(`${API_BASE}/api/certifications`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to add certification');
  return res.json();
}

export async function deleteCertification(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/certifications/${id}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to delete certification');
}

// Current Projects
export async function getCurrentProjects(): Promise<{ projects: CurrentProject[] }> {
  const res = await fetch(`${API_BASE}/api/current-projects`);
  if (!res.ok) throw new Error('Failed to fetch current projects');
  return res.json();
}

export async function addCurrentProject(data: Omit<CurrentProject, 'id'>): Promise<any> {
  const res = await fetch(`${API_BASE}/api/current-projects`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to add current project');
  return res.json();
}

export async function deleteCurrentProject(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/current-projects/${id}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to delete current project');
}

// Research Proposals
export async function getResearchProposals(): Promise<{ proposals: ResearchProposal[] }> {
  const res = await fetch(`${API_BASE}/api/research-proposals`);
  if (!res.ok) throw new Error('Failed to fetch research proposals');
  return res.json();
}

export async function addResearchProposal(data: Omit<ResearchProposal, 'id'>): Promise<any> {
  const res = await fetch(`${API_BASE}/api/research-proposals`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to add research proposal');
  return res.json();
}

export async function deleteResearchProposal(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/research-proposals/${id}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to delete research proposal');
}
