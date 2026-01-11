"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { onAuthStateChanged, User } from "firebase/auth";
import { auth } from "@/lib/firebase";
import LoginModal from "./dialog/login";
// Ensure path is correct

const GetStartedButton = () => {
  const [user, setUser] = useState<User | null>(null);
  const [showLoginModal, setShowLoginModal] = useState(false);
  const router = useRouter();

  // Track auth state but do NOT redirect automatically
  useEffect(() => {
    if (!auth) {
      // Firebase not configured; skip auth tracking
      return;
    }
    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      setUser(currentUser);
    });
    return () => unsubscribe();
  }, []);

  const handleGetStarted = () => {
    // Skip login for now; go directly to dashboard
    router.push("/dashboard");
  };

  const handleLoginSuccess = () => {
    setShowLoginModal(false);
    // router.push("/dashboard"); // Redirect after successful login
  };

  return (
    <>
      <button
        onClick={handleGetStarted}
        className="px-6 py-3 rounded-lg font-semibold shadow-lg hover:opacity-90 transition"
        style={{ backgroundColor: "#DAA520", color: "#111" }}
      >
        Get Started
      </button>

      {/* Login modal disabled for now */}
    </>
  );
};

export default GetStartedButton;
