import React from 'react';

const nodeTypes = [
  'agent', 'llm_call', 'tool_call', 'memory_read', 
  'approval', 'condition', 'handoff', 'workflow_timer', 
  'webhook_wait', 'final_response'
];

const NodePalette: React.FC = () => {
  return (
    <div>
      <h3 className="text-sm font-bold uppercase text-gray-500 mb-4">Node Palette</h3>
      <div className="space-y-2">
        {nodeTypes.map(type => (
          <div key={type} className="p-3 bg-white border rounded shadow-sm cursor-move hover:border-blue-500 transition-colors">
            {type.replace('_', ' ')}
          </div>
        ))}
      </div>
    </div>
  );
};

export default NodePalette;
