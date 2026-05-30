import { useState, useEffect, useCallback } from 'react';
import { X, Menu, Database } from 'lucide-react';
import type { ReactNode } from 'react';

interface MobileShellProps {
  children: ReactNode;
  navItems: Array<{ id: string; label: string; icon: ReactNode }>;
  activeTab: string;
  onTabChange: (tab: string) => void;
}

export function MobileShell({ children, navItems, activeTab, onTabChange }: MobileShellProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 1024);
    check();
    window.addEventListener('resize', check);
    return () => window.removeEventListener('resize', check);
  }, []);

  const handleTabChange = useCallback((tab: string) => {
    onTabChange(tab);
    setSidebarOpen(false);
  }, [onTabChange]);

  return (
    <div className="flex min-h-[100dvh] bg-bg-base">
      {/* Mobile backdrop */}
      {sidebarOpen && isMobile && (
        <div
          className="fixed inset-0 bg-black/50 z-40 transition-opacity"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed inset-y-0 left-0 z-50
          w-64 bg-sidebar text-sidebar-text p-5
          transform transition-transform duration-300 ease-in-out
          ${sidebarOpen || !isMobile ? 'translate-x-0' : '-translate-x-full'}
          ${isMobile ? 'shadow-2xl' : 'lg:static'}
        `}
      >
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <Database size={28} className="text-primary" />
            <span className="text-xl font-bold">LLM Portal</span>
          </div>
          {isMobile && (
            <button onClick={() => setSidebarOpen(false)} className="p-1 hover:bg-white/10 rounded-lg">
              <X size={24} />
            </button>
          )}
        </div>
        <nav className="space-y-1">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => handleTabChange(item.id)}
              className={`
                w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors
                ${activeTab === item.id
                  ? 'bg-primary text-white shadow-lg shadow-primary/20'
                  : 'hover:bg-white/10'}
              `}
            >
              {item.icon}
              <span className="font-medium">{item.label}</span>
            </button>
          ))}
        </nav>
      </aside>

      {/* Main */}
      <main className="flex-1 flex flex-col min-w-0">
        {isMobile && (
          <header className="flex items-center justify-between p-4 bg-white border-b border-border-base sticky top-0 z-30">
            <div className="flex items-center gap-2">
              <Database size={24} className="text-primary" />
              <span className="font-bold">LLM Portal</span>
            </div>
            <button
              onClick={() => setSidebarOpen(true)}
              className="p-2 hover:bg-slate-100 rounded-lg"
            >
              <Menu size={24} />
            </button>
          </header>
        )}
        <div className="p-4 md:p-8 max-w-7xl mx-auto w-full">
          {children}
        </div>
      </main>
    </div>
  );
}
