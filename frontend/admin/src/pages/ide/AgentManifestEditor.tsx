import React from 'react';

interface AgentManifestEditorProps {
  content: string;
  onChange: (content: string) => void;
}

const AgentManifestEditor: React.FC<AgentManifestEditorProps> = ({ content, onChange }) => {
  return (
    <div className="h-full flex flex-col bg-gray-900">
      <div className="p-4 bg-gray-800 border-b border-gray-700 font-bold text-sm">AGENT MANIFEST EDITOR</div>
      <textarea
        className="flex-1 bg-gray-900 text-green-400 p-4 font-mono focus:outline-none resize-none"
        value={content}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
};

export default AgentManifestEditor;
