import React from 'react';

interface ChannelListProps {
  channels: any[];
  selectedChannel: any;
  onSelect: (channel: any) => void;
}

const ChannelList: React.FC<ChannelListProps> = ({ channels, selectedChannel, onSelect }) => {
  return (
    <div className="p-4">
      <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4">Canais</h3>
      <div className="space-y-1">
        {channels.map((channel) => (
          <button
            key={channel.id}
            onClick={() => onSelect(channel)}
            className={`w-full text-left px-3 py-2 rounded transition ${
              selectedChannel?.id === channel.id
                ? 'bg-blue-100 text-blue-700 font-medium'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            # {channel.name}
          </button>
        ))}
        <button className="w-full text-left px-3 py-2 text-gray-400 hover:text-gray-600 italic">
          + Novo Canal
        </button>
      </div>
    </div>
  );
};

export default ChannelList;
