'use client';

import React, { useState } from 'react';
import { generatePptMulti, listPresentations, downloadPpt, uploadSyllabus, generatePpt } from '../services/pptService';

type Message = { role: 'user' | 'system'; text: string };

export default function PPTGenerator() {
  const [topic, setTopic] = useState('');
  const [subject, setSubject] = useState('');
  const [content, setContent] = useState('');
  const [numSlides, setNumSlides] = useState(8); // can remove this if not needed
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    { role: 'system', text: 'Hi! Enter Topics (one per line) and a Subject, then click Generate PPT.' },
  ]);
  const [presentations, setPresentations] = useState<any[]>([]);
  const [syllabusFile, setSyllabusFile] = useState<File | null>(null);

  const push = (m: Message) => setMessages((prev) => [...prev, m]);

  // --- GENERATE HANDLER: uses single-topic API when user provides content ---
  const handleGenerate = async () => {
    const topicList = topic
      .split('\n')
      .map(t => t.trim())
      .filter(Boolean);
    if (topicList.length === 0 || !subject.trim()) return;
    setLoading(true);
    push({ role: 'user', text: `Topics: ${topicList.join(', ')}\nSubject: ${subject}${content.trim() ? `\nContent provided (${content.trim().length} chars)` : ''}` });
    try {
      let resp;
      if (content.trim() && topicList.length === 1) {
        // If user provided content for a single topic, use the single-topic endpoint
        resp = await generatePpt({ topic: topicList[0], content, num_slides: numSlides, subject });
      } else {
        // Otherwise generate via multi-topic endpoint (Gemini uses its own knowledge)
        resp = await generatePptMulti(topicList, subject, numSlides);
      }
      if (resp.success && resp.file_path) {
        push({ role: 'system', text: `Presentation created ✅\nFile: ${resp.presentation_id}` });
      } else {
        push({ role: 'system', text: 'Generation failed. Please try again.' });
      }
    } catch (e: any) {
      push({ role: 'system', text: `Error: ${e.message}` });
    } finally {
      setLoading(false);
    }
  };

  const handleList = async () => {
    try {
      const data = await listPresentations();
      setPresentations(data.presentations || []);
      push({ role: 'system', text: `Found ${data.presentations?.length || 0} presentations.` });
    } catch (e: any) {
      push({ role: 'system', text: `Error listing files: ${e.message}` });
    }
  };

  const handleSyllabusUpload = async () => {
    try {
      if (!syllabusFile) {
        push({ role: 'system', text: 'Please choose a PDF syllabus to upload.' });
        return;
      }
      if (syllabusFile.type !== 'application/pdf') {
        push({ role: 'system', text: 'Only PDF files are allowed.' });
        return;
      }
      setLoading(true);
      await uploadSyllabus(syllabusFile);
      push({ role: 'system', text: 'Syllabus uploaded ✅' });
    } catch (e: any) {
      push({ role: 'system', text: `Upload failed: ${e.message}` });
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (filename: string) => {
    try {
      await downloadPpt(filename);
      push({ role: 'system', text: `Downloaded: ${filename}` });
    } catch (e: any) {
      push({ role: 'system', text: `Download error: ${e.message}` });
    }
  };

  return (
    <div className="max-w-5xl mx-auto p-6 text-gray-100 min-h-screen bg-gray-950">
      <h1 className="text-3xl font-bold mb-6 text-[#DAA520]">PPT Generator</h1>

      {/* Chat window */}
      <div className="bg-gray-800 rounded-lg p-4 h-80 overflow-y-auto mb-4 space-y-3 border border-gray-700">
        {messages.map((m, i) => (
          <div key={i} className={m.role === 'user' ? 'text-right' : 'text-left'}>
            <span className={`inline-block px-3 py-2 rounded-lg ${m.role === 'user' ? 'bg-[#DAA520] text-black' : 'bg-gray-800 text-gray-100'}`}>
              {m.text}
            </span>
          </div>
        ))}
      </div>

      {/* Form */}
      <div className="bg-gray-900 rounded-lg p-6 mb-6 border border-gray-800">
        {/* Syllabus upload */}
        <div className="mb-6">
          <label className="block mb-2 font-semibold">Upload Syllabus PDF (one-time)</label>
          <div className="flex gap-3 items-center">
            <input
              type="file"
              accept="application/pdf"
              onChange={(e) => setSyllabusFile(e.target.files?.[0] || null)}
              className="flex-1 p-2 rounded-lg bg-gray-700 text-white border border-gray-600"
            />
            <button
              onClick={handleSyllabusUpload}
              className="px-4 py-2 bg-[#DAA520] text-black rounded-lg font-semibold hover:bg-[#B8860B] transition"
              disabled={loading}
            >
              {loading ? 'Uploading…' : 'Upload'}
            </button>
          </div>
        </div>
        {/* Multi-topic and subject input */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="md:col-span-2">
            <label htmlFor="topics" className="block text-sm font-medium text-gray-700 mb-2">
              Topics (one per line) *
            </label>
            <textarea
              id="topics"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Photosynthesis&#10;Cell Division&#10;World War II"
              rows={5}
              required
            />
            {/* Optional content box */}
            <label htmlFor="content" className="block text-sm font-medium text-gray-700 mb-2 mt-4">
              Content (optional — used when a single topic is entered)
            </label>
            <textarea
              id="content"
              value={content}
              onChange={(e) => setContent(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Paste your own points or text here. If left empty, Gemini will generate content based on the topic and subject."
              rows={6}
            />
          </div>
          <div>
            <label htmlFor="subject" className="block text-sm font-medium text-gray-700 mb-2">
              Subject *
            </label>
            <input
              type="text"
              id="subject"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Biology"
              required
            />
            <label htmlFor="numslides" className="block text-sm font-medium text-gray-700 mb-2 mt-4">
              Slide count
            </label>
            <input
              type="number"
              id="numslides"
              value={numSlides}
              min={1}
              onChange={(e) => setNumSlides(parseInt(e.target.value || '0', 10))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g., 12"
            />
          </div>
        </div>
        <div className="mt-4 flex gap-3">
          <button
            onClick={handleGenerate}
            disabled={loading || !topic.trim() || !subject.trim()}
            className="px-6 py-3 bg-[#DAA520] text-black rounded-lg font-semibold hover:bg-[#B8860B] transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Generating…' : 'Generate PPT'}
          </button>
          <button
            onClick={handleList}
            className="px-6 py-3 bg-gray-700 text-white rounded-lg border border-gray-600 hover:bg-gray-600"
          >
            View Previous PPTs
          </button>
        </div>
      </div>

      {/* Previous list */}
      {presentations.length > 0 && (
        <div className="bg-gray-800 rounded-lg p-6">
          <h2 className="text-2xl font-bold mb-4 text-[#DAA520]">Previous Presentations</h2>
          <div className="space-y-3">
            {presentations.map((p: any) => (
              <div key={p.filename} className="flex items-center justify-between bg-gray-700 rounded p-3">
                <div>
                  <div className="font-semibold">{p.filename}</div>
                  <div className="text-sm text-gray-300">Slides: {p.num_slides} • {new Date(p.created_at).toLocaleString()}</div>
                </div>
                <button onClick={() => handleDownload(p.filename)} className="px-4 py-2 bg-[#DAA520] text-black rounded hover:bg-[#B8860B]">
                  Download
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}