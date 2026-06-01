export interface StudioFlowNode {
  id: string;
  type: string;
  label: string;
  status: 'idle' | 'success' | 'running' | 'failed';
  config: string;
  summary: string;
  nextStep: string;
}

export interface StudioNodeLibraryItem {
  type: string;
  label: string;
  badge: string;
  description: string;
}

export const studioFlowNodes: StudioFlowNode[] = [
  {
    id: '1',
    type: 'llm_call',
    label: 'Reasoning Loop (LLM)',
    status: 'success',
    config: 'Modelo principal do fluxo',
    summary: 'Executa o raciocinio principal e consolida o contexto antes de acionar ferramentas.',
    nextStep: 'Encaminhar a saida estruturada para a etapa de execucao de ferramenta.',
  },
  {
    id: '2',
    type: 'tool_call',
    label: 'Code Sandbox Run',
    status: 'running',
    config: 'Execucao controlada em sandbox',
    summary: 'Roda comandos isolados para gerar artefatos tecnicos sem acesso irrestrito ao ambiente.',
    nextStep: 'Enviar o resultado para revisao humana quando a execucao terminar.',
  },
  {
    id: '3',
    type: 'approval',
    label: 'Human Review Check',
    status: 'idle',
    config: 'Aprovacao operacional',
    summary: 'Bloqueia a promocao do fluxo ate que um operador valide impacto e conformidade.',
    nextStep: 'Liberar a publicacao apenas apos aprovacao explicita.',
  },
  {
    id: '4',
    type: 'final',
    label: 'Publish Artifacts',
    status: 'idle',
    config: 'Entrega dos artefatos finais',
    summary: 'Publica os resultados finais do fluxo para consumo operacional e auditoria.',
    nextStep: 'Disponibilizar JSON e Markdown para downstream e trilha de auditoria.',
  },
];

export const studioNodeLibrary: StudioNodeLibraryItem[] = [
  {
    type: 'agent',
    label: 'Agente',
    badge: 'Node',
    description: 'Bloco principal de execucao do agente no fluxo.',
  },
  {
    type: 'llm_call',
    label: 'Chamada de modelo',
    badge: 'Node',
    description: 'Etapa de inferencia com um modelo configurado.',
  },
  {
    type: 'tool_call',
    label: 'Ferramenta',
    badge: 'Node',
    description: 'Etapa para acionar uma ferramenta registrada.',
  },
  {
    type: 'memory_read',
    label: 'Leitura de memoria',
    badge: 'Node',
    description: 'Recupera contexto persistido para o fluxo.',
  },
  {
    type: 'approval',
    label: 'Aprovacao',
    badge: 'Node',
    description: 'Pausa a execucao aguardando decisao humana.',
  },
  {
    type: 'condition',
    label: 'Condicao',
    badge: 'Node',
    description: 'Define ramificacao com base em uma condicao.',
  },
  {
    type: 'handoff',
    label: 'Handoff',
    badge: 'Node',
    description: 'Transfere a execucao para outro agente ou etapa.',
  },
  {
    type: 'workflow_timer',
    label: 'Temporizador',
    badge: 'Node',
    description: 'Agenda ou retarda a continuacao do fluxo.',
  },
  {
    type: 'webhook_wait',
    label: 'Espera por webhook',
    badge: 'Node',
    description: 'Aguarda um evento externo antes de prosseguir.',
  },
  {
    type: 'final_response',
    label: 'Resposta final',
    badge: 'Node',
    description: 'Entrega a saida final do fluxo.',
  },
];
