import React from 'react';

const FlowCanvas: React.FC<any> = ({ nodes, setNodes, edges, setEdges }) => {
  return (
    <div className="w-full h-full bg-slate-100 p-8">
      <div className="text-gray-400 italic text-center mt-20">
        Canvas: Drag nodes from palette to start building the agentic flow.
      </div>
      {/* Real implementation would use React Flow or similar */}
    </div>
  );
};

export default FlowCanvas;
