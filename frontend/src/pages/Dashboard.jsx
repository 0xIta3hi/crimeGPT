import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import axios from "axios";

const MOCK_CASES = [
  { case_id: "CASE-2026-001", fir_number: "FIR-12/2026", ps_code: "PS-DELHI-04" },
  { case_id: "CASE-2026-002", fir_number: "FIR-34/2026", ps_code: "PS-MUMBAI-02" },
  { case_id: "CASE-2026-003", fir_number: "FIR-56/2026", ps_code: "PS-BENGALURU-05" }
];

export default function Dashboard() {
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    axios
      .get("http://localhost:8000/api/v1/cases/")
      .then((res) => {
        if (res.data && res.data.length > 0) {
          setCases(res.data);
        } else {
          setCases(MOCK_CASES);
        }
        setLoading(false);
      })
      .catch((err) => {
        console.warn("Failed to fetch cases from API, falling back to mocks:", err);
        setCases(MOCK_CASES);
        setLoading(false);
      });
  }, []);

  return (
    <div className="space-y-8">
      {/* Header Panel */}
      <div className="bg-gray-900 border border-gray-800 rounded-2xl p-8 flex flex-col md:flex-row md:items-center justify-between shadow-2xl relative overflow-hidden">
        <div className="space-y-2 relative z-10">
          <h1 className="text-4xl font-extrabold tracking-tight text-white md:text-5xl">
            CrimeGPT
          </h1>
          <p className="text-lg font-medium text-gray-400">
            Graph RAG Legal Intelligence & Entity Resolution
          </p>
        </div>
        <div className="absolute right-0 top-0 -mt-12 -mr-12 w-64 h-64 bg-blue-600 rounded-full opacity-10 blur-3xl"></div>
      </div>

      {/* Primary Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Link
          to="/case/new"
          className="group relative bg-gray-900 border border-gray-800 hover:border-blue-500 rounded-2xl p-6 transition-all duration-300 shadow-lg hover:shadow-2xl overflow-hidden flex items-center space-x-6"
        >
          <div className="p-4 rounded-xl bg-blue-500/10 group-hover:bg-blue-500/20 text-blue-500 transition-colors duration-300">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v3m0 0v3m0-3h3m-3 0H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div>
            <h3 className="text-xl font-bold text-white group-hover:text-blue-400 transition-colors duration-300">New Case File</h3>
            <p className="text-gray-400 mt-1">Initialize case profile, register suspects and evidence.</p>
          </div>
        </Link>

        <Link
          to="/rag"
          className="group relative bg-gray-900 border border-gray-800 hover:border-emerald-500 rounded-2xl p-6 transition-all duration-300 shadow-lg hover:shadow-2xl overflow-hidden flex items-center space-x-6"
        >
          <div className="p-4 rounded-xl bg-emerald-500/10 group-hover:bg-emerald-500/20 text-emerald-500 transition-colors duration-300">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
          <div>
            <h3 className="text-xl font-bold text-white group-hover:text-emerald-400 transition-colors duration-300">Query Legal RAG</h3>
            <p className="text-gray-400 mt-1">Map crime narratives to statutes and landmark judgments.</p>
          </div>
        </Link>
      </div>

      {/* Case Directory */}
      <div className="space-y-4">
        <h2 className="text-2xl font-bold text-white tracking-wide flex items-center">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 mr-2 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
          </svg>
          Recent Case Directories
        </h2>

        {loading ? (
          <div className="flex justify-center items-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {cases.map((c) => (
              <Link
                key={c.case_id}
                to={`/case/${c.case_id}/graph`}
                className="bg-gray-900 border border-gray-800 hover:border-gray-700 rounded-xl p-5 block transition-all duration-200 hover:-translate-y-1 shadow-md hover:shadow-xl relative overflow-hidden group"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-blue-500 uppercase tracking-widest bg-blue-500/10 px-2.5 py-1 rounded-full">
                    {c.ps_code}
                  </span>
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-500 group-hover:text-white transition-colors duration-200" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                  </svg>
                </div>
                <h3 className="text-lg font-bold text-white mt-4 tracking-wide group-hover:text-blue-400 transition-colors duration-200">
                  {c.case_id}
                </h3>
                <p className="text-sm text-gray-400 mt-2">
                  FIR: <span className="font-mono text-gray-300">{c.fir_number}</span>
                </p>
                <div className="absolute bottom-0 left-0 h-1 w-0 bg-blue-500 group-hover:w-full transition-all duration-300"></div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
