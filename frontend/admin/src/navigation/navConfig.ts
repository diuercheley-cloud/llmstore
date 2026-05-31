import type { LucideIcon } from 'lucide-react'
import {
  LayoutDashboard,
  Users,
  Box,
  Server,
  Zap,
  Cloud,
  Activity,
  Bot,
  Wrench,
  FlaskConical,
  ShieldCheck,
  BarChart3,
  MessageSquare,
  Code2,
  Key,
  Wallet,
  TrendingUp,
  FileText,
  Shield,
  ShieldAlert,
  Rocket,
  GitBranch,
  Network,
  Inbox,
} from 'lucide-react'

export type RouteStatus = 'active' | 'beta' | 'coming_soon' | 'disabled'

export interface NavRoute {
  label: string
  path: string
  icon: LucideIcon
  section: 'core' | 'agents' | 'operations' | 'performance' | 'enterprise' | 'observability' | 'compliance' | 'advanced' | 'developers'
  status: RouteStatus
  featureFlag?: string
  description: string
  hidden?: boolean
}

export const navConfig: NavRoute[] = [
  // ── Core ──────────────────────────────────────────
  {
    label: 'Hub',
    path: '/',
    icon: LayoutDashboard,
    section: 'core',
    status: 'active',
    description: 'Painel central de controle do sistema.',
  },
  {
    label: 'Clientes',
    path: '/clients',
    icon: Users,
    section: 'core',
    status: 'active',
    description: 'Gestão de contas, tenants e dados principais de clientes.',
  },
  {
    label: 'Modelos',
    path: '/models',
    icon: Box,
    section: 'core',
    status: 'active',
    description: 'Catálogo de modelos, aliases, defaults e controles operacionais.',
  },
  {
    label: 'Backends',
    path: '/backends',
    icon: Server,
    section: 'core',
    status: 'active',
    description: 'Integrações de inferência, providers e estado do backend.',
  },
  {
    label: 'Plugins',
    path: '/plugins',
    icon: Zap,
    section: 'core',
    status: 'active',
    description: 'Marketplace de plugins e extensões do sistema.',
  },
  {
    label: 'SaaS',
    path: '/saas',
    icon: Cloud,
    section: 'core',
    status: 'active',
    description: 'Managed control plane para deployments SaaS.',
    featureFlag: 'MANAGED_CONTROL_PLANE_ENABLED',
  },
  {
    label: 'API Keys',
    path: '/api-keys',
    icon: Key,
    section: 'core',
    status: 'active',
    description: 'Emissão, rotação e governança de credenciais.',
  },
  {
    label: 'Billing',
    path: '/billing',
    icon: Wallet,
    section: 'core',
    status: 'active',
    description: 'Planos, pricing e cobrança.',
  },
  {
    label: 'Uso',
    path: '/usage',
    icon: TrendingUp,
    section: 'core',
    status: 'active',
    description: 'Consumo por cliente e métricas agregadas.',
  },

  // ── Agentic Platform ──────────────────────────────
  {
    label: 'Agentes',
    path: '/agents',
    icon: Bot,
    section: 'agents',
    status: 'active',
    description: 'Agentes IA, registry, runs, tools e políticas.',
  },
  {
    label: 'Agent Studio',
    path: '/agents/studio',
    icon: Wrench,
    section: 'agents',
    status: 'active',
    description: 'Visual flow editor para construir e depurar agentes.',
    featureFlag: 'AGENT_STUDIO_ENABLED',
  },
  {
    label: 'Analytics',
    path: '/agents/analytics',
    icon: BarChart3,
    section: 'agents',
    status: 'active',
    description: 'Métricas de latência, custo e uso de ferramentas dos agentes.',
  },
  {
    label: 'Approval Portal',
    path: '/agents/approvals',
    icon: Inbox,
    section: 'agents',
    status: 'active',
    description: 'Portal de aprovação humana para ações de agentes.',
    featureFlag: 'AGENT_APPROVAL_PORTAL_ENABLED',
  },
  {
    label: 'Chat Colaborativo',
    path: '/agents/chat',
    icon: MessageSquare,
    section: 'agents',
    status: 'active',
    description: 'Chat colaborativo com menções de agentes em tempo real.',
    featureFlag: 'COLLAB_CHAT_ENABLED',
  },
  {
    label: 'Promotion',
    path: '/agents/promotion',
    icon: Rocket,
    section: 'agents',
    status: 'beta',
    description: 'Promoção de agentes entre ambientes.',
  },
  {
    label: 'Lineage',
    path: '/agents/lineage',
    icon: GitBranch,
    section: 'agents',
    status: 'beta',
    description: 'Histórico de versões e linhagem de agentes.',
  },

  // ── Operations ────────────────────────────────────
  {
    label: 'Operações',
    path: '/operations',
    icon: Activity,
    section: 'operations',
    status: 'active',
    description: 'Overview operacional, nós de runtime, readiness e remediação.',
  },

  // ── Developers ────────────────────────────────────
  {
    label: 'Web IDE',
    path: '/ide',
    icon: Code2,
    section: 'developers',
    status: 'active',
    description: 'IDE web para edição de agentes, plugins e manifests.',
    featureFlag: 'WEB_IDE_ENABLED',
  },
  {
    label: 'Developer Portal',
    path: '/developers',
    icon: Key,
    section: 'developers',
    status: 'active',
    description: 'Portal do desenvolvedor com API keys, CLI e templates.',
  },
  {
    label: 'Bundles',
    path: '/developers/bundles',
    icon: Box,
    section: 'developers',
    status: 'active',
    description: 'Criação, assinatura e publicação de pacotes de agentes.',
  },
  {
    label: 'Prompts',
    path: '/prompts',
    icon: FileText,
    section: 'developers',
    status: 'active',
    description: 'Criação, versionamento e gestão de templates de prompts.',
    featureFlag: 'PROMPT_TEMPLATES_ENABLED',
  },

  // ── Compliance ────────────────────────────────────
  {
    label: 'Compliance',
    path: '/compliance',
    icon: ShieldCheck,
    section: 'compliance',
    status: 'active',
    description: 'Preparação para SOC 2 e ISO 27001 com evidências auditáveis.',
  },

  // ── Advanced ──────────────────────────────────────
  {
    label: 'Multi-Cluster',
    path: '/multicluster',
    icon: Network,
    section: 'advanced',
    status: 'coming_soon',
    description: 'Gestão multi-cluster e failover orquestrado.',
  },
  {
    label: 'Chaos Engineering',
    path: '/chaos',
    icon: FlaskConical,
    section: 'advanced',
    status: 'coming_soon',
    description: 'Injeção controlada de falhas para validar resiliência.',
  },
]

export const sectionMeta: Record<string, { label: string; icon: LucideIcon }> = {
  core: { label: 'Core', icon: LayoutDashboard },
  agents: { label: 'Agentic Platform', icon: Bot },
  operations: { label: 'Operations', icon: Activity },
  performance: { label: 'Performance', icon: TrendingUp },
  enterprise: { label: 'Enterprise', icon: Briefcase },
  observability: { label: 'Observability', icon: Monitor },
  compliance: { label: 'Compliance', icon: ShieldCheck },
  advanced: { label: 'Advanced', icon: Network },
  developers: { label: 'Developers', icon: Code2 },
}
