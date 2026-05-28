import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
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
  User,
  ArrowLeft,
  Loader2,
  AlertCircle,
  Bot,
  Filter,
  X,
  Lock,
  Layers
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

const ARTIFACT_TYPE_CONFIG: Record<string, { icon: React.ElementType; color: string; bg: string; label: string }> = {
  markdown_doc: { icon: FileText, color: 'text-blue-400', bg: 'bg-blue-500/10', label: 'Documento' },
  code_file: { icon: FileCode2, color: 'text-emerald-400', bg: 'bg-emerald-500/10', label: 'Código' },
  json_plan: { icon: FileJson, color: 'text-amber-400', bg: 'bg-amber-500/10', label: 'Plano JSON' },
  eval_report: { icon: ClipboardCheck, color: 'text-violet-400', bg: 'bg-violet-500/10', label: 'Eval Report' },
  compliance_evidence: { icon: ShieldCheck, color: 'text-rose-400', bg: 'bg-rose-500/10', label: 'Evidência' },
  support_bundle: { icon: Package, color: 'text-orange-400', bg: 'bg-orange-500/10', label: 'Support Bundle' },
  workflow_definition: { icon: Workflow, color: 'text-cyan-400', bg: 'bg-cyan-500/10', label: 'Workflow' },
  prompt_baseline: { icon: MessageSquare, color: 'text-pink-400', bg: 'bg-pink-500/10', label: 'Prompt Baseline' },
  tool_definition: { icon: Wrench, color: 'text-teal-400', bg: 'bg-teal-500/10', label: 'Tool Definition' },
};

const STATUS_CONFIG: Record<string, { color: string; bg: string; label: string; dot: string }> = {
  draft: { color: 'text-amber-500', bg: 'bg-amber-500/10 border-amber-500/20', label: 'Draft', dot: 'bg-amber-500' },
  published: { color: 'text-emerald-500', bg: 'bg-emerald-500/10 border-emerald-500/20', label: 'Publicado', dot: 'bg-emerald-500' },
  archived: { color: 'text-muted-foreground', bg: 'bg-secondary border-border', label: 'Arquivado', dot: 'bg-muted-foreground' },
};

