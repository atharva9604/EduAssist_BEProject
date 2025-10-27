import React, { useState } from 'react'
import { 
  Home, 
  MessageSquare, 
  Settings, 
  User,
  LogOut,
  X
} from 'lucide-react'
import { CgProfile } from 'react-icons/cg';
import { useRouter } from 'next/navigation';

interface SidebarProps {
  isOpen: boolean;
  onToggle: () => void;
  onLogout: () => void;
  userName: string;
  activeTab:string;
  onTabChange:(tab:string)=>void;
}

const Sidebar = ({ isOpen, onToggle, onLogout, userName,activeTab,onTabChange }: SidebarProps) => {
  const router = useRouter();

  const navigationItems = [
    { id: 'home', label: 'Home', icon: Home },
    { id: 'chat', label: 'Chat', icon: MessageSquare },
    { id: 'profile', label: 'Profile', icon: CgProfile },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

   const handleNavigation = (item:any)=>{
    if(item.path){
      router.push(item.path);
    }else{
      onTabChange(item.id);
    }
   }

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
          onClick={onToggle}
        />
      )}
      
      {/* Sidebar */}
      <div className={`
        fixed top-0 left-0 h-full w-80 bg-gray-900 border-r border-gray-700 z-50 transform transition-transform duration-300 ease-in-out
        ${isOpen ? 'translate-x-0' : '-translate-x-full'}
        lg:translate-x-0 lg:static lg:z-auto
      `}>
        {/* Header with Logo */}
        <div className="p-6 border-b border-gray-700">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-[#DAA520] rounded-lg flex items-center justify-center">
                <span className="text-black font-bold text-xl">E</span>
              </div>
              <div>
                <h1 className="text-xl font-bold text-white">EduAssist</h1>
                <p className="text-xs text-gray-400">AI based teacher's companion</p>
              </div>
            </div>
            <button
              onClick={onToggle}
              className="lg:hidden p-2 hover:bg-gray-700 rounded-lg transition"
            >
              <X className="w-5 h-5 text-gray-400" />
            </button>
          </div>
        </div>

        {/* User Info */}
        <div className="p-4 border-b border-gray-700">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-[#DAA520] rounded-full flex items-center justify-center">
              <User className="w-4 h-4 text-black" />
            </div>
            <div>
              <p className="text-sm font-medium text-white">{userName}</p>
              <p className="text-xs text-gray-400">Teacher</p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <div className="p-4">
          <h3 className="text-sm font-semibold text-gray-400 mb-3">Navigation</h3>
          <nav className="space-y-2">
            {navigationItems.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.id}
                  onClick={() => handleNavigation(item)}
                  className={`
                    w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left transition
                    ${activeTab === item.id 
                      ? 'bg-[#DAA520] text-black font-medium' 
                      : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                    }
                  `}
                >
                  <Icon className="w-5 h-5" />
                  <span className="text-sm">{item.label}</span>
                </button>
              );
            })}
          </nav>
        </div>

        

        {/* Logout Button */}
        <div className="p-4 border-t border-gray-700">
          <button
            onClick={onLogout}
            className="w-full flex items-center gap-3 px-3 py-2 text-red-400 hover:bg-red-900/20 hover:text-red-300 rounded-lg transition"
          >
            <LogOut className="w-5 h-5" />
            <span className="text-sm">Logout</span>
          </button>
        </div>
      </div>
    </>
  );
};

export default Sidebar;