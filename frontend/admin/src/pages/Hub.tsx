import { Users, Key, Box, Cpu, Wallet, Activity, Shield, FileText, Settings, ArrowRight } from 'lucide-react'
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
    title: "Configurações",
    href: "/settings",
    icon: <Settings className="w-6 h-6" />,
    badge: "System",
    description: "Configuração geral, parâmetros do sistema e controles administrativos."
  }
];

export default function Hub() {
  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <header className="mb-12">
        <div className="flex items-center gap-2 text-teal-600 font-bold uppercase tracking-wider text-sm mb-4">
          <Shield className="w-4 h-4" />
          Admin Hub
        </div>
        <h1 className="text-5xl font-extrabold tracking-tight text-slate-900 mb-4">
          Infraestrutura <span className="text-teal-600">Global</span>
        </h1>
        <p className="text-lg text-slate-600 max-w-2xl leading-relaxed">
          Plataforma de controle para inferência de LLMs em escala. 
          Gerencie clientes, modelos e custos em um único painel.
        </p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {adminSections.map((item) => (
          <Link 
            key={item.title} 
            to={item.href}
            className="group block p-6 bg-white border border-slate-200 rounded-2xl shadow-sm hover:shadow-md hover:border-teal-500 transition-all"
          >
            <div className="flex justify-between items-start mb-4">
              <div className="p-3 bg-slate-50 text-slate-700 rounded-xl group-hover:bg-teal-50 group-hover:text-teal-600 transition-colors">
                {item.icon}
              </div>
              <span className="px-3 py-1 bg-slate-100 text-slate-600 text-xs font-bold rounded-full uppercase tracking-wider">
                {item.badge}
              </span>
            </div>
            <h3 className="text-xl font-bold text-slate-900 mb-2 group-hover:text-teal-700">{item.title}</h3>
            <p className="text-slate-500 text-sm leading-relaxed mb-6">
              {item.description}
            </p>
            <div className="flex items-center justify-between text-slate-400 group-hover:text-teal-600 transition-colors">
              <span className="text-xs font-mono">/admin{item.href}</span>
              <strong className="text-sm flex items-center gap-1">
                Acessar <ArrowRight className="w-4 h-4" />
              </strong>
            </div>
          </Link>
        ))}
      </div>

      <footer className="mt-20 pt-8 border-t border-slate-200 text-slate-400 text-sm flex justify-between">
        <p>© {new Date().getFullYear()} LLM Inference Stack • Enterprise Edition</p>
        <p className="font-mono text-xs">V2.0-REACT-STABLE</p>
      </footer>
    </div>
  )
}
