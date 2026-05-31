import { useState } from 'react';
import { Database, Loader2, CheckCircle, Copy, ArrowRight } from 'lucide-react';
import { toast } from 'sonner';

interface SignupResult {
  api_key: string;
  client_id: string;
  plan_name: string;
  portal_url: string;
}

export function Signup({ onComplete }: { onComplete: (result: SignupResult) => void }) {
  const [step, setStep] = useState<'form' | 'result'>('form');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SignupResult | null>(null);
  const [form, setForm] = useState({ name: '', email: '', company: '' });

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const resp = await fetch('/public/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: form.name,
          email: form.email,
          company: form.company || undefined,
        }),
      });
      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || 'Signup failed');
      }
      const data = await resp.json();
      setResult({
        api_key: data.api_key,
        client_id: data.client_id,
        plan_name: data.plan_name,
        portal_url: data.portal_url,
      });
      setStep('result');
      toast.success('Account created successfully!');
    } catch (err: any) {
      toast.error(err.message || 'Failed to create account');
    } finally {
      setLoading(false);
    }
  };

  const copyKey = () => {
    if (!result) return;
    navigator.clipboard.writeText(result.api_key);
    toast.success('API key copied to clipboard');
  };

  if (step === 'result' && result) {
    return (
      <div className="min-h-screen bg-bg-base flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-xl p-8 text-center">
          <div className="flex justify-center mb-4">
            <div className="p-3 bg-green-100 text-green-600 rounded-full">
              <CheckCircle size={32} />
            </div>
          </div>
          <h2 className="text-2xl font-bold mb-2">Welcome!</h2>
          <p className="text-gray-500 mb-6">Your account is ready. Save your API key now.</p>
          <div className="bg-gray-50 rounded-xl p-4 mb-6 text-left">
            <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Your API Key</label>
            <div className="flex items-center gap-2 mt-1">
              <code className="flex-1 text-sm font-mono bg-white border rounded-lg px-3 py-2 truncate">
                {result.api_key}
              </code>
              <button onClick={copyKey} className="p-2 hover:bg-gray-200 rounded-lg transition-colors">
                <Copy size={18} />
              </button>
            </div>
            <p className="text-xs text-red-500 mt-2">This key is shown once. Store it securely.</p>
          </div>
          <button
            onClick={() => onComplete(result)}
            className="w-full bg-primary text-white font-semibold py-3 rounded-xl hover:opacity-90 flex items-center justify-center gap-2 transition-all"
          >
            Enter Dashboard <ArrowRight size={18} />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-bg-base flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-xl p-8">
        <div className="flex justify-center mb-6">
          <div className="p-3 bg-primary/10 text-primary rounded-full">
            <Database size={28} />
          </div>
        </div>
        <h1 className="text-2xl font-bold text-center mb-2">Get Started</h1>
        <p className="text-gray-500 text-center mb-8">Create your account to access the LLM Portal.</p>
        <form onSubmit={handleSignup} className="space-y-4">
          <div>
            <label className="block text-sm font-semibold mb-1">Name</label>
            <input
              type="text"
              required
              placeholder="Your name"
              className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-primary focus:border-primary outline-none"
              value={form.name}
              onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
            />
          </div>
          <div>
            <label className="block text-sm font-semibold mb-1">Email</label>
            <input
              type="email"
              required
              placeholder="you@example.com"
              className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-primary focus:border-primary outline-none"
              value={form.email}
              onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
            />
          </div>
          <div>
            <label className="block text-sm font-semibold mb-1">Company (optional)</label>
            <input
              type="text"
              placeholder="Your company"
              className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-primary focus:border-primary outline-none"
              value={form.company}
              onChange={e => setForm(f => ({ ...f, company: e.target.value }))}
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-primary text-white font-semibold py-3 rounded-xl hover:opacity-90 flex items-center justify-center gap-2 transition-all disabled:opacity-50"
          >
            {loading ? <Loader2 size={18} className="animate-spin" /> : null}
            {loading ? 'Creating account...' : 'Create Account'}
          </button>
        </form>
        <p className="text-xs text-gray-400 text-center mt-6">
          By signing up you agree to our Terms of Service and Privacy Policy.
        </p>
      </div>
    </div>
  );
}
