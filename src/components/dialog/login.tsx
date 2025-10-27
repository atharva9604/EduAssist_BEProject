"use client";

import { signInWithPopup, GoogleAuthProvider } from "firebase/auth";
import { auth } from "@/lib/firebase";

interface LoginModalProps {
  onClose: () => void;
  onLoginSuccess: () => void;
}

export default function LoginModal({ onClose, onLoginSuccess }: LoginModalProps) {
  const handleGoogleLogin = async () => {
    const provider = new GoogleAuthProvider();
    try {
      await signInWithPopup(auth, provider);
      onLoginSuccess(); // Trigger redirect after successful login
    } catch (err) {
      console.error("Google sign-in error:", err);
    }
  };

  return (
    <div className="fixed inset-0 bg-gray-900/90 flex items-center justify-center z-50">
      <div className="bg-gray-800 p-8 rounded-xl shadow-xl text-center">
        <h2 className="text-2xl font-bold mb-6 text-white">Login to Continue</h2>
        <button
          onClick={handleGoogleLogin}
          className="px-6 py-3 rounded-lg font-semibold shadow-lg hover:opacity-90 transition bg-[#DAA520] text-black"
        >
          Sign in with Google
        </button>
        <p
          onClick={onClose}
          className="mt-4 text-gray-400 cursor-pointer hover:text-white"
        >
          Cancel
        </p>
      </div>
    </div>
  );
}
