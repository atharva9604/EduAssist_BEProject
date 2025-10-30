'use client';

import { useRef, useState } from 'react';
import { Upload } from 'lucide-react';
import { generateQuestionPaper, QuestionPaperResponse } from '@/services/questionPaperService';

export default function QuestionPaperGenerator() {
  const [content, setContent] = useState('');
  const [numMcq, setNumMcq] = useState(5);
  const [numShort, setNumShort] = useState(3);
  const [numLong, setNumLong] = useState(2);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<QuestionPaperResponse | null>(null);
  const [error, setError] = useState('');
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const uploadPdfAndExtract = async (file: File): Promise<string> => {
    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch("/api/pdf/extract", { method: "POST", body: fd });
    if (!res.ok) throw new Error("PDF extraction failed");
    const data = await res.json();
    return data.text || "";
  };

  const handleGenerate = async () => {
    try {
      setLoading(true);
      setError('');
      setResult(null);
  
      let sourceText = content;
  
      // If textarea empty but a PDF is selected → extract text from PDF
      if (!sourceText.trim() && pdfFile) {
        sourceText = await uploadPdfAndExtract(pdfFile);
        if (!sourceText.trim()) {
          setError('Extracted PDF content is empty.');
          setLoading(false);
          return;
        }
        // optional: show a preview in textarea
        setContent(sourceText.slice(0, 5000));
      }
  
      if (!sourceText.trim()) {
        setError('Please enter content or upload a PDF.');
        setLoading(false);
        return;
      }
  
      // Normalize numeric inputs; allow empty/invalid -> 0
      const safeInt = (v: number) => (Number.isFinite(v) && v >= 0 ? Math.floor(v) : 0);
      const response = await generateQuestionPaper({
        content: sourceText,
        document_type: pdfFile ? 'pdf' : 'text',
        num_mcq: safeInt(numMcq),
        num_short: safeInt(numShort),
        num_long: safeInt(numLong),
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

  const buildText = () => {
    if (!result) return "";
    const lines: string[] = [];
    lines.push("Generated Question Paper");
    lines.push(`Total Marks: ${result.total_marks}`);
    lines.push("");
  
    if (result.questions.mcq_questions.length) {
      lines.push("MCQs:");
      result.questions.mcq_questions.forEach((q, i) => {
        lines.push(`${i + 1}. ${q.question}`);
        (q.options || []).forEach((opt, j) => {
          lines.push(`   ${String.fromCharCode(65 + j)}. ${opt}`);
        });
        lines.push(`   Answer: ${q.correct_answer}`);
        lines.push("");
      });
    }
  
    if (result.questions.short_answer_questions.length) {
      lines.push("Short Answer Questions:");
      result.questions.short_answer_questions.forEach((q, i) => {
        lines.push(`${i + 1}. ${q.question}`);
        lines.push(`   Marks: ${q.marks}`);
        lines.push("");
      });
    }
  
    if (result.questions.long_answer_questions.length) {
      lines.push("Long Answer Questions:");
      result.questions.long_answer_questions.forEach((q, i) => {
        lines.push(`${i + 1}. ${q.question}`);
        lines.push(`   Marks: ${q.marks}`);
        lines.push("");
      });
    }
  
    return lines.join("\n");
  };

  const downloadTXT = () => {
    const text = buildText();
    if (!text) return;
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "question-paper.txt";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="max-w-4xl mx-auto p-6 bg-gray-950 text-gray-100 min-h-screen">
      <h1 className="text-3xl font-bold mb-6 text-[#DAA520]">
        Question Paper Generator
      </h1>

      {/* Input Form */}
      <div className="bg-gray-800 rounded-lg p-6 mb-6">
        <div className="flex items-center justify-between mb-2">
          <label className="font-semibold">Content</label>
          <div className="flex items-center gap-2">
            {pdfFile ? (
              <span className="text-xs text-gray-400 truncate max-w-[200px]" title={pdfFile.name}>
                {pdfFile.name}
              </span>
            ) : null}
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="p-2 rounded-lg bg-gray-700 hover:bg-gray-600 border border-gray-600"
              title="Upload PDF"
            >
              <Upload className="w-4 h-4" />
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="application/pdf"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0] || null;
                setPdfFile(f);
                setError('');
              }}
            />
            <button
  onClick={downloadTXT}
  className="mt-4 px-4 py-2 rounded-lg bg-[#DAA520] text-black font-semibold hover:bg-[#B8860B]"
>
  Download TXT
</button>
          </div>
        </div>
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
              onChange={(e) => {
                const v = e.target.value;
                setNumMcq(v === '' ? 0 : (parseInt(v, 10) || 0));
              }}
              className="w-full p-2 rounded-lg bg-gray-700 text-white border border-gray-600"
              min="0"
            />
          </div>
          <div>
            <label className="block mb-2 font-semibold">Short Questions</label>
            <input
              type="number"
              value={numShort}
              onChange={(e) => {
                const v = e.target.value;
                setNumShort(v === '' ? 0 : (parseInt(v, 10) || 0));
              }}
              className="w-full p-2 rounded-lg bg-gray-700 text-white border border-gray-600"
              min="0"
            />
          </div>
          <div>
            <label className="block mb-2 font-semibold">Long Questions</label>
            <input
              type="number"
              value={numLong}
              onChange={(e) => {
                const v = e.target.value;
                setNumLong(v === '' ? 0 : (parseInt(v, 10) || 0));
              }}
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
        {pdfFile && (
          <p className="mt-2 text-xs text-gray-400">
            Note: PDF selected. Hook backend to extract text from PDF for generation.
          </p>
        )}
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