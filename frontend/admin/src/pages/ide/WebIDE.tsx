import React, { useState, useEffect } from 'react';
import FileExplorer from './FileExplorer';
import CodeEditor from './CodeEditor';
import TerminalPanel from './TerminalPanel';
import AgentManifestEditor from './AgentManifestEditor';
import PluginManifestEditor from './PluginManifestEditor';

const WebIDE: React.FC = () => {
  const [activeFile, setActiveFile] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  const handleFileSelect = (path: string) => {
    fetch(`/v1/ide/files/read?path=${encodeURIComponent(path)}`, {
      headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
    })
      .then(res => res.json())
      .then(data => {
        setActiveFile(path);
        setFileContent(data.content);
      });
  };

  const handleSave = () => {
    if (!activeFile) return;
    setIsSaving(true);
    fetch('/v1/ide/files/write', {
      method: 'POST',
      headers: { 
        'Authorization': `Bearer ${localStorage.getItem('token')}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ path: activeFile, content: fileContent })
    })
      .then(() => setIsSaving(false));
  };

  return (
    <div className="flex h-screen bg-gray-900 text-white overflow-hidden">
      {/* Sidebar - File Explorer */}
      <div className="w-64 border-r border-gray-800 flex flex-col">
        <div className="p-4 font-bold border-b border-gray-800">WORKSPACE</div>
        <div className="flex-1 overflow-y-auto">
          <FileExplorer onSelect={handleFileSelect} activeFile={activeFile} />
        </div>
      </div>

      {/* Main Area */}
      <div className="flex-1 flex flex-col">
        {/* Editor Toolbar */}
        <div className="h-10 bg-gray-800 flex items-center px-4 justify-between">
          <div className="text-sm text-gray-400">{activeFile || 'No file selected'}</div>
          <button 
            onClick={handleSave}
            disabled={!activeFile || isSaving}
            className="text-xs bg-blue-600 hover:bg-blue-500 px-3 py-1 rounded disabled:opacity-50"
          >
            {isSaving ? 'Salvando...' : 'Salvar (Ctrl+S)'}
          </button>
        </div>

        {/* Editor */}
        <div className="flex-1 flex overflow-hidden">
          <div className="flex-1 overflow-hidden border-r border-gray-800">
            {activeFile?.endsWith('.yaml') && activeFile.includes('agents/') ? (
              <AgentManifestEditor content={fileContent} onChange={setFileContent} />
            ) : activeFile?.endsWith('.yaml') && activeFile.includes('plugins/') ? (
              <PluginManifestEditor content={fileContent} onChange={setFileContent} />
            ) : (
              <CodeEditor content={fileContent} onChange={setFileContent} />
            )}
          </div>
        </div>

        {/* Bottom Panel - Terminal */}
        <div className="h-64 border-t border-gray-800">
          <TerminalPanel />
        </div>
      </div>
    </div>
  );
};

export default WebIDE;
