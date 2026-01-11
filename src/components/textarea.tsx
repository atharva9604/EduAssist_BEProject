"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { IoIosPaper } from "react-icons/io";
import { MdAssignment } from "react-icons/md";
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

const TextArea = () => {
  const router = useRouter();
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<AssistResult | null>(null);
  const [selectedImages, setSelectedImages] = useState<File[]>([]);
  const [showPPTModes, setShowPPTModes] = useState(false);

  const handleQuestionPaper = () => {
    router.push("/question-paper");
  };

  const handlePPT = () => {
    router.push("/ppt-generator");
  };

  const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    const imageFiles = files.filter(file => 
      file.type.startsWith('image/') && 
      ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'].includes(file.type)
    );
    setSelectedImages(prev => [...prev, ...imageFiles]);
    // Reset input
    e.target.value = '';
  };

  const removeImage = (index: number) => {
    setSelectedImages(prev => prev.filter((_, i) => i !== index));
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
    // Focus the textarea after a brief delay to ensure it's rendered
    setTimeout(() => {
      const textarea = document.querySelector('textarea');
      if (textarea) {
        textarea.focus();
        // Place cursor at the first placeholder
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
        // Use multipart/form-data for image uploads
        const formData = new FormData();
        formData.append('prompt', prompt);
        selectedImages.forEach((img, idx) => {
          formData.append('images', img);
        });
        
        res = await fetch(`${API_BASE}/api/assist`, {
          method: "POST",
          body: formData,
        });
      } else {
        // Use JSON for text-only requests (backward compatible)
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
      // Clear images after successful submission
      setSelectedImages([]);
    } catch (e: any) {
      setError(e?.message || "Failed to send prompt");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative w-full max-w-4xl space-y-3">
        <textarea 
        className="w-full h-60 p-5 border border-gray-600 rounded-lg bg-gray-800 text-white placeholder-gray-400 focus:border-[#DAA520] focus:outline-none"
        placeholder="Type what you want to do... (e.g., 'Make a PPT on RNNs, 12 slides, subject Deep Learning, use this image on slide 3' or 'Create a question paper on Photosynthesis, 5 mcq, 3 short, 2 long')"
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
      
      <div className="flex items-center justify-between">
        <div className="flex flex-col gap-2">
          <div className="flex gap-2">
            <button
              onClick={handlePPT}
              className="flex justify-center items-center gap-1 text-xs cursor-pointer bg-[#DAA520] text-black px-3 py-2 rounded hover:bg-[#B8860B] transition"
            >
              <PiFilePptBold /> PPT
            </button>
          <button 
            onClick={handleQuestionPaper}
              className="flex justify-center items-center gap-1 text-xs cursor-pointer bg-[#DAA520] text-black px-3 py-2 rounded hover:bg-[#B8860B] transition"
            >
            <IoIosPaper /> Question Paper
          </button>
            <button className="flex justify-center items-center gap-1 text-xs cursor-pointer bg-[#DAA520] text-black px-3 py-2 rounded hover:bg-[#B8860B] transition">
              <MdAssignment /> Assignments
            </button>
          </div>
          <button
            onClick={() => setShowPPTModes(!showPPTModes)}
            className="flex justify-center items-center gap-1 text-xs cursor-pointer bg-[#DAA520] text-black px-3 py-2 rounded hover:bg-[#B8860B] transition w-fit"
          >
            <PiFilePptBold /> PPT Modes
          </button>
        </div>
        <button
          onClick={handleAskCopilot}
          disabled={loading || !prompt.trim()}
          className="flex items-center gap-2 px-3 py-2 rounded bg-[#DAA520] text-black font-semibold hover:bg-[#B8860B] transition disabled:opacity-50"
        >
          <PiPaperPlaneTiltBold /> {loading ? "Sending..." : "Ask Copilot"}
        </button>
      </div>

      {/* PPT Modes Modal */}
      {showPPTModes && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
          <div className="bg-gray-800 rounded-lg border border-gray-700 w-full max-w-2xl max-h-[80vh] overflow-y-auto">
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

      {error && (
        <div className="text-sm text-red-400 border border-red-500/40 bg-red-500/10 rounded p-2">
          {error}
        </div>
      )}
      {result && (
        <div className="text-sm text-gray-100 border border-gray-700 rounded p-3 bg-gray-900">
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
  );
};

export default TextArea;