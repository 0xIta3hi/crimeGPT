import React from "react";
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from "react-router-dom";

// Page Imports
import Dashboard from "./pages/Dashboard";
import NewCase from "./pages/NewCase";
import RAGQuery from "./pages/RAGQuery";
import CaseGraph from "./pages/CaseGraph";

function NavigationSidebar() {
  const location = useLocation();

  const navItems = [
    {
      path: "/",
      label: "Dashboard",
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
        </svg>
      )
    },
    {
      path: "/case/new",
      label: "New Case File",
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      )
    },
    {
      path: "/rag",
      label: "RAG Query",
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
      )
    }
  ];

  return (
    <div className="w-64 bg-gray-900 border-r border-gray-800 flex flex-col justify-between shrink-0 h-screen sticky top-0">
      <div className="p-6 space-y-6">
        {/* Brand Logotype */}
        <div className="flex items-center space-x-3 border-b border-gray-800 pb-5">
          <span className="p-2 rounded-xl bg-blue-600/10 text-blue-500 font-extrabold text-lg tracking-wider">
            CG
          </span>
          <div>
            <h1 className="text-md font-extrabold text-white leading-none">CrimeGPT</h1>
            <span className="text-[10px] text-gray-500 uppercase tracking-widest font-bold">RAG Engine</span>
          </div>
        </div>

        {/* Links Navigation */}
        <nav className="space-y-1.5">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center space-x-3.5 px-4 py-3 rounded-xl text-sm font-semibold transition-all duration-150 ${isActive ? "bg-blue-600 text-white shadow-lg shadow-blue-600/10" : "text-gray-400 hover:bg-gray-800/50 hover:text-white"}`}
              >
                {item.icon}
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Footer stamp */}
      <div className="p-6 border-t border-gray-800 text-[10px] text-gray-600 font-bold uppercase tracking-wider text-center">
        v1.0.0 National Security
      </div>
    </div>
  );
}

export default function App() {
  return (
    <Router>
      <div className="flex bg-gray-950 min-h-screen text-gray-100">
        {/* Sidebar Nav */}
        <NavigationSidebar />

        {/* Content Panel Area */}
        <main className="flex-1 p-8 overflow-y-auto max-w-7xl">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/case/new" element={<NewCase />} />
            <Route path="/rag" element={<RAGQuery />} />
            <Route path="/case/:case_id/graph" element={<CaseGraph />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}
