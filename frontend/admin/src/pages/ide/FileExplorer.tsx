import React, { useState, useEffect } from 'react';

interface FileExplorerProps {
  onSelect: (path: string) => void;
  activeFile: string | null;
}

const FileExplorer: React.FC<FileExplorerProps> = ({ onSelect, activeFile }) => {
  const [files, setFiles] = useState<any[]>([]);

  useEffect(() => {
    fetch('/v1/ide/files', {
      headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
    })
      .then(res => res.json())
      .then(data => setFiles(data));
  }, []);

  return (
    <div className="py-2">
      {files.map(file => (
        <div key={file.path}>
          <button
            onClick={() => !file.is_dir && onSelect(file.path)}
            className={`w-full text-left px-4 py-1 text-sm flex items-center gap-2 hover:bg-gray-800 transition ${
              activeFile === file.path ? 'bg-gray-800 text-blue-400' : 'text-gray-400'
            }`}
          >
            <span>{file.is_dir ? '📁' : '📄'}</span>
            <span className="truncate">{file.name}</span>
          </button>
        </div>
      ))}
    </div>
  );
};

export default FileExplorer;
