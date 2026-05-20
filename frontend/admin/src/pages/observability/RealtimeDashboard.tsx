import { useEffect, useState, useRef } from "react"
import { 
  Activity, 
  Cpu, 
  Database, 
  ShieldAlert, 
  Zap, 
  Clock, 
  Thermometer, 
  AlertTriangle,
  CheckCircle2,
  XCircle,
  BarChart3
} from "lucide-react"
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer, 
  AreaChart, 
  Area 
} from "recharts"

interface Metrics {
  system: {
    cpu: number
    ram: number
    gpus: Array<{
      utilization: number
      memory_used: number
      memory_total: number
      temperature: number
    }>
  }
  inference: {
    queue: {
      depth: number
      active_requests: number
      avg_wait_time_ms: number
    }
  }
  latency: {
    p50: number
    p95: number
    p99: number
  }
  backends: Array<{
    id: string
    name: string
    provider: string
    ok: boolean
    latency_ms: number
  }>
  security: Array<{
    id: string
    type: string
    severity: string
    message: string
    timestamp: string
  }>
  timestamp: string
}

const MAX_DATA_POINTS = 30

export default function RealtimeDashboard() {
  const [data, setData] = useState<Metrics | null>(null)
  const [history, setHistory] = useState<any[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const eventSourceRef = useRef<EventSource | null>(null)

  useEffect(() => {
    const connect = () => {
      // Note: EventSource doesn't support custom headers (X-Admin-Token).
      // In a real scenario, we might use a cookie or a signed URL / query param.
      // For this implementation, I'll assume the SSE endpoint is accessible.
      const es = new EventSource("/admin/metrics/stream")
      
      es.onopen = () => setIsConnected(true)
      es.onerror = () => {
        setIsConnected(false)
        es.close()
        // Reconnect after 5s
        setTimeout(connect, 5000)
      }

      es.onmessage = (event) => {
        const payload: Metrics = JSON.parse(event.data)
        setData(payload)
        
        setHistory(prev => {
          const timeStr = new Date(payload.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
          const newPoint = {
            time: timeStr,
            cpu: payload.system.cpu,
            ram: payload.system.ram,
            gpu: payload.system.gpus[0]?.utilization || 0,
            depth: payload.inference.queue.depth,
            p50: payload.latency.p50,
            p95: payload.latency.p95
          }
          const updated = [...prev, newPoint]
          if (updated.length > MAX_DATA_POINTS) return updated.slice(1)
          return updated
        })
      }

      eventSourceRef.current = es
    }

    connect()
    return () => eventSourceRef.current?.close()
  }, [])

  if (!data) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
        <p className="text-muted-foreground font-medium">Conectando ao stream de métricas...</p>
      </div>
    )
  }

  const thresholds = {
    cpu: 80,
    ram: 90,
    gpu: 85,
    temp: 80,
    queue: 10
  }

  const MetricCard = ({ title, value, unit, icon: Icon, color, trend, alert }: any) => (
    <div className={`bg-card border ${alert ? 'border-destructive animate-pulse' : 'border-border'} p-6 rounded-3xl shadow-sm transition-all`}>
      <div className="flex justify-between items-start mb-4">
        <div className={`p-3 rounded-2xl ${color}`}>
          <Icon className="w-6 h-6" />
        </div>
        {alert && <AlertTriangle className="w-5 h-5 text-destructive" />}
      </div>
      <div className="text-xs font-bold text-muted-foreground uppercase tracking-widest mb-1">{title}</div>
      <div className="flex items-baseline gap-1">
        <span className="text-3xl font-black text-foreground">{value}</span>
        <span className="text-sm font-bold text-muted-foreground">{unit}</span>
      </div>
    </div>
  )

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <header className="mb-8 flex justify-between items-end">
        <div>
          <div className="flex items-center gap-2 text-primary font-bold uppercase tracking-wider text-sm mb-2">
            <Activity className="w-4 h-4" />
            Live Monitor
          </div>
          <h1 className="text-4xl font-extrabold tracking-tight text-foreground">Real-time Performance</h1>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 bg-secondary rounded-full border border-border">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-primary animate-pulse' : 'bg-destructive'}`}></div>
          <span className="text-[10px] font-black uppercase tracking-wider">{isConnected ? 'Stream Active' : 'Disconnected'}</span>
        </div>
      </header>

      {/* Primary Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <MetricCard 
          title="CPU Usage" 
          value={data.system.cpu.toFixed(1)} 
          unit="%" 
          icon={Cpu} 
          color="bg-blue-500/10 text-blue-500" 
          alert={data.system.cpu > thresholds.cpu}
        />
        <MetricCard 
          title="RAM Usage" 
          value={data.system.ram.toFixed(1)} 
          unit="%" 
          icon={Database} 
          color="bg-purple-500/10 text-purple-500" 
          alert={data.system.ram > thresholds.ram}
        />
        <MetricCard 
          title="GPU Load" 
          value={data.system.gpus[0]?.utilization.toFixed(1) || "0.0"} 
          unit="%" 
          icon={Zap} 
          color="bg-yellow-500/10 text-yellow-500" 
          alert={data.system.gpus[0]?.utilization > thresholds.gpu}
        />
        <MetricCard 
          title="GPU Temp" 
          value={data.system.gpus[0]?.temperature.toFixed(0) || "0"} 
          unit="°C" 
          icon={Thermometer} 
          color="bg-rose-500/10 text-rose-500" 
          alert={data.system.gpus[0]?.temperature > thresholds.temp}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">
        {/* System Load Chart */}
        <div className="lg:col-span-2 bg-card border border-border rounded-[2rem] p-8 shadow-sm">
          <h2 className="text-xl font-bold text-foreground mb-6 flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-primary" />
            System Resource History
          </h2>
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={history}>
                <defs>
                  <linearGradient id="colorCpu" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--color-primary)" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="var(--color-primary)" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" vertical={false} />
                <XAxis dataKey="time" stroke="#64748b" fontSize={10} tickLine={false} axisLine={false} />
                <YAxis stroke="#64748b" fontSize={10} tickLine={false} axisLine={false} unit="%" />
                <Tooltip 
                  contentStyle={{ backgroundColor: 'var(--color-card)', border: '1px solid var(--color-border)', borderRadius: '1rem' }}
                  itemStyle={{ fontWeight: 'bold' }}
                />
                <Area type="monotone" dataKey="cpu" stroke="var(--color-primary)" fillOpacity={1} fill="url(#colorCpu)" strokeWidth={3} />
                <Area type="monotone" dataKey="gpu" stroke="#eab308" fillOpacity={0} strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Inference Queue */}
        <div className="bg-card border border-border rounded-[2rem] p-8 shadow-sm">
          <h2 className="text-xl font-bold text-foreground mb-6 flex items-center gap-2">
            <Clock className="w-5 h-5 text-primary" />
            Inference Queue
          </h2>
          <div className="space-y-6">
            <div className="flex justify-between items-center p-4 bg-secondary rounded-2xl border border-border">
              <span className="text-sm font-bold text-muted-foreground">Requests em Fila</span>
              <span className={`text-2xl font-black ${data.inference.queue.depth > thresholds.queue ? 'text-destructive' : 'text-foreground'}`}>
                {data.inference.queue.depth}
              </span>
            </div>
            <div className="flex justify-between items-center p-4 bg-secondary rounded-2xl border border-border">
              <span className="text-sm font-bold text-muted-foreground">Requests Ativos</span>
              <span className="text-2xl font-black text-primary">{data.inference.queue.active_requests}</span>
            </div>
            <div className="flex justify-between items-center p-4 bg-secondary rounded-2xl border border-border">
              <span className="text-sm font-bold text-muted-foreground">Espera Média</span>
              <span className="text-2xl font-black text-foreground">{data.inference.queue.avg_wait_time_ms.toFixed(0)}<span className="text-xs">ms</span></span>
            </div>
          </div>

          <div className="mt-8 pt-6 border-t border-border">
            <h3 className="text-xs font-black uppercase tracking-widest text-muted-foreground mb-4">Latência de Inferência</h3>
            <div className="grid grid-cols-3 gap-2">
              <div className="text-center">
                <div className="text-[10px] font-bold text-muted-foreground">P50</div>
                <div className="text-lg font-black">{data.latency.p50.toFixed(0)}ms</div>
              </div>
              <div className="text-center border-x border-border">
                <div className="text-[10px] font-bold text-muted-foreground">P95</div>
                <div className="text-lg font-black text-primary">{data.latency.p95.toFixed(0)}ms</div>
              </div>
              <div className="text-center">
                <div className="text-[10px] font-bold text-muted-foreground">P99</div>
                <div className="text-lg font-black text-yellow-500">{data.latency.p99.toFixed(0)}ms</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Data Planes Health */}
        <div className="bg-card border border-border rounded-[2rem] p-8 shadow-sm">
          <h2 className="text-xl font-bold text-foreground mb-6 flex items-center gap-2">
            <Database className="w-5 h-5 text-primary" />
            Data Planes Health
          </h2>
          <div className="space-y-4">
            {data.backends.map(backend => (
              <div key={backend.id} className="flex items-center justify-between p-4 bg-secondary/50 rounded-2xl border border-border">
                <div className="flex items-center gap-4">
                  <div className={`p-2 rounded-lg ${backend.ok ? 'bg-primary/10 text-primary' : 'bg-destructive/10 text-destructive'}`}>
                    {backend.ok ? <CheckCircle2 className="w-5 h-5" /> : <XCircle className="w-5 h-5" />}
                  </div>
                  <div>
                    <div className="font-bold text-foreground">{backend.name}</div>
                    <div className="text-[10px] font-black uppercase text-muted-foreground tracking-tighter">{backend.provider}</div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-black text-foreground">{backend.latency_ms.toFixed(0)}ms</div>
                  <div className={`text-[10px] font-bold ${backend.ok ? 'text-primary' : 'text-destructive'}`}>
                    {backend.ok ? 'HEALTHY' : 'UNSTABLE'}
                  </div>
                </div>
              </div>
            ))}
            {data.backends.length === 0 && (
              <p className="text-center text-muted-foreground py-8 italic">Nenhum backend ativo detectado.</p>
            )}
          </div>
        </div>

        {/* Security Events */}
        <div className="bg-card border border-border rounded-[2rem] p-8 shadow-sm">
          <h2 className="text-xl font-bold text-foreground mb-6 flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-destructive" />
            Security & Abuse Events
          </h2>
          <div className="space-y-3">
            {data.security.map(event => (
              <div key={event.id} className="p-4 bg-secondary/30 rounded-2xl border border-border group hover:border-destructive/30 transition-all">
                <div className="flex justify-between items-start mb-1">
                  <span className={`text-[10px] font-black px-2 py-0.5 rounded uppercase tracking-wider ${
                    event.severity === 'critical' ? 'bg-destructive text-white' : 'bg-yellow-500/20 text-yellow-600'
                  }`}>
                    {event.type}
                  </span>
                  <span className="text-[10px] font-bold text-muted-foreground">{new Date(event.timestamp).toLocaleTimeString()}</span>
                </div>
                <p className="text-sm font-medium text-foreground leading-tight">{event.message}</p>
              </div>
            ))}
            {data.security.length === 0 && (
              <div className="flex flex-col items-center justify-center py-12 text-muted-foreground opacity-50">
                <ShieldAlert className="w-12 h-12 mb-2" />
                <p className="font-bold">No threats detected</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
