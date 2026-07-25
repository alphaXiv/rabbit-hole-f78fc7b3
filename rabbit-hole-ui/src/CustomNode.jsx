import React, { memo } from 'react';
import { Handle, Position } from '@xyflow/react';

// Using memo() optimizes performance so React only re-renders nodes when their specific data changes
const CustomNode = memo(({ data, selected }) => {
  return (
    <div
      style={{
        padding: '16px 24px',
        borderRadius: '12px',
        background: selected ? '#eff6ff' : '#ffffff',
        border: selected ? '2px solid #3b82f6' : '1px solid #e2e8f0',
        boxShadow: selected 
          ? '0 10px 15px -3px rgba(59, 130, 246, 0.2)' 
          : '0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03)',
        minWidth: '200px',
        textAlign: 'center',
        transition: 'all 0.2s ease-in-out', // Smooth hover/select animation
        fontFamily: 'system-ui, -apple-system, sans-serif',
      }}
    >
      {/* Top connection point (Incoming) */}
      <Handle 
        type="target" 
        position={Position.Top} 
        style={{ background: '#94a3b8', width: '8px', height: '8px', border: 'none' }} 
      />
      
      {/* The Concept Label */}
      <div style={{ fontWeight: '600', color: '#1e293b', fontSize: '14px', lineHeight: '1.4' }}>
        {data.label}
      </div>

      {/* Bottom connection point (Outgoing) */}
      <Handle 
        type="source" 
        position={Position.Bottom} 
        style={{ background: '#3b82f6', width: '10px', height: '10px', border: '2px solid white' }} 
      />
    </div>
  );
});

export default CustomNode;