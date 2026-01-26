"use client";
import React, { useEffect, useState } from "react";
import { auth } from "@/lib/firebase";
import { ensureUserProfile, getTeacherProfile, updateTeacherProfile } from "@/services/firestore";
import { onAuthStateChanged, User } from "firebase/auth";
import {
  getContinuousAssessments,
  getFDPs,
  getLectures,
  getCertifications,
  getCurrentProjects,
  getResearchProposals,
  addContinuousAssessment,
  addFDP,
  addLecture,
  addCertification,
  uploadCertificate,
  addCurrentProject,
  addResearchProposal,
  deleteContinuousAssessment,
  deleteFDP,
  deleteLecture,
  deleteCertification,
  deleteCurrentProject,
  deleteResearchProposal,
  type ContinuousAssessment,
  type FDP,
  type Lecture,
  type Certification,
  type CurrentProject,
  type ResearchProposal,
} from "@/services/profileService";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';
import { Plus, Trash2, BookOpen, Award, Presentation, FileCheck, Briefcase, FileText, Download, X, Users } from "lucide-react";
import ProfileAddFormModal from "@/components/ProfileAddFormModal";
import AttendanceManager from "@/components/AttendanceManager";

function waitForAuthUser(): Promise<User> {
  return new Promise((resolve, reject) => {
    const unsub = onAuthStateChanged(auth, (u) => {
      unsub();
      if (u) resolve(u);
      else reject(new Error("Not authenticated"));
    }, reject);
  });
}

