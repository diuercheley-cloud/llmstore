import React from 'react';
import { Hash, Plus } from 'lucide-react';

interface ChannelListProps {
  channels: any[];
  selectedChannel: any;
  onSelect: (channel: any) => void;
  onCreate: () => void;
}

const ChannelList: React.FC<ChannelListProps> = ({ channels, selectedChannel, onSelect, onCreate }) => {
  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b border-border">
        <h3 className="text-[10px] font-black text-muted-foreground uppercase tracking-widest">Canais</h3>
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {channels.map((channel) => (
          <button
            key={channel.id}
            onClick={() => onSelect(channel)}
            className={`w-full text-left px-3 py-2 rounded-xl transition-all flex items-center gap-2 group ${
              selectedChannel?.id === channel.id
                ? 'bg-primary text-primary-foreground font-bold shadow-sm shadow-primary/20'
                : 'text-muted-foreground hover:bg-muted hover:text-foreground'
            }`}
          >
            <Hash className={`w-4 h-4 ${selectedChannel?.id === channel.id ? 'opacity-100' : 'opacity-40 group-hover:opacity-70'}`} />
            <span className="truncate">{channel.name}</span>
          </button>
        ))}
      </div>
      <div className="p-2 border-t border-border bg-muted/20">
        <button 
          onClick={onCreate}
          className="w-full flex items-center gap-2 px-3 py-2 text-xs font-bold text-muted-foreground hover:text-primary transition-all"
        >
          <Plus className="w-4 h-4" />
          Novo Canal
        </button>
      </div>
    </div>
  );
};

export default ChannelList;
