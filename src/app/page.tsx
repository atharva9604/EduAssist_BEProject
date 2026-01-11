"use client";

import Footer from "@/components/footer";
import GetStartedButton from "@/components/getstartedbutton";
import Navbar from "@/components/navbar";
import { auth } from "@/lib/firebase";
import { onAuthStateChanged } from "firebase/auth";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export default function HomePage() {
  const router = useRouter();
  const [checking,setChecking] = useState(true);

useEffect(()=>{
  if (!auth) {
    // Firebase not configured, skip auth check
    setChecking(false);
    return;
  }
  const unsubscribe = onAuthStateChanged(auth,(u)=>{
    if(u){
     
    }
    setChecking(false);
  });
  return ()=>unsubscribe();
},[router]);

if(checking){
  return(
    <main className="min-h-screen bg-gray-950 text-gray-100 flex items-center justify-center">
        <div className="h-8 w-8 rounded-full border-2 border-yellow-500 border-t-transparent animate-spin" />
    </main>
  )
}

  return (
    <main className="min-h-screen flex flex-col bg-gray-950 text-gray-100 font-sans">
      {/* Navbar */}
      <header className="flex items-center px-8 py-4 bg-gray-900 shadow-lg">
        <h1 className="text-2xl font-bold tracking-wide" style={{ color: "#DAA520" }}>
          EduAssist
        </h1>
        <Navbar />
      </header>

      {/* Hero Section */}
      <section className="flex flex-1 flex-col md:flex-row items-center justify-between px-12 py-20 bg-gradient-to-br from-gray-950 via-gray-900 to-black">
        <motion.div
          initial={{ opacity: 0, x: -50 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.8 }}
          className="max-w-xl"
        >
          <h2 className="text-5xl font-extrabold leading-tight text-white">
            AI-Powered{" "}
            <span style={{ color: "#DAA520" }}>Teaching Assistant</span>
          </h2>
          <p className="mt-6 text-lg text-gray-400">
            EduAssist helps teachers save time by automating PPTs, quizzes,
            assignments, and reports. Manage classes, track attendance, and
            provide personalized insights — all from one platform.
          </p>
          <div className="mt-8 flex gap-4">
            <GetStartedButton />
          </div>
        </motion.div>

        <motion.img
          src=".\assets\illustration-gorilla-wearing-sunglasses-reading-600nw-2585135015.webp"
          alt="EduAssist Teaching"
          initial={{ opacity: 0, x: 50 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.8 }}
          className="border rounded-4xl w-full md:w-1/2 mt-10 md:mt-0 drop-shadow-2xl"
        />
      </section>

      {/* Features */}
      <section id="features" className="px-12 py-20 bg-gray-950">
        <h3 className="text-3xl font-bold text-center mb-12 text-white">
          What can EduAssist do for you?
        </h3>
        <div className="grid md:grid-cols-3 gap-10">
          {[
            {
              title: "📝 Content Generation",
              desc: "Create PPTs, question papers, quizzes, and assignments instantly with natural language prompts."
            },
            {
              title: "📊 Performance Reports",
              desc: "Track student progress with automated dashboards and smart feedback."
            },
            {
              title: "🏫 Administrative Tasks",
              desc: "Take attendance, manage classes, and reduce paperwork with AI automation."
            },
          ].map((item, idx) => (
            <div
              key={idx}
              className="bg-gray-900/70 backdrop-blur-lg p-6 rounded-2xl shadow-xl border border-gray-800 hover:border-[#DAA520] hover:shadow-[#DAA520]/30 transition transform hover:-translate-y-1"
            >
              <h4 className="text-xl font-semibold mb-3" style={{ color: "#DAA520" }}>
                {item.title}
              </h4>
              <p className="text-gray-300">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Teacher Benefits */}
      <section id="benefits" className="px-12 py-20 bg-gradient-to-br from-gray-900 to-gray-950">
        <div className="max-w-4xl mx-auto text-center">
          <h3 className="text-3xl font-bold mb-6 text-white">
            Why Teachers ❤️ EduAssist
          </h3>
          <p className="text-lg text-gray-400 mb-12">
            We built EduAssist to save educators hours of repetitive work every
            week. Focus on teaching — we’ll handle the rest.
          </p>
          <div className="grid md:grid-cols-2 gap-8 text-left">
            {[
              { title: "⏱ Save Time", desc: "Generate teaching materials in minutes instead of hours." },
              { title: "📂 Stay Organized", desc: "All lessons, quizzes, and attendance in one place." },
              { title: "🤖 AI Powered", desc: "Smart prompts deliver ready-to-use content instantly." },
              { title: "🎓 Better Outcomes", desc: "Students get timely reports and tailored feedback." },
            ].map((item, idx) => (
              <div
                key={idx}
                className="bg-gray-900 p-6 rounded-xl border border-gray-800 shadow-md hover:border-[#DAA520] hover:shadow-[#DAA520]/30 transition"
              >
                <h4 className="font-semibold mb-2" style={{ color: "#DAA520" }}>
                  {item.title}
                </h4>
                <p className="text-gray-300">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
      <Footer />
    </main>
  );
}
