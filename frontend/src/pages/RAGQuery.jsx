import React, { useState } from "react";
import axios from "axios";

export default function RAGQuery() {
  const [narrative, setNarrative] = useState("");
  const [caseId, setCaseId] = useState("TEST-CASE-1"); // Default target case for document generation
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  // Document generation state
  const [genDocLoading, setGenDocLoading] = useState({});
  const [genDocMsg, setGenDocMsg] = useState({});

  const handleQuerySubmit = (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResults(null);
    setGenDocMsg({});

    axios
      .post("http://localhost:8000/api/v1/rag/query", { narrative })
      .then((res) => {
        setResults(res.data);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setError("Error running Graph RAG query. Please check if Ollama and the backend are online.");
        setLoading(false);
      });
  };

  const handleGenerateDoc = (docName) => {
    // Map human document names to backend enums
    // fir_summary, remand_request, seizure_receipt
    let docType = "fir_summary";
    const nameLower = docName.toLowerCase();
    if (nameLower.includes("remand")) {
      docType = "remand_request";
    } else if (nameLower.includes("seizure") || nameLower.includes("receipt") || nameLower.includes("inventory")) {
      docType = "seizure_receipt";
    }

    setGenDocLoading((prev) => ({ ...prev, [docName]: true }));
    setGenDocMsg((prev) => ({ ...prev, [docName]: null }));

    axios
      .post("http://localhost:8000/api/v1/documents/generate", {
        case_id: caseId,
        doc_type: docType
      })
      .then((res) => {
        setGenDocLoading((prev) => ({ ...prev, [docName]: false }));
        setGenDocMsg((prev) => ({
          ...prev,
          [docName]: {
            success: true,
            text: `Successfully generated "${res.data.title}". ID: ${res.data.doc_id}`
          }
        }));
      })
      .catch((err) => {
        console.error(err);
        setGenDocLoading((prev) => ({ ...prev, [docName]: false }));
        setGenDocMsg((prev) => ({
          ...prev,
          [docName]: {
            success: false,
            text: `Failed: ${err.response?.data?.detail || "Connection refused by generator."}`
          }
        }));
      });
  };

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Search Header Panel */}
      <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 shadow-xl space-y-4">
        <h2 className="text-2xl font-bold text-white flex items-center">
          <span className="p-2 rounded-lg bg-emerald-500/10 text-emerald-500 mr-3">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </span>
          AI Graph RAG Legal Intelligence
        </h2>
        <p className="text-sm text-gray-400">
          Enter an incident narrative or FIR text. CrimeGPT will perform NLP entity extraction, retrieve statutory context from the Neo4j Knowledge Graph, and consult a local LLM to draft recommended charges and procedural checklists.
        </p>

        <form onSubmit={handleQuerySubmit} className="space-y-4 pt-2">
          <div className="space-y-1">
            <label className="text-xs font-semibold text-gray-400">FIR Narrative / Crime Text Input</label>
            <textarea
              required
              rows={5}
              placeholder="e.g. A suspect broke into a residential apartment in Delhi on MG Road at midnight, stealing jewelry..."
              value={narrative}
              onChange={(e) => setNarrative(e.target.value)}
              className="w-full bg-gray-950 border border-gray-800 focus:border-emerald-500 rounded-xl px-4 py-3 text-white placeholder-gray-600 outline-none transition-colors resize-none"
            />
          </div>

          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center space-x-3 bg-gray-950 border border-gray-800 rounded-xl px-4 py-2 w-full md:w-auto">
              <label className="text-xs font-bold text-gray-400 uppercase tracking-wider whitespace-nowrap">Target Case ID:</label>
              <input
                type="text"
                required
                value={caseId}
                onChange={(e) => setCaseId(e.target.value)}
                className="bg-transparent text-sm text-white font-mono outline-none border-none w-28 placeholder-gray-700"
                placeholder="TEST-CASE-1"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full md:w-auto bg-emerald-600 hover:bg-emerald-700 text-white font-bold px-8 py-3 rounded-xl transition-colors shadow-lg flex items-center justify-center disabled:opacity-50"
            >
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Analyzing Legal Graph...
                </>
              ) : (
                "Query Legal RAG"
              )}
            </button>
          </div>
        </form>
      </div>

      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/20 text-red-400 rounded-xl text-sm font-semibold">
          {error}
        </div>
      )}

      {/* Analysis Results Panel */}
      {results && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Results Column */}
          <div className="lg:col-span-2 space-y-6">
            {/* Extracted Entities */}
            <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 shadow-xl space-y-4">
              <h3 className="text-lg font-bold text-white flex items-center border-b border-gray-800 pb-2">
                Extracted Entities
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-gray-950 border border-gray-800 rounded-xl p-3">
                  <span className="text-[10px] font-extrabold uppercase tracking-widest text-emerald-400">Accused</span>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {results.extracted_entities?.Accused?.length > 0 ? (
                      results.extracted_entities.Accused.map((a) => (
                        <span key={a} className="text-xs bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 px-2 py-0.5 rounded">
                          {a}
                        </span>
                      ))
                    ) : (
                      <span className="text-xs text-gray-600 italic">None detected</span>
                    )}
                  </div>
                </div>

                <div className="bg-gray-950 border border-gray-800 rounded-xl p-3">
                  <span className="text-[10px] font-extrabold uppercase tracking-widest text-blue-400">Location</span>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {results.extracted_entities?.Location?.length > 0 ? (
                      results.extracted_entities.Location.map((l) => (
                        <span key={l} className="text-xs bg-blue-500/10 text-blue-300 border border-blue-500/20 px-2 py-0.5 rounded">
                          {l}
                        </span>
                      ))
                    ) : (
                      <span className="text-xs text-gray-600 italic">None detected</span>
                    )}
                  </div>
                </div>

                <div className="bg-gray-950 border border-gray-800 rounded-xl p-3">
                  <span className="text-[10px] font-extrabold uppercase tracking-widest text-violet-400">Offense Keywords</span>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {results.extracted_entities?.Offense?.length > 0 ? (
                      results.extracted_entities.Offense.map((o) => (
                        <span key={o} className="text-xs bg-violet-500/10 text-violet-300 border border-violet-500/20 px-2 py-0.5 rounded">
                          {o}
                        </span>
                      ))
                    ) : (
                      <span className="text-xs text-gray-600 italic">None detected</span>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Recommended Charges */}
            <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 shadow-xl space-y-4">
              <h3 className="text-lg font-bold text-white flex items-center border-b border-gray-800 pb-2">
                Recommended BNS Charges
              </h3>
              {results.recommended_sections?.length > 0 ? (
                <div className="space-y-4">
                  {results.recommended_sections.map((secId) => (
                    <div key={secId} className="bg-gray-950 border border-gray-800 rounded-xl p-4 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-extrabold text-blue-400 uppercase tracking-wide">
                          BNS Section {secId}
                        </span>
                      </div>
                      <p className="text-sm text-gray-300 font-semibold italic mt-2">
                        Reasoning: "{results.reasoning}"
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-sm text-gray-500 italic p-4 text-center">
                  No statutory recommendations generated.
                </div>
              )}
            </div>
          </div>

          {/* Sidebar Checklists & Documents */}
          <div className="space-y-6">
            {/* Required Documents / Checklist */}
            <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 shadow-xl space-y-4">
              <h3 className="text-lg font-bold text-white flex items-center border-b border-gray-800 pb-2">
                Procedural Documents
              </h3>
              {results.required_documents?.length > 0 ? (
                <div className="space-y-3">
                  {results.required_documents.map((docName) => (
                    <div key={docName} className="bg-gray-950 border border-gray-800 rounded-xl p-3 space-y-3">
                      <div className="flex items-center justify-between space-x-2">
                        <span className="text-xs font-bold text-gray-300 break-words flex-1">
                          {docName}
                        </span>
                        <button
                          onClick={() => handleGenerateDoc(docName)}
                          disabled={genDocLoading[docName]}
                          className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-800 text-[10px] font-extrabold text-white px-2.5 py-1.5 rounded transition-all tracking-wider uppercase shrink-0"
                        >
                          {genDocLoading[docName] ? "Writing..." : "Generate"}
                        </button>
                      </div>

                      {genDocMsg[docName] && (
                        <div className={`text-[10px] font-semibold p-2 rounded ${genDocMsg[docName].success ? "bg-blue-500/10 text-blue-400" : "bg-red-500/10 text-red-400"}`}>
                          {genDocMsg[docName].text}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-xs text-gray-500 italic">No document checklist returned.</div>
              )}
            </div>

            {/* Landmark Judgments */}
            <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 shadow-xl space-y-4">
              <h3 className="text-lg font-bold text-white flex items-center border-b border-gray-800 pb-2">
                Landmark Precedents
              </h3>
              {results.landmark_judgments?.length > 0 ? (
                <div className="space-y-2.5">
                  {results.landmark_judgments.map((cit) => (
                    <div key={cit} className="bg-gray-950 border border-gray-800 rounded-xl p-3 flex items-center space-x-3">
                      <span className="p-1.5 rounded bg-red-500/10 text-red-500 shrink-0">
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                        </svg>
                      </span>
                      <span className="text-xs font-mono font-bold text-red-400 break-all">
                        {cit}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-xs text-gray-500 italic">No precedents linked in RAG context.</div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
