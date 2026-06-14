import type { ReactNode } from 'react'

export const inputClassName = 'rounded-2xl border border-border bg-background px-4 py-3 text-sm text-foreground outline-none focus:border-primary'

export function SectionCard({ title, subtitle, actions, children }: { title: string; subtitle?: string; actions?: ReactNode; children: ReactNode }) {
  return (
    <section className="rounded-3xl border border-border bg-card p-6 shadow-sm">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <div className="text-sm font-semibold text-foreground">{title}</div>
          {subtitle && <div className="mt-1 text-sm text-muted-foreground">{subtitle}</div>}
        </div>
        {actions}
      </div>
      {children}
    </section>
  )
}

export function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-border bg-card p-4 shadow-sm">
      <div className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">{label}</div>
      <div className="mt-2 text-2xl font-black text-foreground">{value}</div>
    </div>
  )
}

export function JsonPanel({ data, empty = 'Sem dados.' }: { data: unknown; empty?: string }) {
  const hasData =
    data !== null &&
    data !== undefined &&
    (!Array.isArray(data) || data.length > 0) &&
    (typeof data !== 'object' || Array.isArray(data) || Object.keys(data as Record<string, unknown>).length > 0)

  if (!hasData) {
    return <div className="rounded-2xl border border-dashed border-border p-8 text-center text-sm text-muted-foreground">{empty}</div>
  }

  return (
    <pre className="max-h-[520px] overflow-auto rounded-2xl bg-slate-950 p-4 text-xs text-slate-100">
      {JSON.stringify(data, null, 2)}
    </pre>
  )
}
