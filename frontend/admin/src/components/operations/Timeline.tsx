interface TimelineEvent {
  id: string
  title: string
  description: string
  timestamp: string
  status: 'info' | 'success' | 'warning' | 'error'
}

interface TimelineProps {
  events: TimelineEvent[]
}

export default function Timeline({ events }: TimelineProps) {
  const statusColors = {
    info: 'bg-slate-400',
    success: 'bg-green-500',
    warning: 'bg-amber-500',
    error: 'bg-rose-500',
  }

  return (
    <div className="relative space-y-8 before:absolute before:inset-0 before:ml-5 before:-translate-x-px before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-slate-200 before:to-transparent">
      {events.map((event) => (
        <div key={event.id} className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
          <div className="flex items-center justify-center w-10 h-10 rounded-full border border-white bg-slate-50 shadow shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 z-10">
            <div className={`w-3 h-3 rounded-full ${statusColors[event.status]}`}></div>
          </div>
          <div className="w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
            <div className="flex items-center justify-between space-x-2 mb-1">
              <div className="font-bold text-slate-900">{event.title}</div>
              <time className="font-mono text-[10px] text-slate-400">{event.timestamp}</time>
            </div>
            <div className="text-slate-500 text-sm leading-relaxed">{event.description}</div>
          </div>
        </div>
      ))}
    </div>
  )
}
