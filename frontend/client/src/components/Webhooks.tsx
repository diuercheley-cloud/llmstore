import { useState } from 'react';
import { Plus, Trash2, Webhook as WebhookIcon } from 'lucide-react';

export const Webhooks = () => {
  const [webhooks] = useState([
    { id: '1', url: 'https://api.mycompany.com/webhooks/billing', events: ['invoice.created', 'invoice.paid'], active: true },
    { id: '2', url: 'https://api.mycompany.com/webhooks/usage', events: ['limit.reached'], active: true }
  ]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <h1 className="text-2xl md:text-3xl font-bold tracking-tight">Webhooks</h1>
        <button className="btn btn-primary w-full sm:w-auto">
          <Plus size={18} /> Add Endpoint
        </button>
      </div>

      <div className="card !p-0 overflow-hidden">
        <div className="resp-table-container">
          <table className="resp-table">
            <thead>
              <tr>
                <th>ENDPOINT URL</th>
                <th>EVENTS</th>
                <th>STATUS</th>
                <th className="text-right">ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              {webhooks.map(wh => (
                <tr key={wh.id}>
                  <td data-label="URL" className="font-medium text-slate-900 truncate max-w-[300px]">
                    <div className="flex items-center gap-2">
                      <WebhookIcon size={14} className="text-slate-400" />
                      {wh.url}
                    </div>
                  </td>
                  <td data-label="EVENTS">
                    <div className="flex flex-wrap gap-1">
                      {wh.events.map(ev => (
                        <span key={ev} className="bg-slate-100 text-slate-600 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-tight">
                          {ev}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td data-label="STATUS">
                    <span className={`badge ${wh.active ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>
                      {wh.active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td data-label="ACTIONS" className="md:text-right">
                    <button className="btn btn-danger !p-2">
                      <Trash2 size={16} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
