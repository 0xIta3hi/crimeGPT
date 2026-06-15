import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import axios from "axios";
import InsightCard, { timeAgo } from "../components/InsightCard";

export default function SHODashboard() {
  const navigate = useNavigate();
  const [summary, setSummary] = useState({
    total: 0,
    unread: 0,
    by_severity: { critical: 0, high: 0, medium: 0, low: 0 },
    by_type: { recidivism_flag: 0, location_cluster: 0, shared_evidence: 0, mo_pattern: 0 },
    last_scan_at: null
  });
  const [insights, setInsights] = useState([]);
  const [selectedInsight, setSelectedInsight] = useState(null);
  const [activeFilter, setActiveFilter] = useState("All");
  const [loadingScan, setLoadingScan] = useState(false);
  const [toastMsg, setToastMsg] = useState(null);

  const fetchSummary = async () => {
    try {
      const res = await axios.get("http://localhost:8000/api/v1/insights/summary");
      setSummary(res.data);
    } catch (err) {
      console.error("Error fetching insights summary:", err);
    }
  };

  const fetchInsights = async () => {
    try {
      // Fetch unread insights by default as requested
      const res = await axios.get("http://localhost:8000/api/v1/insights/?read=false&limit=50");
      setInsights(res.data);
    } catch (err) {
      console.error("Error fetching insights list:", err);
    }
  };

  useEffect(() => {
    fetchSummary();
    fetchInsights();
  }, []);

  const handleCardClick = async (insight) => {
    setSelectedInsight(insight);
    
    // If it is unread, mark it as read in backend
    if (insight.read === false) {
      try {
        const res = await axios.patch(`http://localhost:8000/api/v1/insights/${insight.insight_id}/read`);
        // Update local state to show it is read
        setInsights((prev) =>
          prev.map((item) =>
            item.insight_id === insight.insight_id ? { ...item, read: true } : item
          )
        );
        setSelectedInsight((prev) => (prev ? { ...prev, read: true } : null));
        // Refresh summary stats to update unread count
        fetchSummary();
      } catch (err) {
        console.error("Error marking insight as read:", err);
      }
    }
  };

  const handleForceScan = async () => {
    setLoadingScan(true);
    setToastMsg(null);
    try {
      const res = await axios.post("http://localhost:8000/api/v1/insights/trigger-scan");
      const created = res.data.insights_created || 0;
      setToastMsg(`Scan complete — ${created} new insights found`);
      
      // Refresh summary and feed list
      await fetchSummary();
      await fetchInsights();
      
      // Clear toast after 4s
      setTimeout(() => setToastMsg(null), 4000);
    } catch (err) {
      console.error("Error running manual scan:", err);
      setToastMsg("Scan failed. Connection refused.");
      setTimeout(() => setToastMsg(null), 4000);
    } finally {
      setLoadingScan(false);
    }
  };

  const handleFeedback = async (insightId, feedbackValue) => {
    try {
      const res = await axios.patch(`http://localhost:8000/api/v1/insights/${insightId}/feedback`, {
        feedback: feedbackValue
      });
      
      const updatedInsight = res.data.updated_insight;
      
      // Update local state arrays
      setInsights((prev) =>
        prev.map((item) =>
          item.insight_id === insightId ? { ...item, ...updatedInsight } : item
        )
      );
      
      if (selectedInsight && selectedInsight.insight_id === insightId) {
        setSelectedInsight((prev) => (prev ? { ...prev, ...updatedInsight } : null));
      }
      
      // Refresh summary counts
      fetchSummary();
      
      // If false positive was clicked, we might want to re-fetch the list to remove auto-suppressed duplicates
      if (feedbackValue === "false_positive") {
        fetchInsights();
        setSelectedInsight(null); // Close detail panel
      }
    } catch (err) {
      console.error("Error submitting feedback:", err);
    }
  };

  // Filter insights client-side
  const filteredInsights = insights.filter((item) => {
    if (activeFilter === "All") return true;
    if (activeFilter === "Recidivism") return item.type === "recidivism_flag";
    if (activeFilter === "Location Cluster") return item.type === "location_cluster";
    if (activeFilter === "Shared Evidence") return item.type === "shared_evidence";
    if (activeFilter === "MO Pattern") return item.type === "mo_pattern";
    return true;
  });

  const criticalAndHigh = (summary.by_severity?.critical || 0) + (summary.by_severity?.high || 0);

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      {/* Header and Force Rescan Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center">
            <span className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 mr-3">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </span>
            SHO legal intelligence Dashboard
          </h2>
          <p className="text-sm text-gray-400 mt-1">
            Real-time pattern analysis, recidivism tracking, and crime location hotspots.
          </p>
        </div>

        <div className="flex items-center space-x-3 self-end md:self-center">
          <button
            onClick={handleForceScan}
            disabled={loadingScan}
            className="border border-indigo-500 hover:bg-indigo-500/10 disabled:bg-gray-800 text-indigo-400 disabled:text-gray-500 font-bold px-5 py-2.5 rounded-xl transition-all shadow-md text-sm flex items-center shrink-0"
          >
            {loadingScan ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-indigo-400 mr-2.5"></div>
                Scanning Database...
              </>
            ) : (
              <>
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M4 4v5h.582m15.356 2A8.001 8.001 0 1121.21 7.89M9 11l3 3L22 4" />
                </svg>
                Force Rescan
              </>
            )}
          </button>
        </div>
      </div>

      {/* Toast Notification Alert */}
      {toastMsg && (
        <div className="p-4 bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 rounded-xl text-sm font-bold shadow-md animate-pulse">
          {toastMsg}
        </div>
      )}

      {/* Section A: Stats Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-gray-900 border border-gray-850 rounded-2xl p-5 shadow-lg space-y-1">
          <span className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Total scanned</span>
          <div className="text-3xl font-extrabold text-white">{summary.total || 0}</div>
        </div>

        <div className="bg-gray-900 border border-gray-850 rounded-2xl p-5 shadow-lg space-y-1">
          <span className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Unread insights</span>
          <div className="text-3xl font-extrabold text-yellow-500">{summary.unread || 0}</div>
        </div>

        <div className="bg-gray-900 border border-gray-850 rounded-2xl p-5 shadow-lg space-y-1">
          <span className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Critical / High</span>
          <div className="text-3xl font-extrabold text-red-500">{criticalAndHigh}</div>
        </div>

        <div className="bg-gray-900 border border-gray-850 rounded-2xl p-5 shadow-lg space-y-1">
          <span className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Last scan</span>
          <div className="text-sm font-bold text-gray-400 pt-2 break-all">
            {summary.last_scan_at ? timeAgo(summary.last_scan_at) : "Never"}
          </div>
        </div>
      </div>

      {/* Filter Row Button Bar */}
      <div className="flex flex-wrap gap-2.5 border-b border-gray-900 pb-4">
        {["All", "Recidivism", "Location Cluster", "Shared Evidence", "MO Pattern"].map((filter) => (
          <button
            key={filter}
            onClick={() => setActiveFilter(filter)}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
              activeFilter === filter
                ? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/10"
                : "bg-gray-900 hover:bg-gray-800 text-gray-400 hover:text-white border border-gray-850"
            }`}
          >
            {filter}
          </button>
        ))}
      </div>

      {/* Main Grid: Feed + Detail Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        {/* Section B: Insight Feed (Left 65%) */}
        <div className="lg:col-span-2 space-y-4 max-h-[70vh] overflow-y-auto pr-2">
          {filteredInsights.length > 0 ? (
            filteredInsights.map((insight) => (
              <InsightCard
                key={insight.insight_id}
                insight={insight}
                isSelected={selectedInsight?.insight_id === insight.insight_id}
                onClick={() => handleCardClick(insight)}
              />
            ))
          ) : (
            <div className="text-sm text-gray-500 italic p-12 text-center bg-gray-900 rounded-2xl border border-gray-850">
              No unread insights matching filter.
            </div>
          )}
        </div>

        {/* Section C: Detail Panel (Right 35%) */}
        <div className="lg:col-span-1">
          {selectedInsight ? (
            <div className="bg-gray-900 border border-gray-850 rounded-2xl p-6 shadow-xl space-y-6 sticky top-24 max-h-[80vh] overflow-y-auto">
              {/* Type + Severity Badges */}
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-extrabold uppercase px-2 py-0.5 rounded bg-gray-950 text-gray-400 border border-gray-800">
                  {selectedInsight.type?.replace("_", " ")}
                </span>
                <span className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">
                  {selectedInsight.severity}
                </span>
              </div>

              {/* Title */}
              <h3 className="text-lg font-bold text-white leading-snug border-b border-gray-850 pb-4">
                {selectedInsight.title}
              </h3>

              {/* Description */}
              <div className="space-y-2">
                <h5 className="text-[10px] font-extrabold text-gray-500 uppercase tracking-widest">Scan analysis</h5>
                <p className="text-xs text-gray-300 leading-relaxed bg-gray-950/60 p-4 rounded-xl border border-gray-950">
                  {selectedInsight.description}
                </p>
              </div>

              {/* Timestamp + Trigger Details */}
              <div className="grid grid-cols-2 gap-4 text-[10px]">
                <div className="space-y-1">
                  <span className="font-extrabold text-gray-500 uppercase tracking-widest">Generated at</span>
                  <div className="text-gray-300 font-mono">
                    {selectedInsight.generated_at ? new Date(selectedInsight.generated_at).toLocaleString() : "N/A"}
                  </div>
                </div>

                <div className="space-y-1">
                  <span className="font-extrabold text-gray-500 uppercase tracking-widest">Trigger mechanism</span>
                  <div className="text-gray-300 font-bold uppercase tracking-wider text-[9px] mt-1 bg-gray-950 px-2 py-0.5 rounded inline-block">
                    {selectedInsight.triggered_by?.replace("_", " ")}
                  </div>
                </div>
              </div>

              {/* Concerned Cases */}
              {selectedInsight.concerned_cases?.length > 0 && (
                <div className="space-y-2.5">
                  <h5 className="text-[10px] font-extrabold text-gray-500 uppercase tracking-widest">Concerned Cases</h5>
                  <div className="flex flex-wrap gap-2">
                    {selectedInsight.concerned_cases.map((cid) => (
                      <button
                        key={cid}
                        onClick={() => navigate(`/case/${cid}/graph`)}
                        className="bg-indigo-500/10 text-indigo-400 hover:bg-indigo-500 hover:text-white px-3 py-1.5 rounded-lg text-xs font-mono font-bold transition-all border border-indigo-500/20 shadow-sm cursor-pointer"
                      >
                        {cid}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Feedback Actions */}
              <div className="border-t border-gray-850 pt-5 space-y-3">
                <h5 className="text-[10px] font-extrabold text-gray-500 uppercase tracking-widest">Analyst feedback</h5>

                {selectedInsight.analyst_feedback === "none" ? (
                  <div className="grid grid-cols-2 gap-3">
                    <button
                      onClick={() => handleFeedback(selectedInsight.insight_id, "confirmed")}
                      className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-2.5 px-4 rounded-xl text-xs transition-colors flex items-center justify-center space-x-1.5 shadow-md cursor-pointer"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                      </svg>
                      <span>Confirm Lead</span>
                    </button>

                    <button
                      onClick={() => handleFeedback(selectedInsight.insight_id, "false_positive")}
                      className="border border-red-500/30 hover:bg-red-500/10 text-red-400 font-bold py-2.5 px-4 rounded-xl text-xs transition-colors flex items-center justify-center space-x-1.5 cursor-pointer"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                      <span>False Positive</span>
                    </button>
                  </div>
                ) : (
                  <div className="bg-gray-950 p-4 rounded-xl border border-gray-950 space-y-2">
                    <div className="flex items-center space-x-2 text-xs font-bold">
                      {selectedInsight.analyst_feedback === "confirmed" ? (
                        <>
                          <span className="text-emerald-500">✓ Verified Lead</span>
                          <span className="text-gray-650">•</span>
                          <span className="text-gray-500 text-[10px]">Confirmed by Analyst</span>
                        </>
                      ) : (
                        <>
                          <span className="text-red-500">✗ False Positive</span>
                          <span className="text-gray-650">•</span>
                          <span className="text-gray-500 text-[10px]">Suppressed</span>
                        </>
                      )}
                    </div>
                    {selectedInsight.feedback_at && (
                      <div className="text-[9px] text-gray-550 font-mono">
                        Reviewed: {new Date(selectedInsight.feedback_at).toLocaleString()}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="bg-gray-900 border border-gray-850 rounded-2xl p-6 shadow-xl text-center py-16 space-y-3 sticky top-24 text-gray-550">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-10 w-10 mx-auto text-gray-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <h4 className="text-sm font-bold text-gray-400">Select an insight</h4>
              <p className="text-xs text-gray-500 max-w-[200px] mx-auto leading-relaxed">
                Click any card in the feed to inspect details, concerned cases, and submit analyst feedback.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
