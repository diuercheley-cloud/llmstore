import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

const DeveloperPortal: React.FC = () => {
    const navigate = useNavigate();
    const [apiKey, setApiKey] = useState('sk-proj-********************');

    const generateKey = () => {
        setApiKey(`sk-proj-${Math.random().toString(36).substring(2, 15)}`);
    };

    return (
        <div className="p-8 space-y-8">
            <header className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-black tracking-tight">DEVELOPER PORTAL</h1>
                    <p className="text-muted-foreground">Build, test, and deploy agents and plugins.</p>
                </div>
            </header>

            <section className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div className="bg-card p-6 rounded-xl border border-border space-y-4">
                    <h2 className="text-xl font-bold flex items-center gap-2">
                        <span className="p-1.5 bg-primary/10 text-primary rounded-md">🔑</span>
                        API KEYS
                    </h2>
                    <div className="flex items-center gap-2">
                        <code className="bg-muted p-2 rounded block w-full text-xs font-mono">{apiKey}</code>
                        <button onClick={generateKey} className="px-4 py-2 bg-primary text-primary-foreground font-black text-xs rounded-md">REVOKE & ROTATE</button>
                    </div>
                </div>

                <div className="bg-card p-6 rounded-xl border border-border space-y-4">
                    <h2 className="text-xl font-bold flex items-center gap-2">
                        <span className="p-1.5 bg-primary/10 text-primary rounded-md">📦</span>
                        CLI AGENTCTL
                    </h2>
                    <code className="bg-black text-white p-3 rounded block text-[10px] font-mono">
                        $ pip install agentctl<br/>
                        $ agentctl bundle init my-agent<br/>
                        $ agentctl bundle test .<br/>
                        $ agentctl bundle publish .
                    </code>
                </div>
            </section>

            <section className="space-y-4">
                <h2 className="text-xl font-bold">AGENT TEMPLATES</h2>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    {['support-triage', 'compliance-evidence', 'github-issue-triage'].map(t => (
                        <div key={t} className="p-4 border border-border rounded-lg hover:border-primary transition-colors cursor-pointer group">
                            <h3 className="font-bold uppercase text-xs">{t}</h3>
                            <p className="text-[10px] text-muted-foreground">Starter template for {t.replace('-', ' ')} agents.</p>
                            <div className="mt-2 text-primary font-black text-[9px]">USE TEMPLATE →</div>
                        </div>
                    ))}
                </div>
            </section>

            <section className="bg-card p-6 rounded-xl border border-border space-y-4">
                <h2 className="text-xl font-bold uppercase">Bundle Uploads</h2>
                <div className="border-2 border-dashed border-border rounded-lg p-12 text-center space-y-2">
                    <div className="text-4xl">📦</div>
                    <div className="text-sm font-bold">Drag and drop your agent bundle (.zip or manifest.json)</div>
                    <div className="text-xs text-muted-foreground">Manifest must be signed with your developer key for marketplace publication.</div>
                    <button 
                        onClick={() => navigate('/developers/bundles')}
                        className="mt-4 px-6 py-2 bg-primary text-primary-foreground font-black text-xs rounded-md"
                    >
                        GO TO BUNDLES PAGE
                    </button>
                </div>
            </section>
        </div>
    );
};

export default DeveloperPortal;