function CreateArtifactModal({ isOpen, onClose, workspaceId, onCreated }: { isOpen: boolean; onClose: () => void; workspaceId: string; onCreated: () => void }) {
  const [name, setName] = useState('');
  const [type, setType] = useState('markdown_doc');
  const [content, setContent] = useState('');
  const [creatorId, setCreatorId] = useState('admin');
  const [creatorType, setCreatorType] = useState('human');
  const [changeSummary, setChangeSummary] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !content.trim()) return;
    setLoading(true);
    setError('');
    try {
      await api.post(`/admin/agents/workspaces/${workspaceId}/artifacts`, {
        name: name.trim(),
        artifact_type: type,
        content,
        creator_id: creatorId,
        creator_type: creatorType,
        change_summary: changeSummary || 'Initial version',
      });
      setName('');
      setContent('');
      setChangeSummary('');
      onCreated();
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Erro ao criar artefato.');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-in fade-in" onClick={onClose}>
      <div className="bg-card border border-border rounded-3xl shadow-2xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto animate-in zoom-in-95 slide-in-from-bottom-4" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between p-6 border-b border-border sticky top-0 bg-card rounded-t-3xl z-10">
          <h2 className="text-xl font-black tracking-tight">Novo Artefato</h2>
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
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="art-name" className="block text-sm font-bold text-foreground mb-2">Nome</label>
              <input
                id="art-name"
                type="text"
                placeholder="e.g. deploy-script.py"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-4 py-3 rounded-xl border border-border bg-background focus:ring-2 focus:ring-primary focus:border-primary outline-none transition-all"
                required
                autoFocus
              />
            </div>
            <div>
              <label htmlFor="art-type" className="block text-sm font-bold text-foreground mb-2">Tipo</label>
              <select
                id="art-type"
                value={type}
                onChange={(e) => setType(e.target.value)}
                className="w-full px-4 py-3 rounded-xl border border-border bg-background focus:ring-2 focus:ring-primary focus:border-primary outline-none transition-all appearance-none cursor-pointer"
              >
                {Object.entries(ARTIFACT_TYPE_CONFIG).map(([key, cfg]) => (
                  <option key={key} value={key}>{cfg.label}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="art-creator" className="block text-sm font-bold text-foreground mb-2">Criador ID</label>
              <input
                id="art-creator"
                type="text"
                value={creatorId}
                onChange={(e) => setCreatorId(e.target.value)}
                className="w-full px-4 py-3 rounded-xl border border-border bg-background focus:ring-2 focus:ring-primary focus:border-primary outline-none transition-all"
              />
            </div>
            <div>
              <label htmlFor="art-creator-type" className="block text-sm font-bold text-foreground mb-2">Tipo de Criador</label>
              <select
                id="art-creator-type"
                value={creatorType}
                onChange={(e) => setCreatorType(e.target.value)}
                className="w-full px-4 py-3 rounded-xl border border-border bg-background focus:ring-2 focus:ring-primary focus:border-primary outline-none transition-all appearance-none cursor-pointer"
              >
                <option value="human">🧑 Humano</option>
                <option value="agent">🤖 Agente</option>
              </select>
            </div>
          </div>

          <div>
            <label htmlFor="art-summary" className="block text-sm font-bold text-foreground mb-2">Resumo da Alteração</label>
            <input
              id="art-summary"
              type="text"
              placeholder="e.g. Versão inicial do script de deploy"
              value={changeSummary}
              onChange={(e) => setChangeSummary(e.target.value)}
              className="w-full px-4 py-3 rounded-xl border border-border bg-background focus:ring-2 focus:ring-primary focus:border-primary outline-none transition-all"
            />
          </div>

          <div>
            <label htmlFor="art-content" className="block text-sm font-bold text-foreground mb-2">Conteúdo</label>
            <textarea
              id="art-content"
              placeholder="Cole ou escreva o conteúdo do artefato aqui..."
              value={content}
              onChange={(e) => setContent(e.target.value)}
              rows={8}
              className="w-full px-4 py-3 rounded-xl border border-border bg-background font-mono text-sm focus:ring-2 focus:ring-primary focus:border-primary outline-none transition-all resize-none"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading || !name.trim() || !content.trim()}
            className="w-full bg-primary text-primary-foreground font-bold py-3 rounded-xl hover:opacity-90 flex items-center justify-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Plus size={18} />}
            {loading ? 'Criando...' : 'Criar Artefato'}
          </button>
        </form>
      </div>
    </div>
  );
}

export default function AgentArtifactBrowser() {
  const { id: workspaceId } = useParams<{ id: string }>();
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filterType, setFilterType] = useState<string>('');
  const [filterStatus, setFilterStatus] = useState<string>('');
  const [showCreate, setShowCreate] = useState(false);
  const navigate = useNavigate();

  const fetchData = useCallback(async () => {
    if (!workspaceId) return;
    setLoading(true);
    try {
      const [wsRes, artRes] = await Promise.all([
        api.get('/admin/agents/workspaces'),
        api.get(`/admin/agents/workspaces/${workspaceId}/artifacts`),
      ]);
      const ws = (wsRes.data as Workspace[]).find(w => w.id === workspaceId);
      setWorkspace(ws || null);
      setArtifacts(artRes.data);
    } catch (err) {
      console.error('Failed to fetch workspace data:', err);
    } finally {
      setLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const filtered = artifacts.filter(a => {
    const matchSearch = a.name.toLowerCase().includes(search.toLowerCase());
    const matchType = !filterType || a.artifact_type === filterType;
    const matchStatus = !filterStatus || a.status === filterStatus;
    return matchSearch && matchType && matchStatus;
  });

  const typeCounts = artifacts.reduce<Record<string, number>>((acc, a) => {
    acc[a.artifact_type] = (acc[a.artifact_type] || 0) + 1;
    return acc;
  }, {});

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] gap-4">
        <Loader2 className="w-10 h-10 text-primary animate-spin" />
        <p className="text-sm text-muted-foreground font-bold animate-pulse">Carregando workspace...</p>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4">
      {/* Header */}
      <header className="flex flex-col md:flex-row md:justify-between md:items-end gap-4">
        <div>
          <Link to="/agents/workspaces" className="inline-flex items-center gap-1.5 text-sm font-bold text-muted-foreground hover:text-primary mb-3 transition-colors">
            <ArrowLeft size={14} /> Workspaces
          </Link>
          <h1 className="text-4xl font-black tracking-tight flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-primary/20 to-primary/5 border border-primary/10 flex items-center justify-center">
              <FolderOpen className="text-primary w-5 h-5" />
            </div>
            {workspace?.name || 'Workspace'}
          </h1>
          <p className="text-muted-foreground mt-2 text-base">{workspace?.description || 'Sem descrição'}</p>
          <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
            <span className="flex items-center gap-1"><User size={12} /> {workspace?.owner_id}</span>
            <span className="flex items-center gap-1"><Clock size={12} /> {workspace?.created_at ? new Date(workspace.created_at).toLocaleDateString('pt-BR') : ''}</span>
            <span className="flex items-center gap-1"><Layers size={12} /> {artifacts.length} artefato{artifacts.length !== 1 ? 's' : ''}</span>
          </div>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="bg-primary text-primary-foreground px-5 py-2.5 rounded-xl font-bold flex items-center gap-2 hover:opacity-90 transition-opacity shadow-lg shadow-primary/20"
        >
          <Plus size={18} /> Novo Artefato
        </button>
      </header>

      {/* Type Summary Cards */}
      {Object.keys(typeCounts).length > 0 && (
        <div className="flex flex-wrap gap-3">
          {Object.entries(typeCounts).map(([type, count]) => {
            const cfg = ARTIFACT_TYPE_CONFIG[type] || { icon: FileText, color: 'text-muted-foreground', bg: 'bg-secondary', label: type };
            const Icon = cfg.icon;
            const isActive = filterType === type;
            return (
              <button
                key={type}
                onClick={() => setFilterType(isActive ? '' : type)}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl border text-sm font-bold transition-all ${
                  isActive
                    ? 'border-primary bg-primary/10 text-primary shadow-sm'
                    : 'border-border bg-card hover:border-primary/30 text-muted-foreground hover:text-foreground'
                }`}
              >
                <Icon size={14} className={cfg.color} />
                <span>{cfg.label}</span>
                <span className={`text-[10px] font-black px-1.5 py-0.5 rounded-md ${isActive ? 'bg-primary/20 text-primary' : 'bg-secondary text-muted-foreground'}`}>
                  {count}
                </span>
              </button>
            );
          })}
        </div>
      )}

      {/* Search & Filters */}
      <div className="bg-card border border-border rounded-3xl shadow-sm overflow-hidden">
        <div className="p-4 border-b border-border bg-secondary/30 flex flex-col sm:flex-row gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground w-4 h-4" />
            <input
              type="text"
              placeholder="Buscar artefatos..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 bg-background border border-border rounded-xl text-sm focus:ring-2 focus:ring-primary outline-none transition-all"
            />
          </div>
          <div className="flex gap-2">
            {['draft', 'published', 'archived'].map(st => {
              const sCfg = STATUS_CONFIG[st];
              const isActive = filterStatus === st;
              return (
                <button
                  key={st}
                  onClick={() => setFilterStatus(isActive ? '' : st)}
                  className={`px-3 py-2 rounded-xl text-xs font-bold border transition-all ${
                    isActive ? `${sCfg.bg} ${sCfg.color}` : 'border-border bg-card text-muted-foreground hover:bg-secondary'
                  }`}
                >
                  {sCfg.label}
                </button>
              );
            })}
          </div>
        </div>

        {filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 gap-4">
            <FileText className="w-12 h-12 text-muted-foreground/30" />
            <p className="text-muted-foreground font-bold">
              {search || filterType || filterStatus ? 'Nenhum artefato corresponde aos filtros.' : 'Nenhum artefato neste workspace.'}
            </p>
            {!search && !filterType && !filterStatus && (
              <button
                onClick={() => setShowCreate(true)}
                className="text-primary text-sm font-bold hover:underline flex items-center gap-1"
              >
                <Plus size={14} /> Criar primeiro artefato
              </button>
            )}
          </div>
        ) : (
          <div className="divide-y divide-border">
            {filtered.map((artifact) => {
              const typeCfg = ARTIFACT_TYPE_CONFIG[artifact.artifact_type] || { icon: FileText, color: 'text-muted-foreground', bg: 'bg-secondary', label: artifact.artifact_type };
              const statusCfg = STATUS_CONFIG[artifact.status] || STATUS_CONFIG.draft;
              const Icon = typeCfg.icon;

              return (
                <Link
                  key={artifact.id}
                  to={`/agents/workspaces/${workspaceId}/artifacts/${artifact.id}`}
                  className="flex items-center gap-4 p-5 hover:bg-secondary/30 transition-all cursor-pointer group"
                >
                  <div className={`w-10 h-10 rounded-xl ${typeCfg.bg} flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform`}>
                    <Icon className={`w-5 h-5 ${typeCfg.color}`} />
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="text-sm font-black text-foreground truncate group-hover:text-primary transition-colors">{artifact.name}</h3>
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md border text-[9px] font-black uppercase tracking-wider ${statusCfg.color} ${statusCfg.bg}`}>
                        <span className={`w-1 h-1 rounded-full ${statusCfg.dot}`} />
                        {statusCfg.label}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 mt-1.5 text-[10px] text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <span className={typeCfg.color}>{typeCfg.label}</span>
                      </span>
                      <span className="flex items-center gap-1">
                        {artifact.owner_id.startsWith('agent') ? <Bot size={10} /> : <User size={10} />}
                        {artifact.owner_id}
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock size={10} /> {new Date(artifact.updated_at).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })}
                      </span>
                    </div>
                  </div>

                  <div className="text-xs text-primary font-bold opacity-0 group-hover:opacity-100 transition-opacity">
                    Ver detalhes →
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </div>

      <CreateArtifactModal isOpen={showCreate} onClose={() => setShowCreate(false)} workspaceId={workspaceId!} onCreated={fetchData} />
    </div>
  );
}
