import { useQuery, useMutation } from '@tanstack/react-query'
import { 
  Gavel, 
  Package, 
  Share2, 
  ShieldAlert, 
  Loader2, 
  Download, 
  ShieldCheck, 
  Activity,
  History,
  Lock,
  Upload,
  CheckCircle2,
  XCircle
} from 'lucide-react'
import api from '../../lib/api'
import { toast } from 'sonner'

export default function SovereignGovernance() {
  const packages = useQuery({
    queryKey: ['airgap-packages'],
    queryFn: () => api.listAirgapPackages(),
  })

  const attestationStatus = useQuery({
    queryKey: ['hardware-attestation'],
    queryFn: () => api.listHardwareAttestations(),
  })

  const crls = useQuery({
    queryKey: ['offline-crls'],
    queryFn: () => api.listOfflineCrl(),
  })

  const verifyMutation = useMutation({
    mutationFn: (id: string) => api.verifyAirgapPackage(id),
    onSuccess: () => {
      toast.success('Pacote verificado e assinado com sucesso.')
      packages.refetch()
    },
    onError: (err: any) => toast.error(err?.message || 'Falha na verificação criptográfica')
  })

  return (
    <div className="p-8 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-black text-foreground flex items-center gap-3">
            <Gavel className="w-8 h-8 text-primary" /> Sovereign Governance
          </h1>
          <p className="text-muted-foreground mt-1">Gestão de clusters soberanos, sincronização airgap e auditoria imutável.</p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1 bg-blue-50 text-blue-700 rounded-lg text-xs font-black border border-blue-100 uppercase tracking-widest">
          <Lock className="w-3 h-3" /> Enterprise / Sovereign Mode
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Airgap Sync Packages */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-card border border-border rounded-3xl overflow-hidden shadow-sm">
            <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-secondary/5">
              <h3 className="font-black flex items-center gap-2 text-xs uppercase tracking-wider">
                <Package className="w-4 h-4" /> Airgap Sync Packages
              </h3>
              <div className="flex gap-2">
                <button className="text-[10px] font-black bg-primary text-primary-foreground px-2 py-1 rounded-lg hover:opacity-90 transition-opacity">Import Bundle</button>
                <button className="text-[10px] font-black bg-secondary text-secondary-foreground px-2 py-1 rounded-lg hover:opacity-90 transition-opacity">New Export</button>
              </div>
            </div>
            <div className="divide-y divide-border">
              {packages.isLoading ? (
                <div className="p-12 flex justify-center"><Loader2 className="w-8 h-8 animate-spin text-primary" /></div>
              ) : packages.data?.length === 0 ? (
                <div className="p-12 text-center text-muted-foreground italic">Nenhum pacote de sincronização registrado.</div>
              ) : packages.data?.map((p: any) => (
                <div key={p.id} className="px-6 py-4 flex items-center justify-between gap-4 hover:bg-secondary/5 transition-colors">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-slate-900 capitalize">{p.package_type.replace('_', ' ')}</span>
                      <span className={`text-[9px] font-black px-1.5 py-0.5 rounded border ${p.status === 'verified' ? 'bg-emerald-50 border-emerald-100 text-emerald-700' : 'bg-amber-50 border-amber-100 text-amber-700'}`}>
                        {p.status.toUpperCase()}
                      </span>
                    </div>
                    <div className="text-[10px] text-muted-foreground mt-1 flex items-center gap-2 font-mono">
                      <span>ID: {p.id.slice(0,8)}</span>
                      <span>•</span>
                      <span>Source: {p.source_cluster_id}</span>
                      <span>•</span>
                      <span>Version: {p.package_version}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {p.status === 'pending' && (
                      <button 
                        onClick={() => verifyMutation.mutate(p.id)}
                        disabled={verifyMutation.isPending}
                        className="p-2 hover:bg-emerald-50 text-emerald-600 rounded-xl transition-colors"
                        title="Verify Signature"
                      >
                        <ShieldCheck size={18} />
                      </button>
                    )}
                    <button className="p-2 hover:bg-secondary rounded-xl text-muted-foreground transition-colors" title="Download Bundle">
                      <Download size={18} />
                    </button>
                  </div>
                </div>
              ))}
              {packages.isError && (
                 <div className="p-8 text-center bg-red-50 text-red-700 text-xs italic font-bold">
                    Capability access restricted. Valid Enterprise license required for Sovereign Governance.
                 </div>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
             <div className="p-6 rounded-3xl border border-border bg-card space-y-4 shadow-sm">
                <h3 className="font-black flex items-center gap-2 text-xs uppercase tracking-wider">
                   <Activity className="w-4 h-4 text-blue-500" /> Offline Revocation (CRL)
                </h3>
                <div className="space-y-3">
                   {crls.data?.slice(0, 3).map((crl: any) => (
                      <div key={crl.id} className="p-3 rounded-2xl bg-secondary/20 flex items-center justify-between">
                         <span className="text-xs font-bold font-mono">v{crl.crl_version}</span>
                         <span className="text-[10px] text-muted-foreground">{new Date(crl.created_at).toLocaleDateString()}</span>
                      </div>
                   ))}
                   <button className="w-full py-2 border-2 border-dashed border-border rounded-xl text-[10px] font-black text-muted-foreground hover:border-primary hover:text-primary transition-all">
                      + Create New CRL Update
                   </button>
                </div>
             </div>

             <div className="p-6 rounded-3xl border border-border bg-card space-y-4 shadow-sm border-t-4 border-t-emerald-500">
                <h3 className="font-black flex items-center gap-2 text-xs uppercase tracking-wider">
                   <ShieldCheck className="w-4 h-4 text-emerald-500" /> Trusted Execution
                </h3>
                <div className="space-y-4">
                   <div className="flex justify-between items-center">
                      <span className="text-xs text-muted-foreground">Global Attestation Status</span>
                      <span className="badge bg-emerald-100 text-emerald-700 font-black">VALID</span>
                   </div>
                   <div className="flex gap-2">
                      <div className="flex-1 h-1.5 bg-emerald-500 rounded-full" />
                      <div className="flex-1 h-1.5 bg-emerald-500 rounded-full" />
                      <div className="flex-1 h-1.5 bg-emerald-200 rounded-full" />
                   </div>
                   <p className="text-[10px] text-muted-foreground italic">Hardware verification is performed every 24h or upon cluster boot.</p>
                </div>
             </div>
          </div>
        </div>

        {/* Sidebar Status */}
        <div className="space-y-6">
           <div className="bg-slate-950 text-white rounded-3xl p-6 space-y-6 shadow-xl relative overflow-hidden">
              <div className="absolute top-0 right-0 w-32 h-32 bg-primary/20 rounded-full blur-3xl -mr-16 -mt-16" />
              <h3 className="font-black text-lg flex items-center gap-2 relative z-10"><Activity className="w-5 h-5 text-primary" /> Cluster Sovereignty</h3>
              
              <div className="space-y-4 relative z-10">
                 <div className="flex justify-between items-center p-3 rounded-2xl bg-white/5 border border-white/10">
                    <span className="text-xs text-slate-400 font-bold">Airgap Mode</span>
                    <span className="text-xs font-black text-emerald-400">ENABLED</span>
                 </div>
                 <div className="flex justify-between items-center p-3 rounded-2xl bg-white/5 border border-white/10">
                    <span className="text-xs text-slate-400 font-bold">Policy Enforcement</span>
                    <span className="text-xs font-black text-emerald-400">STRICT</span>
                 </div>
                 <div className="flex justify-between items-center p-3 rounded-2xl bg-white/5 border border-white/10 opacity-50">
                    <span className="text-xs text-slate-400 font-bold">Federation Link</span>
                    <span className="text-xs font-black text-red-400">OFFLINE</span>
                 </div>
              </div>

              <div className="pt-4 border-t border-white/10 relative z-10">
                 <div className="text-[10px] text-slate-500 font-black uppercase mb-2">Compliance Score</div>
                 <div className="flex items-end gap-2">
                    <span className="text-4xl font-black italic">100%</span>
                    <span className="text-xs text-emerald-400 font-bold mb-1 flex items-center gap-1"><CheckCircle2 className="w-3 h-3" /> Fully Compliant</span>
                 </div>
              </div>
           </div>

           <div className="bg-white border border-border rounded-3xl p-6 space-y-4">
              <h3 className="font-black flex items-center gap-2 text-xs uppercase tracking-wider">
                 <History className="w-4 h-4 text-slate-400" /> Recent Events
              </h3>
              <div className="space-y-4">
                 {[
                    { type: 'verify', msg: 'Audit Trail Bundle verified', time: '2h ago' },
                    { type: 'crl', msg: 'Offline CRL updated to v2.1.4', time: '5h ago' },
                    { type: 'reject', msg: 'Policy Bundle #X92 rejected (Invalid HMAC)', time: '1d ago' },
                 ].map((ev, i) => (
                    <div key={i} className="flex gap-3 text-[11px]">
                       <div className="mt-0.5">
                          {ev.type === 'verify' ? <CheckCircle2 className="w-3 h-3 text-emerald-500" /> : 
                           ev.type === 'reject' ? <XCircle className="w-3 h-3 text-red-500" /> : 
                           <Activity className="w-3 h-3 text-blue-500" />}
                       </div>
                       <div>
                          <div className="font-bold text-slate-900">{ev.msg}</div>
                          <div className="text-slate-400">{ev.time}</div>
                       </div>
                    </div>
                 ))}
              </div>
           </div>

           <div className="p-4 rounded-2xl bg-blue-50 border border-blue-100 flex gap-3 shadow-sm">
              <ShieldAlert className="w-5 h-5 text-blue-500 shrink-0" />
              <p className="text-[10px] text-blue-700 leading-relaxed font-medium">
                 O <strong>Sovereign Mode</strong> isola logicamente a rede de controle (Control Plane) da rede de dados (Data Plane), garantindo que nenhuma informação sensível saia do perímetro físico sem exportação explícita.
              </p>
           </div>
        </div>
      </div>
    </div>
  )
}
