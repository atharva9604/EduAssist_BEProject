const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface QuestionPaperRequest {
  content: string;
  document_type?: string;
  num_mcq?: number;
  num_short?: number;
  num_long?: number;
  marks_mcq?: number;
  marks_short?: number;
  marks_long?: number;
  difficulty?: string;
}

export interface Question {
  question: string;
  options?: string[];
  correct_answer: string;
  marks: number;
  difficulty: string;
}

export interface QuestionPaperResponse {
  success: boolean;
  content_analysis: {
    key_concepts: string[];
    difficulty_level: string;
    subject_areas: string[];
    important_points: string[];
    question_worthy_content: string[];
  };
  questions: {
    mcq_questions: Question[];
    short_answer_questions: Question[];
    long_answer_questions: Question[];
  };
  total_marks: number;
  summary: {
    total_mcqs: number;
    total_short: number;
    total_long: number;
  };
  pdf_path?: string;
  pdf_filename?: string;
}

export const generateQuestionPaper = async (
  request: QuestionPaperRequest,
  generatePdf: boolean = false
): Promise<QuestionPaperResponse> => {
  try {
    const endpoint = generatePdf 
      ? '/api/generate-question-paper-pdf' 
      : '/api/generate-question-paper';
    
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error generating question paper:', error);
    throw error;
  }
};

export const downloadQuestionPaperPdf = async (filename: string): Promise<void> => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/download-question-paper/${encodeURIComponent(filename)}`);
    
    if (!response.ok) {
      throw new Error('Failed to download PDF');
    }

    // Get the blob
    const blob = await response.blob();
    
    // Create download link
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename.endsWith('.pdf') ? filename : `${filename}.pdf`;
    document.body.appendChild(a);
    a.click();
    
    // Cleanup
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  } catch (error) {
    console.error('Error downloading PDF:', error);
    throw error;
  }
};