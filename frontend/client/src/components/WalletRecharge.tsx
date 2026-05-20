import { useState } from 'react';
import { QrCode, X, Copy, CheckCircle2 } from 'lucide-react';

export const WalletRecharge = () => {
  const [amount, setAmount] = useState('');
  const [showPix, setShowPix] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl md:text-3xl font-bold tracking-tight">Wallet Recharge</h1>
      
      <div className="card max-w-xl mx-auto lg:mx-0">
        <h2 className="text-xl font-bold mb-6">Add Funds via PIX</h2>
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
        <p className="mt-6 text-sm text-slate-500 text-center">
          The balance will be available in your account immediately after payment confirmation.
        </p>
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
