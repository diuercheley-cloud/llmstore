import React from 'react';
import { Database } from 'lucide-react';
import { MemoryAccessTable } from '../../components/agents/MemoryAccessTable';

export default function AgentMemory() {
  const memoryItems = [
    { id: "mem_1a2b3c", type: "short_term", summary: "O usuário prefere respostas curtas.", created_at: "2026-05-21T10:00:00Z" },
    { id: "mem_4d5e6f", type: "episodic", summary: "Resolvido problema de faturamento #998", created_at: "2026-05-20T15:30:00Z" },
    { id: "mem_7g8h9i", type: "long_term", content: "[REDACTED]@example.com atualizado.", created_at: "2026-05-19T09:00:00Z" },
  ];

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4">
      <header>
        <h1 className="text-4xl font-black tracking-tight">Agent <span className="text-primary">Memory</span></h1>
        <p className="text-muted-foreground mt-2 text-lg">Camada de persistência isolada para agentes.</p>
      </header>

      <div>
        <MemoryAccessTable items={memoryItems} />
      </div>
    </div>
  );
}
