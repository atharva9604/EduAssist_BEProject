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
}

export const generateQuestionPaper = async (
  request: QuestionPaperRequest
): Promise<QuestionPaperResponse> => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/generate-question-paper`, {
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