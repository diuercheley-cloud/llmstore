import { Download } from 'lucide-react';

export const Invoices = () => {
  const invoices = [
    { id: 'INV-001', date: '2026-05-01', amount: '$45.00', status: 'Paid' },
    { id: 'INV-002', date: '2026-04-01', amount: '$32.50', status: 'Paid' },
    { id: 'INV-003', date: '2026-03-01', amount: '$12.00', status: 'Paid' },
  ];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl md:text-3xl font-bold tracking-tight">Invoices</h1>

      <div className="card !p-0 overflow-hidden">
        <div className="resp-table-container">
          <table className="resp-table">
            <thead>
              <tr>
                <th>INVOICE NUMBER</th>
                <th>DATE</th>
                <th>AMOUNT</th>
                <th>STATUS</th>
                <th className="text-right">DOWNLOAD</th>
              </tr>
            </thead>
            <tbody>
              {invoices.map(inv => (
                <tr key={inv.id}>
                  <td data-label="INVOICE" className="font-medium text-slate-900">{inv.id}</td>
                  <td data-label="DATE" className="text-slate-500">{inv.date}</td>
                  <td data-label="AMOUNT" className="font-bold text-slate-900">{inv.amount}</td>
                  <td data-label="STATUS">
                    <span className="badge bg-emerald-100 text-emerald-700">{inv.status}</span>
                  </td>
                  <td data-label="DOWNLOAD" className="md:text-right">
                    <button className="btn btn-outline text-xs py-1 px-3">
                      <Download size={14} /> PDF
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
