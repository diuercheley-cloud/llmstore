import React, { useState } from 'react';
import FlowCanvas from './components/FlowCanvas';
import NodePalette from './components/NodePalette';
import DAGValidatorPanel from './components/DAGValidatorPanel';
import FlowCompilerPanel from './components/FlowCompilerPanel';
import FlowTestRunner from './components/FlowTestRunner';

const VisualFlowEditor: React.FC = () => {
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [validationErrors, setValidationErrors] = useState([]);

  const handleSave = async () => {
    console.log("Saving flow version...", { nodes, edges });
  };

  return (
    <div className="flex h-screen w-full overflow-hidden">
      <div className="w-64 border-r bg-gray-50 p-4">
        <NodePalette />
      </div>
      
      <div className="flex-1 relative bg-white">
        <FlowCanvas nodes={nodes} setNodes={setNodes} edges={edges} setEdges={setEdges} />
        
        <div className="absolute top-4 right-4 flex space-x-2">
          <button onClick={handleSave} className="px-4 py-2 bg-blue-600 text-white rounded shadow">
            Save Version
          </button>
        </div>
      </div>

      <div className="w-80 border-l bg-gray-50 flex flex-col">
        <DAGValidatorPanel errors={validationErrors} />
        <FlowCompilerPanel />
        <FlowTestRunner />
      </div>
    </div>
  );
};

export default VisualFlowEditor;
