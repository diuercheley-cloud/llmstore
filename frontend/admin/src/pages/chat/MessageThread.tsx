import React from 'react';
import { Bot, User } from 'lucide-react';

interface MessageThreadProps {
  messages: any[];
}

const MessageThread: React.FC<MessageThreadProps> = ({ messages }) => {
  return (
    <div className="space-y-6">
      {messages.map((msg) => (
        <div key={msg.id} className="flex gap-4 group">
          <div className={`w-10 h-10 rounded-2xl flex items-center justify-center font-bold shadow-sm ${
            msg.agent_id 
              ? 'bg-primary/10 text-primary' 
              : 'bg-muted text-muted-foreground'
          }`}>
            {msg.agent_id ? <Bot size={20} /> : <User size={20} />}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-baseline gap-2 mb-1">
              <span className="font-black text-xs uppercase tracking-tight text-foreground">
                {msg.agent_id ? (msg.agent_name || 'Agente AI') : (msg.user_id === 'admin' ? 'System Admin' : 'Usuário')}
              </span>
              <span className="text-[10px] font-black text-muted-foreground uppercase">
                {new Date(msg.created_at).toLocaleTimeString()}
              </span>
            </div>
            <div className={`text-sm leading-relaxed ${
              msg.message_type === 'agent_response' 
                ? 'text-primary font-medium bg-primary/5 p-4 rounded-2xl rounded-tl-none border border-primary/10' 
                : 'text-foreground bg-card p-4 rounded-2xl rounded-tl-none border border-border group-hover:border-primary/20 transition-all'
            }`}>
              {msg.content}
            </div>
          </div>
        </div>
      ))}
      {messages.length === 0 && (
        <div className="h-full flex flex-col items-center justify-center text-center opacity-20 py-20">
          <div className="p-6 bg-muted rounded-full mb-4">
             <Bot size={40} />
          </div>
          <p className="font-black uppercase tracking-widest text-xs">Nenhuma mensagem neste canal</p>
        </div>
      )}
    </div>
  );
};

export default MessageThread;
