import React, { useState } from "react";
import axios from "axios";

export default function NewCase() {
  // Case state
  const [caseId, setCaseId] = useState("");
  const [firNumber, setFirNumber] = useState("");
  const [psCode, setPsCode] = useState("");
  const [officerBadgeId, setOfficerBadgeId] = useState("");
  const [caseCreated, setCaseCreated] = useState(false);
  const [caseMsg, setCaseMsg] = useState("");

  // Person state
  const [personName, setPersonName] = useState("");
  const [personRole, setPersonRole] = useState("accused");
  const [aadharHash, setAadharHash] = useState("");
  const [personMsg, setPersonMsg] = useState("");
  const [crossCaseAlert, setCrossCaseAlert] = useState(null);

  // Evidence state
  const [evidenceDesc, setEvidenceDesc] = useState("");
  const [evidenceType, setEvidenceType] = useState("Physical");
  const [evidenceMsg, setEvidenceMsg] = useState("");

  // Handler for Case Submit
  const handleCaseSubmit = (e) => {
    e.preventDefault();
    setCaseMsg("");
    axios
      .post("http://localhost:8000/api/v1/cases/", {
        case_id: caseId,
        fir_number: firNumber,
        ps_code: psCode,
        officer_badge_id: officerBadgeId,
      })
      .then((res) => {
        setCaseCreated(true);
        setCaseMsg(`Success! Case "${res.data.case_id}" created successfully.`);
      })
      .catch((err) => {
        console.error(err);
        setCaseMsg(`Error: ${err.response?.data?.detail || "Could not create case profile."}`);
      });
  };

  // Handler for Person Submit
  const handlePersonSubmit = (e) => {
    e.preventDefault();
    setPersonMsg("");
    setCrossCaseAlert(null);
    axios
      .post(`http://localhost:8000/api/v1/cases/${caseId}/persons`, {
        name: personName,
        role: personRole,
        aadhar_hash: aadharHash,
      })
      .then((res) => {
        setPersonName("");
        setAadharHash("");
        setPersonMsg(`Person successfully registered: ${res.data.name} (${res.data.role})`);
        
        // Entity resolution check
        if (res.data.cross_case_alert) {
          setCrossCaseAlert(res.data.alert_message);
        }
      })
      .catch((err) => {
        console.error(err);
        setPersonMsg(`Error: ${err.response?.data?.detail || "Could not add person to case."}`);
      });
  };

  // Handler for Evidence Submit
  const handleEvidenceSubmit = (e) => {
    e.preventDefault();
    setEvidenceMsg("");
    axios
      .post(`http://localhost:8000/api/v1/cases/${caseId}/evidence`, {
        description: evidenceDesc,
        evidence_type: evidenceType,
      })
      .then((res) => {
        setEvidenceDesc("");
        setEvidenceMsg(`Evidence logged successfully with ID: ${res.data.evidence_id}`);
      })
      .catch((err) => {
        console.error(err);
        setEvidenceMsg(`Error: ${err.response?.data?.detail || "Could not log evidence."}`);
      });
  };

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      {/* 1. Register Case Profile */}
      <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 shadow-xl">
        <h2 className="text-2xl font-bold text-white mb-6 flex items-center">
          <span className="p-2 rounded-lg bg-blue-500/10 text-blue-500 mr-3">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </span>
          Create New Case File
        </h2>

        <form onSubmit={handleCaseSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div className="space-y-2">
            <label className="text-sm font-semibold text-gray-300">Case ID</label>
            <input
              type="text"
              required
              disabled={caseCreated}
              placeholder="e.g. CASE-2026-001"
              value={caseId}
              onChange={(e) => setCaseId(e.target.value)}
              className="w-full bg-gray-950 border border-gray-800 focus:border-blue-500 rounded-xl px-4 py-2.5 text-white placeholder-gray-600 outline-none transition-colors disabled:opacity-50"
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-semibold text-gray-300">FIR Number</label>
            <input
              type="text"
              required
              disabled={caseCreated}
              placeholder="e.g. FIR-101/2026"
              value={firNumber}
              onChange={(e) => setFirNumber(e.target.value)}
              className="w-full bg-gray-950 border border-gray-800 focus:border-blue-500 rounded-xl px-4 py-2.5 text-white placeholder-gray-600 outline-none transition-colors disabled:opacity-50"
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-semibold text-gray-300">Police Station Code</label>
            <input
              type="text"
              required
              disabled={caseCreated}
              placeholder="e.g. PS-DELHI-01"
              value={psCode}
              onChange={(e) => setPsCode(e.target.value)}
              className="w-full bg-gray-950 border border-gray-800 focus:border-blue-500 rounded-xl px-4 py-2.5 text-white placeholder-gray-600 outline-none transition-colors disabled:opacity-50"
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-semibold text-gray-300">Officer Badge ID</label>
            <input
              type="text"
              required
              disabled={caseCreated}
              placeholder="e.g. BADGE-007"
              value={officerBadgeId}
              onChange={(e) => setOfficerBadgeId(e.target.value)}
              className="w-full bg-gray-950 border border-gray-800 focus:border-blue-500 rounded-xl px-4 py-2.5 text-white placeholder-gray-600 outline-none transition-colors disabled:opacity-50"
            />
          </div>

          {!caseCreated && (
            <div className="md:col-span-2 pt-2">
              <button
                type="submit"
                className="w-full md:w-auto bg-blue-600 hover:bg-blue-700 text-white font-bold px-6 py-3 rounded-xl transition-colors shadow-lg"
              >
                Register Case Profile
              </button>
            </div>
          )}
        </form>

        {caseMsg && (
          <div className={`mt-4 p-4 rounded-xl text-sm font-semibold ${caseCreated ? "bg-blue-500/10 text-blue-400 border border-blue-500/20" : "bg-red-500/10 text-red-400 border border-red-500/20"}`}>
            {caseMsg}
          </div>
        )}
      </div>

      {caseCreated && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* 2. Add Person Section */}
          <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 shadow-xl space-y-6">
            <h2 className="text-xl font-bold text-white flex items-center">
              <span className="p-2 rounded-lg bg-emerald-500/10 text-emerald-500 mr-3">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 9v3m0 0v3m0-3h3m-3 0H5m2 5h10a2 2 0 002-2v-3a2 2 0 00-2-2H7a2 2 0 00-2 2v3a2 2 0 002 2z" />
                </svg>
              </span>
              Add Person to Case
            </h2>

            <form onSubmit={handlePersonSubmit} className="space-y-4">
              <div className="space-y-1">
                <label className="text-xs font-semibold text-gray-400">Full Name</label>
                <input
                  type="text"
                  required
                  placeholder="Suspect or Victim Name"
                  value={personName}
                  onChange={(e) => setPersonName(e.target.value)}
                  className="w-full bg-gray-950 border border-gray-800 focus:border-emerald-500 rounded-xl px-4 py-2 text-white placeholder-gray-700 outline-none transition-colors"
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-semibold text-gray-400">Role</label>
                <select
                  value={personRole}
                  onChange={(e) => setPersonRole(e.target.value)}
                  className="w-full bg-gray-950 border border-gray-800 focus:border-emerald-500 rounded-xl px-4 py-2 text-white outline-none transition-colors"
                >
                  <option value="accused">Accused</option>
                  <option value="victim">Victim</option>
                  <option value="witness">Witness</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-xs font-semibold text-gray-400">Aadhar Hash</label>
                <input
                  type="text"
                  required
                  placeholder="Unique ID Hash for resolution"
                  value={aadharHash}
                  onChange={(e) => setAadharHash(e.target.value)}
                  className="w-full bg-gray-950 border border-gray-800 focus:border-emerald-500 rounded-xl px-4 py-2 text-white placeholder-gray-700 outline-none transition-colors font-mono"
                />
              </div>

              <button
                type="submit"
                className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-2.5 rounded-xl transition-colors shadow-md"
              >
                Register Individual
              </button>
            </form>

            {personMsg && (
              <div className="p-3 rounded-lg bg-gray-950 border border-gray-800 text-xs font-medium text-emerald-400">
                {personMsg}
              </div>
            )}

            {crossCaseAlert && (
              <div className="p-4 bg-red-600 border border-red-500 rounded-xl flex items-start space-x-3 shadow-lg animate-bounce">
                <div className="p-1.5 bg-red-800 rounded-lg text-white">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                </div>
                <div>
                  <h4 className="text-sm font-extrabold text-white uppercase tracking-wider">Cross-Case Alert</h4>
                  <p className="text-xs font-bold text-red-100 mt-1">{crossCaseAlert}</p>
                </div>
              </div>
            )}
          </div>

          {/* 3. Add Evidence Section */}
          <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 shadow-xl space-y-6">
            <h2 className="text-xl font-bold text-white flex items-center">
              <span className="p-2 rounded-lg bg-amber-500/10 text-amber-500 mr-3">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                </svg>
              </span>
              Add Evidence to Case
            </h2>

            <form onSubmit={handleEvidenceSubmit} className="space-y-4">
              <div className="space-y-1">
                <label className="text-xs font-semibold text-gray-400">Description</label>
                <textarea
                  required
                  rows={3}
                  placeholder="Describe the seized evidence item"
                  value={evidenceDesc}
                  onChange={(e) => setEvidenceDesc(e.target.value)}
                  className="w-full bg-gray-950 border border-gray-800 focus:border-amber-500 rounded-xl px-4 py-2 text-white placeholder-gray-700 outline-none transition-colors resize-none"
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-semibold text-gray-400">Evidence Type</label>
                <select
                  value={evidenceType}
                  onChange={(e) => setEvidenceType(e.target.value)}
                  className="w-full bg-gray-950 border border-gray-800 focus:border-amber-500 rounded-xl px-4 py-2 text-white outline-none transition-colors"
                >
                  <option value="Physical">Physical</option>
                  <option value="Digital">Digital</option>
                  <option value="Documentary">Documentary</option>
                </select>
              </div>

              <button
                type="submit"
                className="w-full bg-amber-600 hover:bg-amber-700 text-white font-bold py-2.5 rounded-xl transition-colors shadow-md"
              >
                Log Evidence Item
              </button>
            </form>

            {evidenceMsg && (
              <div className="p-3 rounded-lg bg-gray-950 border border-gray-800 text-xs font-medium text-amber-400">
                {evidenceMsg}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
