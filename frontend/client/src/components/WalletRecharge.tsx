import { useState, useEffect } from 'react';
import { QrCode, X, Copy, CheckCircle2, Wallet as WalletIcon, History, Loader2, AlertCircle } from 'lucide-react';
import { api } from '../lib/api';
import type { Wallet, WalletTransaction } from '../lib/types';
import { toast } from 'sonner';

export const WalletRecharge = () => {
  const [wallet, setWallet] = useState<Wallet | null>(null);
  const [loading, setLoading] = useState(true);
  const [amount, setAmount] = useState('');
  const [showPix, setShowPix] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const loadWallet = async () => {
      try {
        const data = await api.getWallet();
        setWallet(data);
      } catch (err: any) {
        console.error('Failed to load wallet', err);
      } finally {
        setLoading(false);
      }
    };
    loadWallet();
  }, []);

  const handleCopy = () => {
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    toast.info("Código PIX copiado.");
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] gap-4">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
        <p className="text-slate-500">Carregando carteira...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl md:text-3xl font-bold tracking-tight">Wallet</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card h-fit">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 bg-emerald-100 text-emerald-600 rounded-lg">
              <WalletIcon size={24} />
            </div>
            <div>
              <h2 className="text-xl font-bold">Balance</h2>
              <p className="text-slate-500 text-sm">Available funds for usage</p>
            </div>
          </div>

          <div className="text-4xl font-black text-slate-900 mb-8">
            R$ {wallet?.available_brl?.toFixed(2) || '0.00'}
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Amount to recharge (BRL)</label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 font-medium">R$</span>
                <input 
                  type="number" 
                  className="input-field pl-10 text-lg" 
                  placeholder="0.00" 
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                />
              </div>
            </div>
            <button 
              className="btn btn-primary w-full py-3 text-lg" 
              onClick={() => setShowPix(true)}
              disabled={!amount || parseFloat(amount) <= 0}
            >
              <QrCode size={20} /> Generate PIX QR Code
            </button>
          </div>
          
          {wallet?.low_balance && (
            <div className="mt-6 p-4 bg-amber-50 border border-amber-100 rounded-xl flex gap-3">
              <AlertCircle className="text-amber-500 shrink-0" size={20} />
              <p className="text-sm text-amber-700">Saldo baixo. Recomendamos recarga para evitar interrupções.</p>
            </div>
          )}
        </div>

        <div className="card !p-0 overflow-hidden">
          <div className="p-6 border-b border-border-base flex items-center gap-2">
            <History size={18} className="text-slate-400" />
            <h3 className="font-bold">Recent Transactions</h3>
          </div>
          <div className="divide-y divide-border-base">
            {!wallet?.transactions?.length ? (
              <div className="p-12 text-center text-slate-400 italic">Nenhuma transação registrada.</div>
            ) : wallet.transactions.map((tx: WalletTransaction) => (
              <div key={tx.id} className="p-4 hover:bg-slate-50 transition-colors flex items-center justify-between">
                <div>
                  <div className="font-bold text-sm text-slate-900 capitalize">{tx.type.replace('_', ' ')}</div>
                  <div className="text-xs text-slate-500">{new Date(tx.created_at).toLocaleString()}</div>
                </div>
                <div className={`font-mono font-bold ${tx.amount_brl > 0 ? 'text-emerald-600' : 'text-slate-900'}`}>
                  {tx.amount_brl > 0 ? '+' : ''}{tx.amount_brl.toFixed(2)}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {showPix && (
        <div className="fixed inset-0 z-[100] flex items-end sm:items-center justify-center p-0 sm:p-4">
          <div className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm" onClick={() => setShowPix(false)} />
          
          <div className="relative bg-white w-full sm:max-w-md h-[90vh] sm:h-auto rounded-t-3xl sm:rounded-2xl shadow-2xl overflow-hidden animate-in slide-in-from-bottom duration-300">
            <div className="flex items-center justify-between p-6 border-b border-border-base">
              <h3 className="text-xl font-bold">Pay with PIX</h3>
              <button onClick={() => setShowPix(false)} className="p-2 hover:bg-slate-100 rounded-full transition-colors">
                <X size={24} />
              </button>
            </div>

            <div className="p-8 text-center space-y-6 overflow-y-auto">
              <div className="p-4 bg-blue-50 border border-blue-100 rounded-xl text-blue-700 text-sm flex gap-3 text-left">
                <AlertCircle size={20} className="shrink-0" />
                <p>Ambiente de Demonstração: O pagamento não é real. O saldo será atualizado após clicar no botão abaixo.</p>
              </div>

              <div>
                <div className="text-sm text-slate-500 font-medium uppercase tracking-wider">Total Amount</div>
                <div className="text-4xl font-black text-slate-900 mt-1">R$ {parseFloat(amount).toFixed(2)}</div>
              </div>

              <div className="bg-slate-50 p-6 rounded-2xl border-2 border-dashed border-border-base inline-block">
                <QrCode size={200} className="mx-auto text-slate-900" />
              </div>

              <div className="space-y-3">
                <p className="text-sm text-slate-600 font-medium text-left">Copy and paste code:</p>
                <div className="flex gap-2">
                  <div className="flex-1 bg-slate-100 p-3 rounded-lg text-xs font-mono text-slate-600 break-all text-left line-clamp-2">
                    00020101021126580014br.gov.bcb.pix0136e2940342-b68b-4ad7-b8f3-e59325603...
                  </div>
                  <button 
                    onClick={handleCopy}
                    className={`btn ${copied ? 'bg-emerald-500 text-white' : 'btn-outline'} shrink-0 px-4`}
                  >
                    {copied ? <CheckCircle2 size={18} /> : <Copy size={18} />}
                  </button>
                </div>
              </div>

              <div className="pt-4">
                <button className="btn btn-outline w-full py-3" onClick={() => setShowPix(false)}>
                  I've made the payment
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
