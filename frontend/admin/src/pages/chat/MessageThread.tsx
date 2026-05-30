import React from 'react';

interface MessageThreadProps {
  messages: any[];
}

const MessageThread: React.FC<MessageThreadProps> = ({ messages }) => {
  return (
    <div className="space-y-4">
      {messages.map((msg) => (
        <div key={msg.id} className="flex gap-3 group">
          <div className="w-10 h-10 rounded bg-gray-200 flex items-center justify-center text-gray-500 font-bold">
            {msg.agent_id ? 'AI' : (msg.user_id?.substring(0, 2).toUpperCase() || 'U')}
          </div>
          <div className="flex-1">
            <div className="flex items-baseline gap-2">
              <span className="font-bold text-gray-900">
                {msg.agent_id ? 'Agente' : (msg.user_id?.split('-')[0] || 'Usuário')}
              </span>
              <span className="text-xs text-gray-400">
                {new Date(msg.created_at).toLocaleTimeString()}
              </span>
            </div>
            <div className={`mt-1 text-gray-800 whitespace-pre-wrap ${msg.message_type === 'agent_response' ? 'text-blue-700 bg-blue-50 p-2 rounded border border-blue-100' : ''}`}>
              {msg.content}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

export default MessageThread;
