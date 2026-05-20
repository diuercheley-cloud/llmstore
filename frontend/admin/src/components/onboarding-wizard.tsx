import { useState, useEffect } from "react"
import { 
  Box, 
  Users, 
  Key, 
  MessageSquare, 
  Cloud, 
  ArrowRight, 
  CheckCircle2, 
  Loader2,
  AlertCircle
} from "lucide-react"
import api from "../lib/api"

interface Step {
  id: number
  title: string
  description: string
  icon: React.ReactNode
}

const STEPS: Step[] = [
  { 
    id: 1, 
    title: "Modelo GGUF", 
    description: "Carregue seu primeiro modelo local para inferência otimizada.",
    icon: <Box className="w-6 h-6" />
  },
  { 
    id: 2, 
    title: "Primeiro Cliente", 
    description: "Crie um tenant para organizar seus acessos e quotas.",
    icon: <Users className="w-6 h-6" />
  },
  { 
    id: 3, 
    title: "Chave de API", 
    description: "Gere credenciais para integração com suas aplicações.",
    icon: <Key className="w-6 h-6" />
  },
  { 
    id: 4, 
    title: "Teste de Chat", 
    description: "Valide se tudo está funcionando com uma requisição real.",
    icon: <MessageSquare className="w-6 h-6" />
  },
  { 
    id: 5, 
    title: "Provedores Cloud", 
    description: "Opcional: Conecte-se a providers externos como OpenAI ou Anthropic.",
    icon: <Cloud className="w-6 h-6" />
  }
]

export function OnboardingWizard() {
  const [isVisible, setIsVisible] = useState(false)
  const [currentStep, setCurrentStep] = useState(1)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<any>({
    clientId: null,
    apiKey: null,
    modelId: null
  })

  useEffect(() => {
    const checkStatus = async () => {
      try {
        const res = await api.get("/admin/onboarding/status")
        if (!res.data.is_finished) {
          setIsVisible(true)
        }
      } catch (e) {
        // If endpoint doesn't exist yet, show wizard by default for now
        setIsVisible(true)
      }
    }
    checkStatus()
  }, [])

  const finishOnboarding = async () => {
    try {
      await api.post("/admin/onboarding/status", { is_finished: true })
      setIsVisible(false)
    } catch (e) {
      setIsVisible(false)
    }
  }

  const handleNext = async () => {
    setError(null)
    setIsLoading(true)
    try {
      if (currentStep === 1) {
        // Step 1: Just list models and pick the first one or a default
        const res = await api.get("/admin/models")
        if (res.data && res.data.length > 0) {
          const model = res.data[0]
          await api.post("/admin/models/runtime/load", {
            model_id: model.id,
            backend_id: model.inference_backend_id,
            model_path: model.model_file
          })
          setData({ ...data, modelId: model.model_id })
        }
      } else if (currentStep === 2) {
        // Step 2: Create first client
        const res = await api.post("/admin/clients", {
          name: "Onboarding Client",
          description: "Created during initial setup"
        })
        setData({ ...data, clientId: res.data.id })
      } else if (currentStep === 3) {
        // Step 3: Create API Key
        const res = await api.post("/admin/api-keys", {
          client_id: data.clientId,
          name: "Default Key"
        })
        setData({ ...data, apiKey: res.data.api_key })
      } else if (currentStep === 4) {
        // Step 4: Test Chat
        // This is a test, we don't need to store result
        await api.post("/v1/chat/completions", {
          model: data.modelId || "default",
          messages: [{ role: "user", content: "Olá!" }],
          max_tokens: 10
        }, {
          headers: { "Authorization": `Bearer ${data.apiKey}` }
        })
      }

      if (currentStep < STEPS.length) {
        setCurrentStep(currentStep + 1)
      } else {
        await finishOnboarding()
      }
    } catch (e: any) {
      setError(e.response?.data?.detail || "Ocorreu um erro nesta etapa.")
    } finally {
      setIsLoading(false)
    }
  }

  if (!isVisible) return null

  const activeStep = STEPS.find(s => s.id === currentStep)!

  return (
    <div className="fixed inset-0 z-[200] bg-background/95 backdrop-blur-md flex items-center justify-center p-4">
      <div className="max-w-2xl w-full bg-card border border-border rounded-[2rem] shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Progress Bar */}
        <div className="h-1.5 w-full bg-secondary">
          <div 
            className="h-full bg-primary transition-all duration-500" 
            style={{ width: `${(currentStep / STEPS.length) * 100}%` }}
          />
        </div>

        <div className="p-8 md:p-12 overflow-y-auto flex-1">
          <div className="flex items-center gap-4 mb-8">
            <div className="p-4 bg-primary/10 text-primary rounded-2xl">
              {activeStep.icon}
            </div>
            <div>
              <div className="text-xs font-bold text-primary uppercase tracking-widest mb-1">Passo {currentStep} de {STEPS.length}</div>
              <h2 className="text-3xl font-black text-foreground">{activeStep.title}</h2>
            </div>
          </div>

          <p className="text-lg text-muted-foreground leading-relaxed mb-8">
            {activeStep.description}
          </p>

          {error && (
            <div className="p-4 bg-destructive/10 text-destructive rounded-xl flex items-start gap-3 mb-8 border border-destructive/20">
              <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
              <p className="text-sm font-medium">{error}</p>
            </div>
          )}

          {currentStep === 3 && data.apiKey && (
            <div className="p-4 bg-secondary rounded-xl mb-8 border border-border">
              <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest mb-2 block">Sua Nova Chave</label>
              <code className="text-sm font-mono break-all text-primary">{data.apiKey}</code>
              <p className="text-[10px] text-muted-foreground mt-2 italic">Salve esta chave, ela não será exibida novamente.</p>
            </div>
          )}
        </div>

        <div className="p-8 border-t border-border bg-secondary/30 flex items-center justify-between gap-4">
          <button 
            onClick={finishOnboarding}
            className="text-sm font-bold text-muted-foreground hover:text-foreground transition-colors"
          >
            Pular Onboarding
          </button>
          
          <div className="flex gap-3">
            <button 
              disabled={isLoading}
              onClick={handleNext}
              className="bg-primary hover:bg-primary/90 text-primary-foreground px-8 py-3 rounded-2xl font-bold flex items-center gap-2 transition-all shadow-lg shadow-primary/20 disabled:opacity-50"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Processando...
                </>
              ) : (
                <>
                  {currentStep === STEPS.length ? "Finalizar" : "Próximo Passo"}
                  <ArrowRight className="w-5 h-5" />
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
