import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ArrowLeft,
  FileText,
  FileCode2,
  FileJson,
  ClipboardCheck,
  ShieldCheck,
  Package,
  Workflow,
  MessageSquare,
  Wrench,
  Clock,
  User,
  Bot,
  Loader2,
  GitBranch,
  GitCommit,
  History,
  Eye,
  Lock,
  Unlock,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Send,
  ArrowUpDown,
  ChevronDown,
  ChevronRight,
  Diff,
  Activity,
  Layers,
  Plus,
  Minus
} from 'lucide-react';
import api from '../../lib/api';

// ─── Types ──────────────────────────────────────────────────────────────────
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

interface Version {
  id: string;
  artifact_id: string;
  version_number: number;
  content: string;
  content_hash: string;
  creator_id: string;
  creator_type: string;
  run_id: string | null;
  step_id: string | null;
  change_summary: string | null;
  version_metadata: Record<string, any> | null;
  created_at: string;
}

interface Review {
  id: string;
  artifact_id: string;
  version_id: string;
  reviewer_id: string;
  reviewer_type: string;
  status: string;
  comment: string | null;
  created_at: string;
  updated_at: string;
}

interface Comment {
  id: string;
  artifact_id: string;
  version_id: string | null;
  author_id: string;
  author_type: string;
  content: string;
  parent_id: string | null;
  created_at: string;
}

interface ArtifactEvent {
  id: string;
  artifact_id: string;
  event_type: string;
  actor_id: string;
  actor_type: string;
  payload: Record<string, any> | null;
  created_at: string;
}

interface DiffLine {
  type: 'equal' | 'delete' | 'insert';
  value: string;
}

interface DiffResult {
  raw_diff: string;
  structured: DiffLine[];
}

