"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { auth } from "@/lib/firebase";
import { onAuthStateChanged, signOut, User } from "firebase/auth";
import Sidebar from "@/components/sidebar";
import { Menu, FileText, Presentation, FileQuestion } from "lucide-react";

const MainPage = () => {
  const router = useRouter();
  const [user,setUser] = useState<User | null>(null);
  const [loading,setLoading] = useState(true);
  const [sidebarOpen,setSidebarOpen] = useState(false);
  const [activeTab,setActiveTab] = useState('chat');

  useEffect(()=>{
    const unsubscribe = onAuthStateChanged(auth,(user)=>{
      setUser(user);
      setLoading(false);
    });
    return()=>unsubscribe();
  },[]);

  const getUserName = ()=>{
    if(!user) return "User";
    return user.displayName || user.email?.split('@')[0] || 'User';
  };

  const handleLogout = async () => {
    try {
      await signOut(auth);
      router.push("/"); 
    } catch (err) {
      console.error("Logout failed:", err);
    }
  };

  const handleTabChange =(tab:string)=>{
    setActiveTab(tab);
    if(tab==='home'){
      router.push('/dashboard');
    }else if(tab==='profile'){
      router.push('/profile');
    }else if(tab==='settings'){
      router.push('/settings');
    }else{
      router.push('/mainpage');
    }
  }

  if(loading){
    return(
      <div className="min-h-screen flex items-center justify-center bg-gray-950 text-gray-100">
        <div className="text-xl">Loading...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex bg-gray-950 text-gray-100">

      <Sidebar
      isOpen={sidebarOpen}
      onToggle={()=>setSidebarOpen(!sidebarOpen)}
      onLogout={handleLogout}
      userName={getUserName()} 
      activeTab={activeTab}
      onTabChange={handleTabChange}
      />
      <div className="flex-1 flex flex-col">
        <div className="bg-gray-900 p-4 flex items-center justify-between border-b border-gray-700">
          <button onClick={() => setSidebarOpen(!sidebarOpen)} className="p-2 hover:bg-gray-700 rounded-lg transition lg:hidden"
          >
            <Menu />
          </button>
          <h1 className="text-xl font-bold">EduAssist</h1>
          <div className="w-8"></div>
        </div>
        <div className="flex-1 flex flex-col items-center justify-center gap-6 p-8">
          <div className="text-center">
            <h1 className="text-3xl font-bold mb-2">
              Welcome, <span className="text-[#DAA520]">{getUserName()}!</span>
            </h1>
            <h1 className="text-3xl font-bold text-gray-300">How can I assist you today?</h1>
          </div>
          
          {/* Quick Actions */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full max-w-5xl">
            <button
              onClick={() => router.push('/lab-manual-generator')}
              className="flex flex-col items-center gap-4 p-8 bg-gray-800 rounded-xl border-2 border-gray-700 hover:border-[#DAA520] hover:bg-gray-750 transition-all group shadow-lg hover:shadow-xl"
            >
              <div className="w-16 h-16 bg-[#DAA520] rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform shadow-md">
                <FileText className="w-8 h-8 text-black" />
              </div>
              <span className="font-bold text-lg text-white">Lab Manual Generator</span>
              <span className="text-sm text-gray-400 text-center">Generate lab manuals from PDF</span>
            </button>
            
            <button
              onClick={() => router.push('/ppt-generator')}
              className="flex flex-col items-center gap-4 p-8 bg-gray-800 rounded-xl border-2 border-gray-700 hover:border-[#DAA520] hover:bg-gray-750 transition-all group shadow-lg hover:shadow-xl"
            >
              <div className="w-16 h-16 bg-[#DAA520] rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform shadow-md">
                <Presentation className="w-8 h-8 text-black" />
              </div>
              <span className="font-bold text-lg text-white">PPT Generator</span>
              <span className="text-sm text-gray-400 text-center">Create presentations</span>
            </button>
            
            <button
              onClick={() => router.push('/question-paper')}
              className="flex flex-col items-center gap-4 p-8 bg-gray-800 rounded-xl border-2 border-gray-700 hover:border-[#DAA520] hover:bg-gray-750 transition-all group shadow-lg hover:shadow-xl"
            >
              <div className="w-16 h-16 bg-[#DAA520] rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform shadow-md">
                <FileQuestion className="w-8 h-8 text-black" />
              </div>
              <span className="font-bold text-lg text-white">Question Paper</span>
              <span className="text-sm text-gray-400 text-center">Generate question papers</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MainPage;
