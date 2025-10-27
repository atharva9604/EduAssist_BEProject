"use client";
import React, { useEffect, useState } from "react";
import { auth } from "@/lib/firebase";
import { ensureUserProfile, getTeacherProfile, updateTeacherProfile } from "@/services/firestore";

import { onAuthStateChanged, User } from "firebase/auth";


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
  const [profile, setProfile] = useState<any>(null);
  const [needsOnBoarding, setNeedsOnBoarding] = useState(false);
  const [departmentInput, setDepartmentInput] = useState("");

  useEffect(() => {
    const init = async () => {
      try {
        setLoading(true);
        setError("");
        const user = await waitForAuthUser();

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
      } catch (e: any) {
        setError(e?.message || "Failed to load profile");
      } finally {
        setLoading(false);
      }
    };
    init();
  }, []);

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

  if (loading) {
    return <div className="p-6 text-gray-200">Loading profile...</div>;
  }

  if (error) {
    return <div className="p-6 text-red-400">{error}</div>;
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <img
          src={profile?.photoURL || "/assets/add.png"}
          alt="avatar"
          className="w-16 h-16 rounded-full object-cover"
        />
        <div>
          <div className="text-xl font-semibold text-white">{profile?.name || "Teacher"}</div>
          <div className="text-sm text-gray-400">{profile?.email}</div>
          <div className="text-sm text-gray-400">
            Department: {profile?.departmentId || "—"}
          </div>
        </div>
      </div>

      {/* Onboarding: set department */}
      {needsOnBoarding && (
        <div className="bg-gray-900 border border-gray-700 rounded-lg p-4">
          <div className="text-white font-medium mb-2">Complete your profile</div>
          <form onSubmit={handleSaveDepartment} className="flex items-center gap-2">
            <input
              value={departmentInput}
              onChange={(e) => setDepartmentInput(e.target.value)}
              placeholder="Enter department (e.g., CSE)"
              className="bg-gray-800 text-gray-100 px-3 py-2 rounded-md outline-none border border-gray-700 w-64"
            />
            <button
              type="submit"
              className="px-3 py-2 rounded-md bg-[#DAA520] text-black font-medium"
            >
              Save
            </button>
          </form>
        </div>
      )}

      {/* Placeholder for next steps */}
      {!needsOnBoarding && (
        <div className="text-gray-300 text-sm">
          Profile ready. Next: show subjects, enrolled students, and attendance.
        </div>
      )}
    </div>
  );
};

export default ProfilePage;