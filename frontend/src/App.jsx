import { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1';

// We'll hardcode X-Merchant-Id to 1 for the challenge scope
const axiosInstance = axios.create({
  baseURL: API_BASE,
  headers: {
    'X-Merchant-Id': '1'
  }
});

function App() {
  const [merchant, setMerchant] = useState(null);
  const [amount, setAmount] = useState('');
  const [bankAccount, setBankAccount] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitError, setSubmitError] = useState('');
  const [submitSuccess, setSubmitSuccess] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchDashboard = async () => {
    try {
      const res = await axiosInstance.get('/merchants/me');
      setMerchant(res.data);
      setLoading(false);
    } catch (err) {
      console.error('Failed to fetch dashboard', err);
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
    // Poll every 3 seconds for live updates
    const interval = setInterval(fetchDashboard, 3000);
    return () => clearInterval(interval);
  }, []);

  const handlePayoutSubmit = async (e) => {
    e.preventDefault();
    setSubmitError('');
    setSubmitSuccess(false);
    setIsSubmitting(true);

    // Generate random UUID for idempotency key
    const idempotencyKey = crypto.randomUUID();

    try {
      await axiosInstance.post('/payouts', {
        amount_paise: parseInt(amount) * 100, // Assuming user inputs INR, convert to paise
        bank_account_id: bankAccount
      }, {
        headers: {
          'Idempotency-Key': idempotencyKey
        }
      });
      setSubmitSuccess(true);
      setAmount('');
      setBankAccount('');
      fetchDashboard(); // Immediate refresh
    } catch (err) {
      setSubmitError(err.response?.data?.error || 'Failed to submit payout');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) {
    return <div className="flex h-screen items-center justify-center font-bold text-xl text-blue-400">Loading Dashboard...</div>;
  }

  if (!merchant) {
    return <div className="flex h-screen items-center justify-center font-bold text-xl text-red-400">Failed to load merchant data. Ensure backend is running.</div>;
  }

  return (
    <div className="w-full min-h-screen p-8 selection:bg-blue-500/30">
      <div className="max-w-6xl mx-auto space-y-8">
        
        {/* Header */}
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-emerald-400">
              Playto Pay
            </h1>
            <p className="text-slate-400 mt-1">Founding Engineer Challenge</p>
          </div>
          <div className="px-4 py-2 bg-slate-800/50 rounded-full border border-slate-700 backdrop-blur-md">
            <span className="text-sm text-slate-300">Merchant:</span>
            <span className="ml-2 font-semibold text-white">{merchant.name}</span>
          </div>
        </header>

        {/* Top Row: Balances & Payout Form */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Balance Cards */}
          <div className="lg:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-slate-800/40 p-6 rounded-2xl border border-slate-700/50 backdrop-blur-md shadow-xl transition-all hover:border-blue-500/50">
              <h3 className="text-slate-400 font-medium text-sm">Available Balance</h3>
              <div className="mt-4 flex items-baseline">
                <span className="text-4xl font-bold text-white">₹{(merchant.available_balance / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
              </div>
            </div>
            <div className="bg-slate-800/40 p-6 rounded-2xl border border-slate-700/50 backdrop-blur-md shadow-xl transition-all hover:border-amber-500/50">
              <h3 className="text-slate-400 font-medium text-sm">Held Funds <span className="text-xs ml-2 bg-amber-500/20 text-amber-300 px-2 py-0.5 rounded-full">Processing</span></h3>
              <div className="mt-4 flex items-baseline">
                <span className="text-4xl font-bold text-white">₹{(merchant.held_balance / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
              </div>
            </div>
          </div>

          {/* Request Payout Form */}
          <div className="bg-slate-800/60 p-6 rounded-2xl border border-slate-700/50 backdrop-blur-md shadow-xl relative overflow-hidden group">
            <div className="absolute top-0 right-0 p-32 bg-blue-500/10 rounded-full blur-3xl -mr-16 -mt-16 transition-transform group-hover:scale-110"></div>
            <h3 className="text-lg font-bold text-white mb-4">Request Payout</h3>
            <form onSubmit={handlePayoutSubmit} className="space-y-4 relative z-10">
              {submitError && <div className="text-red-400 text-sm bg-red-400/10 p-2 rounded">{submitError}</div>}
              {submitSuccess && <div className="text-emerald-400 text-sm bg-emerald-400/10 p-2 rounded">Payout requested successfully!</div>}
              
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Amount (INR)</label>
                <input 
                  type="number" 
                  min="1"
                  required
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all font-mono"
                  placeholder="e.g. 5000"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Bank Account ID</label>
                <input 
                  type="text" 
                  required
                  value={bankAccount}
                  onChange={(e) => setBankAccount(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all font-mono"
                  placeholder="acc_123456"
                />
              </div>
              <button 
                type="submit" 
                disabled={isSubmitting}
                className="w-full bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white font-semibold py-2.5 rounded-lg shadow-lg hover:shadow-blue-500/25 transition-all outline-none focus:ring-2 focus:ring-blue-500/50 focus:ring-offset-2 focus:ring-offset-slate-900 disabled:opacity-50"
              >
                {isSubmitting ? 'Processing...' : 'Withdraw Funds'}
              </button>
            </form>
          </div>
        </div>

        {/* Bottom Row: History */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          
          {/* Recent Ledger Entries */}
          <div className="bg-slate-800/30 p-6 rounded-2xl border border-slate-700/30 backdrop-blur-md">
            <h3 className="text-lg font-bold text-white mb-4">Ledger History</h3>
            <div className="space-y-3">
              {merchant.recent_transactions.map(txn => (
                <div key={txn.id} className="flex justify-between items-center p-3 rounded-xl bg-slate-800/50 hover:bg-slate-700/50 transition-colors border border-slate-700/30">
                  <div>
                    <div className="text-sm font-medium text-slate-200">{txn.reference || 'Transfer'}</div>
                    <div className="text-xs text-slate-500">{new Date(txn.created_at).toLocaleString()}</div>
                  </div>
                  <div className={`font-mono font-bold ${txn.entry_type === 'CREDIT' ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {txn.entry_type === 'CREDIT' ? '+' : '-'}₹{(txn.amount / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                  </div>
                </div>
              ))}
              {merchant.recent_transactions.length === 0 && <p className="text-slate-500 text-sm">No recent transactions.</p>}
            </div>
          </div>

          {/* Recent Payouts */}
          <div className="bg-slate-800/30 p-6 rounded-2xl border border-slate-700/30 backdrop-blur-md">
            <h3 className="text-lg font-bold text-white mb-4">Payouts</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-300">
                <thead className="text-xs text-slate-500 uppercase bg-slate-800/80 rounded-t-lg">
                  <tr>
                    <th className="px-4 py-3 rounded-tl-lg">ID</th>
                    <th className="px-4 py-3">Amount</th>
                    <th className="px-4 py-3">Account</th>
                    <th className="px-4 py-3 rounded-tr-lg text-right">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {merchant.recent_payouts.map(p => (
                    <tr key={p.id} className="border-b border-slate-700/50 hover:bg-slate-800/40 transition-colors">
                      <td className="px-4 py-3 font-mono text-slate-400">...{p.idempotency_key.substring(p.idempotency_key.length-8)}</td>
                      <td className="px-4 py-3 font-medium text-white">₹{(p.amount_paise / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                      <td className="px-4 py-3 font-mono text-xs">{p.bank_account_id}</td>
                      <td className="px-4 py-3 text-right">
                        <span className={`px-2 py-1 rounded-full text-xs font-semibold
                          ${p.status === 'COMPLETED' ? 'bg-emerald-500/20 text-emerald-400' : ''}
                          ${p.status === 'PROCESSING' || p.status === 'PENDING' ? 'bg-amber-500/20 text-amber-400 animate-pulse' : ''}
                          ${p.status === 'FAILED' ? 'bg-rose-500/20 text-rose-400' : ''}
                        `}>
                          {p.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                  {merchant.recent_payouts.length === 0 && (
                    <tr><td colSpan="4" className="px-4 py-3 text-slate-500 text-center">No payouts found.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}

export default App;
