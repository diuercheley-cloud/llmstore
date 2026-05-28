import React, { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  FolderOpen,
  Plus,
  Search,
  FileCode2,
  FileText,
  FileJson,
  ClipboardCheck,
  ShieldCheck,
  Package,
  Workflow,
  MessageSquare,
  Wrench,
  Clock,
  Users,
  Layers,
  Bot,
  User,
  X,
  Loader2,
  AlertCircle
} from 'lucide-react';
import api from '../../lib/api';

interface Workspace {
  id: string;
  name: string;
  tenant_id: string;
  description: string | null;
  owner_id: string;
  created_at: string;
  updated_at: string;
}

interface Artifact {
  id: string;
  workspace_id: string;
  tenant_id: string;
  name: string;
  artifact_type: string;
  current_version_id: string | null;
  owner_id: string;
  status: string;
  created_at: string;
  updated_at: string;
}

const ARTIFACT_TYPE_CONFIG: Record<string, { icon: React.ElementType; color: string; label: string }> = {
  markdown_doc: { icon: FileText, color: 'text-blue-400', label: 'Documento' },
  code_file: { icon: FileCode2, color: 'text-emerald-400', label: 'Código' },
  json_plan: { icon: FileJson, color: 'text-amber-400', label: 'Plano JSON' },
  eval_report: { icon: ClipboardCheck, color: 'text-violet-400', label: 'Eval Report' },
  compliance_evidence: { icon: ShieldCheck, color: 'text-rose-400', label: 'Evidência' },
  support_bundle: { icon: Package, color: 'text-orange-400', label: 'Support Bundle' },
  workflow_definition: { icon: Workflow, color: 'text-cyan-400', label: 'Workflow' },
  prompt_baseline: { icon: MessageSquare, color: 'text-pink-400', label: 'Prompt Baseline' },
  tool_definition: { icon: Wrench, color: 'text-teal-400', label: 'Tool Definition' },
};

const STATUS_CONFIG: Record<string, { color: string; bg: string; label: string }> = {
  draft: { color: 'text-amber-500', bg: 'bg-amber-500/10 border-amber-500/20', label: 'Draft' },
  published: { color: 'text-emerald-500', bg: 'bg-emerald-500/10 border-emerald-500/20', label: 'Publicado' },
  archived: { color: 'text-muted-foreground', bg: 'bg-secondary border-border', label: 'Arquivado' },
};

function ArtifactTypeBadge({ type }: { type: string }) {
  const cfg = ARTIFACT_TYPE_CONFIG[type] || { icon: FileText, color: 'text-muted-foreground', label: type };
  const Icon = cfg.icon;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-secondary/50 text-[10px] font-black uppercase tracking-wider ${cfg.color}`}>
      <Icon size={12} />
      {cfg.label}
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.draft;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-[10px] font-black uppercase tracking-wider ${cfg.color} ${cfg.bg}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${cfg.color.replace('text-', 'bg-')}`} />
      {cfg.label}
    </span>
  );
}

function CreateWorkspaceModal({ isOpen, onClose, onCreated }: { isOpen: boolean; onClose: () => void; onCreated: () => void }) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setLoading(true);
    setError('');
    try {
      await api.post('/admin/agents/workspaces', { name: name.trim(), description: description.trim() || null });
      setName('');
      setDescription('');
      onCreated();
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Erro ao criar workspace.');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-in fade-in" onClick={onClose}>
      <div className="bg-card border border-border rounded-3xl shadow-2xl w-full max-w-lg mx-4 animate-in zoom-in-95 slide-in-from-bottom-4" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between p-6 border-b border-border">
          <h2 className="text-xl font-black tracking-tight">Novo Workspace</h2>
          <button onClick={onClose} className="p-2 hover:bg-secondary rounded-xl transition-colors">
            <X size={18} />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {error && (
            <div className="flex items-center gap-2 p-3 bg-destructive/10 border border-destructive/20 rounded-xl text-sm text-destructive">
              <AlertCircle size={16} />
              {error}
            </div>
          )}
          <div>
            <label htmlFor="ws-name" className="block text-sm font-bold text-foreground mb-2">Nome do Workspace</label>
            <input
              id="ws-name"
              type="text"
              placeholder="e.g. Agent Collab v2"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-4 py-3 rounded-xl border border-border bg-background focus:ring-2 focus:ring-primary focus:border-primary outline-none transition-all"
              required
              autoFocus
            />
          </div>
          <div>
            <label htmlFor="ws-desc" className="block text-sm font-bold text-foreground mb-2">Descrição (opcional)</label>
            <textarea
              id="ws-desc"
              placeholder="Descreva o propósito deste workspace..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="w-full px-4 py-3 rounded-xl border border-border bg-background focus:ring-2 focus:ring-primary focus:border-primary outline-none transition-all resize-none"
            />
          </div>
          <button
            type="submit"
            disabled={loading || !name.trim()}
            className="w-full bg-primary text-primary-foreground font-bold py-3 rounded-xl hover:opacity-90 flex items-center justify-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Plus size={18} />}
            {loading ? 'Criando...' : 'Criar Workspace'}
          </button>
        </form>
      </div>
    </div>
  );
}

