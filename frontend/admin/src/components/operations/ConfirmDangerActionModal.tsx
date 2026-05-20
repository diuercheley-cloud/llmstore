import { AlertTriangle, X } from 'lucide-react'

interface ConfirmDangerActionModalProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: () => void
  title: string
  description: string
  confirmLabel?: string
  isPending?: boolean
}

export default function ConfirmDangerActionModal({ 
  isOpen, 
  onClose, 
  onConfirm, 
  title, 
  description, 
  confirmLabel = 'Confirmar Ação',
  isPending = false
}: ConfirmDangerActionModalProps) {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-foreground/60 backdrop-blur-sm">
      <div className="bg-card w-full max-w-md rounded-3xl shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-200">
        <div className="p-6 border-b border-border flex justify-between items-center bg-destructive/10">
          <div className="flex items-center gap-3 text-destructive">
            <AlertTriangle className="w-6 h-6" />
            <h3 className="font-black uppercase tracking-tight">{title}</h3>
          </div>
          <button onClick={onClose} className="text-muted-foreground hover:text-muted-foreground transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-8">
          <p className="text-muted-foreground leading-relaxed mb-8">
            {description}
          </p>
          <div className="flex flex-col gap-3">
            <button 
              onClick={onConfirm}
              disabled={isPending}
              className="w-full bg-destructive hover:bg-destructive/90 text-white font-bold py-3 rounded-2xl transition-colors shadow-lg shadow-rose-600/20 disabled:opacity-50"
            >
              {isPending ? 'Processando...' : confirmLabel}
            </button>
            <button 
              onClick={onClose}
              className="w-full bg-secondary hover:bg-secondary text-foreground font-bold py-3 rounded-2xl transition-colors"
            >
              Cancelar
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
