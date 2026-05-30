import { Shield, ArrowRight, Construction } from 'lucide-react'
import { Link } from 'react-router-dom'
import { navRoutes, hubCardMeta, isRouteDisabled } from '../navigation/navConfig'
import { PageHeader } from '../components/layout/PageHeader'

interface HubCard {
  title: string
  href: string
  icon: React.ReactNode
  badge: string
  description: string
  disabled: boolean
}

function buildHubCards(): HubCard[] {
  const cards: HubCard[] = []

  for (const route of navRoutes) {
    if (route.path === '/' || route.hidden || route.sidebarHidden) continue
    const meta = hubCardMeta[route.path]
    if (!meta) continue

    const Icon = route.icon
    cards.push({
      title: route.label,
      href: route.path,
      icon: <Icon className="w-6 h-6" />,
      badge: meta.badge,
      description: meta.description,
      disabled: isRouteDisabled(route.status),
    })
  }

  return cards
}

export default function Hub() {
  const cards = buildHubCards()

  return (
    <div className="space-y-12">
      <PageHeader
        title="Admin Hub"
        subtitle="Plataforma de controle para inferencia de LLMs em escala. Gerencie clientes, modelos, agentes e custos em um unico painel."
        icon={<Shield className="w-5 h-5" />}
        badge="V2"
        badgeVariant="beta"
      />

      <section aria-label="Secoes Administrativas">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6">
          {cards.map(item => (
            <Link
              key={item.title}
              to={item.disabled ? '#' : item.href}
              onClick={e => item.disabled && e.preventDefault()}
              className={`
                group block p-6 bg-card border border-border rounded-2xl
                transition-all duration-200
                focus-visible:ring-2 focus-visible:ring-primary outline-none active:scale-[0.98]
                ${item.disabled
                  ? 'opacity-60 cursor-not-allowed'
                  : 'hover:shadow-lg hover:border-primary/30'}
              `}
            >
              <div className="flex justify-between items-start mb-4">
                <div className={`p-3 rounded-xl transition-all duration-200 ${
                  item.disabled
                    ? 'bg-muted text-muted-foreground'
                    : 'bg-secondary text-foreground group-hover:bg-primary group-hover:text-white'
                }`}>
                  {item.icon}
                </div>
                <div className="flex items-center gap-2">
                  {item.disabled && (
                    <span className="flex items-center gap-1 px-2 py-1 bg-muted text-muted-foreground text-[10px] font-bold rounded-full uppercase tracking-widest border border-border">
                      <Construction size={10} />
                      Soon
                    </span>
                  )}
                  <span className={`px-2.5 py-1 text-[10px] font-bold rounded-full uppercase tracking-widest border transition-colors ${
                    item.disabled
                      ? 'bg-muted text-muted-foreground border-border'
                      : 'bg-secondary text-muted-foreground border-border group-hover:border-primary/20'
                  }`}>
                    {item.badge}
                  </span>
                </div>
              </div>
              <h2 className={`text-lg font-bold mb-2 transition-colors ${
                item.disabled ? 'text-muted-foreground' : 'text-foreground group-hover:text-primary'
              }`}>{item.title}</h2>
              <p className="text-muted-foreground text-sm leading-relaxed mb-6 line-clamp-2">
                {item.description}
              </p>
              <div className={`flex items-center justify-between transition-colors pt-2 border-t ${
                item.disabled
                  ? 'text-muted-foreground/50 border-border'
                  : 'text-muted-foreground group-hover:text-primary group-hover:border-primary/10 border-border'
              }`}>
                <span className="text-[10px] font-mono opacity-60">/admin{item.href}</span>
                <strong className="text-xs flex items-center gap-1 font-bold uppercase tracking-tighter">
                  {item.disabled ? 'Em Breve' : <>Ver Mais <ArrowRight className="w-4 h-4" /></>}
                </strong>
              </div>
            </Link>
          ))}
        </div>
      </section>

      <footer className="pt-12 border-t border-border text-muted-foreground text-xs flex flex-col md:flex-row justify-between gap-4">
        <p>&copy; {new Date().getFullYear()} LLM Inference Stack &bull; Enterprise Edition</p>
        <p className="font-mono opacity-50">V2.0-REACT-STABLE</p>
      </footer>
    </div>
  )
}
