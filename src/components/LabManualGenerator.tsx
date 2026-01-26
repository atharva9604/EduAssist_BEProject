'use client';

import React, { useState } from 'react';
import { generateLabManualFromPdf, listLabManuals, downloadLabManual } from '@/services/labManualService';
import { Upload, FileText, Download, Loader2 } from 'lucide-react';

type Message = { role: 'user' | 'system'; text: string };

export default function LabManualGenerator() {
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [numModules, setNumModules] = useState(5);
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    { role: 'system', text: 'Upload a PDF containing prerequisites, objectives, and outcomes. The system will generate a complete lab manual with experiments.' },
  ]);
  const [manuals, setManuals] = useState<any[]>([]);

  const push = (m: Message) => setMessages((prev) => [...prev, m]);

  const handleGenerate = async () => {
    if (!pdfFile) {
      push({ role: 'system', text: 'Please select a PDF or DOCX file first.' });
      return;
    }

    const fileType = pdfFile.type || '';
    const fileName = pdfFile.name.toLowerCase();
    const isPdf = fileType === 'application/pdf' || fileName.endsWith('.pdf');
    const isDocx = fileType.includes('wordprocessingml') || fileType.includes('msword') || fileName.endsWith('.docx') || fileName.endsWith('.doc');
    
    if (!isPdf && !isDocx) {
      push({ role: 'system', text: 'Only PDF or DOCX files are allowed.' });
      return;
    }

    setLoading(true);
    push({ role: 'user', text: `Generating lab manual from: ${pdfFile.name} (${numModules} modules)` });
    
    try {
      await generateLabManualFromPdf(pdfFile, numModules);
      push({ role: 'system', text: `✅ Lab manual generated successfully! The file should download automatically.` });
      setPdfFile(null); // Clear file input
      // Refresh the list
      await handleListManuals();
    } catch (e: any) {
      push({ role: 'system', text: `❌ Error: ${e.message || 'Failed to generate lab manual'}` });
    } finally {
      setLoading(false);
    }
  };

  const handleListManuals = async () => {
    try {
      const data = await listLabManuals();
      setManuals(data.manuals || []);
      push({ role: 'system', text: `Found ${data.manuals?.length || 0} lab manual(s).` });
    } catch (e: any) {
      push({ role: 'system', text: `Error listing lab manuals: ${e.message}` });
    }
  };

  const handleDownload = async (manualId: number) => {
    try {
      await downloadLabManual(manualId);
      push({ role: 'system', text: `Downloaded lab manual #${manualId}` });
    } catch (e: any) {
      push({ role: 'system', text: `Download error: ${e.message}` });
    }
  };

  return (
    <div className="max-w-5xl mx-auto p-6 text-gray-100 min-h-screen bg-gray-950">
      <h1 className="text-3xl font-bold mb-6 text-[#DAA520]">Lab Manual Generator</h1>

      {/* Chat window */}
      <div className="bg-gray-800 rounded-lg p-4 h-80 overflow-y-auto mb-4 space-y-3 border border-gray-700">
        {messages.map((m, i) => (
          <div key={i} className={m.role === 'user' ? 'text-right' : 'text-left'}>
            <span className={`inline-block px-3 py-2 rounded-lg ${m.role === 'user' ? 'bg-[#DAA520] text-black' : 'bg-gray-700 text-gray-100'}`}>
              {m.text}
            </span>
          </div>
        ))}
      </div>

      {/* Form */}
      <div className="bg-gray-900 rounded-lg p-6 mb-6 border border-gray-800">
        <div className="mb-6">
          <label className="block mb-2 font-semibold text-gray-200">
            Upload PDF or DOCX with Prerequisites, Objectives & Outcomes *
          </label>
          <div className="flex gap-3 items-center">
            <div className="flex-1 relative">
              <input
                type="file"
                accept="application/pdf,.pdf,.docx,.doc,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                onChange={(e) => {
                  const file = e.target.files?.[0] || null;
                  setPdfFile(file);
                  if (file) {
                    push({ role: 'user', text: `Selected: ${file.name}` });
                  }
                }}
                className="hidden"
                id="pdf-upload"
                disabled={loading}
              />
              <label
                htmlFor="pdf-upload"
                className={`flex items-center gap-3 px-4 py-3 rounded-lg border-2 border-dashed cursor-pointer transition ${
                  pdfFile
                    ? 'border-[#DAA520] bg-[#DAA520]/10'
                    : 'border-gray-600 hover:border-gray-500 bg-gray-800'
                } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                <Upload className="w-5 h-5" />
                <span className="text-sm">
                  {pdfFile ? pdfFile.name : 'Choose PDF file'}
                </span>
              </label>
            </div>
          </div>
          <p className="text-xs text-gray-400 mt-2">
            The PDF should contain course prerequisites, lab objectives, and lab outcomes.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label htmlFor="modules" className="block text-sm font-medium text-gray-200 mb-2">
              Number of Modules *
            </label>
            <input
              type="number"
              id="modules"
              value={numModules}
              min={1}
              max={10}
              onChange={(e) => setNumModules(parseInt(e.target.value || '5', 10))}
              className="w-full px-3 py-2 bg-gray-800 text-white border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#DAA520]"
              placeholder="5"
              disabled={loading}
            />
          </div>
        </div>

        <div className="flex gap-3">
          <button
            onClick={handleGenerate}
            disabled={loading || !pdfFile}
            className="flex items-center gap-2 px-6 py-3 bg-[#DAA520] text-black rounded-lg font-semibold hover:bg-[#B8860B] transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                <span>Generating...</span>
              </>
            ) : (
              <>
                <FileText className="w-5 h-5" />
                <span>Generate Lab Manual</span>
              </>
            )}
          </button>
          <button
            onClick={handleListManuals}
            disabled={loading}
            className="px-6 py-3 bg-gray-700 text-white rounded-lg border border-gray-600 hover:bg-gray-600 transition disabled:opacity-50"
          >
            View Previous Manuals
          </button>
        </div>
      </div>

      {/* Previous manuals list */}
      {manuals.length > 0 && (
        <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
          <h2 className="text-2xl font-bold mb-4 text-[#DAA520]">Previous Lab Manuals</h2>
          <div className="space-y-3">
            {manuals.map((manual: any) => (
              <div key={manual.id} className="flex items-center justify-between bg-gray-700 rounded-lg p-4">
                <div className="flex-1">
                  <div className="font-semibold text-white">{manual.subject}</div>
                  {manual.course_code && (
                    <div className="text-sm text-gray-300">Course Code: {manual.course_code}</div>
                  )}
                  <div className="text-sm text-gray-400">
                    Created: {manual.created_at ? new Date(manual.created_at).toLocaleDateString() : 'N/A'}
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {manual.lab_objectives?.length || 0} objectives • {manual.lab_outcomes?.length || 0} outcomes
                  </div>
                </div>
                <button
                  onClick={() => handleDownload(parseInt(manual.id))}
                  className="flex items-center gap-2 px-4 py-2 bg-[#DAA520] text-black rounded-lg hover:bg-[#B8860B] transition"
                >
                  <Download className="w-4 h-4" />
                  <span>Download</span>
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
