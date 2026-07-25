import React, { useState, useCallback, useRef, useEffect } from 'react';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  getNodesBounds,
  getViewportForBounds
} from '@xyflow/react';

// Core styles required by React Flow
import '@xyflow/react/dist/style.css';
import dagre from 'dagre';
import { toPng } from 'html-to-image';
import CustomNode from './CustomNode';

import { useNavigate } from 'react-router-dom';

// Define the custom types outside the component to prevent re-rendering issues
const nodeTypes = {
  custom: CustomNode,
};

const defaultEdgeOptions = {
  type: 'smoothstep', // Changes curves to sleek, angular lines
  style: {
    stroke: '#94a3b8', // Forces a visible slate-grey color
    strokeWidth: 2,    // Forces the lines to be thick enough to capture
  },
  animated: false, // Ensures html-to-image doesn't drop them due to animation frames
};

// Dagre Layout Engine
const dagreGraph = new dagre.graphlib.Graph();
dagreGraph.setDefaultEdgeLabel(() => ({}));

// Standard dimensions for our nodes
const nodeWidth = 200;
const nodeHeight = 120;

const getLayoutedElements = (nodes, edges, direction = 'TB') => {
  dagreGraph.setGraph({ rankdir: direction }); // 'TB' = Top to Bottom

  // Feed nodes to dagre
  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
  });

  // Feed edges to dagre
  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  // Calculate the layout
  dagre.layout(dagreGraph);

  // Map the new perfect coordinates back to React Flow's nodes
  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      type: 'custom',
      position: {
        x: nodeWithPosition.x - nodeWidth / 2,
        y: nodeWithPosition.y - nodeHeight / 2,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
};

