import { useState, useEffect } from 'react';
import { Download, Loader2, FileText, AlertCircle } from 'lucide-react';
import { api } from '../lib/api';
import type { Invoice } from '../lib/types';

export const Invoices = () => {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadInvoices = async () => {
      try {
        const data = await api.listPortalInvoices();
        setInvoices(data.invoices);
      } catch (err: any) {
        setError(err.message || 'Failed to load invoices');
      } finally {
        setLoading(false);
      }
    };
    loadInvoices();
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl md:text-3xl font-bold tracking-tight">Invoices</h1>

      <div className="card !p-0 overflow-hidden">
        {loading ? (
          <div className="p-12 flex flex-col items-center justify-center gap-4">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
            <p className="text-slate-500">Carregando faturas...</p>
          </div>
        ) : error ? (
          <div className="p-12 flex flex-col items-center justify-center gap-4 text-center">
            <AlertCircle className="w-12 h-12 text-red-500" />
            <p className="text-red-700 font-medium">{error}</p>
          </div>
        ) : (
          <div className="resp-table-container">
            <table className="resp-table">
              <thead>
                <tr>
                  <th>INVOICE NUMBER</th>
                  <th>PERIOD</th>
                  <th>AMOUNT</th>
                  <th>STATUS</th>
                  <th className="text-right">DOWNLOAD</th>
                </tr>
              </thead>
              <tbody>
                {invoices.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="text-center py-12 text-slate-400 italic">
                      Nenhuma fatura encontrada.
                    </td>
                  </tr>
                ) : invoices.map(inv => (
                  <tr key={inv.id}>
                    <td data-label="INVOICE" className="font-medium text-slate-900">
                      <div className="flex items-center gap-2">
                        <FileText size={16} className="text-slate-400" />
                        <span className="font-mono text-xs">{inv.id.slice(0, 8).toUpperCase()}</span>
                      </div>
                    </td>
                    <td data-label="PERIOD" className="text-slate-500 text-xs">
                      {new Date(inv.period_start).toLocaleDateString()} - {new Date(inv.period_end).toLocaleDateString()}
                    </td>
                    <td data-label="AMOUNT" className="font-bold text-slate-900">
                      {inv.currency} {inv.total_amount.toFixed(2)}
                    </td>
                    <td data-label="STATUS">
                      <span className={`badge ${inv.status === 'paid' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>
                        {inv.status.toUpperCase()}
                      </span>
                    </td>
                    <td data-label="DOWNLOAD" className="md:text-right">
                      <button className="btn btn-outline text-xs py-1 px-3 flex items-center gap-2 ml-auto">
                        <Download size={14} /> PDF
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