export default function AgentWorkspaces() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [artifacts, setArtifacts] = useState<Record<string, Artifact[]>>({});
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const navigate = useNavigate();

  const fetchWorkspaces = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get('/admin/agents/workspaces');
      const wsList = res.data as Workspace[];
      setWorkspaces(wsList);

      // Fetch artifacts for each workspace
      const artifactMap: Record<string, Artifact[]> = {};
      await Promise.allSettled(
        wsList.map(async (ws) => {
          try {
            const artRes = await api.get(`/admin/agents/workspaces/${ws.id}/artifacts`);
            artifactMap[ws.id] = artRes.data;
          } catch {
            artifactMap[ws.id] = [];
          }
        })
      );
      setArtifacts(artifactMap);
    } catch (err) {
      console.error('Failed to fetch workspaces:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchWorkspaces();
  }, [fetchWorkspaces]);

  const filtered = workspaces.filter((ws) =>
    ws.name.toLowerCase().includes(search.toLowerCase()) ||
    (ws.description || '').toLowerCase().includes(search.toLowerCase())
  );

  const totalArtifacts = Object.values(artifacts).reduce((sum, a) => sum + a.length, 0);
  const publishedCount = Object.values(artifacts).flat().filter(a => a.status === 'published').length;

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4">
      <header className="flex flex-col md:flex-row md:justify-between md:items-end gap-4">
        <div>
          <h1 className="text-4xl font-black tracking-tight flex items-center gap-3">
            <FolderOpen className="text-primary w-8 h-8" />
            Shared <span className="text-primary">Workspaces</span>
          </h1>
          <p className="text-muted-foreground mt-2 text-lg">Ambientes colaborativos para agentes e humanos.</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="bg-primary text-primary-foreground px-5 py-2.5 rounded-xl font-bold flex items-center gap-2 hover:opacity-90 transition-opacity shadow-lg shadow-primary/20"
        >
          <Plus size={18} /> Novo Workspace
        </button>
      </header>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { title: 'Workspaces', value: workspaces.length, icon: FolderOpen, color: 'text-primary' },
          { title: 'Artefatos Totais', value: totalArtifacts, icon: Layers, color: 'text-violet-500' },
          { title: 'Publicados', value: publishedCount, icon: ShieldCheck, color: 'text-emerald-500' },
          { title: 'Colaboradores', value: new Set(Object.values(artifacts).flat().map(a => a.owner_id)).size, icon: Users, color: 'text-amber-500' },
        ].map((stat, i) => {
          const Icon = stat.icon;
          return (
            <div key={i} className="bg-card border border-border p-5 rounded-2xl shadow-sm hover:border-primary/30 transition-all group">
              <div className="flex items-center justify-between mb-3">
                <div className={`p-2.5 rounded-xl bg-secondary/50 group-hover:bg-primary/10 transition-colors`}>
                  <Icon className={`w-5 h-5 ${stat.color} group-hover:text-primary transition-colors`} />
                </div>
              </div>
              <h3 className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">{stat.title}</h3>
              <p className="text-2xl font-black text-foreground mt-1">{stat.value}</p>
            </div>
          );
        })}
      </div>

      {/* Search */}
      <div className="bg-card border border-border rounded-3xl shadow-sm overflow-hidden">
        <div className="p-4 border-b border-border bg-secondary/30 flex flex-col sm:flex-row gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground w-4 h-4" />
            <input
              type="text"
              placeholder="Buscar workspaces..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 bg-background border border-border rounded-xl text-sm focus:ring-2 focus:ring-primary outline-none transition-all"
            />
          </div>
        </div>

        {loading ? (
          <div className="flex flex-col items-center justify-center py-20 gap-4">
            <Loader2 className="w-8 h-8 text-primary animate-spin" />
            <p className="text-sm text-muted-foreground font-bold animate-pulse">Carregando workspaces...</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 gap-4">
            <FolderOpen className="w-12 h-12 text-muted-foreground/30" />
            <p className="text-muted-foreground font-bold">
              {search ? 'Nenhum workspace encontrado.' : 'Nenhum workspace criado ainda.'}
            </p>
            {!search && (
              <button
                onClick={() => setShowCreate(true)}
                className="text-primary text-sm font-bold hover:underline flex items-center gap-1"
              >
                <Plus size={14} /> Criar primeiro workspace
              </button>
            )}
          </div>
        ) : (
          <div className="divide-y divide-border">
            {filtered.map((ws) => {
              const wsArtifacts = artifacts[ws.id] || [];
              const typeBreakdown = wsArtifacts.reduce<Record<string, number>>((acc, a) => {
                acc[a.artifact_type] = (acc[a.artifact_type] || 0) + 1;
                return acc;
              }, {});

              return (
                <Link
                  key={ws.id}
                  to={`/agents/workspaces/${ws.id}`}
                  className="flex flex-col md:flex-row items-start md:items-center gap-4 p-5 hover:bg-secondary/30 transition-all cursor-pointer group"
                >
                  <div className="flex items-center gap-4 flex-1 min-w-0">
                    <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-primary/20 to-primary/5 border border-primary/10 flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
                      <FolderOpen className="w-6 h-6 text-primary" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <h3 className="text-base font-black text-foreground truncate group-hover:text-primary transition-colors">{ws.name}</h3>
                      <p className="text-xs text-muted-foreground truncate mt-0.5">{ws.description || 'Sem descrição'}</p>
                      <div className="flex items-center gap-3 mt-2 text-[10px] text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <User size={10} /> {ws.owner_id}
                        </span>
                        <span className="flex items-center gap-1">
                          <Clock size={10} /> {new Date(ws.created_at).toLocaleDateString('pt-BR')}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 flex-wrap">
                    <span className="text-xs font-black text-muted-foreground bg-secondary px-3 py-1.5 rounded-lg">
                      {wsArtifacts.length} artefato{wsArtifacts.length !== 1 ? 's' : ''}
                    </span>
                    {Object.entries(typeBreakdown).slice(0, 3).map(([type, count]) => (
                      <ArtifactTypeBadge key={type} type={type} />
                    ))}
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </div>

      <CreateWorkspaceModal isOpen={showCreate} onClose={() => setShowCreate(false)} onCreated={fetchWorkspaces} />
    </div>
  );
}
