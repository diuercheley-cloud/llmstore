import React from 'react';
import { Database, Search, Download, Trash2, Eye } from 'lucide-react';

interface MemoryItem {
  id: string;
  type: string;
  summary?: string;
  content?: string;
  created_at: string;
}

export function MemoryAccessTable({ items }: { items: MemoryItem[] }) {
  if (!items || items.length === 0) {
    return (
      <div className="text-center p-10 border border-dashed border-border rounded-xl">
        <Database className="w-8 h-8 text-muted-foreground mx-auto mb-3 opacity-50" />
        <p className="text-muted-foreground font-medium">Nenhum item de memória registrado.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto bg-card border border-border rounded-xl shadow-sm">
      <table className="w-full text-left border-collapse">
        <thead>
          <tr className="bg-secondary/30 text-muted-foreground text-[10px] font-black uppercase tracking-widest border-b border-border">
            <th className="px-4 py-3">ID</th>
            <th className="px-4 py-3">Tipo</th>
            <th className="px-4 py-3">Resumo / Conteúdo (Redigido)</th>
            <th className="px-4 py-3">Data</th>
            <th className="px-4 py-3 text-right">Ações</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {items.map((item) => (
            <tr key={item.id} className="hover:bg-secondary/50 transition-colors">
              <td className="px-4 py-3 font-mono text-xs">{item.id.slice(0, 8)}...</td>
              <td className="px-4 py-3">
                <span className="text-[10px] font-black px-2 py-0.5 rounded uppercase tracking-tighter bg-primary/10 text-primary">
                  {item.type}
                </span>
              </td>
              <td className="px-4 py-3 text-sm max-w-xs truncate">
                {item.summary || item.content || 'Conteúdo sensível / Oculto'}
              </td>
              <td className="px-4 py-3 text-xs text-muted-foreground">
                {new Date(item.created_at).toLocaleString()}
              </td>
              <td className="px-4 py-3 text-right space-x-2">
                <button className="p-1.5 text-muted-foreground hover:text-primary hover:bg-primary/10 rounded transition-colors" title="Visualizar Detalhes">
                  <Eye size={16} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
