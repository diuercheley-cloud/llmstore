import { useQuery, useMutation } from '@tanstack/react-query'
import api from '../../lib/api'
import { Eye, Image as ImageIcon, Video, Layers, Play, CheckCircle2, AlertCircle, Info, Activity, Wand2 } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

export default function MultimodalManagement() {
  const [selectedModel, setSelectedModel] = useState<string>('llava')
  const [simulationResult, setSimulationResult] = useState<any>(null)

  const { data: capabilities, isLoading } = useQuery({
    queryKey: ['multimodal-capabilities'],
    queryFn: async () => {
      const res = await api.get('/api/multimodal/capabilities')
      return res.data
    }
  })

  const analyzeMutation = useMutation({
    mutationFn: async (formData: FormData) => {
      const isVideo = selectedModel === 'video-llama'
      const endpoint = isVideo ? '/api/multimodal/video/analyze' : '/api/multimodal/vision/analyze'
      const res = await api.post(endpoint, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      return res.data
    },
    onSuccess: (data) => {
      setSimulationResult(data)
      toast.success('Análise concluída')
    },
    onError: () => {
      toast.error('Falha na análise')
    }
  })

  const handleTest = () => {
    const fileInput = document.getElementById('test-file') as HTMLInputElement
    const promptInput = document.getElementById('test-prompt') as HTMLInputElement
    
    if (!fileInput.files?.[0]) {
      toast.error('Selecione um arquivo para teste')
      return
    }

    const formData = new FormData()
    formData.append('file', fileInput.files[0])
    formData.append('prompt', promptInput.value || 'Describe this.')
    formData.append('model_hint', selectedModel)

    analyzeMutation.mutate(formData)
  }

  return (
    <div className="p-8 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-black text-foreground flex items-center gap-3">
            <Eye className="w-8 h-8 text-primary" /> MULTIMODAL PLATFORM
          </h1>
          <p className="text-muted-foreground mt-1">Gestão de visão computacional, análise de vídeo e capacidades multimodais.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-8">
          <div className="bg-card border border-border rounded-3xl overflow-hidden shadow-sm p-6">
            <h2 className="font-bold flex items-center gap-2 mb-6 text-lg">
              <Layers className="w-5 h-5 text-primary" /> Adapters & Capabilities
            </h2>
            
            {isLoading ? (
              <div className="animate-pulse space-y-4">
                {[1, 2, 3].map(i => <div key={i} className="h-16 bg-secondary rounded-2xl" />)}
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {Object.entries(capabilities || {}).map(([name, caps]: [string, any]) => (
                  <div key={name} className="p-4 bg-secondary/30 border border-border rounded-2xl">
                    <div className="flex items-center justify-between mb-3">
                      <span className="font-black uppercase text-sm tracking-wider">{name}</span>
                      {name === 'video-llama' ? <Video className="w-4 h-4 text-primary" /> : <ImageIcon className="w-4 h-4 text-primary" />}
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {caps.map((cap: string) => (
                        <span key={cap} className="px-2 py-0.5 bg-background text-[10px] font-bold rounded-md border border-border">
                          {cap}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {simulationResult && (
            <div className="bg-card border border-border rounded-3xl p-6 shadow-sm space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="font-bold flex items-center gap-2">
                  <Activity className="w-5 h-5 text-primary" /> Resultado da Análise
                </h2>
                <span className="text-[10px] font-black bg-primary/10 text-primary px-2 py-1 rounded-md">
                  MODELO: {simulationResult.model_used}
                </span>
              </div>
              
              <div className="p-4 bg-secondary/20 rounded-2xl border border-border font-medium text-sm leading-relaxed">
                {simulationResult.text}
              </div>

              {simulationResult.detected_objects?.length > 0 && (
                <div className="space-y-3">
                  <h3 className="text-[10px] font-black uppercase text-muted-foreground">Objetos Detectados</h3>
                  <div className="flex flex-wrap gap-2">
                    {simulationResult.detected_objects.map((obj: any, idx: number) => (
                      <span key={idx} className="px-3 py-1 bg-primary text-primary-foreground text-xs font-bold rounded-full">
                        {obj.label} ({(simulationResult.confidence * 100).toFixed(0)}%)
                      </span>
                    ))}
                  </div>
                </div>
              )}

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 border-t border-border">
                <div>
                  <div className="text-[10px] font-black text-muted-foreground uppercase">Confidence</div>
                  <div className="font-bold text-sm">{(simulationResult.confidence * 100).toFixed(1)}%</div>
                </div>
                <div>
                  <div className="text-[10px] font-black text-muted-foreground uppercase">Backend</div>
                  <div className="font-bold text-sm">{simulationResult.backend_used}</div>
                </div>
                <div className="col-span-2">
                  <div className="text-[10px] font-black text-muted-foreground uppercase">File Hash</div>
                  <div className="font-mono text-[9px] truncate">{simulationResult.audit_metadata?.file_hash}</div>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="space-y-6">
          <div className="bg-primary/5 border border-primary/10 rounded-3xl p-6">
            <h2 className="font-bold flex items-center gap-2 mb-6">
              <Wand2 className="w-5 h-5 text-primary" /> Teste Multimodal
            </h2>
            <div className="space-y-5">
              <div>
                <label className="text-[10px] font-black uppercase text-muted-foreground mb-1 block tracking-widest">Selecione o Modelo</label>
                <select 
                  className="w-full bg-background border border-border rounded-xl px-4 py-3 text-sm font-medium focus:ring-2 ring-primary/20 outline-none transition-all"
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                >
                  <option value="llava">Llava v1.5 (Image/VQA)</option>
                  <option value="qwen-vl">Qwen-VL (OCR/Detection)</option>
                  <option value="moondream">Moondream (Fast/Small)</option>
                  <option value="florence2">Florence-2 (Structured)</option>
                  <option value="video-llama">Video-LLaMA (Video)</option>
                </select>
              </div>

              <div>
                <label className="text-[10px] font-black uppercase text-muted-foreground mb-1 block tracking-widest">Arquivo (Imagem ou Vídeo)</label>
                <div className="relative group">
                  <input 
                    type="file" 
                    id="test-file"
                    className="w-full bg-background border border-border rounded-xl px-4 py-3 text-sm file:mr-4 file:py-1 file:px-3 file:rounded-full file:border-0 file:text-[10px] file:font-black file:bg-primary file:text-primary-foreground file:uppercase"
                  />
                </div>
              </div>

              <div>
                <label className="text-[10px] font-black uppercase text-muted-foreground mb-1 block tracking-widest">Prompt / Pergunta</label>
                <textarea 
                  id="test-prompt"
                  rows={3}
                  placeholder="Ex: O que tem nesta imagem? Onde está o gato?"
                  className="w-full bg-background border border-border rounded-xl px-4 py-3 text-sm resize-none focus:ring-2 ring-primary/20 outline-none transition-all"
                />
              </div>

              <button 
                onClick={handleTest}
                disabled={analyzeMutation.isPending}
                className="w-full py-4 bg-primary text-primary-foreground rounded-2xl font-black text-sm shadow-xl shadow-primary/20 hover:scale-[1.02] active:scale-[0.98] transition-all disabled:opacity-50 flex items-center justify-center gap-3"
              >
                {analyzeMutation.isPending ? (
                  <> <Activity className="w-4 h-4 animate-spin" /> ANALISANDO... </>
                ) : (
                  <> <Play className="w-4 h-4" /> INICIAR ANÁLISE </>
                )}
              </button>
            </div>
          </div>

          <div className="bg-card border border-border rounded-3xl p-6">
            <h2 className="font-bold flex items-center gap-2 mb-4">
              <Info className="w-5 h-5 text-muted-foreground" /> Governança Multimodal
            </h2>
            <div className="space-y-4 text-[11px] leading-relaxed">
              <div className="flex gap-3">
                <CheckCircle2 className="w-4 h-4 text-primary shrink-0" />
                <span>Hashing determinístico de arquivos para auditoria e detecção de duplicidade.</span>
              </div>
              <div className="flex gap-3">
                <CheckCircle2 className="w-4 h-4 text-primary shrink-0" />
                <span>Sanitização automática de metadados EXIF antes do processamento.</span>
              </div>
              <div className="flex gap-3">
                <CheckCircle2 className="w-4 h-4 text-primary shrink-0" />
                <span>Isolamento de tenant preservado em todas as camadas de abstração.</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
