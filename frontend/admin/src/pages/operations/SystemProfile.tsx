import { useQuery } from '@tanstack/react-query'
import { CheckCircle2, CircleOff, Layers3, Loader2 } from 'lucide-react'
import api from '../../lib/api'
import { PageHeader } from '../../components/layout/PageHeader'

interface ProfileSummary {
  profile: string
  description: string
  active_features: string[]
  disabled_features: string[]
}

function featureLabel(feature: string): string {
  return feature
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

function FeatureList({
  title,
  features,
  enabled,
}: {
  title: string
  features: string[]
  enabled: boolean
}) {
  const Icon = enabled ? CheckCircle2 : CircleOff

  return (
    <section className="bg-card border border-border rounded-3xl p-6 shadow-sm">
      <div className="flex items-center justify-between mb-5">
        <h2 className="text-lg font-black text-foreground">{title}</h2>
        <span className="px-2.5 py-1 rounded-full bg-secondary text-xs font-bold text-muted-foreground">
          {features.length}
        </span>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {features.map(feature => (
          <div
            key={feature}
            className="flex items-center gap-3 p-3 rounded-xl border border-border bg-background"
          >
            <Icon className={`w-4 h-4 ${enabled ? 'text-primary' : 'text-muted-foreground'}`} />
            <span className="text-sm font-semibold text-foreground">{featureLabel(feature)}</span>
          </div>
        ))}
      </div>
    </section>
  )
}

export default function SystemProfile() {
  const { data, isLoading, isError } = useQuery<ProfileSummary>({
    queryKey: ['system-profile'],
    queryFn: async () => {
      const response = await api.get<ProfileSummary>('/api/system/profile')
      return response.data
    },
  })

  if (isLoading) {
    return (
      <div className="h-[50vh] flex items-center justify-center gap-3 text-muted-foreground">
        <Loader2 className="w-5 h-5 animate-spin" />
        Carregando perfil operacional...
      </div>
    )
  }

  if (isError || !data) {
    return <div className="p-8 text-center text-destructive">Não foi possível carregar o perfil operacional.</div>
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Perfil Operacional"
        subtitle={data.description}
        icon={<Layers3 className="w-5 h-5" />}
        badge={data.profile.toUpperCase()}
        badgeVariant="beta"
      />

      <div className="bg-foreground text-background rounded-3xl p-8 shadow-xl">
        <p className="text-xs font-bold uppercase tracking-widest opacity-70 mb-2">Perfil atual</p>
        <p className="text-4xl font-black capitalize">{data.profile}</p>
        <p className="mt-3 text-sm opacity-80">
          {data.active_features.length} recursos ativos e {data.disabled_features.length} desabilitados.
        </p>
      </div>

      <FeatureList title="Recursos ativos" features={data.active_features} enabled />
      <FeatureList title="Recursos desabilitados" features={data.disabled_features} enabled={false} />
    </div>
  )
}
