import { useState } from 'react'
import { Code2, Play, Terminal, Box, Shield, Loader2, Search, FileJson, AlertCircle } from 'lucide-react'
import api from '../../lib/api'
import { toast } from 'sonner'

export default function CodeInterpreterAdmin() {
  const [code, setCode] = useState('import math\nprint(f"PI is {math.pi}")\n# Test sandbox write\nwith open("test.txt", "w") as f:\n    f.write("sandbox-test")\nprint("File written successfully!")')
  const [runResult, setRunResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [runIdLookup, setRunIdLookup] = useState('')
  const [lookupResult, setRunLookupResult] = useState<any>(null)
  const [searching, setSearching] = useState(false)

  const handleRun = async () => {
    setLoading(true)
    try {
      const resp = await api.runCode({ code })
      setRunResult(resp)
      toast.success('Execução em sandbox concluída.')
    } catch (err: any) {
      toast.error(err?.message || 'Erro na execução da sandbox')
    } finally {
      setLoading(false)
    }
  }

  const handleLookup = async () => {
    if (!runIdLookup) return
    setSearching(true)
    try {
      const resp = await api.getCodeRun(runIdLookup)
      setRunLookupResult(resp)
      toast.success('Execução encontrada.')
    } catch (err: any) {
      toast.error('Execução não encontrada ou erro na API.')
      setRunLookupResult(null)
    } finally {
      setSearching(false)
    }
  }

  return (
    <div className="p-8 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-black text-foreground flex items-center gap-3">
            <Code2 className="w-8 h-8 text-primary" /> Code Interpreter Admin
          </h1>
          <p className="text-muted-foreground mt-1">Gestão de sandboxes de execução e inspeção de logs de agentes.</p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1 bg-amber-50 text-amber-700 rounded-lg text-xs font-bold border border-amber-100">
          <Shield className="w-3 h-3" /> Isolation: gVisor/Firecracker
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Left: Playground */}
        <div className="space-y-6">
          <div className="bg-card border border-border rounded-3xl overflow-hidden shadow-sm">
            <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-secondary/5">
              <h3 className="font-black flex items-center gap-2">
                <Terminal className="w-4 h-4 text-blue-500" /> Admin Playground
              </h3>
              <button 
                onClick={handleRun}
                disabled={loading}
                className="btn btn-primary py-1.5 px-4 text-xs font-black flex items-center gap-2"
              >
                {loading ? <Loader2 className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3 fill-current" />}
                Run in Sandbox
              </button>
            </div>
            <div className="p-0">
               <textarea
                 value={code}
                 onChange={e => setCode(e.target.value)}
                 className="w-full h-64 p-6 bg-slate-950 text-emerald-400 font-mono text-sm outline-none resize-none border-none"
                 spellCheck={false}
               />
            </div>
          </div>

          <div className="bg-card border border-border rounded-3xl overflow-hidden">
             <div className="px-6 py-4 border-b border-border bg-secondary/5 font-black text-xs uppercase tracking-widest">
                Result Output
             </div>
             <div className="p-6 bg-slate-50 min-h-[150px] font-mono text-xs overflow-auto max-h-[300px]">
                {runResult ? (
                   <div className="space-y-4">
                      {runResult.stdout && <div className="text-slate-900 whitespace-pre-wrap">{runResult.stdout}</div>}
                      {runResult.stderr && <div className="text-red-500 whitespace-pre-wrap">{runResult.stderr}</div>}
                      <div className="pt-4 border-t border-slate-200 flex items-center gap-4 text-slate-400">
                         <span>Exit Code: <b className="text-slate-600">{runResult.exit_code}</b></span>
                         <span>Time: <b className="text-slate-600">{runResult.execution_time_ms}ms</b></span>
                      </div>
                   </div>
                ) : (
                   <span className="text-slate-400 italic">Aguardando execução...</span>
                )}
             </div>
          </div>
        </div>

        {/* Right: Inspector */}
        <div className="space-y-6">
           <div className="bg-card border border-border rounded-3xl p-6 space-y-4 shadow-sm">
              <h3 className="font-black flex items-center gap-2">
                 <Search className="w-4 h-4 text-primary" /> Run Inspector
              </h3>
              <p className="text-xs text-muted-foreground">Inspeccione execuções passadas realizadas por agentes via UUID.</p>
              <div className="flex gap-2">
                 <input 
                   type="text" 
                   placeholder="Enter Run ID (UUID)..." 
                   className="input-field py-2 text-sm font-mono"
                   value={runIdLookup}
                   onChange={e => setRunIdLookup(e.target.value)}
                 />
                 <button 
                   onClick={handleLookup}
                   disabled={searching || !runIdLookup}
                   className="p-2 bg-secondary rounded-xl hover:bg-secondary/80 transition-colors disabled:opacity-50"
                 >
                    {searching ? <Loader2 className="w-5 h-5 animate-spin" /> : <Search className="w-5 h-5" />}
                 </button>
              </div>
           </div>

           {lookupResult && (
              <div className="bg-white border border-border rounded-3xl overflow-hidden animate-in fade-in slide-in-from-right-4">
                 <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-primary/5">
                    <span className="font-black text-xs uppercase text-primary">Run Details</span>
                    <FileJson className="w-4 h-4 text-primary" />
                 </div>
                 <div className="p-6 space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                       <div className="p-3 rounded-2xl bg-secondary/20">
                          <div className="text-[10px] uppercase font-black text-muted-foreground">Agent ID</div>
                          <div className="text-xs font-mono truncate">{lookupResult.agent_id || 'N/A'}</div>
                       </div>
                       <div className="p-3 rounded-2xl bg-secondary/20">
                          <div className="text-[10px] uppercase font-black text-muted-foreground">Created At</div>
                          <div className="text-xs font-mono">{new Date(lookupResult.created_at).toLocaleString()}</div>
                       </div>
                    </div>
                    <div className="space-y-2">
                       <div className="text-[10px] uppercase font-black text-muted-foreground">Execution Log</div>
                       <div className="p-4 bg-slate-900 rounded-2xl text-[11px] font-mono text-slate-300 max-h-40 overflow-y-auto">
                          {lookupResult.stdout || lookupResult.stderr || 'No logs available.'}
                       </div>
                    </div>
                 </div>
              </div>
           )}

           <div className="p-6 rounded-3xl border border-border bg-card space-y-4">
              <h3 className="font-black flex items-center gap-2">
                 <Box className="w-4 h-4 text-emerald-500" /> Runtime Policies
              </h3>
              <div className="space-y-3">
                 <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">Max CPU Time</span>
                    <span className="font-black">30.0s</span>
                 </div>
                 <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">Max Memory</span>
                    <span className="font-black">512 MB</span>
                 </div>
                 <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">Network Access</span>
                    <span className="font-black text-red-500">BLOCKED (Airgap)</span>
                 </div>
                 <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">Filesystem Persistency</span>
                    <span className="font-black text-amber-500">EPHEMERAL</span>
                 </div>
              </div>
           </div>

           <div className="p-4 rounded-2xl bg-amber-50 border border-amber-100 flex gap-3">
              <AlertCircle className="w-5 h-5 text-amber-500 shrink-0" />
              <p className="text-[11px] text-amber-700 leading-relaxed font-medium">
                 Atenção: A execução de código via admin playground é real e utiliza os mesmos recursos de isolamento dos agentes. O abuso pode resultar em throttling do node de execução.
              </p>
           </div>
        </div>
      </div>
    </div>
  )
}
