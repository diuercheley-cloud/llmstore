import React, { useState } from 'react';
import { ShieldAlert, Check, X, AlertTriangle } from 'lucide-react';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  onApprove: (reason: string) => Promise<void>;
  onReject: (reason: string) => Promise<void>;
  title?: string;
  isDestructive?: boolean;
}

export function ApprovalDecisionModal({ isOpen, onClose, onApprove, onReject, title = "Revisão de Ação do Agente", isDestructive = false }: ModalProps) {
  const [reason, setReason] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleAction = async (action: 'approve' | 'reject') => {
    setIsSubmitting(true);
    try {
      if (action === 'approve') await onApprove(reason);
      else await onReject(reason);
      onClose();
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
      <div className="bg-card w-full max-w-md rounded-3xl border border-border shadow-2xl overflow-hidden animate-in fade-in zoom-in-95">
        <div className={`p-6 border-b ${isDestructive ? 'bg-red-500/10 border-red-500/20' : 'bg-secondary/50 border-border'}`}>
          <div className="flex items-center gap-3">
            {isDestructive ? <AlertTriangle className="text-red-500 w-6 h-6" /> : <ShieldAlert className="text-primary w-6 h-6" />}
            <h2 className="text-xl font-bold text-foreground">{title}</h2>
          </div>
          {isDestructive && <p className="text-xs text-red-500 mt-2 font-bold uppercase tracking-widest">Ação Destrutiva Detectada</p>}
        </div>
        
        <div className="p-6 space-y-4">
          <div>
            <label className="block text-xs font-black uppercase text-muted-foreground tracking-widest mb-2">
              Justificativa da Decisão (Obrigatório)
            </label>
            <textarea
              className="w-full h-24 bg-background border border-border rounded-xl p-3 text-sm focus:ring-2 focus:ring-primary outline-none resize-none"
              placeholder="Descreva o motivo desta aprovação ou rejeição para os logs de auditoria..."
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
          </div>
          
          <div className="flex gap-3 pt-4">
            <button 
              className="flex-1 bg-secondary text-foreground font-bold py-2.5 rounded-xl hover:bg-secondary/80 transition-colors"
              onClick={onClose}
              disabled={isSubmitting}
            >
              Cancelar
            </button>
            <button 
              className="flex-1 bg-destructive text-white font-bold py-2.5 rounded-xl hover:opacity-90 flex items-center justify-center gap-2 disabled:opacity-50"
              onClick={() => handleAction('reject')}
              disabled={!reason.trim() || isSubmitting}
            >
              <X size={16} /> Rejeitar
            </button>
            <button 
              className="flex-1 bg-primary text-primary-foreground font-bold py-2.5 rounded-xl hover:opacity-90 flex items-center justify-center gap-2 disabled:opacity-50"
              onClick={() => handleAction('approve')}
              disabled={!reason.trim() || isSubmitting}
            >
              <Check size={16} /> Aprovar
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
