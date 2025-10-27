"use client";

import React, { useEffect, useState } from "react";
import { FaUserLarge } from "react-icons/fa6";
import { auth } from "@/lib/firebase";
import {
  GoogleAuthProvider,
  onAuthStateChanged,
  signInWithPopup,
  signOut,
  User,
} from "firebase/auth";

const Navbar = () => {
  const [user, setUser] = useState<User | null>(null);

  // 🔹 Track Firebase user
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      setUser(currentUser);
    });
    return () => unsubscribe();
  }, []);

  // 🔹 Sign in with Google
  const loginWithGoogle = async () => {
    const provider = new GoogleAuthProvider();
    try {
      await signInWithPopup(auth, provider);
    } catch (error) {
      console.error("Login error:", error);
    }
  };

  // 🔹 Logout
  const logout = async () => {
    try {
      await signOut(auth);
    } catch (error) {
      console.error("Logout error:", error);
    }
  };

  return (
    <div className="w-full flex justify-end items-center">
      <nav className="ml-auto flex items-center gap-4">
        <a href="#features" className="hover:text-[#DAA520] transition">
          Features
        </a>
        <a href="#benefits" className="hover:text-[#DAA520] transition">
          For Teachers
        </a>
        <a href="#contact" className="hover:text-[#DAA520] transition">
          Contact
        </a>

        {/* 👇 User Icon or Profile Photo */}
        {!user ? (
          <FaUserLarge
            className="text-gray-300 hover:text-[#DAA520] hover:cursor-pointer"
            onClick={loginWithGoogle}
          />
        ) : (
          <div className="flex items-center gap-3">
            <img
              src={user.photoURL || "/assets/add.png"}
              alt="Profile"
              className="h-9 w-9 rounded-full border border-gray-700 hover:border-[#DAA520] transition cursor-pointer"
              referrerPolicy="no-referrer"
              title={user.displayName || user.email || "User"}
            />
            <button
              onClick={logout}
              className="text-gray-300 hover:text-white text-sm"
            >
              Logout
            </button>
          </div>
        )}
      </nav>
    </div>
  );
};

export default Navbar;