// ─── Constants ──────────────────────────────────────────────────────────────
const TYPE_CONFIG: Record<string, { icon: React.ElementType; color: string; bg: string; label: string }> = {
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

const REVIEW_STATUS_CONFIG: Record<string, { icon: React.ElementType; color: string; label: string }> = {
  pending: { icon: Clock, color: 'text-amber-500', label: 'Pendente' },
  approved: { icon: CheckCircle2, color: 'text-emerald-500', label: 'Aprovado' },
  rejected: { icon: XCircle, color: 'text-destructive', label: 'Rejeitado' },
  changes_requested: { icon: AlertTriangle, color: 'text-orange-500', label: 'Mudanças Requeridas' },
};

const EVENT_TYPE_CONFIG: Record<string, { color: string; label: string; bg: string }> = {
  created: { color: 'text-emerald-500', bg: 'bg-emerald-500', label: 'Criado' },
  version_created: { color: 'text-blue-500', bg: 'bg-blue-500', label: 'Nova Versão' },
  lock_acquired: { color: 'text-amber-500', bg: 'bg-amber-500', label: 'Lock Adquirido' },
  lock_released: { color: 'text-cyan-500', bg: 'bg-cyan-500', label: 'Lock Liberado' },
  review_added: { color: 'text-violet-500', bg: 'bg-violet-500', label: 'Review Adicionada' },
  promoted: { color: 'text-primary', bg: 'bg-primary', label: 'Promovido' },
  comment_added: { color: 'text-pink-500', bg: 'bg-pink-500', label: 'Comentário' },
};

// ─── Tabs Enum ──────────────────────────────────────────────────────────────
type TabKey = 'content' | 'versions' | 'diff' | 'reviews' | 'timeline';

// ─── Component ──────────────────────────────────────────────────────────────
export default function AgentArtifactDetail() {
  const { id: workspaceId, artifactId } = useParams<{ id: string; artifactId: string }>();
  const [artifact, setArtifact] = useState<Artifact | null>(null);
  const [versions, setVersions] = useState<Version[]>([]);
  const [events, setEvents] = useState<ArtifactEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabKey>('content');

  // Diff state
  const [diffFrom, setDiffFrom] = useState<number>(0);
  const [diffTo, setDiffTo] = useState<number>(0);
  const [diffResult, setDiffResult] = useState<DiffResult | null>(null);
  const [diffLoading, setDiffLoading] = useState(false);

  // Review state
  const [reviewStatus, setReviewStatus] = useState('approved');
  const [reviewComment, setReviewComment] = useState('');
  const [reviewLoading, setReviewLoading] = useState(false);

  // Comment state
  const [commentContent, setCommentContent] = useState('');
  const [commentLoading, setCommentLoading] = useState(false);
  const [comments, setComments] = useState<Comment[]>([]);

  // Reviews state
  const [reviews, setReviews] = useState<Review[]>([]);

  const fetchData = useCallback(async () => {
    if (!artifactId) return;
    setLoading(true);
    try {
      const [artRes, versRes, evtRes] = await Promise.all([
        api.get(`/admin/agents/artifacts/${artifactId}`),
        api.get(`/admin/agents/artifacts/${artifactId}/versions`),
        api.get(`/admin/agents/artifacts/${artifactId}/events`),
      ]);
      setArtifact(artRes.data);
      const vers = versRes.data as Version[];
      setVersions(vers);
      setEvents(evtRes.data);

      if (vers.length >= 2) {
        setDiffFrom(vers[vers.length - 1].version_number);
        setDiffTo(vers[0].version_number);
      }
    } catch (err) {
      console.error('Failed to fetch artifact:', err);
    } finally {
      setLoading(false);
    }
  }, [artifactId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const loadDiff = useCallback(async () => {
    if (!artifactId || diffFrom === diffTo || diffFrom === 0 || diffTo === 0) return;
    setDiffLoading(true);
    try {
      const res = await api.get(`/admin/agents/artifacts/${artifactId}/diff?from_version=${diffFrom}&to_version=${diffTo}`);
      setDiffResult(res.data);
    } catch (err) {
      console.error('Failed to load diff:', err);
    } finally {
      setDiffLoading(false);
    }
  }, [artifactId, diffFrom, diffTo]);

  const handleSubmitReview = async () => {
    if (!artifact || !artifact.current_version_id) return;
    setReviewLoading(true);
    try {
      await api.post(`/admin/agents/artifacts/${artifactId}/review`, {
        version_id: artifact.current_version_id,
        reviewer_id: 'admin',
        reviewer_type: 'human',
        status: reviewStatus,
        comment: reviewComment || null,
      });
      setReviewComment('');
      fetchData();
    } catch (err) {
      console.error('Review failed:', err);
    } finally {
      setReviewLoading(false);
    }
  };

  const handleSubmitComment = async () => {
    if (!commentContent.trim()) return;
    setCommentLoading(true);
    try {
      await api.post(`/admin/agents/artifacts/${artifactId}/comments`, {
        content: commentContent.trim(),
        author_id: 'admin',
        author_type: 'human',
      });
      setCommentContent('');
      fetchData();
    } catch (err) {
      console.error('Comment failed:', err);
    } finally {
      setCommentLoading(false);
    }
  };

  if (loading || !artifact) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] gap-4">
        <Loader2 className="w-10 h-10 text-primary animate-spin" />
        <p className="text-sm text-muted-foreground font-bold animate-pulse">Carregando artefato...</p>
      </div>
    );
  }

  const typeCfg = TYPE_CONFIG[artifact.artifact_type] || { icon: FileText, color: 'text-muted-foreground', bg: 'bg-secondary', label: artifact.artifact_type };
  const statusCfg = STATUS_CONFIG[artifact.status] || STATUS_CONFIG.draft;
  const TypeIcon = typeCfg.icon;
  const currentVersion = versions.find(v => v.id === artifact.current_version_id);

  const tabs: { key: TabKey; label: string; icon: React.ElementType; count?: number }[] = [
    { key: 'content', label: 'Conteúdo', icon: Eye },
    { key: 'versions', label: 'Versões', icon: History, count: versions.length },
    { key: 'diff', label: 'Diff', icon: Diff },
    { key: 'reviews', label: 'Reviews', icon: ShieldCheck },
    { key: 'timeline', label: 'Timeline', icon: Activity, count: events.length },
  ];

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4">
      {/* Breadcrumb & Header */}
      <header>
        <div className="flex items-center gap-2 text-sm font-bold text-muted-foreground mb-3">
          <Link to="/agents/workspaces" className="hover:text-primary transition-colors">Workspaces</Link>
          <ChevronRight size={12} />
          <Link to={`/agents/workspaces/${workspaceId}`} className="hover:text-primary transition-colors">Artefatos</Link>
          <ChevronRight size={12} />
          <span className="text-foreground">{artifact.name}</span>
        </div>

        <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
          <div className="flex items-start gap-4">
            <div className={`w-14 h-14 rounded-2xl ${typeCfg.bg} border border-${typeCfg.color.replace('text-', '')}/20 flex items-center justify-center shrink-0`}>
              <TypeIcon className={`w-7 h-7 ${typeCfg.color}`} />
            </div>
            <div>
              <h1 className="text-3xl font-black tracking-tight">{artifact.name}</h1>
              <div className="flex flex-wrap items-center gap-3 mt-2">
                <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10px] font-black uppercase tracking-wider ${typeCfg.color} bg-secondary/50`}>
                  <TypeIcon size={12} />
                  {typeCfg.label}
                </span>
                <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-[10px] font-black uppercase tracking-wider ${statusCfg.color} ${statusCfg.bg}`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${statusCfg.dot}`} />
                  {statusCfg.label}
                </span>
                {currentVersion && (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-secondary/50 text-[10px] font-black uppercase tracking-wider text-muted-foreground">
                    <GitCommit size={12} /> v{currentVersion.version_number}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                <span className="flex items-center gap-1">
                  {artifact.owner_id.startsWith('agent') ? <Bot size={12} /> : <User size={12} />}
                  {artifact.owner_id}
                </span>
                <span className="flex items-center gap-1">
                  <Clock size={12} />
                  {new Date(artifact.updated_at).toLocaleString('pt-BR')}
                </span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Tab Navigation */}
      <div className="flex items-center gap-1 border-b border-border overflow-x-auto pb-px">
        {tabs.map(tab => {
          const TIcon = tab.icon;
          const isActive = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-bold border-b-2 transition-all whitespace-nowrap ${
                isActive
                  ? 'text-primary border-primary'
                  : 'text-muted-foreground border-transparent hover:text-foreground hover:border-border'
              }`}
            >
              <TIcon size={16} />
              {tab.label}
              {tab.count !== undefined && (
                <span className={`text-[10px] font-black px-1.5 py-0.5 rounded-md ${isActive ? 'bg-primary/20 text-primary' : 'bg-secondary text-muted-foreground'}`}>
                  {tab.count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      <div className="animate-in fade-in">
        {/* ─── Content Tab ─── */}
        {activeTab === 'content' && currentVersion && (
          <div className="bg-card border border-border rounded-3xl shadow-sm overflow-hidden">
            <div className="flex items-center justify-between p-4 border-b border-border bg-secondary/30">
              <div className="flex items-center gap-3">
                <GitCommit size={16} className="text-muted-foreground" />
                <span className="text-sm font-bold">Versão {currentVersion.version_number}</span>
                {currentVersion.change_summary && (
                  <span className="text-xs text-muted-foreground italic">— {currentVersion.change_summary}</span>
                )}
              </div>
              <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                <span className="flex items-center gap-1">
                  {currentVersion.creator_type === 'agent' ? <Bot size={10} /> : <User size={10} />}
                  {currentVersion.creator_id}
                </span>
              </div>
            </div>
            <div className="p-5">
              <pre className="whitespace-pre-wrap font-mono text-sm text-foreground leading-relaxed bg-secondary/20 rounded-xl p-5 overflow-x-auto border border-border/50 max-h-[600px] overflow-y-auto">
                {currentVersion.content}
              </pre>
            </div>

            {/* Provenance Info */}
            {(currentVersion.run_id || currentVersion.step_id) && (
              <div className="px-5 pb-5">
                <div className="flex items-center gap-2 px-4 py-3 bg-violet-500/10 border border-violet-500/20 rounded-xl text-sm">
                  <Bot size={16} className="text-violet-500 shrink-0" />
                  <div>
                    <span className="font-bold text-violet-500">Agent Provenance</span>
                    <span className="text-muted-foreground ml-2">
                      {currentVersion.run_id && <span className="font-mono text-xs">run: {currentVersion.run_id.slice(0, 8)}…</span>}
                      {currentVersion.step_id && <span className="font-mono text-xs ml-2">step: {currentVersion.step_id.slice(0, 8)}…</span>}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'content' && !currentVersion && (
          <div className="bg-card border border-border rounded-3xl p-12 text-center">
            <FileText className="w-12 h-12 text-muted-foreground/30 mx-auto mb-4" />
            <p className="text-muted-foreground font-bold">Nenhuma versão disponível.</p>
          </div>
        )}

        {/* ─── Versions Tab ─── */}
        {activeTab === 'versions' && (
          <div className="bg-card border border-border rounded-3xl shadow-sm overflow-hidden">
            <div className="p-4 border-b border-border bg-secondary/30">
              <h3 className="font-black text-sm uppercase tracking-widest text-muted-foreground flex items-center gap-2">
                <History size={16} /> Histórico de Versões
              </h3>
            </div>
            {versions.length === 0 ? (
              <div className="py-16 text-center">
                <GitBranch className="w-10 h-10 text-muted-foreground/30 mx-auto mb-3" />
                <p className="text-muted-foreground font-bold text-sm">Nenhuma versão registrada.</p>
              </div>
            ) : (
              <div className="divide-y divide-border">
                {versions.map((v, idx) => {
                  const isCurrent = v.id === artifact.current_version_id;
                  return (
                    <div
                      key={v.id}
                      className={`p-5 flex items-start gap-4 transition-colors ${isCurrent ? 'bg-primary/5' : 'hover:bg-secondary/30'}`}
                    >
                      {/* Timeline dot */}
                      <div className="flex flex-col items-center shrink-0 pt-1">
                        <div className={`w-3.5 h-3.5 rounded-full border-2 ${isCurrent ? 'bg-primary border-primary shadow-lg shadow-primary/30' : 'bg-card border-border'}`} />
                        {idx < versions.length - 1 && <div className="w-0.5 h-full mt-1 bg-border" />}
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-black">v{v.version_number}</span>
                          {isCurrent && (
                            <span className="text-[9px] font-black uppercase tracking-wider text-primary bg-primary/10 px-2 py-0.5 rounded-md">Atual</span>
                          )}
                          <span className="text-[10px] font-mono text-muted-foreground">{v.content_hash.slice(0, 10)}</span>
                        </div>
                        {v.change_summary && (
                          <p className="text-sm text-foreground mt-1">{v.change_summary}</p>
                        )}
                        <div className="flex items-center gap-3 mt-2 text-[10px] text-muted-foreground">
                          <span className="flex items-center gap-1">
                            {v.creator_type === 'agent' ? <Bot size={10} className="text-violet-400" /> : <User size={10} />}
                            {v.creator_id}
                          </span>
                          <span className="flex items-center gap-1">
                            <Clock size={10} />
                            {new Date(v.created_at).toLocaleString('pt-BR')}
                          </span>
                          {v.run_id && (
                            <span className="flex items-center gap-1 text-violet-400">
                              <Bot size={10} />
                              <span className="font-mono">run:{v.run_id.slice(0, 8)}</span>
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* ─── Diff Tab ─── */}
        {activeTab === 'diff' && (
          <div className="space-y-4">
            <div className="bg-card border border-border rounded-3xl p-5 shadow-sm">
              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
                <div className="flex items-center gap-3 flex-1">
                  <label className="text-sm font-bold text-foreground whitespace-nowrap">De versão:</label>
                  <select
                    value={diffFrom}
                    onChange={(e) => setDiffFrom(Number(e.target.value))}
                    className="px-3 py-2 rounded-xl border border-border bg-background text-sm focus:ring-2 focus:ring-primary outline-none flex-1 appearance-none cursor-pointer"
                  >
                    {versions.map(v => (
                      <option key={v.id} value={v.version_number}>v{v.version_number} – {v.change_summary || v.content_hash.slice(0, 10)}</option>
                    ))}
                  </select>
                </div>
                <ArrowUpDown size={16} className="text-muted-foreground shrink-0" />
                <div className="flex items-center gap-3 flex-1">
                  <label className="text-sm font-bold text-foreground whitespace-nowrap">Para versão:</label>
                  <select
                    value={diffTo}
                    onChange={(e) => setDiffTo(Number(e.target.value))}
                    className="px-3 py-2 rounded-xl border border-border bg-background text-sm focus:ring-2 focus:ring-primary outline-none flex-1 appearance-none cursor-pointer"
                  >
                    {versions.map(v => (
                      <option key={v.id} value={v.version_number}>v{v.version_number} – {v.change_summary || v.content_hash.slice(0, 10)}</option>
                    ))}
                  </select>
                </div>
                <button
                  onClick={loadDiff}
                  disabled={diffLoading || diffFrom === diffTo || versions.length < 2}
                  className="bg-primary text-primary-foreground px-5 py-2 rounded-xl font-bold text-sm hover:opacity-90 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {diffLoading ? <Loader2 size={14} className="animate-spin" /> : <Diff size={14} />}
                  Comparar
                </button>
              </div>
            </div>

            {diffResult && (
              <div className="bg-card border border-border rounded-3xl shadow-sm overflow-hidden">
                <div className="p-4 border-b border-border bg-secondary/30 flex items-center gap-2">
                  <Diff size={16} className="text-muted-foreground" />
                  <span className="text-sm font-bold">Diff v{diffFrom} → v{diffTo}</span>
                  <span className="text-[10px] ml-auto text-muted-foreground">
                    {diffResult.structured.filter(l => l.type === 'insert').length} inserções, {diffResult.structured.filter(l => l.type === 'delete').length} remoções
                  </span>
                </div>
                <div className="p-1 overflow-x-auto max-h-[600px] overflow-y-auto">
                  <div className="font-mono text-xs leading-6">
                    {diffResult.structured.map((line, i) => (
                      <div
                        key={i}
                        className={`flex items-start px-4 py-0.5 ${
                          line.type === 'insert'
                            ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                            : line.type === 'delete'
                              ? 'bg-red-500/10 text-red-600 dark:text-red-400'
                              : 'text-foreground/70'
                        }`}
                      >
                        <span className="w-6 shrink-0 text-right mr-3 text-muted-foreground/50 select-none">
                          {line.type === 'insert' ? <Plus size={12} className="inline text-emerald-500" /> : line.type === 'delete' ? <Minus size={12} className="inline text-red-500" /> : ' '}
                        </span>
                        <span className="whitespace-pre-wrap break-all">{line.value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {versions.length < 2 && (
              <div className="bg-card border border-border rounded-3xl p-12 text-center">
                <Diff className="w-10 h-10 text-muted-foreground/30 mx-auto mb-3" />
                <p className="text-muted-foreground font-bold text-sm">São necessárias ao menos 2 versões para gerar um diff.</p>
              </div>
            )}
          </div>
        )}

        {/* ─── Reviews Tab ─── */}
        {activeTab === 'reviews' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Submit Review */}
            <div className="bg-card border border-border rounded-3xl shadow-sm overflow-hidden">
              <div className="p-4 border-b border-border bg-secondary/30">
                <h3 className="font-black text-sm uppercase tracking-widest text-muted-foreground flex items-center gap-2">
                  <ShieldCheck size={16} /> Enviar Review
                </h3>
              </div>
              <div className="p-5 space-y-4">
                <div>
                  <label className="block text-sm font-bold text-foreground mb-2">Decisão</label>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(REVIEW_STATUS_CONFIG).map(([key, cfg]) => {
                      const RIcon = cfg.icon;
                      const isActive = reviewStatus === key;
                      return (
                        <button
                          key={key}
                          onClick={() => setReviewStatus(key)}
                          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-bold border transition-all ${
                            isActive
                              ? `${cfg.color} border-current bg-current/10`
                              : 'border-border text-muted-foreground hover:bg-secondary'
                          }`}
                        >
                          <RIcon size={14} />
                          {cfg.label}
                        </button>
                      );
                    })}
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-bold text-foreground mb-2">Comentário (opcional)</label>
                  <textarea
                    value={reviewComment}
                    onChange={(e) => setReviewComment(e.target.value)}
                    placeholder="Adicione notas sobre a review..."
                    rows={3}
                    className="w-full px-4 py-3 rounded-xl border border-border bg-background text-sm focus:ring-2 focus:ring-primary outline-none resize-none"
                  />
                </div>
                <button
                  onClick={handleSubmitReview}
                  disabled={reviewLoading || !artifact.current_version_id}
                  className="w-full bg-primary text-primary-foreground font-bold py-3 rounded-xl hover:opacity-90 flex items-center justify-center gap-2 transition-all disabled:opacity-50"
                >
                  {reviewLoading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
                  Enviar Review
                </button>
              </div>
            </div>

            {/* Comments */}
            <div className="bg-card border border-border rounded-3xl shadow-sm overflow-hidden">
              <div className="p-4 border-b border-border bg-secondary/30">
                <h3 className="font-black text-sm uppercase tracking-widest text-muted-foreground flex items-center gap-2">
                  <MessageSquare size={16} /> Comentários
                </h3>
              </div>
              <div className="p-5 space-y-4">
                {/* Comment list from events */}
                {events
                  .filter(e => e.event_type === 'review_added' || e.event_type === 'comment_added')
                  .map(evt => {
                    const evtCfg = EVENT_TYPE_CONFIG[evt.event_type] || { color: 'text-muted-foreground', bg: 'bg-muted-foreground', label: evt.event_type };
                    return (
                      <div key={evt.id} className="flex items-start gap-3 p-3 bg-secondary/30 rounded-xl">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${evt.actor_type === 'agent' ? 'bg-violet-500/10' : 'bg-primary/10'}`}>
                          {evt.actor_type === 'agent' ? <Bot size={14} className="text-violet-500" /> : <User size={14} className="text-primary" />}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 text-xs">
                            <span className="font-bold text-foreground">{evt.actor_id}</span>
                            <span className={`text-[9px] font-black uppercase tracking-wider ${evtCfg.color}`}>{evtCfg.label}</span>
                            <span className="text-muted-foreground ml-auto">{new Date(evt.created_at).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })}</span>
                          </div>
                          {evt.payload?.comment && (
                            <p className="text-sm text-foreground/80 mt-1">{evt.payload.comment}</p>
                          )}
                          {evt.payload?.status && (
                            <span className={`inline-flex items-center gap-1 mt-1 text-[10px] font-bold ${REVIEW_STATUS_CONFIG[evt.payload.status]?.color || 'text-muted-foreground'}`}>
                              {(() => { const I = REVIEW_STATUS_CONFIG[evt.payload.status]?.icon; return I ? <I size={10} /> : null })()}
                              {REVIEW_STATUS_CONFIG[evt.payload.status]?.label || evt.payload.status}
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })}

                {events.filter(e => e.event_type === 'review_added' || e.event_type === 'comment_added').length === 0 && (
                  <div className="text-center py-8">
                    <MessageSquare className="w-8 h-8 text-muted-foreground/30 mx-auto mb-2" />
                    <p className="text-xs text-muted-foreground">Nenhum comentário ou review ainda.</p>
                  </div>
                )}

                <div className="flex gap-2 pt-2 border-t border-border">
                  <input
                    type="text"
                    value={commentContent}
                    onChange={(e) => setCommentContent(e.target.value)}
                    placeholder="Adicionar comentário..."
                    className="flex-1 px-4 py-2.5 rounded-xl border border-border bg-background text-sm focus:ring-2 focus:ring-primary outline-none"
                    onKeyDown={(e) => e.key === 'Enter' && handleSubmitComment()}
                  />
                  <button
                    onClick={handleSubmitComment}
                    disabled={commentLoading || !commentContent.trim()}
                    className="bg-primary text-primary-foreground px-4 py-2.5 rounded-xl font-bold hover:opacity-90 transition-all disabled:opacity-50"
                  >
                    {commentLoading ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ─── Timeline Tab ─── */}
        {activeTab === 'timeline' && (
          <div className="bg-card border border-border rounded-3xl shadow-sm overflow-hidden">
            <div className="p-4 border-b border-border bg-secondary/30">
              <h3 className="font-black text-sm uppercase tracking-widest text-muted-foreground flex items-center gap-2">
                <Activity size={16} /> Provenance Timeline
              </h3>
            </div>

            {events.length === 0 ? (
              <div className="py-16 text-center">
                <Activity className="w-10 h-10 text-muted-foreground/30 mx-auto mb-3" />
                <p className="text-muted-foreground font-bold text-sm">Nenhum evento registrado.</p>
              </div>
            ) : (
              <div className="relative p-5">
                {/* Vertical Line */}
                <div className="absolute left-[39px] top-5 bottom-5 w-0.5 bg-border" />

                <div className="space-y-6">
                  {events.map((evt, idx) => {
                    const evtCfg = EVENT_TYPE_CONFIG[evt.event_type] || { color: 'text-muted-foreground', bg: 'bg-muted-foreground', label: evt.event_type };
                    return (
                      <div key={evt.id} className="flex items-start gap-4 relative">
                        <div className={`w-8 h-8 rounded-full border-2 border-card flex items-center justify-center shrink-0 z-10 ${evtCfg.bg}`}>
                          {evt.actor_type === 'agent' ? (
                            <Bot size={12} className="text-white" />
                          ) : (
                            <User size={12} className="text-white" />
                          )}
                        </div>

                        <div className="flex-1 min-w-0 bg-secondary/30 rounded-xl p-4 hover:bg-secondary/50 transition-colors">
                          <div className="flex items-center flex-wrap gap-2 text-xs">
                            <span className={`font-black uppercase tracking-wider text-[10px] ${evtCfg.color}`}>{evtCfg.label}</span>
                            <span className="text-muted-foreground">por</span>
                            <span className="font-bold text-foreground flex items-center gap-1">
                              {evt.actor_type === 'agent' ? <Bot size={10} className="text-violet-400" /> : <User size={10} />}
                              {evt.actor_id}
                            </span>
                            <span className="text-muted-foreground ml-auto flex items-center gap-1">
                              <Clock size={10} />
                              {new Date(evt.created_at).toLocaleString('pt-BR')}
                            </span>
                          </div>

                          {evt.payload && Object.keys(evt.payload).length > 0 && (
                            <div className="mt-2 text-[10px] font-mono text-muted-foreground space-y-1">
                              {Object.entries(evt.payload).slice(0, 6).map(([key, val]) => (
                                <div key={key} className="flex gap-2">
                                  <span className="text-primary font-bold">{key}:</span>
                                  <span className="truncate">{typeof val === 'string' ? val : JSON.stringify(val)}</span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
