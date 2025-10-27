'use client';

import { useState } from 'react';
import { generateQuestionPaper, QuestionPaperResponse } from '@/services/questionPaperService';

export default function QuestionPaperGenerator() {
  const [content, setContent] = useState('');
  const [numMcq, setNumMcq] = useState(5);
  const [numShort, setNumShort] = useState(3);
  const [numLong, setNumLong] = useState(2);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<QuestionPaperResponse | null>(null);
  const [error, setError] = useState('');

  const handleGenerate = async () => {
    if (!content.trim()) {
      setError('Please enter some content');
      return;
    }

    setLoading(true);
    setError('');
    setResult(null);

    try {
      const response = await generateQuestionPaper({
        content,
        document_type: 'text',
        num_mcq: numMcq,
        num_short: numShort,
        num_long: numLong,
        marks_mcq: 1,
        marks_short: 3,
        marks_long: 5,
        difficulty: 'medium'
      });

      setResult(response);
    } catch (err) {
      setError('Failed to generate question paper. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6 bg-gray-950 text-gray-100 min-h-screen">
      <h1 className="text-3xl font-bold mb-6 text-[#DAA520]">
        Question Paper Generator
      </h1>

      {/* Input Form */}
      <div className="bg-gray-800 rounded-lg p-6 mb-6">
        <label className="block mb-2 font-semibold">Content</label>
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Enter the content for question generation..."
          className="w-full h-40 p-3 rounded-lg bg-gray-700 text-white border border-gray-600 focus:border-[#DAA520] focus:outline-none"
        />

        <div className="grid grid-cols-3 gap-4 mt-4">
          <div>
            <label className="block mb-2 font-semibold">MCQ Questions</label>
            <input
              type="number"
              value={numMcq}
              onChange={(e) => setNumMcq(parseInt(e.target.value))}
              className="w-full p-2 rounded-lg bg-gray-700 text-white border border-gray-600"
              min="0"
            />
          </div>
          <div>
            <label className="block mb-2 font-semibold">Short Questions</label>
            <input
              type="number"
              value={numShort}
              onChange={(e) => setNumShort(parseInt(e.target.value))}
              className="w-full p-2 rounded-lg bg-gray-700 text-white border border-gray-600"
              min="0"
            />
          </div>
          <div>
            <label className="block mb-2 font-semibold">Long Questions</label>
            <input
              type="number"
              value={numLong}
              onChange={(e) => setNumLong(parseInt(e.target.value))}
              className="w-full p-2 rounded-lg bg-gray-700 text-white border border-gray-600"
              min="0"
            />
          </div>
        </div>

        <button
          onClick={handleGenerate}
          disabled={loading}
          className="mt-4 px-6 py-3 bg-[#DAA520] text-black rounded-lg font-semibold hover:bg-[#B8860B] transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? 'Generating...' : 'Generate Question Paper'}
        </button>
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-500 text-white p-4 rounded-lg mb-6">
          {error}
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="bg-gray-800 rounded-lg p-6">
          <h2 className="text-2xl font-bold mb-4 text-[#DAA520]">
            Generated Question Paper
          </h2>

          {/* Summary */}
          <div className="bg-gray-700 rounded-lg p-4 mb-6">
            <h3 className="font-semibold mb-2">Summary</h3>
            <p>Total Marks: <span className="font-bold">{result.total_marks}</span></p>
            <p>MCQs: {result.summary.total_mcqs} | Short: {result.summary.total_short} | Long: {result.summary.total_long}</p>
          </div>

          {/* MCQ Questions */}
          {result.questions.mcq_questions.length > 0 && (
            <div className="mb-6">
              <h3 className="text-xl font-bold mb-3">Multiple Choice Questions</h3>
              {result.questions.mcq_questions.map((q, idx) => (
                <div key={idx} className="bg-gray-700 rounded-lg p-4 mb-3">
                  <p className="font-semibold">{idx + 1}. {q.question}</p>
                  {q.options && (
                    <ul className="mt-2 ml-6 list-disc">
                      {q.options.map((opt, i) => (
                        <li key={i}>{opt}</li>
                      ))}
                    </ul>
                  )}
                  <p className="mt-2 text-sm text-gray-400">Correct Answer: {q.correct_answer}</p>
                  <p className="text-sm text-gray-400">Marks: {q.marks}</p>
                </div>
              ))}
            </div>
          )}

          {/* Short Answer Questions */}
          {result.questions.short_answer_questions.length > 0 && (
            <div className="mb-6">
              <h3 className="text-xl font-bold mb-3">Short Answer Questions</h3>
              {result.questions.short_answer_questions.map((q, idx) => (
                <div key={idx} className="bg-gray-700 rounded-lg p-4 mb-3">
                  <p className="font-semibold">{idx + 1}. {q.question}</p>
                  <p className="mt-2 text-sm text-gray-400">Answer: {q.correct_answer}</p>
                  <p className="text-sm text-gray-400">Marks: {q.marks}</p>
                </div>
              ))}
            </div>
          )}

          {/* Long Answer Questions */}
          {result.questions.long_answer_questions.length > 0 && (
            <div className="mb-6">
              <h3 className="text-xl font-bold mb-3">Long Answer Questions</h3>
              {result.questions.long_answer_questions.map((q, idx) => (
                <div key={idx} className="bg-gray-700 rounded-lg p-4 mb-3">
                  <p className="font-semibold">{idx + 1}. {q.question}</p>
                  <p className="mt-2 text-sm text-gray-400">Answer: {q.correct_answer}</p>
                  <p className="text-sm text-gray-400">Marks: {q.marks}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}