import { useState } from 'react';
import { 
  LayoutDashboard, 
  Key, 
  FileText, 
  Wallet, 
  Webhook, 
  Palette,
  Bot,
  Bell,
  Settings
} from 'lucide-react';
import { Dashboard } from './components/Dashboard';
import { ApiKeys } from './components/ApiKeys';
import { Invoices } from './components/Invoices';
import { WalletRecharge } from './components/WalletRecharge';
import { AgentChat } from './pages/AgentChat';
import { RagDocs } from './components/RagDocs';
import { Webhooks } from './components/Webhooks';
import { BrandingSettings } from './components/BrandingSettings';
import { MobileShell } from './mobile/MobileShell';
import { PushSettings } from './mobile/PushSettings';
import { Toaster } from 'sonner';

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard size={20} /> },
    { id: 'chat', label: 'AI Assistant', icon: <Bot size={20} /> },
    { id: 'rag', label: 'RAG Documents', icon: <FileText size={20} /> },
    { id: 'keys', label: 'API Keys', icon: <Key size={20} /> },
    { id: 'invoices', label: 'Invoices', icon: <FileText size={20} /> },
    { id: 'wallet', label: 'Wallet', icon: <Wallet size={20} /> },
    { id: 'webhooks', label: 'Webhooks', icon: <Webhook size={20} /> },
    { id: 'branding', label: 'Branding', icon: <Palette size={20} /> },
    { id: 'notifications', label: 'Notifications', icon: <Bell size={20} /> },
    { id: 'settings', label: 'Settings', icon: <Settings size={20} /> },
  ];

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard': return <Dashboard />;
      case 'keys': return <ApiKeys />;
      case 'invoices': return <Invoices />;
      case 'wallet': return <WalletRecharge />;
      case 'chat': return <AgentChat />;
      case 'rag': return <RagDocs />;
      case 'webhooks': return <Webhooks />;
      case 'branding': return <BrandingSettings />;
      case 'notifications': return <PushSettings />;
      case 'settings': return <PushSettings />;
      default: return <Dashboard />;
    }
  };

  return (
    <>
      <Toaster position="top-right" richColors />
      <MobileShell
        navItems={navItems}
        activeTab={activeTab}
        onTabChange={setActiveTab}
      >
        {renderContent()}
      </MobileShell>
    </>
  );
}

export default App;
