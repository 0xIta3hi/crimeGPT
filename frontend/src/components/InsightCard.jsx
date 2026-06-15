import React, { useState } from "react";

export function timeAgo(dateString) {
  if (!dateString) return "";
  const now = new Date();
  const past = new Date(dateString);
  const diffMs = now - past;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);
  
  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${diffDays}d ago`;
}

export default function InsightCard({ insight, isSelected, onClick }) {
  const [isExpanded, setIsExpanded] = useState(false);

  const severityStyles = {
    critical: { border: "border-l-4 border-l-red-600", badge: "bg-red-500/10 text-red-400 border border-red-500/20" },
    high: { border: "border-l-4 border-l-orange-500", badge: "bg-orange-500/10 text-orange-400 border border-orange-500/20" },
    medium: { border: "border-l-4 border-l-yellow-500", badge: "bg-yellow-500/10 text-yellow-400 border border-yellow-500/20" },
    low: { border: "border-l-4 border-l-blue-400", badge: "bg-blue-500/10 text-blue-400 border border-blue-500/20" },
  };

  const style = severityStyles[insight.severity] || severityStyles.low;
  const isUnread = insight.read === false;

  const handleToggleExpand = (e) => {
    e.stopPropagation();
    setIsExpanded(!isExpanded);
  };

  return (
    <div
      onClick={onClick}
      className={`p-5 rounded-2xl cursor-pointer transition-all duration-200 shadow-md ${style.border} ${
        isSelected
          ? "bg-gray-800 ring-2 ring-indigo-500/70"
          : isUnread
          ? "bg-gray-800 hover:bg-gray-700/80 border border-gray-750"
          : "bg-gray-900 hover:bg-gray-800/70 border border-gray-800"
      } space-y-3 relative`}
    >
      {/* Top Header Row */}
      <div className="flex items-center justify-between">
        <span className={`text-[10px] font-extrabold uppercase px-2 py-0.5 rounded ${style.badge}`}>
          {insight.severity}
        </span>
        <span className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">
          {insight.type?.replace("_", " ")}
        </span>
      </div>

      {/* Title */}
      <h4 className="text-sm font-bold text-white leading-snug">
        {insight.title}
      </h4>

      {/* Description with Expand Toggle */}
      <div className="text-xs text-gray-400 leading-relaxed">
        <p className={isExpanded ? "" : "line-clamp-2"}>
          {insight.description}
        </p>
        {insight.description && insight.description.length > 80 && (
          <button
            onClick={handleToggleExpand}
            className="text-indigo-400 hover:text-indigo-300 font-semibold mt-1 cursor-pointer outline-none focus:outline-none"
          >
            {isExpanded ? "Show less" : "Show more"}
          </button>
        )}
      </div>

      {/* Bottom Metadata Row */}
      <div className="flex items-center justify-between pt-2 text-[10px] text-gray-500 font-semibold">
        <div className="flex items-center space-x-2.5">
          <span>{timeAgo(insight.generated_at)}</span>
          <span>•</span>
          <span className="bg-gray-950 px-1.5 py-0.5 rounded text-[9px] uppercase tracking-wider text-gray-400">
            {insight.triggered_by?.replace("_", " ")}
          </span>
          {insight.concerned_cases?.length > 0 && (
            <>
              <span>•</span>
              <span className="text-indigo-400">
                Affects {insight.concerned_cases.length} case{insight.concerned_cases.length > 1 ? "s" : ""}
              </span>
            </>
          )}
        </div>

        {/* Feedback Badges */}
        {insight.analyst_feedback === "confirmed" && (
          <div className="flex items-center space-x-1 text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20 font-bold uppercase tracking-wider text-[9px]">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
            </svg>
            <span>Confirmed</span>
          </div>
        )}
        {insight.analyst_feedback === "false_positive" && (
          <div className="flex items-center space-x-1 text-red-400 bg-red-500/10 px-2 py-0.5 rounded border border-red-500/20 font-bold uppercase tracking-wider text-[9px]">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M6 18L18 6M6 6l12 12" />
            </svg>
            <span>False Positive</span>
          </div>
        )}
      </div>
    </div>
  );
}