export default function Dashboard() {
  // 1. Start with an empty canvas instead of hardcoded data
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  
  // 2. State for the search bar and loading indicator
  const [topic, setTopic] = useState('');
  const [loading, setLoading] = useState(false);

  // STATE FOR DATABASE FEATURES
  const [savedGraphs, setSavedGraphs] = useState([]);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const reactFlowWrapper = useRef(null);

  const navigate = useNavigate();
  const currentUsername = localStorage.getItem('username') || 'Explorer';

  // --- 1. FETCH SAVED GRAPHS ON LOAD ---
  useEffect(() => {
    fetchSavedGraphs();
  }, []);

  const handleLogout = () => {
    // Destroy the VIP passes
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    // Kick them back to the landing page
    navigate('/');
  };

  // --- 1. FETCH SAVED GRAPHS ON LOAD ---
  const fetchSavedGraphs = async () => {
    try {
      const token = localStorage.getItem('token'); // Grab the VIP pass
      
      const response = await fetch('https://rabbit-hole-y6t6.onrender.com/api/graphs', {
        headers: { 'x-auth-token': token } // Show it to the bouncer
      });
      
      const data = await response.json();
      
      // Safety Check: Only set the state if data is actually an array!
      if (Array.isArray(data)) {
        setSavedGraphs(data);
      } else {
        setSavedGraphs([]);
      }
    } catch (error) {
      console.error("Failed to fetch library:", error);
    }
  };

  // --- 2. SAVE THE CURRENT GRAPH ---
  const saveGraph = async () => {
    if (nodes.length === 0 || !topic) return;
    setIsSaving(true);
    
    try {
      const token = localStorage.getItem('token'); 
      
      const response = await fetch('https://rabbit-hole-y6t6.onrender.com/api/graphs', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'x-auth-token': token // Include the token here too
        },
        body: JSON.stringify({ topic, nodes, edges }),
      });
      
      if (response.ok) {
        alert("Graph saved successfully!");
        fetchSavedGraphs(); // Refresh the sidebar list
      } else {
        const data = await response.json();
        alert(`Failed to save: ${data.error}`);
      }
    } catch (error) {
      console.error("Failed to save graph:", error);
    } finally {
      setIsSaving(false);
    }
  };

  // --- 3. LOAD A SPECIFIC GRAPH FROM THE SIDEBAR ---
  const loadGraph = async (id) => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      
      const response = await fetch(`https://rabbit-hole-y6t6.onrender.com/api/graphs/${id}`, {
        headers: { 'x-auth-token': token } // And include it here
      });
      
      const data = await response.json();
      
      if (response.ok) {
        setTopic(data.topic);
        setNodes(data.nodes);
        setEdges(data.edges);
        setIsSidebarOpen(false); // Close sidebar after loading
      } else {
        alert(`Failed to load: ${data.error}`);
      }
    } catch (error) {
      console.error("Failed to load graph:", error);
    } finally {
      setLoading(false);
    }
  };

  // 3. The Fetch function that talks to your Express backend
  const handleSearch = async (e) => {
    e.preventDefault();
    if (!topic.trim()) return;

    setLoading(true);
    try {
      const response = await fetch('https://rabbit-hole-y6t6.onrender.com/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic }),
      });

      const data = await response.json();

      if (data.nodes && data.edges) {
        // Run the auto-layout before setting state
        const layouted = getLayoutedElements(data.nodes, data.edges);
        setNodes(layouted.nodes);
        setEdges(layouted.edges);
      }
    } catch (error) {
      console.error("Failed to fetch graph data:", error);
    } finally {
      setLoading(false);
    }
  };

  // The Click Handler
  const onNodeClick = useCallback(async (event, node) => {
    setLoading(true); 
    try {
      const response = await fetch('https://rabbit-hole-y6t6.onrender.com/api/expand', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          parentNodeId: node.id, 
          concept: node.data.label,
          parentPosition: node.position 
        }),
      });

      const data = await response.json();

      if (data.nodes && data.edges) {
        // Combine the old nodes/edges with the new ones
        const combinedNodes = [...nodes, ...data.nodes];
        const combinedEdges = [...edges, ...data.edges];
        
        // Run the auto-layout on the entire combined graph
        const layouted = getLayoutedElements(combinedNodes, combinedEdges);
        
        // Update the state with the perfectly spaced graph
        setNodes(layouted.nodes);
        setEdges(layouted.edges);
      }
    } catch (error) {
      console.error("Failed to expand node:", error);
    } finally {
      setLoading(false);
    }
  }, [nodes, edges, setNodes, setEdges]);

  // Allow users to manually connect nodes
  const onConnect = useCallback(
    (params) => setEdges((eds) => addEdge(params, eds)),
    [setEdges],
  );

  // The Image Exporter
  const downloadImage = () => {
    if (nodes.length === 0) return;

    // 1. Calculate the exact bounding box of all nodes
    const nodesBounds = getNodesBounds(nodes);
    
    // 2. Calculate the perfect zoom and pan to fit that box
    const viewport = getViewportForBounds(
      nodesBounds,
      nodesBounds.width + 200,  // Adding 200px of padding
      nodesBounds.height + 200, // Adding 200px of padding
      0.5, // min zoom
      2    // max zoom
    );

    // 3. Target the DOM element and convert it to a PNG
    const viewportElement = document.querySelector('.react-flow__viewport');
    
    toPng(viewportElement, {
      backgroundColor: '#f8fafc',
      width: nodesBounds.width + 200,
      height: nodesBounds.height + 200,
      style: {
        width: `${nodesBounds.width + 200}px`,
        height: `${nodesBounds.height + 200}px`,
        // Apply the newly calculated x, y, and zoom values
        transform: `translate(${viewport.x}px, ${viewport.y}px) scale(${viewport.zoom})`,
      },
    }).then((dataUrl) => {
      // Trigger the browser download
      const a = document.createElement('a');
      a.setAttribute('download', `${topic ? topic.replace(/\s+/g, '-') : 'rabbit-hole'}.png`);
      a.setAttribute('href', dataUrl);
      a.click();
    }).catch((err) => {
      console.error('Failed to export image:', err);
      alert('Failed to download the map. Check the console for details.');
    });
  };

  return (
    <div style={{ width: '100%', height: '100vh', display: 'flex', flexDirection: 'column', backgroundColor: '#f8fafc', overflow: 'hidden', boxSizing: 'border-box' }}>
      
      {/* --- THE HEADER --- */}
      <header style={{ padding: '16px 24px', boxSizing: 'border-box', backgroundColor: 'white', boxShadow: '0 2px 4px rgba(0,0,0,0.1)', display: 'flex', gap: '16px', alignItems: 'center', zIndex: 10, justifyContent: 'space-between' }}>
        
        <div style={{ display: 'flex', gap: '24px', alignItems: 'center' }}>
          <div>
              <h1 style={{ margin: 0, fontSize: '1.25rem', fontFamily: 'sans-serif', color: '#1e293b' }}>Rabbit Hole</h1>
            <span style={{ fontSize: '12px', color: '#64748b', fontWeight: 'bold' }}>Welcome, {currentUsername}</span>
          </div>

          <form onSubmit={handleSearch} style={{ display: 'flex', gap: '8px' }}>
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="Enter a concept..."
              disabled={loading}
              style={{ padding: '8px 12px', borderRadius: '4px', border: '1px solid #cbd5e1', outline: 'none', width: '250px' }}
            />
            <button type="submit" disabled={loading} style={{ padding: '8px 16px', backgroundColor: loading ? '#94a3b8' : '#2563eb', color: 'white', border: 'none', borderRadius: '4px', cursor: loading ? 'not-allowed' : 'pointer' }}>
              {loading ? 'Digging...' : 'Explore'}
            </button>
          </form>
        </div>
        
        {/* ACTION BUTTONS */}
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <button onClick={() => setIsSidebarOpen(!isSidebarOpen)} style={{ padding: '8px 16px', backgroundColor: '#f1f5f9', color: '#334155', border: '1px solid #cbd5e1', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}>
            {isSidebarOpen ? 'Close Library' : 'My Library'}
          </button>

          {nodes.length > 0 && (
            <>
              <button onClick={saveGraph} disabled={isSaving} style={{ padding: '8px 16px', backgroundColor: '#8b5cf6', color: 'white', border: 'none', borderRadius: '4px', cursor: isSaving ? 'not-allowed' : 'pointer', fontWeight: 'bold' }}>
                {isSaving ? 'Saving...' : 'Save to DB'}
              </button>
              <button onClick={downloadImage} style={{ padding: '8px 16px', backgroundColor: '#10b981', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}>
                Download Map
              </button>
            </>
          )}

          {/* THE LOGOUT BUTTON */}
          <div style={{ width: '1px', height: '24px', backgroundColor: '#e2e8f0', margin: '0 4px' }}></div>
          <button onClick={handleLogout} style={{ padding: '8px 16px', backgroundColor: 'transparent', color: '#ef4444', border: '1px solid #ef4444', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold', transition: 'all 0.2s' }} onMouseOver={(e) => { e.target.style.backgroundColor = '#fef2f2'; }} onMouseOut={(e) => { e.target.style.backgroundColor = 'transparent'; }}>
            Logout
          </button>
        </div>
      </header>

      {/* --- THE MAIN CONTENT AREA --- */}
      <div style={{ flex: 1, display: 'flex', position: 'relative' }}>
        
        {/* THE SIDEBAR (Slides in from the left) */}
        <div style={{ 
          width: '300px', 
          backgroundColor: 'white', 
          borderRight: '1px solid #e2e8f0', 
          display: isSidebarOpen ? 'block' : 'none',
          overflowY: 'auto',
          zIndex: 5,
          boxShadow: '4px 0 6px rgba(0,0,0,0.05)'
        }}>
          <h2 style={{ padding: '16px', margin: 0, fontSize: '1rem', borderBottom: '1px solid #e2e8f0', color: '#475569' }}>Saved Rabbit Holes</h2>
          <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
            {savedGraphs.length === 0 ? (
              <li style={{ padding: '16px', color: '#94a3b8', textAlign: 'center' }}>No saved graphs yet.</li>
            ) : (
              savedGraphs.map((graph) => (
                <li key={graph._id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                  <button 
                    onClick={() => loadGraph(graph._id)}
                    style={{ width: '100%', textAlign: 'left', padding: '16px', background: 'none', border: 'none', cursor: 'pointer', fontSize: '14px', color: '#1e293b' }}
                    onMouseOver={(e) => e.target.style.backgroundColor = '#f8fafc'}
                    onMouseOut={(e) => e.target.style.backgroundColor = 'transparent'}
                  >
                    <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>{graph.topic}</div>
                    <div style={{ fontSize: '12px', color: '#94a3b8' }}>{new Date(graph.createdAt).toLocaleDateString()}</div>
                  </button>
                </li>
              ))
            )}
          </ul>
        </div>

        {/* THE INTERACTIVE CANVAS */}
        <div style={{ flex: 1, position: 'relative' }} ref={reactFlowWrapper}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            defaultEdgeOptions={defaultEdgeOptions}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            fitView
          >
            <Controls />
            <MiniMap />
            <Background variant="dots" gap={12} size={1} />
          </ReactFlow>
        </div>

      </div>
    </div>
  );
}