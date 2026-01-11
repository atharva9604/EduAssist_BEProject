'use client';

import React, { useState } from 'react';
import { uploadSyllabus, listPresentations, downloadPpt } from '../services/pptService';
import { PiFilePptBold, PiPaperPlaneTiltBold } from "react-icons/pi";
import { X } from "lucide-react";
import Link from "next/link";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

type AssistResult = {
  text: string;
  link?: string;
  filename?: string;
  type?: string;
};

export default function PPTGenerator() {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<AssistResult | null>(null);
  const [selectedImages, setSelectedImages] = useState<File[]>([]);
  const [showPPTModes, setShowPPTModes] = useState(false);
  const [syllabusFile, setSyllabusFile] = useState<File | null>(null);
  const [uploadStatus, setUploadStatus] = useState<{ type: 'success' | 'error' | null; message: string }>({ type: null, message: '' });
  const [uploading, setUploading] = useState(false);
  const [presentations, setPresentations] = useState<any[]>([]);

  const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    const imageFiles = files.filter(file => 
      file.type.startsWith('image/') && 
      ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'].includes(file.type)
    );
    setSelectedImages(prev => [...prev, ...imageFiles]);
    e.target.value = '';
  };

  const removeImage = (index: number) => {
    setSelectedImages(prev => prev.filter((_, i) => i !== index));
  };

  const handleSyllabusUpload = async () => {
    if (!syllabusFile) {
      setUploadStatus({ type: 'error', message: 'Please choose a PDF syllabus to upload.' });
      return;
    }
    if (syllabusFile.type !== 'application/pdf') {
      setUploadStatus({ type: 'error', message: 'Only PDF files are allowed.' });
      return;
    }
    setUploading(true);
    setUploadStatus({ type: null, message: '' });
    try {
      await uploadSyllabus(syllabusFile);
      setUploadStatus({ type: 'success', message: 'Syllabus uploaded successfully ✅' });
      setSyllabusFile(null);
    } catch (e: any) {
      setUploadStatus({ type: 'error', message: `Upload failed: ${e.message}` });
    } finally {
      setUploading(false);
    }
  };

  const handleList = async () => {
    try {
      const data = await listPresentations();
      setPresentations(data.presentations || []);
    } catch (e: any) {
      setError(`Error listing files: ${e.message}`);
    }
  };

  const handleDownload = async (filename: string) => {
    try {
      await downloadPpt(filename);
    } catch (e: any) {
      setError(`Download error: ${e.message}`);
    }
  };

  // PPT Mode templates - These match backend detection patterns
  const pptModeTemplates = {
    mode1: `Create a {NUMBER}-slide PPT on {TOPIC}.
Subject: {SUBJECT}

Use the default slide structure.
Generate all content yourself.
Add relevant images automatically.`,
    mode2: `Create a {NUMBER}-slide PPT on {TOPIC}.
Subject: {SUBJECT}

Slide titles:
Slide 1: {TITLE}
Slide 2: {TITLE}
Slide 3: {TITLE}

Generate content for each slide based on its title.`,
    mode3: `Create a {NUMBER}-slide PPT on {TOPIC}.
Subject: {SUBJECT}

Use EXACT content below. Do NOT modify.

Slide 1:
Title: {TITLE}
Content:
- {bullet 1}
- {bullet 2}
- {bullet 3}

Slide 2:
Title: {TITLE}
Content:
- {bullet 1}
- {bullet 2}
- {bullet 3}`,
    mode4: `Create a {NUMBER}-slide PPT on {TOPIC}.
Subject: {SUBJECT}

Slide structure:
Slide 1: {TITLE}
Slide 2: {TITLE}
Slide 3: {TITLE}

Image placement:
Use Image 1 on Slide {X}
Use Image 2 on Slide {Y}

Generate content where not provided.`,
    mode5: `Create a {NUMBER}-slide PPT on {TOPIC}.
Subject: {SUBJECT}

Slide instructions:

Slide 1:
Title: {TITLE}
Generate content.
Use Image 1.

Slide 2:
Title: {TITLE}
Use EXACT content:
- {bullet 1}
- {bullet 2}

Slide 3:
Title: {TITLE}
Generate content.
No image.`
  };

  const insertPPTTemplate = (template: string) => {
    setPrompt(template);
    setShowPPTModes(false);
    setTimeout(() => {
      const textarea = document.querySelector('textarea');
      if (textarea) {
        textarea.focus();
        const firstPlaceholder = template.indexOf('{');
        if (firstPlaceholder !== -1) {
          textarea.setSelectionRange(firstPlaceholder, firstPlaceholder);
        }
      }
    }, 100);
  };

  const handleAskCopilot = async () => {
    if (!prompt.trim()) return;
    setError("");
    setResult(null);
    setLoading(true);
    try {
      let res;
      
      if (selectedImages.length > 0) {
        const formData = new FormData();
        formData.append('prompt', prompt);
        selectedImages.forEach((img) => {
          formData.append('images', img);
        });
        
        res = await fetch(`${API_BASE}/api/assist`, {
          method: "POST",
          body: formData,
        });
      } else {
        res = await fetch(`${API_BASE}/api/assist`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ prompt }),
        });
      }
      
      if (!res.ok) {
        const detail = await res.text();
        throw new Error(detail || "Request failed");
      }
      
      const data = await res.json();
      const link =
        data.link && data.link.startsWith("http")
          ? data.link
          : data.link
          ? `${API_BASE}${data.link}`
          : undefined;
      setResult({
        text: data.message || "Done.",
        link,
        filename: data.filename,
        type: data.type,
      });
      setSelectedImages([]);
      setPrompt(""); // Clear prompt after successful generation
    } catch (e: any) {
      setError(e?.message || "Failed to send prompt");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto p-6 text-gray-100 min-h-screen bg-gray-950">
      {/* 1. Page Heading */}
      <h1 className="text-3xl font-bold mb-6 text-[#DAA520]">PPT Generator</h1>

      {/* 2. Syllabus Upload Bar */}
      <div className="bg-gray-900 rounded-lg p-6 mb-6 border border-gray-800">
        <label className="block mb-2 font-semibold">Upload Syllabus PDF (one-time)</label>
        <div className="flex gap-3 items-center">
          <input
            type="file"
            accept="application/pdf"
            onChange={(e) => setSyllabusFile(e.target.files?.[0] || null)}
            className="flex-1 p-2 rounded-lg bg-gray-700 text-white border border-gray-600 text-sm"
          />
          <button
            onClick={handleSyllabusUpload}
            className="px-4 py-2 bg-[#DAA520] text-black rounded-lg font-semibold hover:bg-[#B8860B] transition disabled:opacity-50 disabled:cursor-not-allowed"
            disabled={uploading || !syllabusFile}
          >
            {uploading ? 'Uploading…' : 'Upload'}
          </button>
        </div>
        
        {/* 3. Upload Status Message */}
        {uploadStatus.type && (
          <div className={`mt-3 text-sm ${
            uploadStatus.type === 'success' 
              ? 'text-green-400' 
              : 'text-red-400'
          }`}>
            {uploadStatus.message}
          </div>
        )}
      </div>

      {/* 4. Chat Box (Same as Chat Page) */}
      <div className="bg-gray-900 rounded-lg p-6 mb-6 border border-gray-800">
        <div className="space-y-4">
          <textarea 
            className="w-full h-60 p-5 border border-gray-600 rounded-lg bg-gray-800 text-white placeholder-gray-400 focus:border-[#DAA520] focus:outline-none resize-none"
            placeholder="Type your PPT request here... (e.g., 'Create a 5-slide PPT on Photosynthesis. Subject: Biology')"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            disabled={loading}
          />
          
          {/* Image upload section */}
          <div className="space-y-2">
            <label className="block text-sm text-gray-300">
              Upload Images (optional): Attach images to use in PPT slides
            </label>
            <div className="flex items-center gap-2 flex-wrap">
              <label className="cursor-pointer px-3 py-2 bg-gray-700 text-white rounded hover:bg-gray-600 transition text-sm">
                📷 Select Images
                <input
                  type="file"
                  accept="image/*"
                  multiple
                  onChange={handleImageSelect}
                  className="hidden"
                  disabled={loading}
                />
              </label>
              {selectedImages.map((img, idx) => (
                <div key={idx} className="flex items-center gap-2 bg-gray-700 px-2 py-1 rounded text-sm">
                  <span className="text-gray-300 truncate max-w-[150px]">{img.name}</span>
                  <button
                    onClick={() => removeImage(idx)}
                    className="text-red-400 hover:text-red-300"
                    disabled={loading}
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
            {selectedImages.length > 0 && (
              <p className="text-xs text-gray-400">
                💡 Tip: Mention slide numbers in your prompt (e.g., "use this image on slide 3")
              </p>
            )}
          </div>

          {/* 5. PPT Modes Button (Below Chat Input) */}
          <div className="flex items-center justify-between">
            <button
              onClick={() => setShowPPTModes(!showPPTModes)}
              className="flex justify-center items-center gap-1 text-sm cursor-pointer bg-[#DAA520] text-black px-4 py-2 rounded hover:bg-[#B8860B] transition"
            >
              <PiFilePptBold /> PPT Modes
            </button>
            <div className="flex gap-3">
              <button
                onClick={handleAskCopilot}
                disabled={loading || !prompt.trim()}
                className="flex items-center gap-2 px-4 py-2 rounded bg-[#DAA520] text-black font-semibold hover:bg-[#B8860B] transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <PiPaperPlaneTiltBold /> {loading ? "Generating..." : "Generate PPT"}
              </button>
              <button
                onClick={handleList}
                className="px-4 py-2 bg-gray-700 text-white rounded-lg border border-gray-600 hover:bg-gray-600 transition"
              >
                View Previous PPTs
              </button>
            </div>
          </div>
        </div>

        {/* PPT Modes Modal */}
        {showPPTModes && (
          <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4" onClick={() => setShowPPTModes(false)}>
            <div className="bg-gray-800 rounded-lg border border-gray-700 w-full max-w-2xl max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
              <div className="sticky top-0 bg-gray-800 border-b border-gray-700 p-4 flex items-center justify-between">
                <h2 className="text-xl font-bold text-white">Select PPT Mode</h2>
                <button
                  onClick={() => setShowPPTModes(false)}
                  className="text-gray-400 hover:text-white transition"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              <div className="p-4 space-y-3">
                <button
                  onClick={() => insertPPTTemplate(pptModeTemplates.mode1)}
                  className="w-full text-left p-4 bg-gray-700 hover:bg-gray-600 rounded-lg transition border border-gray-600 hover:border-[#DAA520]"
                >
                  <div className="font-semibold text-white mb-1">Mode 1: Quick Auto PPT</div>
                  <div className="text-sm text-gray-300">
                    Automatically generates PPT with default structure. Just provide topic, subject, and number of slides.
                  </div>
                </button>

                <button
                  onClick={() => insertPPTTemplate(pptModeTemplates.mode2)}
                  className="w-full text-left p-4 bg-gray-700 hover:bg-gray-600 rounded-lg transition border border-gray-600 hover:border-[#DAA520]"
                >
                  <div className="font-semibold text-white mb-1">Mode 2: Custom Slide Titles</div>
                  <div className="text-sm text-gray-300">
                    Specify your own slide titles. The system will generate content for each slide based on its title.
                  </div>
                </button>

                <button
                  onClick={() => insertPPTTemplate(pptModeTemplates.mode3)}
                  className="w-full text-left p-4 bg-gray-700 hover:bg-gray-600 rounded-lg transition border border-gray-600 hover:border-[#DAA520]"
                >
                  <div className="font-semibold text-white mb-1">Mode 3: Exact Slide Content (Strict)</div>
                  <div className="text-sm text-gray-300">
                    Provide exact bullet points for each slide. The system will use your content word-for-word without modification.
                  </div>
                </button>

                <button
                  onClick={() => insertPPTTemplate(pptModeTemplates.mode4)}
                  className="w-full text-left p-4 bg-gray-700 hover:bg-gray-600 rounded-lg transition border border-gray-600 hover:border-[#DAA520]"
                >
                  <div className="font-semibold text-white mb-1">Mode 4: Image-Controlled Slides</div>
                  <div className="text-sm text-gray-300">
                    Specify slide structure and assign uploaded images to specific slides. Content will be generated automatically.
                  </div>
                </button>

                <button
                  onClick={() => insertPPTTemplate(pptModeTemplates.mode5)}
                  className="w-full text-left p-4 bg-gray-700 hover:bg-gray-600 rounded-lg transition border border-gray-600 hover:border-[#DAA520]"
                >
                  <div className="font-semibold text-white mb-1">Mode 5: Mixed Instructions (Per Slide)</div>
                  <div className="text-sm text-gray-300">
                    Mix and match: specify exact content for some slides, generate content for others, and assign images per slide.
                  </div>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Error and Result Messages */}
        {error && (
          <div className="mt-4 text-sm text-red-400 border border-red-500/40 bg-red-500/10 rounded p-2">
            {error}
          </div>
        )}
        {result && (
          <div className="mt-4 text-sm text-gray-100 border border-gray-700 rounded p-3 bg-gray-800">
            <div>{result.text}</div>
            {result.link && (
              <div className="mt-2">
                <Link
                  href={result.link}
                  target="_blank"
                  className="text-[#DAA520] underline"
                >
                  {result.filename ? `Download ${result.filename}` : "Download"}
                </Link>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Previous Presentations List */}
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
                <button 
                  onClick={() => handleDownload(p.filename)} 
                  className="px-4 py-2 bg-[#DAA520] text-black rounded hover:bg-[#B8860B] transition"
                >
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
