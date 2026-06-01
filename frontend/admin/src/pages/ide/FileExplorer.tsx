import React, { useState, useEffect } from 'react';

interface FileNode {
  name: string;
  path: string;
  is_dir: boolean;
  size: number | null;
}

interface TreeItemProps {
  node: FileNode;
  token: string;
  onSelect: (path: string) => void;
  activeFile: string | null;
  depth: number;
}

const TreeItem: React.FC<TreeItemProps> = ({ node, token, onSelect, activeFile, depth }) => {
  const [expanded, setExpanded] = useState(false);
  const [children, setChildren] = useState<FileNode[]>([]);
  const [loading, setLoading] = useState(false);

  const toggleExpand = async () => {
    if (!node.is_dir) {
      onSelect(node.path);
      return;
    }
    
    const nextExpanded = !expanded;
    setExpanded(nextExpanded);

    if (nextExpanded && children.length === 0) {
      setLoading(true);
      try {
        const res = await fetch(`/v1/ide/files?path=${encodeURIComponent(node.path)}`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          setChildren(Array.isArray(data) ? data : []);
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
  };

  return (
    <div>
      <button
        onClick={toggleExpand}
        className={`w-full text-left py-1 text-sm flex items-center gap-2 hover:bg-gray-800 transition ${
          activeFile === node.path ? 'bg-gray-800 text-blue-400' : 'text-gray-400'
        }`}
        style={{ paddingLeft: `${depth * 1 + 1}rem`, paddingRight: '1rem' }}
      >
        <span>
          {node.is_dir ? (expanded ? '📂' : '📁') : '📄'}
        </span>
        <span className="truncate">{node.name}</span>
      </button>
      
      {expanded && node.is_dir && (
        <div>
          {loading && <div className="text-xs text-gray-500 py-1" style={{ paddingLeft: `${(depth + 1) * 1 + 1}rem` }}>Carregando...</div>}
          {children.map(child => (
            <TreeItem
              key={child.path}
              node={child}
              token={token}
              onSelect={onSelect}
              activeFile={activeFile}
              depth={depth + 1}
            />
          ))}
          {!loading && children.length === 0 && (
            <div className="text-xs text-gray-500 py-1" style={{ paddingLeft: `${(depth + 1) * 1 + 1}rem` }}>Vazio</div>
          )}
        </div>
      )}
    </div>
  );
};

interface FileExplorerProps {
  token: string | null;
  onSelect: (path: string) => void;
  activeFile: string | null;
  onStatusChange?: (status: { loading: boolean; error: string | null }) => void;
}

const FileExplorer: React.FC<FileExplorerProps> = ({ token, onSelect, activeFile, onStatusChange }) => {
  const [files, setFiles] = useState<FileNode[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    onStatusChange?.({ loading, error });
  }, [loading, error, onStatusChange]);

  useEffect(() => {
    if (!token) {
      setFiles([]);
      setError(null);
      setLoading(false);
      return;
    }

    const loadFiles = async () => {
      setLoading(true);
      setError(null);
      try {
        // Ensure workspace is initialized
        await fetch('/v1/ide/workspace', {
          headers: { Authorization: `Bearer ${token}` }
        });

        const res = await fetch('/v1/ide/files', {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) {
          const payload = await res.json().catch(() => null);
          throw new Error(payload?.detail || `Falha HTTP ${res.status}`);
        }
        const data = await res.json();
        setFiles(Array.isArray(data) ? data : []);
      } catch (err: any) {
        setFiles([]);
        setError(err?.message || 'Falha ao carregar workspace.');
      } finally {
        setLoading(false);
      }
    };

    loadFiles();
  }, [token]);

  return (
    <div className="py-3">
      {!token && (
        <div className="mx-2 rounded-xl border border-dashed border-gray-700 bg-gray-900/60 p-4 text-sm text-gray-400">
          Informe uma API key de cliente para carregar o workspace.
        </div>
      )}
      {token && loading && (
        <div className="mx-2 rounded-xl border border-gray-800 bg-gray-900/60 p-4 text-sm text-gray-400">
          Carregando workspace...
        </div>
      )}
      {token && error && (
        <div className="mx-2 rounded-xl border border-red-900/60 bg-red-950/40 p-4 text-sm text-red-300">
          {error}
        </div>
      )}
      {token && !loading && !error && files.length === 0 && (
        <div className="mx-2 rounded-xl border border-gray-800 bg-gray-900/60 p-4 text-sm text-gray-400">
          Workspace vazio. O diretório do tenant será criado ao primeiro acesso.
        </div>
      )}
      {files.map(file => (
        <TreeItem
          key={file.path}
          node={file}
          token={token!}
          onSelect={onSelect}
          activeFile={activeFile}
          depth={0}
        />
      ))}
    </div>
  );
};

export default FileExplorer;
