import { useState } from 'react';
import { 
  LayoutDashboard, 
  Key, 
  FileText, 
  Wallet, 
  MessageSquare, 
  Database, 
  Webhook, 
  Palette,
  Menu,
  X
} from 'lucide-react';
import { Dashboard } from './components/Dashboard';
import { ApiKeys } from './components/ApiKeys';
import { Invoices } from './components/Invoices';
import { WalletRecharge } from './components/WalletRecharge';
import { ChatPlayground } from './components/ChatPlayground';
import { RagDocs } from './components/RagDocs';
import { Webhooks } from './components/Webhooks';
import { BrandingSettings } from './components/BrandingSettings';
import { Toaster } from 'sonner';

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'chat', label: 'Playground', icon: MessageSquare },
    { id: 'rag', label: 'RAG Documents', icon: FileText },
    { id: 'keys', label: 'API Keys', icon: Key },
    { id: 'invoices', label: 'Invoices', icon: FileText },
    { id: 'wallet', label: 'Wallet', icon: Wallet },
    { id: 'webhooks', label: 'Webhooks', icon: Webhook },
    { id: 'branding', label: 'Branding', icon: Palette },
  ];

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard': return <Dashboard />;
      case 'keys': return <ApiKeys />;
      case 'invoices': return <Invoices />;
      case 'wallet': return <WalletRecharge />;
      case 'chat': return <ChatPlayground />;
      case 'rag': return <RagDocs />;
      case 'webhooks': return <Webhooks />;
      case 'branding': return <BrandingSettings />;
      default: return <Dashboard />;
    }
  };

  const toggleSidebar = () => setIsSidebarOpen(!isSidebarOpen);

  return (
    <div className="flex min-h-screen bg-bg-base">
      <Toaster position="top-right" richColors />
      {/* Mobile Backdrop */}
      {isSidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 lg:hidden transition-opacity"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={`
        fixed lg:static inset-y-0 left-0 z-50
        w-64 bg-sidebar text-sidebar-text p-5
        transform transition-transform duration-300 ease-in-out
        ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <Database size={28} className="text-primary" />
            <span className="text-xl font-bold">LLM Portal</span>
          </div>
          <button onClick={toggleSidebar} className="lg:hidden">
            <X size={24} />
          </button>
        </div>
        
        <nav className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                onClick={() => {
                  setActiveTab(item.id);
                  setIsSidebarOpen(false);
                }}
                className={`
                  w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors
                  ${activeTab === item.id 
                    ? 'bg-primary text-white shadow-lg shadow-primary/20' 
                    : 'hover:bg-white/10'}
                `}
              >
                <Icon size={20} />
                <span className="font-medium">{item.label}</span>
              </button>
            );
          })}
        </nav>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-w-0">
        {/* Mobile Header */}
        <header className="lg:hidden flex items-center justify-between p-4 bg-white border-b border-border-base sticky top-0 z-30">
          <div className="flex items-center gap-2">
            <Database size={24} className="text-primary" />
            <span className="font-bold">LLM Portal</span>
          </div>
          <button 
            onClick={toggleSidebar}
            className="p-2 hover:bg-slate-100 rounded-lg"
          >
            <Menu size={24} />
          </button>
        </header>

        <div className="p-4 md:p-8 max-w-7xl mx-auto w-full">
          {renderContent()}
        </div>
      </main>
    </div>
  );
}

export default App;
