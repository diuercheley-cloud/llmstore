import React, { useState, useEffect, useRef } from 'react';
import ChannelList from './ChannelList';
import MessageThread from './MessageThread';
import AgentMentionPicker from './AgentMentionPicker';
import { useAuthStore } from '../../store/useAuthStore';
import api from '../../lib/api';
import { LoadingCard } from '../../components/ui-feedback';
import { MessageSquare, AlertCircle } from 'lucide-react';

const CollaborativeChat: React.FC = () => {
  const token = useAuthStore(state => state.token);
  const [selectedChannel, setSelectedChannel] = useState<any>(null);
  const [channels, setChannels] = useState<any[]>([]);
  const [messages, setMessages] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [input, setInput] = useState('');
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!token) return;
    
    setLoading(true);
    api.listChatChannels()
      .then(data => {
        setChannels(Array.isArray(data) ? data : []);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setError("Não foi possível carregar os canais de chat.");
        setLoading(false);
      });
  }, [token]);

  useEffect(() => {
    if (selectedChannel && token) {
      // Fetch messages
      api.listChatMessages(selectedChannel.id)
        .then(data => setMessages(Array.isArray(data) ? data : []));

      // Connect WebSocket
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/v1/chat/channels/${selectedChannel.id}/stream?token=${token}`;
      ws.current = new WebSocket(wsUrl);
      
      ws.current.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === 'new_message') {
            setMessages(prev => [...prev, msg.data]);
          }
        } catch (e) {
          console.error("WS parse error", e);
        }
      };

      return () => {
        ws.current?.close();
      };
    }
  }, [selectedChannel, token]);

  const sendMessage = () => {
    if (!input.trim() || !selectedChannel || !token) return;

    api.postChatMessage(selectedChannel.id, input);
    setInput('');
  };

  const handleCreateChannel = async () => {
    const name = prompt("Nome do novo canal:");
    if (!name) return;

    try {
      setLoading(true);
      const newChannel = await api.createChatChannel({ name });
      setChannels(prev => [...prev, newChannel]);
      setSelectedChannel(newChannel);
    } catch (err) {
      console.error(err);
      alert("Erro ao criar canal.");
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <LoadingCard />;

  if (error) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
        <AlertCircle className="w-12 h-12 text-destructive mb-4" />
        <h2 className="text-xl font-bold mb-2">Erro no Chat</h2>
        <p className="text-muted-foreground">{error}</p>
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-120px)] bg-background rounded-3xl border border-border overflow-hidden shadow-sm">
      <div className="w-64 bg-card border-r border-border">
        <ChannelList 
          channels={channels} 
          selectedChannel={selectedChannel} 
          onSelect={setSelectedChannel} 
          onCreate={handleCreateChannel}
        />
      </div>
      <div className="flex-1 flex flex-col bg-background">
        {selectedChannel ? (
          <>
            <div className="p-4 border-b border-border bg-card/50 flex justify-between items-center">
              <h2 className="text-lg font-black uppercase tracking-tight flex items-center gap-2">
                <MessageSquare className="w-5 h-5 text-primary" />
                #{selectedChannel.name}
              </h2>
            </div>
            <div className="flex-1 overflow-y-auto p-6">
              <MessageThread messages={messages} />
            </div>
            <div className="p-4 border-t border-border bg-card/30">
              <div className="flex gap-2 relative">
                <textarea
                  className="flex-1 border border-border bg-background rounded-xl p-3 focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all resize-none"
                  rows={2}
                  placeholder={`Mensagem #${selectedChannel.name}`}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      sendMessage();
                    }
                  }}
                />
                <button 
                  onClick={sendMessage}
                  disabled={!input.trim()}
                  className="bg-primary text-primary-foreground px-6 py-2 rounded-xl font-bold hover:opacity-90 disabled:opacity-50 self-end transition-all h-[52px]"
                >
                  Enviar
                </button>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground p-8 text-center">
            <div className="p-4 bg-muted rounded-full mb-4">
              <MessageSquare className="w-8 h-8 opacity-20" />
            </div>
            <h3 className="font-bold text-foreground mb-1">Chat Colaborativo</h3>
            <p className="text-sm max-w-xs">Selecione um canal na barra lateral para começar a interagir com outros usuários e agentes.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default CollaborativeChat;
