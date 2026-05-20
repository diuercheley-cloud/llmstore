import { Users, Key, Box, Cpu, Wallet, Activity, Shield, FileText, Settings, ArrowRight, Zap, Briefcase, Monitor, Network, FlaskConical, Gavel } from 'lucide-react'
import { Link } from 'react-router-dom'

const adminSections = [
  {
    title: "Clientes",
    href: "/clients",
    icon: <Users className="w-6 h-6" />,
    badge: "Core",
    description: "Gestão de contas, tenants e dados principais de clientes."
  },
  {
    title: "API Keys",
    href: "/api-keys",
    icon: <Key className="w-6 h-6" />,
    badge: "Core",
    description: "Emissão, rotação, revogação e governança de credenciais."
  },
  {
    title: "Modelos",
    href: "/models",
    icon: <Box className="w-6 h-6" />,
    badge: "Runtime",
    description: "Catálogo de modelos, aliases, defaults e controles operacionais."
  },
  {
    title: "Backends / Providers",
    href: "/backends",
    icon: <Cpu className="w-6 h-6" />,
    badge: "Runtime",
    description: "Integrações de inferência, providers e estado do backend."
  },
  {
    title: "Billing",
    href: "/billing",
    icon: <Wallet className="w-6 h-6" />,
    badge: "Finance",
    description: "Planos, pricing, cobrança local e políticas financeiras."
  },
  {
    title: "Uso",
    href: "/usage",
    icon: <Activity className="w-6 h-6" />,
    badge: "Analytics",
    description: "Consumo por cliente, tokens, quotas e métricas agregadas."
  },
  {
    title: "RAG",
    href: "/rag",
    icon: <FileText className="w-6 h-6" />,
    badge: "Data",
    description: "Vaults, documentos, recibos e controles da camada RAG."
  },
  {
    title: "Segurança / Auditoria",
    href: "/security",
    icon: <Shield className="w-6 h-6" />,
    badge: "Risk",
    description: "Auditoria, receipts, eventos de segurança e verificações operacionais."
  },
  {
    title: "Relatórios",
    href: "/reports",
    icon: <FileText className="w-6 h-6" />,
    badge: "Ops",
    description: "Relatórios executivos, exportações e material operacional."
  },
  {
    title: "Operações",
    href: "/operations",
    icon: <Activity className="w-6 h-6" />,
    badge: "Ops",
    description: "Overview operacional, nós de runtime, readiness e remediação."
  },
  {
    title: "Performance",
    href: "/performance",
    icon: <Zap className="w-6 h-6" />,
    badge: "Tuning",
    description: "Benchmark de runtime, recomendações de IA e perfis de otimização."
  },
  {
    title: "Enterprise Onboarding",
    href: "/enterprise/onboarding",
    icon: <Briefcase className="w-6 h-6" />,
    badge: "Success",
    description: "Gestão de pilotos, checklists enterprise e relatórios de handover."
  },
  {
    title: "Observabilidade",
    href: "/observability",
    icon: <Monitor className="w-6 h-6" />,
    badge: "Advanced",
    description: "Dashboards Grafana, orçamentos de erro (SLO) e timeline de incidentes."
  },
  {
    title: "Monitoramento Live",
    href: "/observability/realtime",
    icon: <Activity className="w-6 h-6" />,
    badge: "Real-time",
    description: "Métricas de sistema, fila e latência em tempo real via SSE."
  },
  {
    title: "Multi-Cluster",
    href: "/multicluster",
    icon: <Network className="w-6 h-6" />,
    badge: "Enterprise",
    description: "Gestão multi-cluster, sincronização de config e failover orquestrado."
  },
  {
    title: "Chaos Engineering",
    href: "/chaos",
    icon: <FlaskConical className="w-6 h-6" />,
    badge: "Experimental",
    description: "Injeção controlada de falhas para validar resiliência e recuperação."
  },
  {
    title: "Compliance Readiness",
    href: "/compliance",
    icon: <Gavel className="w-6 h-6" />,
    badge: "Enterprise",
    description: "Preparação para SOC 2 e ISO 27001 com evidências auditáveis."
  },
  {
    title: "Configurações",
    href: "/settings",
    icon: <Settings className="w-6 h-6" />,
    badge: "System",
    description: "Configuração geral, parâmetros do sistema e controles administrativos."
  }
];

export default function Hub() {
  return (
    <div className="space-y-12">
      <header>
        <div className="flex items-center gap-2 text-primary font-bold uppercase tracking-wider text-xs md:text-sm mb-4" role="status">
          <Shield className="w-4 h-4" aria-hidden="true" />
          Admin Hub
        </div>
        <h1 className="text-3xl md:text-5xl font-extrabold tracking-tight text-foreground mb-4">
          Infraestrutura <span className="text-primary">Global</span>
        </h1>
        <p className="text-sm md:text-lg text-muted-foreground max-w-2xl leading-relaxed">
          Plataforma de controle para inferência de LLMs em escala. 
          Gerencie clientes, modelos e custos em um único painel.
        </p>
      </header>

      <section aria-label="Seções Administrativas">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6">
          {adminSections.map((item) => (
            <Link 
              key={item.title} 
              to={item.href}
              className="group block p-6 bg-card border border-border rounded-2xl shadow-sm hover:shadow-lg hover:border-primary/50 transition-all focus-visible:ring-2 focus-visible:ring-primary outline-none active:scale-[0.98]"
              aria-labelledby={`title-${item.title.replace(/\s+/g, '-').toLowerCase()}`}
            >
              <div className="flex justify-between items-start mb-4">
                <div className="p-3 bg-secondary text-foreground rounded-xl group-hover:bg-primary group-hover:text-white transition-all duration-300 shadow-sm" aria-hidden="true">
                  {item.icon}
                </div>
                <span className="px-2.5 py-1 bg-secondary text-muted-foreground text-[10px] font-black rounded-full uppercase tracking-widest border border-border group-hover:border-primary/20 transition-colors">
                  {item.badge}
                </span>
              </div>
              <h2 id={`title-${item.title.replace(/\s+/g, '-').toLowerCase()}`} className="text-lg md:text-xl font-bold text-foreground mb-2 group-hover:text-primary transition-colors">{item.title}</h2>
              <p className="text-muted-foreground text-xs md:text-sm leading-relaxed mb-6 line-clamp-2 md:line-clamp-none">
                {item.description}
              </p>
              <div className="flex items-center justify-between text-muted-foreground group-hover:text-primary transition-colors pt-2 border-t border-border group-hover:border-primary/10">
                <span className="text-[10px] font-mono opacity-60">/admin{item.href}</span>
                <strong className="text-xs flex items-center gap-1 font-black uppercase tracking-tighter">
                  Ver Mais <ArrowRight className="w-4 h-4" aria-hidden="true" />
                </strong>
              </div>
            </Link>
          ))}
        </div>
      </section>

      <footer className="pt-12 border-t border-border text-muted-foreground text-[10px] md:text-xs flex flex-col md:flex-row justify-between gap-4">
        <p>© {new Date().getFullYear()} LLM Inference Stack • Enterprise Edition</p>
        <p className="font-mono opacity-50">V2.0-REACT-STABLE</p>
      </footer>
    </div>
  )
}
