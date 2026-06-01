import React, { useState } from 'react';
import { studioNodeLibrary } from './studioData';
import { Search, GripVertical, Plus } from 'lucide-react';

interface ToolPaletteProps {
  onAddNode: (item: any) => void;
}

export default function ToolPalette({ onAddNode }: ToolPaletteProps) {
  const [search, setSearch] = useState('');

  const filteredTools = studioNodeLibrary.filter((item) => {
    const term = search.toLowerCase();
    return item.label.toLowerCase().includes(term) || item.type.toLowerCase().includes(term);
  });

  return (
    <div className="p-5 flex flex-col gap-6">
      <div className="space-y-1">
        <h2 className="text-xs font-black uppercase tracking-[0.2em] text-slate-500">
          Biblioteca
        </h2>
        <p className="text-[10px] text-slate-600 font-medium">Clique ou arraste para adicionar</p>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
        <input
          type="text"
          placeholder="Buscar blocos..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="w-full bg-white/5 border border-white/10 rounded-xl pl-10 pr-4 py-2 text-sm text-white placeholder:text-slate-600 focus:border-blue-500/50 outline-none transition-all"
        />
      </div>

      <div className="space-y-3">
        {filteredTools.map((item) => (
          <div 
            key={item.type} 
            onClick={() => onAddNode(item)}
            className="group relative bg-white/[0.03] hover:bg-white/[0.06] border border-white/5 hover:border-white/10 p-3 rounded-xl cursor-pointer transition-all active:scale-[0.98]"
          >
            <div className="flex justify-between items-start mb-1">
              <span className="text-xs font-bold text-slate-200 group-hover:text-white transition-colors">
                {item.label}
              </span>
              <span className="text-[9px] font-black uppercase px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/10">
                {item.badge}
              </span>
            </div>
            <p className="text-[10px] text-slate-500 leading-relaxed line-clamp-2">
              {item.description}
            </p>
            
            <div className="absolute right-2 bottom-2 opacity-0 group-hover:opacity-100 transition-opacity">
              <Plus className="w-4 h-4 text-blue-500" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

