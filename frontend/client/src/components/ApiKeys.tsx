import { useState } from 'react';
import { Plus, Trash2, RefreshCw } from 'lucide-react';

export const ApiKeys = () => {
  const [keys] = useState([
    { id: '1', name: 'Production', prefix: 'sk-prod-...', lastUsed: '2026-05-20 10:15', created: '2026-01-10' },
    { id: '2', name: 'Development', prefix: 'sk-dev-...', lastUsed: '2026-05-19 14:20', created: '2026-02-15' },
  ]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <h1 className="text-2xl md:text-3xl font-bold tracking-tight">API Keys</h1>
        <button className="btn btn-primary w-full sm:w-auto">
          <Plus size={18} /> Create New Key
        </button>
      </div>

      <div className="card !p-0 overflow-hidden">
        <div className="resp-table-container">
          <table className="resp-table">
            <thead>
              <tr>
                <th>NAME</th>
                <th>KEY PREFIX</th>
                <th>CREATED</th>
                <th>LAST USED</th>
                <th className="text-right">ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              {keys.map(k => (
                <tr key={k.id}>
                  <td data-label="NAME" className="font-medium text-slate-900">{k.name}</td>
                  <td data-label="KEY PREFIX"><code className="bg-slate-100 px-2 py-1 rounded text-primary font-mono text-xs">{k.prefix}</code></td>
                  <td data-label="CREATED" className="text-slate-500">{k.created}</td>
                  <td data-label="LAST USED" className="text-slate-500">{k.lastUsed}</td>
                  <td data-label="ACTIONS" className="md:text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button className="btn btn-outline !p-2" title="Rotate Key"><RefreshCw size={16} /></button>
                      <button className="btn btn-danger !p-2" title="Revoke"><Trash2 size={16} /></button>
                    </div>
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
