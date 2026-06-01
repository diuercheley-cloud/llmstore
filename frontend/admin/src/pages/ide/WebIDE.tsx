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
  const [clientToken, setClientToken] = useState(() => localStorage.getItem('webIdeClientToken') || '');
  const [inputValue, setInputValue] = useState(() => localStorage.getItem('webIdeClientToken') || '');
  const [workspaceState, setWorkspaceState] = useState<{ loading: boolean; error: string | null }>({ loading: false, error: null });

  useEffect(() => {
    localStorage.setItem('webIdeClientToken', clientToken);
  }, [clientToken]);

  useEffect(() => {
    if (!clientToken) {
      setActiveFile(null);
      setFileContent('');
      setWorkspaceState({ loading: false, error: null });
    }
  }, [clientToken]);

  const handleApplyToken = () => {
    setClientToken(inputValue.trim());
  };

  const handleClearToken = () => {
    setInputValue('');
    setClientToken('');
  };

  const handleFileSelect = (path: string) => {
    if (!clientToken) return;
    setWorkspaceState({ loading: true, error: null });
    fetch(`/v1/ide/files/read?path=${encodeURIComponent(path)}`, {
      headers: { Authorization: `Bearer ${clientToken}` }
    })
      .then(async res => {
        const payload = await res.json().catch(() => ({}));
        if (!res.ok) {
          throw new Error(payload?.detail || `Falha HTTP ${res.status}`);
        }
        return payload;
      })
      .then(data => {
        setActiveFile(path);
        setFileContent(data.content || '');
        setWorkspaceState({ loading: false, error: null });
      })
      .catch(err => {
        setWorkspaceState({ loading: false, error: err.message || 'Falha ao abrir arquivo.' });
      });
  };

  const handleSave = () => {
    if (!activeFile || !clientToken) return;
    setIsSaving(true);
    fetch('/v1/ide/files/write', {
      method: 'POST',
      headers: { 
        'Authorization': `Bearer ${clientToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ path: activeFile, content: fileContent })
    })
      .finally(() => setIsSaving(false));
  };

  return (
    <div className="flex h-screen bg-slate-950 text-white overflow-hidden">
      <div className="w-full flex flex-col">
        <header className="border-b border-white/10 bg-slate-900/80 px-6 py-4 backdrop-blur flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="text-[10px] font-black uppercase tracking-[0.3em] text-blue-300">Web IDE</div>
            <h1 className="text-xl font-black">Workspace do cliente</h1>
            <p className="text-sm text-slate-400">Use uma API key de cliente para abrir arquivos, salvar manifests e rodar comandos restritos.</p>
          </div>
          <div className="grid gap-2 min-w-[320px]">
            <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">Client API Key</span>
            <div className="flex gap-2">
              <input
                className="flex-1 rounded-xl border border-white/10 bg-slate-950 px-4 py-2 text-sm text-white outline-none focus:border-blue-400"
                type="password"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder="Bearer token do cliente"
              />
              <button 
                onClick={handleApplyToken}
                className="bg-blue-600 hover:bg-blue-500 px-4 py-2 text-sm font-bold rounded-xl transition-colors"
              >
                Aplicar
              </button>
              <button 
                onClick={handleClearToken}
                className="bg-slate-800 hover:bg-slate-700 px-4 py-2 text-sm font-bold rounded-xl transition-colors border border-white/10"
              >
                Limpar
              </button>
            </div>
          </div>
        </header>

        <div className="flex flex-1 overflow-hidden">
          <div className="w-72 border-r border-white/10 bg-slate-900/60 flex flex-col">
            <div className="p-4 font-black border-b border-white/10 text-sm uppercase tracking-widest text-slate-300">Workspace</div>
            <div className="flex-1 overflow-y-auto">
              <FileExplorer
                token={clientToken || null}
                onSelect={handleFileSelect}
                activeFile={activeFile}
                onStatusChange={setWorkspaceState}
              />
            </div>
          </div>

          <div className="flex-1 flex flex-col min-w-0">
            <div className="h-10 bg-slate-900 flex items-center px-4 justify-between border-b border-white/10">
              <div className="text-sm text-slate-400 truncate">
                {workspaceState.loading ? 'Carregando...' : workspaceState.error || activeFile || 'Nenhum arquivo selecionado'}
              </div>
              <button
                onClick={handleSave}
                disabled={!activeFile || !clientToken || isSaving}
                className="text-xs bg-blue-600 hover:bg-blue-500 px-3 py-1 rounded disabled:opacity-50"
              >
                {isSaving ? 'Salvando...' : 'Salvar (Ctrl+S)'}
              </button>
            </div>

            <div className="flex-1 flex overflow-hidden">
              <div className="flex-1 overflow-hidden border-r border-white/10">
                {!activeFile ? (
                  <div className="h-full flex items-center justify-center bg-slate-950 px-8 text-center">
                    {clientToken ? (
                      <div className="max-w-lg">
                        <div className="text-[10px] font-black uppercase tracking-[0.3em] text-blue-300 mb-3">Conectado ao Workspace</div>
                        <h2 className="text-2xl font-black mb-3">Selecione um arquivo</h2>
                        <p className="text-slate-400 leading-relaxed">
                          O workspace já está disponível. Escolha um arquivo na barra lateral para abrir o editor e o terminal restrito. Você pode precisar expandir as pastas para ver os arquivos.
                        </p>
                      </div>
                    ) : (
                      <div className="max-w-lg">
                        <div className="text-[10px] font-black uppercase tracking-[0.3em] text-blue-300 mb-3">Preparado, mas não conectado</div>
                        <h2 className="text-2xl font-black mb-3">Informe uma API key de cliente</h2>
                        <p className="text-slate-400 leading-relaxed">
                          O Web IDE trabalha sobre workspaces de tenant. Sem um bearer token de cliente, a tela fica em modo explicativo e não tenta acessar arquivos ou terminal.
                        </p>
                      </div>
                    )}
                  </div>
                ) : activeFile?.endsWith('.yaml') && activeFile.includes('agents/') ? (
                  <AgentManifestEditor content={fileContent} onChange={setFileContent} />
                ) : activeFile?.endsWith('.yaml') && activeFile.includes('plugins/') ? (
                  <PluginManifestEditor content={fileContent} onChange={setFileContent} />
                ) : (
                  <CodeEditor content={fileContent} onChange={setFileContent} />
                )}
              </div>
            </div>

            <div className="h-64 border-t border-white/10">
              <TerminalPanel token={clientToken || null} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default WebIDE;
