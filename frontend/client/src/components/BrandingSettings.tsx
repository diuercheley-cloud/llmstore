import { useState, useEffect, useRef } from 'react';
import { Image as ImageIcon, CheckCircle2, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

export const BrandingSettings = () => {
  const [primaryColor, setPrimaryColor] = useState('#3b82f6');
  const [logoUrl, setLogoUrl] = useState('https://via.placeholder.com/150x40');
  const [isSaving, setIsSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  const isInitialMount = useRef(true);

  const applyBranding = () => {
    setIsSaving(true);
    // Simulate API call
    setTimeout(() => {
      document.documentElement.style.setProperty('--primary-color', primaryColor);
      setIsSaving(false);
      setLastSaved(new Date());
      toast.success("Branding atualizado!", {
        description: "As alterações foram aplicadas globalmente."
      });
    }, 800);
  };

  // Auto-save effect
  useEffect(() => {
    if (isInitialMount.current) {
      isInitialMount.current = false;
      return;
    }

    const timer = setTimeout(() => {
      applyBranding();
    }, 1500); // Save after 1.5s of inactivity

    return () => clearTimeout(timer);
  }, [primaryColor, logoUrl, applyBranding]);

  useEffect(() => {
    const currentPrimary = getComputedStyle(document.documentElement).getPropertyValue('--primary-color').trim();
    if (currentPrimary) {
      setTimeout(() => {
        setPrimaryColor(currentPrimary);
      }, 0);
    }
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <h1 className="text-2xl md:text-3xl font-bold tracking-tight">White-Label Branding</h1>
        <div className="flex items-center gap-3 bg-white px-4 py-2 rounded-xl border border-border-base shadow-sm">
          {isSaving ? (
            <div className="flex items-center gap-2 text-primary font-bold text-xs animate-pulse">
              <Loader2 className="w-4 h-4 animate-spin" />
              Salvando...
            </div>
          ) : lastSaved ? (
            <div className="flex items-center gap-2 text-emerald-600 font-bold text-xs">
              <CheckCircle2 className="w-4 h-4" />
              Salvo às {lastSaved.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </div>
          ) : (
            <span className="text-xs text-slate-400 font-medium">Todas as alterações salvas</span>
          )}
        </div>
      </div>
      
      <div className="card max-w-2xl">
        <h3 className="text-lg font-bold mb-6 flex items-center gap-2">
          <ImageIcon size={20} className="text-slate-400" />
          Visual Appearance
        </h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">Primary Brand Color</label>
              <div className="flex gap-3">
                <div className="relative w-12 h-12 shrink-0">
                  <input 
                    type="color" 
                    value={primaryColor} 
                    onChange={(e) => setPrimaryColor(e.target.value)} 
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  />
                  <div 
                    className="w-full h-full rounded-xl shadow-inner border-2 border-white ring-1 ring-slate-200" 
                    style={{ backgroundColor: primaryColor }}
                  />
                </div>
                <input 
                  type="text" 
                  className="input-field font-mono" 
                  value={primaryColor} 
                  onChange={(e) => setPrimaryColor(e.target.value)} 
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">Logo URL</label>
              <input 
                type="text" 
                className="input-field" 
                value={logoUrl}
                onChange={(e) => setLogoUrl(e.target.value)}
                placeholder="https://yourcompany.com/logo.png"
              />
            </div>
          </div>

          <div className="space-y-4">
            <label className="block text-sm font-semibold text-slate-700">Preview</label>
            <div className="bg-slate-50 rounded-2xl p-6 border border-border-base min-h-[160px] flex flex-col items-center justify-center gap-4">
              {logoUrl ? (
                <img src={logoUrl} alt="Logo Preview" className="max-h-10 object-contain" />
              ) : (
                <div className="w-10 h-10 bg-slate-200 rounded-lg animate-pulse" />
              )}
              <div className="flex gap-2">
                <div className="h-2 w-16 rounded-full" style={{ backgroundColor: primaryColor }} />
                <div className="h-2 w-8 rounded-full bg-slate-200" />
              </div>
              <button 
                className="px-4 py-2 rounded-lg text-xs font-bold text-white shadow-lg" 
                style={{ backgroundColor: primaryColor }}
              >
                Sample Button
              </button>
            </div>
          </div>
        </div>

        <div className="mt-10 pt-6 border-t border-border-base flex justify-end">
          <p className="text-xs text-muted-foreground italic">Alterações são salvas automaticamente após 1.5s de inatividade.</p>
        </div>
      </div>
    </div>
  );
};
