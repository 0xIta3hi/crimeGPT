import React, { useState, useEffect, useRef } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import cytoscape from "cytoscape";

export default function CaseGraph() {
  const { case_id } = useParams();
  const containerRef = useRef(null);
  const cyRef = useRef(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);

  useEffect(() => {
    if (!case_id) return;

    setLoading(true);
    setError(null);
    setSelectedNode(null);

    axios
      .get(`http://localhost:8000/api/v1/cases/${case_id}/graph`)
      .then((res) => {
        const { nodes, edges } = res.data;

        if (!containerRef.current) return;

        // Initialize Cytoscape
        const cy = cytoscape({
          container: containerRef.current,
          elements: [...nodes, ...edges],
          style: [
            // Generic Node Styles
            {
              selector: "node",
              style: {
                label: "data(label)",
                "color": "#f3f4f6", // text-gray-100
                "font-size": "11px",
                "text-valign": "bottom",
                "text-margin-y": 8,
                "text-background-color": "#030712", // bg-gray-950
                "text-background-opacity": 0.8,
                "text-background-padding": "3px",
                "text-background-shape": "roundrectangle",
                "transition-property": "background-color, border-width",
                "transition-duration": "0.3s"
              }
            },
            // Case Node Styling
            {
              selector: 'node[type="Case"]',
              style: {
                "background-color": "#3b82f6", // blue-500
                shape: "ellipse",
                width: 45,
                height: 45,
                "border-width": 2,
                "border-color": "#1d4ed8"
              }
            },
            // Person Node Styling
            {
              selector: 'node[type="Person"]',
              style: {
                "background-color": "#10b981", // emerald-500
                shape: "ellipse",
                width: 32,
                height: 32,
                "border-width": 2,
                "border-color": "#047857"
              }
            },
            // Evidence Node Styling
            {
              selector: 'node[type="Evidence"]',
              style: {
                "background-color": "#f59e0b", // amber-500
                shape: "diamond",
                width: 34,
                height: 34,
                "border-width": 2,
                "border-color": "#b45309"
              }
            },
            // Officer Node Styling
            {
              selector: 'node[type="Officer"]',
              style: {
                "background-color": "#8b5cf6", // violet-500
                shape: "ellipse",
                width: 32,
                height: 32,
                "border-width": 2,
                "border-color": "#6d28d9"
              }
            },
            // CanonicalPerson (Entity Resolution) Node Styling
            {
              selector: 'node[type="CanonicalPerson"]',
              style: {
                "background-color": "#ef4444", // red-500
                shape: "ellipse",
                width: 36,
                height: 36,
                "border-width": 3,
                "border-color": "#fee2e2", // pulsing animation target
                "border-opacity": 0.9
              }
            },
            // Generic Edge Styles
            {
              selector: "edge",
              style: {
                label: "data(label)",
                "font-size": "9px",
                "color": "#9ca3af", // text-gray-400
                "text-background-color": "#0f172a", // bg-slate-900
                "text-background-opacity": 1,
                "text-background-padding": "2px",
                "width": 1.5,
                "line-color": "#374151", // border-gray-700
                "target-arrow-color": "#374151",
                "target-arrow-shape": "triangle",
                "curve-style": "bezier"
              }
            },
            // Relationship Specific colors
            {
              selector: 'edge[label="RESOLVES_TO"]',
              style: {
                "line-style": "dashed",
                "line-color": "#fca5a5",
                "target-arrow-color": "#ef4444"
              }
            }
          ],
          layout: {
            name: "cose",
            animate: true,
            nodeRepulsion: function( node ){ return 4096; },
            idealEdgeLength: function( edge ){ return 64; },
            edgeElasticity: function( edge ){ return 32; }
          }
        });

        // Save reference
        cyRef.current = cy;

        // Node click listener
        cy.on("tap", "node", (evt) => {
          const node = evt.target;
          setSelectedNode(node.data());
        });

        // Clear selection on background tap
        cy.on("tap", (evt) => {
          if (evt.target === cy) {
            setSelectedNode(null);
          }
        });

        // Pulsing border animation loop for CanonicalPerson
        let tick = 0;
        const animationInterval = setInterval(() => {
          if (!cyRef.current) return;
          tick += 0.25;
          const borderOpacity = 0.4 + Math.sin(tick) * 0.4; // oscillates between 0.0 and 0.8
          const borderWidth = 3 + Math.sin(tick) * 2; // oscillates between 1 and 5
          cyRef.current.style()
            .selector('node[type="CanonicalPerson"]')
            .style({
              "border-opacity": borderOpacity,
              "border-width": borderWidth
            })
            .update();
        }, 120);

        setLoading(false);

        // Clean up
        return () => {
          clearInterval(animationInterval);
          cy.destroy();
        };
      })
      .catch((err) => {
        console.error("Failed to load case graph:", err);
        setError("Error loading case entity graph. Please ensure the case exists.");
        setLoading(false);
      });
  }, [case_id]);

  return (
    <div className="space-y-6">
      {/* Title block */}
      <div className="flex justify-between items-center bg-gray-900 border border-gray-800 rounded-xl p-4 shadow-md">
        <div>
          <h2 className="text-xl font-bold text-white tracking-wide">
            Case Entity Resolution Graph
          </h2>
          <p className="text-xs text-gray-400 font-mono mt-1">
            Reference ID: {case_id}
          </p>
        </div>
      </div>

      <div className="flex flex-col lg:flex-row gap-6">
        {/* Cytoscape Canvas */}
        <div className="lg:w-3/4 bg-gray-950 border border-gray-800 rounded-2xl relative shadow-2xl overflow-hidden flex flex-col justify-between">
          {loading && (
            <div className="absolute inset-0 bg-gray-950/80 z-20 flex flex-col items-center justify-center space-y-4">
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500"></div>
              <p className="text-sm font-semibold text-gray-400">Assembling graph nodes...</p>
            </div>
          )}

          {error && (
            <div className="absolute inset-0 bg-gray-950/90 z-20 flex flex-col items-center justify-center p-6 text-center space-y-4">
              <div className="p-3 bg-red-500/10 rounded-full text-red-500">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-10 w-10" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <p className="text-sm font-bold text-gray-200">{error}</p>
            </div>
          )}

          <div
            ref={containerRef}
            className="w-full bg-gray-950/30"
            style={{ height: "70vh" }}
          ></div>

          {/* Graph Legend */}
          <div className="bg-gray-900/50 border-t border-gray-800 px-6 py-3 flex flex-wrap gap-4 text-xs font-semibold text-gray-400">
            <div className="flex items-center space-x-2">
              <span className="w-3.5 h-3.5 rounded-full bg-blue-500 border border-blue-700"></span>
              <span>Case File</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="w-3.5 h-3.5 rounded-full bg-emerald-500 border border-emerald-700"></span>
              <span>Case Person</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="w-3.5 h-3.5 bg-amber-500 border border-amber-700 rotate-45 transform scale-75"></span>
              <span className="ml-1">Evidence</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="w-3.5 h-3.5 rounded-full bg-violet-500 border border-violet-700"></span>
              <span>Officer</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="w-3.5 h-3.5 rounded-full bg-red-500 border border-red-200 animate-pulse"></span>
              <span>Canonical Person (Entity Resolved)</span>
            </div>
          </div>
        </div>

        {/* Sidebar Info Panel */}
        <div className="lg:w-1/4 space-y-6">
          <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 shadow-xl h-full min-h-[300px] flex flex-col">
            <h3 className="text-lg font-bold text-white border-b border-gray-800 pb-3 flex items-center">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Node Inspector
            </h3>

            {selectedNode ? (
              <div className="mt-4 flex-1 flex flex-col justify-between">
                <div className="space-y-4">
                  {/* Entity Type Label */}
                  <div>
                    <span className="text-[10px] font-extrabold uppercase tracking-widest px-2.5 py-1 rounded bg-blue-500/10 text-blue-400">
                      {selectedNode.type}
                    </span>
                    <h4 className="text-xl font-bold text-white mt-2 leading-tight">
                      {selectedNode.label}
                    </h4>
                  </div>

                  {/* Properties table */}
                  <div className="space-y-3 bg-gray-950 border border-gray-800 rounded-xl p-4 text-xs font-medium">
                    {Object.entries(selectedNode)
                      .filter(([key]) => key !== "id" && key !== "label" && key !== "type")
                      .map(([key, val]) => (
                        <div key={key} className="space-y-1">
                          <span className="text-gray-500 uppercase font-bold text-[9px] tracking-wider block">
                            {key.replace("_", " ")}
                          </span>
                          <span className="text-gray-200 font-mono break-all block">
                            {Array.isArray(val) ? val.join(", ") : String(val)}
                          </span>
                        </div>
                      ))}
                  </div>
                </div>

                <div className="text-[10px] text-gray-500 italic mt-6">
                  Select another node to inspect its attributes.
                </div>
              </div>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center text-center py-12 text-gray-500">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-12 w-12 text-gray-700 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122" />
                </svg>
                <p className="text-sm font-semibold">No node selected</p>
                <p className="text-xs text-gray-600 mt-1">Click any node in the canvas view to inspect properties.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
