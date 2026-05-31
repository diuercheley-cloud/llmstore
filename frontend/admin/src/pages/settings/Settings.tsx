import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui-card'
import { Button } from '../../components/ui-button'
import { Input } from '../../components/ui-input'
import { Label } from '../../components/ui-label'
import { toast } from 'sonner'
import { Settings as SettingsIcon, Bell, Globe, Lock, Palette } from 'lucide-react'
import { useState } from 'react'

export default function Settings() {
  const [form, setForm] = useState({
    siteName: 'Kleber AI',
    supportEmail: 'suporte@kleber.ai',
    defaultLocale: 'pt-BR',
    maintenanceMode: false,
  })

  const handleSave = () => {
    toast.success('Configurações salvas')
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Configurações</h1>
      <p className="text-muted-foreground">Configure parâmetros gerais da plataforma</p>

      <Card><CardHeader><CardTitle className="flex items-center gap-2"><Globe className="w-5 h-5" /> Geral</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div><Label>Nome do Site</Label><Input value={form.siteName} onChange={e => setForm(p => ({ ...p, siteName: e.target.value }))} /></div>
          <div><Label>Email de Suporte</Label><Input value={form.supportEmail} onChange={e => setForm(p => ({ ...p, supportEmail: e.target.value }))} /></div>
          <div><Label>Idioma Padrão</Label><Input value={form.defaultLocale} onChange={e => setForm(p => ({ ...p, defaultLocale: e.target.value }))} /></div>
          <Button onClick={handleSave}>Salvar</Button>
        </CardContent>
      </Card>

      <Card><CardHeader><CardTitle className="flex items-center gap-2"><Bell className="w-5 h-5" /> Notificações</CardTitle></CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Configure webhooks e alertas para eventos da plataforma.</p>
          <Button variant="outline" className="mt-3" onClick={() => toast.success('Configuração de notificações em breve')}>Configurar Webhooks</Button>
        </CardContent>
      </Card>
    </div>
  )
}
