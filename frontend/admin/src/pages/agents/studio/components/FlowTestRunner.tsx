import React from 'react';

const FlowTestRunner: React.FC = () => {
  return (
    <div className="p-4 flex-1">
      <h3 className="text-sm font-bold uppercase text-gray-500 mb-2">Test Runner</h3>
      <div className="space-y-4">
        <div>
          <label className="text-xs text-gray-500">Input JSON</label>
          <textarea className="w-full h-24 p-2 text-xs border rounded bg-white" placeholder='{"query": "..."}' />
        </div>
        <button className="w-full px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 transition-colors shadow">
          Execute Dry-Run
        </button>
      </div>
    </div>
  );
};

export default FlowTestRunner;