const ProfilePage = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>("");
  const [firebaseUser, setFirebaseUser] = useState<User | null>(null);
  const [profile, setProfile] = useState<any>(null);
  const [needsOnBoarding, setNeedsOnBoarding] = useState(false);
  const [departmentInput, setDepartmentInput] = useState("");
  const [activeSection, setActiveSection] = useState<"academics" | "research" | "attendance">("academics");
  const [activeTab, setActiveTab] = useState<"assessments" | "fdps" | "lectures" | "certifications">("assessments");

  // Academics data
  const [assessments, setAssessments] = useState<ContinuousAssessment[]>([]);
  const [fdps, setFdps] = useState<FDP[]>([]);
  const [lectures, setLectures] = useState<Lecture[]>([]);
  const [certifications, setCertifications] = useState<Certification[]>([]);

  // Research data
  const [projects, setProjects] = useState<CurrentProject[]>([]);
  const [proposals, setProposals] = useState<ResearchProposal[]>([]);

  // Form states
  const [showAddForm, setShowAddForm] = useState(false);
  const [formType, setFormType] = useState<string>("");
  
  // Form data states
  const [formData, setFormData] = useState<any>({});
  const [certificateFile, setCertificateFile] = useState<File | null>(null);
  
  // Certificate viewer
  const [showCertificateViewer, setShowCertificateViewer] = useState(false);
  const [selectedCertificate, setSelectedCertificate] = useState<Certification | null>(null);

  useEffect(() => {
    const init = async () => {
      try {
        setLoading(true);
        setError("");
        const user = await waitForAuthUser();
        setFirebaseUser(user); // Store Firebase user

        const result = await ensureUserProfile({
          uid: user.uid,
          displayName: user.displayName,
          email: user.email,
          photoURL: user.photoURL,
        });

        const prof = await getTeacherProfile(user.uid);
        setProfile(prof);
        const depEmpty = !prof?.departmentId || prof.departmentId.trim() === "";
        setNeedsOnBoarding(result?.needsOnBoarding || depEmpty);
        if (depEmpty) setDepartmentInput("");

        // Load all data
        await loadAllData();
      } catch (e: any) {
        setError(e?.message || "Failed to load profile");
      } finally {
        setLoading(false);
      }
    };
    init();
  }, []);

  const loadAllData = async () => {
    try {
      const [assessmentsData, fdpsData, lecturesData, certsData, projectsData, proposalsData] = await Promise.all([
        getContinuousAssessments().catch(() => ({ assessments: [] })),
        getFDPs().catch(() => ({ fdps: [] })),
        getLectures().catch(() => ({ lectures: [] })),
        getCertifications().catch(() => ({ certifications: [] })),
        getCurrentProjects().catch(() => ({ projects: [] })),
        getResearchProposals().catch(() => ({ proposals: [] })),
      ]);

      setAssessments(assessmentsData.assessments || []);
      setFdps(fdpsData.fdps || []);
      setLectures(lecturesData.lectures || []);
      setCertifications(certsData.certifications || []);
      setProjects(projectsData.projects || []);
      setProposals(proposalsData.proposals || []);
    } catch (e) {
      console.error("Error loading data:", e);
    }
  };

  const handleSaveDepartment = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setError("");
      const user = auth.currentUser;
      if (!user) {
        setError("Not authenticated.");
        return;
      }
      if (!departmentInput.trim()) {
        setError("Please enter a department.");
        return;
      }
      await updateTeacherProfile(user.uid, { departmentId: departmentInput.trim() });
      const updated = await getTeacherProfile(user.uid);
      setProfile(updated);
      setNeedsOnBoarding(false);
    } catch (e: any) {
      setError(e?.message || "Failed to save department");
    }
  };

  const handleAdd = async (data: any, file?: File | null) => {
    try {
      let dataToSend = { ...data };
      
      // Handle certificate file upload
      if (formType === "certification" && file) {
        // Upload file first
        const uploadResult = await uploadCertificate(file);
        // Store the API path for the certificate
        dataToSend.certificate_path = uploadResult.path;
      }
      
      let result;
      switch (formType) {
        case "assessment":
          result = await addContinuousAssessment(dataToSend);
          break;
        case "fdp":
          result = await addFDP(dataToSend);
          break;
        case "lecture":
          result = await addLecture(dataToSend);
          break;
        case "certification":
          result = await addCertification(dataToSend);
          break;
        case "project":
          result = await addCurrentProject(dataToSend);
          break;
        case "proposal":
          result = await addResearchProposal(dataToSend);
          break;
      }
      await loadAllData();
      setShowAddForm(false);
      setFormType("");
    } catch (e: any) {
      setError(e?.message || "Failed to add item");
    }
  };

  const handleDelete = async (id: string, type: string) => {
    if (!confirm("Are you sure you want to delete this item?")) return;
    try {
      switch (type) {
        case "assessment":
          await deleteContinuousAssessment(id);
          break;
        case "fdp":
          await deleteFDP(id);
          break;
        case "lecture":
          await deleteLecture(id);
          break;
        case "certification":
          await deleteCertification(id);
          break;
        case "project":
          await deleteCurrentProject(id);
          break;
        case "proposal":
          await deleteResearchProposal(id);
          break;
      }
      await loadAllData();
    } catch (e: any) {
      setError(e?.message || "Failed to delete item");
    }
  };

  if (loading) {
    return <div className="p-6 text-gray-200">Loading profile...</div>;
  }

  if (error && !needsOnBoarding) {
    return <div className="p-6 text-red-400">{error}</div>;
  }

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header Card */}
        <div className="bg-gradient-to-r from-gray-900 to-gray-800 rounded-xl p-6 mb-8 border border-gray-700 shadow-lg">
          <div className="flex items-center gap-6">
            <div className="relative">
              <img
                src={firebaseUser?.photoURL || profile?.photoURL || "/assets/add.png"}
                alt="avatar"
                className="w-20 h-20 rounded-full object-cover border-2 border-[#DAA520]"
              />
              <div className="absolute bottom-0 right-0 w-6 h-6 bg-green-500 rounded-full border-2 border-gray-900"></div>
            </div>
            <div className="flex-1">
              <h1 className="text-2xl font-bold text-white mb-1">
                {firebaseUser?.displayName || firebaseUser?.email?.split('@')[0] || profile?.name || "Teacher"}
              </h1>
              <p className="text-gray-400 mb-2">{firebaseUser?.email || profile?.email || "—"}</p>
              <div className="flex items-center gap-4 text-sm">
                <span className="px-3 py-1 bg-gray-800 rounded-full text-gray-300">
                  Department: {profile?.departmentId || "—"}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Onboarding: set department */}
        {needsOnBoarding && (
          <div className="bg-gradient-to-r from-yellow-900/20 to-yellow-800/20 border border-yellow-700/50 rounded-xl p-6 mb-8">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-yellow-900/30 rounded-lg">
                <FileCheck className="w-5 h-5 text-yellow-400" />
              </div>
              <h3 className="text-lg font-semibold text-white">Complete your profile</h3>
            </div>
            <form onSubmit={handleSaveDepartment} className="flex items-center gap-3">
              <input
                value={departmentInput}
                onChange={(e) => setDepartmentInput(e.target.value)}
                placeholder="Enter department (e.g., CSE, AI-DS)"
                className="flex-1 bg-gray-800 text-gray-100 px-4 py-3 rounded-lg outline-none border border-gray-700 focus:border-yellow-500 focus:ring-2 focus:ring-yellow-500/20"
              />
              <button
                type="submit"
                className="px-6 py-3 rounded-lg bg-[#DAA520] text-black font-semibold hover:bg-[#B8860B] transition"
              >
                Save
              </button>
            </form>
          </div>
        )}

        {/* Section Tabs - Improved Design */}
        <div className="flex gap-3 mb-8 bg-gray-900 rounded-xl p-2 border border-gray-700">
          <button
            onClick={() => setActiveSection("academics")}
            className={`flex items-center gap-2 px-6 py-3 rounded-lg font-semibold transition ${
              activeSection === "academics"
                ? "bg-[#DAA520] text-black shadow-lg"
                : "text-gray-400 hover:text-gray-200 hover:bg-gray-800"
            }`}
          >
            <BookOpen className="w-4 h-4" />
            Academics
          </button>
          <button
            onClick={() => setActiveSection("research")}
            className={`flex items-center gap-2 px-6 py-3 rounded-lg font-semibold transition ${
              activeSection === "research"
                ? "bg-[#DAA520] text-black shadow-lg"
                : "text-gray-400 hover:text-gray-200 hover:bg-gray-800"
            }`}
          >
            <Briefcase className="w-4 h-4" />
            Research
          </button>
          <button
            onClick={() => setActiveSection("attendance")}
            className={`flex items-center gap-2 px-6 py-3 rounded-lg font-semibold transition ${
              activeSection === "attendance"
                ? "bg-[#DAA520] text-black shadow-lg"
                : "text-gray-400 hover:text-gray-200 hover:bg-gray-800"
            }`}
          >
            <Users className="w-4 h-4" />
            Attendance
          </button>
        </div>

        {/* Academics Section */}
        {activeSection === "academics" && (
          <div className="space-y-6">
            {/* Academics Tabs - Improved */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                { id: "assessments", label: "Assessments", icon: BookOpen },
                { id: "fdps", label: "FDPs", icon: Award },
                { id: "lectures", label: "Lectures", icon: Presentation },
                { id: "certifications", label: "Certifications", icon: FileCheck },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`flex flex-col items-center gap-2 px-4 py-4 rounded-xl transition ${
                    activeTab === tab.id
                      ? "bg-[#DAA520] text-black shadow-lg scale-105"
                      : "bg-gray-900 text-gray-300 hover:bg-gray-800 border border-gray-700"
                  }`}
                >
                  <tab.icon className="w-5 h-5" />
                  <span className="text-sm font-medium">{tab.label}</span>
                </button>
              ))}
            </div>

            {/* Content - Improved Card */}
            <div className="bg-gray-900 rounded-xl p-8 border border-gray-700 shadow-lg">
              <div className="flex justify-between items-center mb-6">
                <div>
                  <h3 className="text-2xl font-bold text-white mb-1">
                    {activeTab === "assessments" && "Continuous Assessments"}
                    {activeTab === "fdps" && "Faculty Development Programs"}
                    {activeTab === "lectures" && "Lectures"}
                    {activeTab === "certifications" && "Certifications"}
                  </h3>
                  <p className="text-sm text-gray-400">Manage your academic records</p>
                </div>
                <button
                  onClick={() => {
                    const typeMap: Record<string, string> = {
                      assessments: "assessment",
                      fdps: "fdp",
                      lectures: "lecture",
                      certifications: "certification"
                    };
                    setFormType(typeMap[activeTab] || activeTab);
                    setShowAddForm(true);
                  }}
                  className="flex items-center gap-2 px-6 py-3 bg-[#DAA520] text-black rounded-lg font-semibold hover:bg-[#B8860B] transition shadow-lg hover:shadow-xl"
                >
                  <Plus className="w-5 h-5" />
                  Add New
                </button>
              </div>

              {/* Lists - Improved Cards */}
              {activeTab === "assessments" && (
                <div className="grid gap-4">
                  {assessments.length === 0 ? (
                    <div className="text-center py-12">
                      <BookOpen className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                      <p className="text-gray-400">No assessments added yet.</p>
                    </div>
                  ) : (
                    assessments.map((item) => (
                      <div key={item.id} className="bg-gray-800 p-5 rounded-xl border border-gray-700 hover:border-gray-600 transition flex justify-between items-start group">
                          <div>
                            <div className="font-semibold text-white">{item.subject_name}</div>
                            <div className="text-sm text-gray-400">{item.assessment_type}</div>
                            <div className="text-sm text-gray-300">
                              Marks: {item.marks}/{item.total_marks}
                            </div>
                            {item.assessment_date && (
                              <div className="text-xs text-gray-500">
                                {new Date(item.assessment_date).toLocaleDateString()}
                              </div>
                            )}
                          </div>
                        <button
                          onClick={() => handleDelete(item.id, "assessment")}
                          className="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-300 p-2 hover:bg-red-900/20 rounded-lg transition"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    ))
                  )}
                </div>
              )}

              {activeTab === "fdps" && (
                <div className="grid gap-4">
                  {fdps.length === 0 ? (
                    <div className="text-center py-12">
                      <Award className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                      <p className="text-gray-400">No FDPs added yet.</p>
                    </div>
                  ) : (
                    fdps.map((item) => (
                      <div key={item.id} className="bg-gray-800 p-5 rounded-xl border border-gray-700 hover:border-gray-600 transition flex justify-between items-start group">
                          <div>
                            <div className="font-semibold text-white">{item.title}</div>
                            <div className="text-sm text-gray-400">{item.organization}</div>
                            {item.start_date && (
                              <div className="text-xs text-gray-500">
                                {new Date(item.start_date).toLocaleDateString()}
                                {item.end_date && ` - ${new Date(item.end_date).toLocaleDateString()}`}
                              </div>
                            )}
                          </div>
                        <button
                          onClick={() => handleDelete(item.id, "fdp")}
                          className="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-300 p-2 hover:bg-red-900/20 rounded-lg transition"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    ))
                  )}
                </div>
              )}

              {activeTab === "lectures" && (
                <div className="grid gap-4">
                  {lectures.length === 0 ? (
                    <div className="text-center py-12">
                      <Presentation className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                      <p className="text-gray-400">No lectures added yet.</p>
                    </div>
                  ) : (
                    lectures.map((item) => (
                      <div key={item.id} className="bg-gray-800 p-5 rounded-xl border border-gray-700 hover:border-gray-600 transition flex justify-between items-start group">
                          <div>
                            <div className="font-semibold text-white">{item.title}</div>
                            {item.venue && <div className="text-sm text-gray-400">{item.venue}</div>}
                            {item.date && (
                              <div className="text-xs text-gray-500">
                                {new Date(item.date).toLocaleDateString()}
                              </div>
                            )}
                            {item.description && (
                              <div className="text-sm text-gray-300 mt-1">{item.description}</div>
                            )}
                          </div>
                        <button
                          onClick={() => handleDelete(item.id, "lecture")}
                          className="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-300 p-2 hover:bg-red-900/20 rounded-lg transition"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    ))
                  )}
                </div>
              )}

              {activeTab === "certifications" && (
                <div className="grid gap-4">
                  {certifications.length === 0 ? (
                    <div className="text-center py-12">
                      <FileCheck className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                      <p className="text-gray-400">No certifications added yet.</p>
                    </div>
                  ) : (
                    certifications.map((item) => (
                      <div key={item.id} className="bg-gray-800 p-5 rounded-xl border border-gray-700 hover:border-gray-600 transition flex justify-between items-start group">
                          <div className="flex-1">
                            <button
                              onClick={() => {
                                if (item.certificate_path) {
                                  setSelectedCertificate(item);
                                  setShowCertificateViewer(true);
                                }
                              }}
                              className={`font-semibold ${
                                item.certificate_path
                                  ? "text-[#DAA520] hover:text-[#B8860B] cursor-pointer underline"
                                  : "text-white"
                              }`}
                            >
                              {item.name}
                            </button>
                            <div className="text-sm text-gray-400">{item.issuing_organization}</div>
                            {item.issue_date && (
                              <div className="text-xs text-gray-500">
                                Issued: {new Date(item.issue_date).toLocaleDateString()}
                                {item.expiry_date && ` | Expires: ${new Date(item.expiry_date).toLocaleDateString()}`}
                              </div>
                            )}
                            {item.certificate_path && (
                              <div className="mt-2 flex items-center gap-2">
                                <FileCheck className="w-4 h-4 text-[#DAA520]" />
                                <span className="text-xs text-gray-400">Certificate available - Click name to view</span>
                              </div>
                            )}
                          </div>
                        <button
                          onClick={() => handleDelete(item.id, "certification")}
                          className="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-300 p-2 hover:bg-red-900/20 rounded-lg transition"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Research Section */}
        {activeSection === "research" && (
          <div className="space-y-6">
            <div className="bg-gray-900 rounded-xl p-8 border border-gray-700 shadow-lg">
              <div className="flex justify-between items-center mb-6">
                <div>
                  <h3 className="text-2xl font-bold text-white mb-1">Current Projects</h3>
                  <p className="text-sm text-gray-400">Track your ongoing research projects</p>
                </div>
                <button
                  onClick={() => {
                    setFormType("project");
                    setShowAddForm(true);
                  }}
                  className="flex items-center gap-2 px-6 py-3 bg-[#DAA520] text-black rounded-lg font-semibold hover:bg-[#B8860B] transition shadow-lg hover:shadow-xl"
                >
                  <Plus className="w-5 h-5" />
                  Add Project
                </button>
              </div>
              <div className="grid gap-4">
                {projects.length === 0 ? (
                  <div className="text-center py-12">
                    <Briefcase className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                    <p className="text-gray-400">No projects added yet.</p>
                  </div>
                ) : (
                  projects.map((item) => (
                    <div key={item.id} className="bg-gray-800 p-5 rounded-xl border border-gray-700 hover:border-gray-600 transition flex justify-between items-start group">
                        <div>
                          <div className="font-semibold text-white">{item.title}</div>
                          {item.description && <div className="text-sm text-gray-300 mt-1">{item.description}</div>}
                          <div className="flex gap-4 mt-2">
                            {item.start_date && (
                              <div className="text-xs text-gray-500">
                                Started: {new Date(item.start_date).toLocaleDateString()}
                              </div>
                            )}
                            <div className="text-xs text-gray-500">Status: {item.status}</div>
                          </div>
                        </div>
                      <button
                        onClick={() => handleDelete(item.id, "project")}
                        className="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-300 p-2 hover:bg-red-900/20 rounded-lg transition"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>

            <div className="bg-gray-900 rounded-xl p-8 border border-gray-700 shadow-lg">
              <div className="flex justify-between items-center mb-6">
                <div>
                  <h3 className="text-2xl font-bold text-white mb-1">Research Proposals</h3>
                  <p className="text-sm text-gray-400">Manage your research proposals</p>
                </div>
                <button
                  onClick={() => {
                    setFormType("proposal");
                    setShowAddForm(true);
                  }}
                  className="flex items-center gap-2 px-6 py-3 bg-[#DAA520] text-black rounded-lg font-semibold hover:bg-[#B8860B] transition shadow-lg hover:shadow-xl"
                >
                  <Plus className="w-5 h-5" />
                  Add Proposal
                </button>
              </div>
              <div className="grid gap-4">
                {proposals.length === 0 ? (
                  <div className="text-center py-12">
                    <FileText className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                    <p className="text-gray-400">No proposals added yet.</p>
                  </div>
                ) : (
                  proposals.map((item) => (
                    <div key={item.id} className="bg-gray-800 p-5 rounded-xl border border-gray-700 hover:border-gray-600 transition flex justify-between items-start group">
                        <div>
                          <div className="font-semibold text-white">{item.title}</div>
                          {item.description && <div className="text-sm text-gray-300 mt-1">{item.description}</div>}
                          <div className="flex gap-4 mt-2">
                            {item.submission_date && (
                              <div className="text-xs text-gray-500">
                                Submitted: {new Date(item.submission_date).toLocaleDateString()}
                              </div>
                            )}
                            <div className="text-xs text-gray-500">Status: {item.status}</div>
                          </div>
                        </div>
                      <button
                        onClick={() => handleDelete(item.id, "proposal")}
                        className="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-300 p-2 hover:bg-red-900/20 rounded-lg transition"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}

        {/* Attendance Section */}
        {activeSection === "attendance" && (
          <div className="space-y-6">
            <AttendanceManager />
          </div>
        )}

        {/* Add Form Modal */}
        <ProfileAddFormModal
          show={showAddForm}
          formType={formType}
          onClose={() => {
            setShowAddForm(false);
            setFormType("");
          }}
          onSubmit={handleAdd}
        />

        {/* Certificate Viewer Modal */}
        {showCertificateViewer && selectedCertificate && (
          <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4">
            <div className="bg-gray-900 rounded-xl p-6 w-full max-w-4xl max-h-[90vh] border border-gray-700 shadow-2xl">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-bold text-white">{selectedCertificate.name}</h3>
              <button
                onClick={() => {
                  setShowCertificateViewer(false);
                  setSelectedCertificate(null);
                }}
                className="text-gray-400 hover:text-white"
              >
                <X className="w-6 h-6" />
              </button>
            </div>
            
            <div className="bg-gray-800 rounded-lg p-4 mb-4">
              <div className="text-sm text-gray-300 mb-2">
                <span className="font-semibold">Issuing Organization:</span> {selectedCertificate.issuing_organization}
              </div>
              {selectedCertificate.issue_date && (
                <div className="text-sm text-gray-300 mb-2">
                  <span className="font-semibold">Issued:</span> {new Date(selectedCertificate.issue_date).toLocaleDateString()}
                </div>
              )}
              {selectedCertificate.expiry_date && (
                <div className="text-sm text-gray-300">
                  <span className="font-semibold">Expires:</span> {new Date(selectedCertificate.expiry_date).toLocaleDateString()}
                </div>
              )}
            </div>

            <div className="bg-gray-800 rounded-lg p-4 overflow-auto max-h-[60vh]">
              {selectedCertificate.certificate_path ? (
                <div className="flex flex-col items-center">
                  {(() => {
                    // Prepend API_BASE if path is relative
                    const certUrl = selectedCertificate.certificate_path.startsWith('http') 
                      ? selectedCertificate.certificate_path 
                      : `${API_BASE}${selectedCertificate.certificate_path}`;
                    
                    return selectedCertificate.certificate_path.toLowerCase().endsWith('.pdf') ? (
                      <iframe
                        src={certUrl}
                        className="w-full h-[60vh] border border-gray-700 rounded"
                        title="Certificate PDF"
                      />
                    ) : (
                      <img
                        src={certUrl}
                        alt={selectedCertificate.name}
                        className="max-w-full max-h-[60vh] rounded border border-gray-700"
                        onError={(e) => {
                          (e.target as HTMLImageElement).src = "/assets/add.png";
                          (e.target as HTMLImageElement).alt = "Certificate not found";
                        }}
                      />
                    );
                  })()}
                  <div className="mt-4 flex gap-3">
                    <button
                      onClick={async () => {
                        try {
                          const certUrl = selectedCertificate.certificate_path!.startsWith('http') 
                            ? selectedCertificate.certificate_path! 
                            : `${API_BASE}${selectedCertificate.certificate_path}`;
                          
                          // Fetch the file as blob
                          const response = await fetch(certUrl);
                          if (!response.ok) {
                            throw new Error('Failed to download certificate');
                          }
                          
                          const blob = await response.blob();
                          
                          // Extract filename from path or use certificate name
                          const urlParts = certUrl.split('/');
                          const filenameFromUrl = urlParts[urlParts.length - 1];
                          
                          // Get original filename (remove timestamp prefix if present)
                          // Format: {user_id}_{timestamp}_{original_filename}
                          let downloadFilename = filenameFromUrl;
                          
                          // Try to extract original filename from timestamped format
                          const timestampPattern = /^[^_]+_\d{8}_\d{6}_(.+)$/;
                          const match = filenameFromUrl.match(timestampPattern);
                          if (match && match[1]) {
                            downloadFilename = match[1];
                          } else {
                            // If no timestamp pattern, try splitting by underscore
                            const parts = filenameFromUrl.split('_');
                            if (parts.length >= 3) {
                              // Check if second part looks like a timestamp (YYYYMMDD_HHMMSS)
                              const secondPart = parts[1];
                              if (secondPart && secondPart.length >= 8 && /^\d+$/.test(secondPart.replace('_', ''))) {
                                // Rejoin everything after the timestamp
                                downloadFilename = parts.slice(2).join('_');
                              }
                            }
                          }
                          
                          // If still no good filename or missing extension, use certificate name with extension
                          if (!downloadFilename || downloadFilename === filenameFromUrl || !downloadFilename.includes('.')) {
                            const ext = filenameFromUrl.split('.').pop() || 'pdf';
                            downloadFilename = `${selectedCertificate.name.replace(/[^a-z0-9]/gi, '_')}.${ext}`;
                          }
                          
                          // Determine blob type based on file extension for proper download
                          const ext = downloadFilename.split('.').pop()?.toLowerCase() || '';
                          const blobType = ext === 'pdf' 
                            ? 'application/pdf' 
                            : ext === 'jpg' || ext === 'jpeg'
                            ? 'image/jpeg'
                            : ext === 'png'
                            ? 'image/png'
                            : blob.type;
                          
                          // Create a new blob with the correct type to ensure proper download
                          const typedBlob = new Blob([blob], { type: blobType });
                          
                          // Create download link and trigger
                          const url = window.URL.createObjectURL(typedBlob);
                          const a = document.createElement('a');
                          a.href = url;
                          a.download = downloadFilename;
                          a.style.display = 'none';
                          document.body.appendChild(a);
                          a.click();
                          
                          // Clean up after a short delay to ensure download starts
                          setTimeout(() => {
                            window.URL.revokeObjectURL(url);
                            document.body.removeChild(a);
                          }, 100);
                        } catch (error: any) {
                          alert(`Failed to download certificate: ${error.message}`);
                        }
                      }}
                      className="flex items-center gap-2 px-4 py-2 bg-[#DAA520] text-black rounded-lg hover:bg-[#B8860B]"
                    >
                      <Download className="w-4 h-4" />
                      Download Certificate
                    </button>
                  </div>
                </div>
              ) : (
                <div className="text-center text-gray-400 py-8">
                  Certificate file not available
                </div>
              )}
            </div>
          </div>
        </div>
        )}
      </div>
    </div>
  );
};

export default ProfilePage;
