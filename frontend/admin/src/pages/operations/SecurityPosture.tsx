import { useState } from 'react'
import { ShieldCheck, Lock, Eye, Download, AlertTriangle, Terminal, Copy, Check } from 'lucide-react'
import HealthCard from '../../components/operations/HealthCard'

interface SecurityScript {
  name: string
  type: 'shell' | 'python'
  path: string
  command: string
  description: string
  scope: string
}

export default function SecurityPosture() {
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null)

  const securityScripts: SecurityScript[] = [
    {
      name: 'Execução Geral de Testes de Segurança',
      type: 'shell',
      path: 'scripts/run_security_checks.sh',
      command: './scripts/run_security_checks.sh',
      description: 'Executa a suíte de testes de segurança automatizados, incluindo varreduras de segredos e verificação de vulnerabilidades de dependências.',
      scope: 'Segurança Global / CI'
    },
    {
      name: 'Auditorias de Configurações e Postura',
      type: 'python',
      path: 'scripts/security_audit.py',
      command: 'python3 scripts/security_audit.py',
      description: 'Varre arquivos de configurações e chaves buscando vazamento de credenciais e más práticas de postura de segurança.',
      scope: 'Configurações'
    },
    {
      name: 'Auditoria de Segurança Avançada (v2)',
      type: 'python',
      path: 'scripts/security_audit_v2.py',
      command: 'python3 scripts/security_audit_v2.py',
      description: 'Validador estendido focado na integridade do runtime do Control Plane e assinaturas PKI na versão 2.1.0.',
      scope: 'Control Plane v2.1.0'
    },
    {
      name: 'Validação de Sandbox de Agentes',
      type: 'shell',
      path: 'scripts/validators/validate-agent-security.sh',
      command: './scripts/validators/validate-agent-security.sh',
      description: 'Verifica as permissões do sistema de arquivos e limites de rede dos sandboxes de execução dos agentes.',
      scope: 'Sandbox de Execução'
    },
    {
      name: 'Auditoria de Autenticação Administrativa',
      type: 'python',
      path: 'scripts/validators/validate_admin_route_auth.py',
      command: 'python3 scripts/validators/validate_admin_route_auth.py',
      description: 'Analisa estaticamente as rotas administrativas expostas no Control Plane para garantir cobertura de guards de autorização.',
      scope: 'API / Rotas Admin'
    }
  ]

  const handleCopy = (command: string, index: number) => {
    navigator.clipboard.writeText(command)
    setCopiedIndex(index)
    setTimeout(() => {
      setCopiedIndex(null)
    }, 2000)
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-black text-foreground mb-2">Security <span className="text-primary">Posture</span></h1>
          <p className="text-muted-foreground font-medium">Monitoramento de conformidade, criptografia e auditoria.</p>
        </div>
        <button className="bg-primary text-white px-4 py-2 rounded-xl font-bold flex items-center gap-2 shadow-lg shadow-primary/20 hover:bg-primary/95 transition-all">
          <Download className="w-4 h-4" />
          Baixar Relatório
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
        <HealthCard 
          title="Criptografia" 
          value="ATIVA" 
          icon={<Lock className="w-6 h-6" />}
          description="Tenant-level keys estão rotacionadas."
        />
        <HealthCard 
          title="Auditoria" 
          value="99.9%" 
          icon={<Eye className="w-6 h-6" />}
          description="Ações administrativas logadas e assinadas."
        />
        <HealthCard 
          title="Vulnerabilidades" 
          value="0" 
          icon={<ShieldCheck className="w-6 h-6" />}
          description="Nenhum CVE crítico detectado nos nós."
        />
      </div>

      {/* Seção de Scripts de Segurança do Backend */}
      <div className="bg-card border border-border rounded-3xl p-8 shadow-sm mb-10">
        <div className="flex items-center gap-3 mb-6">
          <Terminal className="w-6 h-6 text-primary" />
          <h3 className="text-xl font-bold text-foreground">Scripts de Segurança & Auditoria (Backend)</h3>
        </div>
        <p className="text-sm text-muted-foreground mb-6 font-medium">
          Estes scripts e validators foram recentemente adicionados ao backend para auditoria contínua da stack. Execute-os localmente ou em pipelines de CI para validar a postura de segurança.
        </p>

        <div className="space-y-4">
          {securityScripts.map((script, index) => (
            <div key={index} className="p-6 bg-secondary/40 border border-border/60 rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-4 hover:border-primary/25 transition-all">
              <div className="space-y-2 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-bold text-foreground text-base">{script.name}</span>
                  <span className={`text-[10px] px-2 py-0.5 font-bold uppercase tracking-wider rounded-md border ${
                    script.type === 'shell' 
                      ? 'bg-blue-500/10 text-blue-500 border-blue-500/20' 
                      : 'bg-green-500/10 text-green-500 border-green-500/20'
                  }`}>
                    {script.type === 'shell' ? 'Shell Script' : 'Python Script'}
                  </span>
                  <span className="text-[10px] px-2 py-0.5 font-semibold bg-muted text-muted-foreground rounded-md">
                    {script.scope}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground font-medium leading-relaxed">{script.description}</p>
                <div className="font-mono text-xs bg-background/90 text-foreground p-3 rounded-xl border border-border flex items-center justify-between mt-2 overflow-x-auto">
                  <span>{script.command}</span>
                  <button 
                    onClick={() => handleCopy(script.command, index)}
                    className="text-muted-foreground hover:text-foreground p-1 transition-colors ml-4"
                    title="Copiar comando"
                  >
                    {copiedIndex === index ? (
                      <Check className="w-4 h-4 text-primary animate-pulse" />
                    ) : (
                      <Copy className="w-4 h-4" />
                    )}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-card border border-border rounded-3xl p-8 shadow-sm">
        <h3 className="text-xl font-bold text-foreground mb-6">Últimos Eventos de Segurança</h3>
        <div className="space-y-4">
          {[
            { event: 'Rotação de Master Key', status: 'success', time: '2h atrás' },
            { event: 'Tentativa de acesso não autorizado (Node-05)', status: 'warning', time: '5h atrás' },
            { event: 'Novo certificado PKI emitido', status: 'success', time: '12h atrás' },
          ].map((e, i) => (
            <div key={i} className="flex items-center justify-between p-4 bg-secondary rounded-2xl">
              <div className="flex items-center gap-3">
                {e.status === 'success' ? (
                  <ShieldCheck className="w-5 h-5 text-primary" />
                ) : (
                  <AlertTriangle className="w-5 h-5 text-yellow-500" />
                )}
                <span className="font-bold text-foreground">{e.event}</span>
              </div>
              <span className="text-xs text-muted-foreground font-mono">{e.time}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
