import React from 'react';

interface CodeEditorProps {
  content: string;
  onChange: (content: string) => void;
}

const CodeEditor: React.FC<CodeEditorProps> = ({ content, onChange }) => {
  return (
    <textarea
      className="w-full h-full bg-gray-900 text-gray-300 p-4 font-mono focus:outline-none resize-none"
      value={content}
      onChange={(e) => onChange(e.target.value)}
      spellCheck={false}
    />
  );
};

export default CodeEditor;
