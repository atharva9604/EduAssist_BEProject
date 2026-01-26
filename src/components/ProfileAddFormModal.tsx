"use client";
import React, { useState } from "react";
import { X, Upload } from "lucide-react";

interface ProfileAddFormModalProps {
  show: boolean;
  formType: string;
  onClose: () => void;
  onSubmit: (data: any, file?: File | null) => void;
}

export default function ProfileAddFormModal({
  show,
  formType,
  onClose,
  onSubmit,
}: ProfileAddFormModalProps) {
  const [formData, setFormData] = useState<any>({});
  const [certificateFile, setCertificateFile] = useState<File | null>(null);

  if (!show) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData, certificateFile);
    setFormData({});
    setCertificateFile(null);
  };

  const handleClose = () => {
    setFormData({});
    setCertificateFile(null);
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-gray-900 rounded-lg p-6 w-full max-w-md border border-gray-700 max-h-[90vh] overflow-y-auto">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-xl font-bold text-white">
            Add {formType === "assessment" && "Continuous Assessment"}
            {formType === "fdp" && "FDP"}
            {formType === "lecture" && "Lecture"}
            {formType === "certification" && "Certification"}
            {formType === "project" && "Project"}
            {formType === "proposal" && "Research Proposal"}
          </h3>
          <button onClick={handleClose} className="text-gray-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Continuous Assessment Form */}
          {formType === "assessment" && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Subject Name</label>
                <input
                  type="text"
                  required
                  value={formData.subject_name || ""}
                  onChange={(e) => setFormData({ ...formData, subject_name: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-800 text-white rounded-lg border border-gray-700"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Assessment Type</label>
                <input
                  type="text"
                  required
                  value={formData.assessment_type || ""}
                  onChange={(e) => setFormData({ ...formData, assessment_type: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-800 text-white rounded-lg border border-gray-700"
                  placeholder="e.g., Quiz, Assignment, Mid-term"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Marks</label>
                  <input
                    type="number"
                    required
                    value={formData.marks || ""}
                    onChange={(e) => setFormData({ ...formData, marks: parseInt(e.target.value) })}
                    className="w-full px-3 py-2 bg-gray-800 text-white rounded-lg border border-gray-700"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Total Marks</label>
                  <input
                    type="number"
                    required
                    value={formData.total_marks || ""}
                    onChange={(e) => setFormData({ ...formData, total_marks: parseInt(e.target.value) })}
                    className="w-full px-3 py-2 bg-gray-800 text-white rounded-lg border border-gray-700"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Assessment Date</label>
                <input
                  type="date"
                  value={formData.assessment_date || ""}
                  onChange={(e) => setFormData({ ...formData, assessment_date: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-800 text-white rounded-lg border border-gray-700"
                />
              </div>
            </>
          )}

          {/* FDP Form */}
          {formType === "fdp" && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Title</label>
                <input
                  type="text"
                  required
                  value={formData.title || ""}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-800 text-white rounded-lg border border-gray-700"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Organization</label>
                <input
                  type="text"
                  required
                  value={formData.organization || ""}
                  onChange={(e) => setFormData({ ...formData, organization: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-800 text-white rounded-lg border border-gray-700"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Start Date</label>
                  <input
                    type="date"
                    value={formData.start_date || ""}
                    onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-800 text-white rounded-lg border border-gray-700"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">End Date</label>
                  <input
                    type="date"
                    value={formData.end_date || ""}
                    onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-800 text-white rounded-lg border border-gray-700"
                  />
                </div>
              </div>
            </>
          )}

          {/* Lecture Form */}
          {formType === "lecture" && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Title</label>
                <input
                  type="text"
                  required
                  value={formData.title || ""}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-800 text-white rounded-lg border border-gray-700"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Venue</label>
                <input
                  type="text"
                  value={formData.venue || ""}
                  onChange={(e) => setFormData({ ...formData, venue: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-800 text-white rounded-lg border border-gray-700"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Date</label>
                <input
                  type="date"
                  value={formData.date || ""}
                  onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-800 text-white rounded-lg border border-gray-700"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Description</label>
                <textarea
                  value={formData.description || ""}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-800 text-white rounded-lg border border-gray-700"
                  rows={3}
                />
              </div>
            </>
          )}

          {/* Certification Form */}
          {formType === "certification" && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Certification Name</label>
                <input
                  type="text"
                  required
                  value={formData.name || ""}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-800 text-white rounded-lg border border-gray-700"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Issuing Organization</label>
                <input
                  type="text"
                  required
                  value={formData.issuing_organization || ""}
                  onChange={(e) => setFormData({ ...formData, issuing_organization: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-800 text-white rounded-lg border border-gray-700"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Issue Date</label>
                  <input
                    type="date"
                    value={formData.issue_date || ""}
                    onChange={(e) => setFormData({ ...formData, issue_date: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-800 text-white rounded-lg border border-gray-700"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Expiry Date</label>
                  <input
                    type="date"
                    value={formData.expiry_date || ""}
                    onChange={(e) => setFormData({ ...formData, expiry_date: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-800 text-white rounded-lg border border-gray-700"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Certificate File</label>
                <div className="flex items-center gap-2">
                  <input
                    type="file"
                    accept=".pdf,.jpg,.jpeg,.png"
                    onChange={(e) => setCertificateFile(e.target.files?.[0] || null)}
                    className="hidden"
                    id="certificate-upload"
                  />
                  <label
                    htmlFor="certificate-upload"
                    className="flex items-center gap-2 px-4 py-2 bg-gray-800 text-white rounded-lg border border-gray-700 cursor-pointer hover:bg-gray-700"
                  >
                    <Upload className="w-4 h-4" />
                    {certificateFile ? certificateFile.name : "Upload Certificate"}
                  </label>
                  {certificateFile && (
                    <button
                      type="button"
                      onClick={() => setCertificateFile(null)}
                      className="text-red-400 hover:text-red-300"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            </>
          )}

          {/* Project Form */}
          {formType === "project" && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Project Title</label>
                <input
                  type="text"
                  required
                  value={formData.title || ""}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-800 text-white rounded-lg border border-gray-700"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Description</label>
                <textarea
                  value={formData.description || ""}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-800 text-white rounded-lg border border-gray-700"
                  rows={3}
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Start Date</label>
                  <input
                    type="date"
                    value={formData.start_date || ""}
                    onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-800 text-white rounded-lg border border-gray-700"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Status</label>
                  <select
                    value={formData.status || "ongoing"}
                    onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-800 text-white rounded-lg border border-gray-700"
                  >
                    <option value="ongoing">Ongoing</option>
                    <option value="completed">Completed</option>
                    <option value="on-hold">On Hold</option>
                  </select>
                </div>
              </div>
            </>
          )}

          {/* Proposal Form */}
          {formType === "proposal" && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Proposal Title</label>
                <input
                  type="text"
                  required
                  value={formData.title || ""}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-800 text-white rounded-lg border border-gray-700"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Description</label>
                <textarea
                  value={formData.description || ""}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-800 text-white rounded-lg border border-gray-700"
                  rows={3}
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Submission Date</label>
                  <input
                    type="date"
                    value={formData.submission_date || ""}
                    onChange={(e) => setFormData({ ...formData, submission_date: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-800 text-white rounded-lg border border-gray-700"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Status</label>
                  <select
                    value={formData.status || "draft"}
                    onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-800 text-white rounded-lg border border-gray-700"
                  >
                    <option value="draft">Draft</option>
                    <option value="submitted">Submitted</option>
                    <option value="approved">Approved</option>
                    <option value="rejected">Rejected</option>
                  </select>
                </div>
              </div>
            </>
          )}

          <div className="flex gap-3 pt-4">
            <button
              type="submit"
              className="flex-1 px-4 py-2 bg-[#DAA520] text-black rounded-lg font-semibold hover:bg-[#B8860B]"
            >
              Add
            </button>
            <button
              type="button"
              onClick={handleClose}
              className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
