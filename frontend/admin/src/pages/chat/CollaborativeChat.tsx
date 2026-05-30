import React, { useState, useEffect, useRef } from 'react';
import ChannelList from './ChannelList';
import MessageThread from './MessageThread';
import AgentMentionPicker from './AgentMentionPicker';

const CollaborativeChat: React.FC = () => {
  const [selectedChannel, setSelectedChannel] = useState<any>(null);
  const [channels, setChannels] = useState<any[]>([]);
  const [messages, setMessages] = useState<any[]>([]);
  const [input, setInput] = useState('');
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Fetch channels
    fetch('/v1/chat/channels', {
      headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
    })
      .then(res => res.json())
      .then(data => setChannels(data));
  }, []);

  useEffect(() => {
    if (selectedChannel) {
      // Fetch messages
      fetch(`/v1/chat/channels/${selectedChannel.id}/messages`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      })
        .then(res => res.json())
        .then(data => setMessages(data));

      // Connect WebSocket
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      ws.current = new WebSocket(`${protocol}//${window.location.host}/v1/chat/channels/${selectedChannel.id}/stream?token=${localStorage.getItem('token')}`);
      
      ws.current.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.type === 'new_message') {
          setMessages(prev => [...prev, msg.data]);
        }
      };

      return () => {
        ws.current?.close();
      };
    }
  }, [selectedChannel]);

  const sendMessage = () => {
    if (!input.trim() || !selectedChannel) return;

    fetch(`/v1/chat/channels/${selectedChannel.id}/messages`, {
      method: 'POST',
      headers: { 
        'Authorization': `Bearer ${localStorage.getItem('token')}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ content: input })
    });
    setInput('');
  };

  return (
    <div className="flex h-screen bg-gray-100">
      <div className="w-64 bg-white border-r">
        <ChannelList 
          channels={channels} 
          selectedChannel={selectedChannel} 
          onSelect={setSelectedChannel} 
        />
      </div>
      <div className="flex-1 flex flex-col">
        {selectedChannel ? (
          <>
            <div className="p-4 border-b bg-white flex justify-between items-center">
              <h2 className="text-xl font-bold">#{selectedChannel.name}</h2>
            </div>
            <div className="flex-1 overflow-y-auto p-4">
              <MessageThread messages={messages} />
            </div>
            <div className="p-4 border-t bg-white">
              <div className="flex gap-2 relative">
                <textarea
                  className="flex-1 border rounded p-2 focus:outline-none focus:ring"
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
                  className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 self-end"
                >
                  Enviar
                </button>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-500">
            Selecione um canal para começar
          </div>
        )}
      </div>
    </div>
  );
};

export default CollaborativeChat;
