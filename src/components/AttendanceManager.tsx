"use client";
import React, { useState } from "react";
import { sendAttendanceCommand, uploadRoster, downloadAttendanceCsv, type AttendanceResponse, type AttendanceSummary } from "@/services/attendanceService";
import { Send, Upload, FileSpreadsheet, Users, Calendar, BookOpen, Download, Loader2, MessageSquare } from "lucide-react";

export default function AttendanceManager() {
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<AttendanceResponse | null>(null);
  const [summary, setSummary] = useState<AttendanceSummary[] | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [classId, setClassId] = useState("1");

  const handleSendCommand = async () => {
    if (!message.trim()) return;
    
    setLoading(true);
    setResponse(null);
    setSummary(null);
    
    try {
      const result = await sendAttendanceCommand(message);
      setResponse(result);
      
      // If it's a summary response, extract the summary data
      if (result.summary) {
        setSummary(result.summary);
      } else if (result.tool === "summary" && result.summary) {
        setSummary(result.summary);
      }
      
      // Clear message on success
      if (!result.error && !result.ask) {
        setMessage("");
      }
    } catch (error: any) {
      setResponse({ error: error.message || "Failed to process command" });
    } finally {
      setLoading(false);
    }
  };

  const handleUploadRoster = async () => {
    if (!uploadFile) {
      alert("Please select a file");
      return;
    }
    
    setUploading(true);
    try {
      const result = await uploadRoster(uploadFile, parseInt(classId));
      alert(`Roster uploaded successfully! ${result.rows_inserted} students added.`);
      setUploadFile(null);
    } catch (error: any) {
      alert(`Upload failed: ${error.message}`);
    } finally {
      setUploading(false);
    }
  };

  const quickCommands = [
    { label: "Mark Attendance", command: "Mark attendance for teacher 1, class 1, subject 1, today, rolls 1-30 are present" },
    { label: "Create Session", command: "Create session for teacher 1, class 1, subject 1, today" },
    { label: "View Summary", command: "Show summary for subject 1" },
    { label: "Export CSV", command: "Export CSV for subject 1" },
  ];

  const handleQuickCommand = (command: string) => {
    setMessage(command);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-3 bg-[#DAA520]/20 rounded-lg">
          <Users className="w-6 h-6 text-[#DAA520]" />
        </div>
        <div>
          <h2 className="text-2xl font-bold text-white">Attendance Management</h2>
          <p className="text-sm text-gray-400">AI-powered natural language attendance system</p>
        </div>
      </div>

      {/* Quick Commands */}
      <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
        <h3 className="text-sm font-semibold text-gray-300 mb-3">Quick Commands</h3>
        <div className="grid grid-cols-2 gap-2">
          {quickCommands.map((cmd, idx) => (
            <button
              key={idx}
              onClick={() => handleQuickCommand(cmd.command)}
              className="text-left px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm text-gray-300 transition"
            >
              {cmd.label}
            </button>
          ))}
        </div>
      </div>

      {/* Natural Language Input */}
      <div className="bg-gray-900 rounded-lg p-6 border border-gray-700">
        <div className="flex items-center gap-2 mb-4">
          <MessageSquare className="w-5 h-5 text-[#DAA520]" />
          <h3 className="text-lg font-semibold text-white">Natural Language Command</h3>
        </div>
        <div className="space-y-3">
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Example: Mark attendance for teacher 1, class 1, subject 1, today, rolls 1-30 except 5,10 are present"
            className="w-full px-4 py-3 bg-gray-800 text-white rounded-lg border border-gray-700 focus:border-[#DAA520] focus:outline-none resize-none"
            rows={3}
            onKeyDown={(e) => {
              if (e.key === "Enter" && e.ctrlKey) {
                handleSendCommand();
              }
            }}
          />
          <button
            onClick={handleSendCommand}
            disabled={loading || !message.trim()}
            className="flex items-center gap-2 px-6 py-3 bg-[#DAA520] text-black rounded-lg font-semibold hover:bg-[#B8860B] disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Processing...
              </>
            ) : (
              <>
                <Send className="w-4 h-4" />
                Send Command
              </>
            )}
          </button>
          <p className="text-xs text-gray-500">Press Ctrl+Enter to send</p>
        </div>
      </div>

      {/* Response Display */}
      {response && (
        <div className="bg-gray-900 rounded-lg p-6 border border-gray-700">
          <h3 className="text-lg font-semibold text-white mb-4">Response</h3>
          {response.error ? (
            <div className="p-4 bg-red-900/20 border border-red-700 rounded-lg text-red-300">
              <p className="font-semibold">Error:</p>
              <p>{response.error}</p>
            </div>
          ) : response.ask ? (
            <div className="p-4 bg-yellow-900/20 border border-yellow-700 rounded-lg text-yellow-300">
              <p className="font-semibold">Need More Information:</p>
              <p className="mt-2">{JSON.stringify(response.ask, null, 2)}</p>
            </div>
          ) : (
            <div className="space-y-3">
              {response.tool && (
                <div className="text-sm text-gray-400">
                  Tool: <span className="text-[#DAA520] font-semibold">{response.tool}</span>
                </div>
              )}
              {response.message && (
                <p className="text-gray-300">{response.message}</p>
              )}
              {response.session_id && (
                <div className="p-3 bg-gray-800 rounded-lg">
                  <p className="text-sm text-gray-400">Session ID: <span className="text-white">{response.session_id}</span></p>
                  {response.present !== undefined && response.total !== undefined && (
                    <p className="text-sm text-gray-400 mt-1">
                      Attendance: <span className="text-white">{response.present}/{response.total}</span>
                    </p>
                  )}
                </div>
              )}
              {/* Export CSV Button - Show when export_csv tool is used */}
              {response.tool === "export_csv" && (
                <div className="p-4 bg-green-900/20 border border-green-700 rounded-lg">
                  <p className="text-green-300 mb-3">
                    ✅ CSV file generated successfully!
                    {response.file_path && (
                      <span className="block text-sm text-gray-400 mt-1">File: {response.file_path}</span>
                    )}
                  </p>
                  <button
                    onClick={(e) => {
                      e.preventDefault();
                      try {
                        // Extract subject_id from response or use default
                        // Try to extract from file_path or use subject 1 as default
                        const subjectIdMatch = response.file_path?.match(/subject_(\d+)/);
                        const subjectId = subjectIdMatch ? parseInt(subjectIdMatch[1]) : 1;
                        
                        // Direct download - trigger immediately from user click
                        const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';
                        const downloadUrl = `${API_BASE}/api/attendance/export-csv/${subjectId}`;
                        
                        const a = document.createElement("a");
                        a.href = downloadUrl;
                        a.download = `attendance_summary_subject_${subjectId}.csv`;
                        a.style.display = "none";
                        document.body.appendChild(a);
                        a.click();
                        setTimeout(() => {
                          document.body.removeChild(a);
                        }, 100);
                      } catch (e: any) {
                        setResponse({ ...response, error: e?.message || "Failed to download CSV" });
                      }
                    }}
                    className="flex items-center gap-2 px-4 py-2 bg-[#DAA520] text-black rounded-lg font-semibold hover:bg-[#B8860B] transition"
                  >
                    <Download className="w-4 h-4" />
                    Download CSV File
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Summary Table */}
      {summary && summary.length > 0 && (
        <div className="bg-gray-900 rounded-lg p-6 border border-gray-700">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold text-white">Attendance Summary</h3>
            <button
              onClick={(e) => {
                e.preventDefault();
                // Direct download - must be synchronous with user click
                const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';
                const downloadUrl = `${API_BASE}/api/attendance/export-csv/1`;
                
                const a = document.createElement("a");
                a.href = downloadUrl;
                a.download = `attendance_summary_subject_1.csv`;
                a.style.display = "none";
                document.body.appendChild(a);
                a.click();
                setTimeout(() => {
                  document.body.removeChild(a);
                }, 100);
                
                // Optionally generate CSV in background (non-blocking)
                sendAttendanceCommand(`Export CSV for subject 1`).then((result) => {
                  setResponse(result);
                }).catch(() => {
                  // Ignore errors - file might already exist
                });
              }}
              className="flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm text-gray-300"
            >
              <Download className="w-4 h-4" />
              Export CSV
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left py-3 px-4 text-sm font-semibold text-gray-300">Roll No</th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-gray-300">Name</th>
                  <th className="text-center py-3 px-4 text-sm font-semibold text-gray-300">Present</th>
                  <th className="text-center py-3 px-4 text-sm font-semibold text-gray-300">Total</th>
                  <th className="text-center py-3 px-4 text-sm font-semibold text-gray-300">Percentage</th>
                </tr>
              </thead>
              <tbody>
                {summary.map((item, idx) => (
                  <tr key={idx} className="border-b border-gray-800 hover:bg-gray-800/50">
                    <td className="py-3 px-4 text-white">{item.roll_no}</td>
                    <td className="py-3 px-4 text-gray-300">{item.name}</td>
                    <td className="py-3 px-4 text-center text-gray-300">{item.present}</td>
                    <td className="py-3 px-4 text-center text-gray-300">{item.total}</td>
                    <td className="py-3 px-4 text-center">
                      <span className={`font-semibold ${
                        item.percentage >= 75 ? "text-green-400" :
                        item.percentage >= 50 ? "text-yellow-400" :
                        "text-red-400"
                      }`}>
                        {item.percentage.toFixed(1)}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Upload Roster */}
      <div className="bg-gray-900 rounded-lg p-6 border border-gray-700">
        <div className="flex items-center gap-2 mb-4">
          <FileSpreadsheet className="w-5 h-5 text-[#DAA520]" />
          <h3 className="text-lg font-semibold text-white">Upload Student Roster</h3>
        </div>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Class ID</label>
            <input
              type="number"
              value={classId}
              onChange={(e) => setClassId(e.target.value)}
              className="w-full px-4 py-2 bg-gray-800 text-white rounded-lg border border-gray-700 focus:border-[#DAA520] focus:outline-none"
              placeholder="1"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Excel File (RollNo, Name columns)</label>
            <div className="flex items-center gap-3">
              <input
                type="file"
                accept=".xlsx,.xls"
                onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                className="hidden"
                id="roster-upload"
              />
              <label
                htmlFor="roster-upload"
                className="flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-gray-300 cursor-pointer transition"
              >
                <Upload className="w-4 h-4" />
                {uploadFile ? uploadFile.name : "Choose File"}
              </label>
              {uploadFile && (
                <button
                  onClick={handleUploadRoster}
                  disabled={uploading}
                  className="flex items-center gap-2 px-6 py-2 bg-[#DAA520] text-black rounded-lg font-semibold hover:bg-[#B8860B] disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {uploading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Uploading...
                    </>
                  ) : (
                    "Upload"
                  )}
                </button>
              )}
            </div>
            <p className="text-xs text-gray-500 mt-2">
              Excel file must have columns: RollNo, Name
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
