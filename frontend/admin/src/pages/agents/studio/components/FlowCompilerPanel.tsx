import React from 'react';

const FlowCompilerPanel: React.FC = () => {
  return (
    <div className="p-4 border-b">
      <h3 className="text-sm font-bold uppercase text-gray-500 mb-2">Flow Compiler</h3>
      <button className="w-full px-4 py-2 bg-indigo-100 text-indigo-700 rounded hover:bg-indigo-200 transition-colors">
        Compile to AgentPlan
      </button>
    </div>
  );
};

export default FlowCompilerPanel;
