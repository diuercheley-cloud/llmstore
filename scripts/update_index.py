import re

with open('control_plane/app/static/portal/index.html', 'r') as f:
    content = f.read()

# 1. Add nav item
nav_item = """        <div class="nav-item" data-tab="demo" id="navDemoTab" style="display: none; background: #e0f2fe; color: #1e40af;">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"></path><path d="M2 17l10 5 10-5M2 12l10 5 10-5"></path></svg>
          Demo Local
        </div>
"""
content = content.replace('      </nav>', nav_item + '      </nav>')

# 2. Add demoTab content
demo_tab = """
        <!-- Demo Tab -->
        <div id="demoTab" class="tab-content">
          <div style="background: #e0f2fe; border: 1px solid #bae6fd; padding: 1rem; border-radius: 0.5rem; margin-bottom: 1.5rem;">
            <h2 style="color: #1e40af; margin-bottom: 0.5rem; font-size: 1.25rem;">Ambiente de Demonstração</h2>
            <p style="margin: 0; font-size: 0.875rem; color: #0369a1;">Você está no modo Demo Local. Funcionalidades e atalhos simplificados foram habilitados para exibir as capacidades do sistema.</p>
          </div>
          
          <div class="card-grid" style="margin-bottom: 1.5rem;">
            <section style="border-color: #bae6fd;">
              <h3>Status do Cliente Demo</h3>
              <div id="demoClientStatus"></div>
            </section>
            
            <section style="border-color: #bae6fd;">
              <h3>Atalhos Rápidos</h3>
              <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                <button class="secondary" onclick="switchTab('usage')">Ver Consumo Detalhado</button>
                <button class="secondary" onclick="switchTab('api-keys')">Minha API Key Completa</button>
                <button class="secondary" id="demoViewInvoices">Ver Faturas Demo</button>
              </div>
            </section>
          </div>
          
          <section>
            <h3>Minha API Key (Demo)</h3>
            <p style="font-size: 0.875rem; color: var(--muted); margin-bottom: 1rem;">A chave demo completa está em <code>.local/demo-client.env</code>. Para acesso seguro em produção, nunca exponha a chave completa na tela.</p>
            <div id="demoApiKeyInfo" style="font-family: monospace; background: var(--bg); padding: 1rem; border-radius: 0.5rem; border: 1px solid var(--border);"></div>
          </section>

          <div class="card-grid" style="margin-bottom: 1.5rem;">
            <section>
              <h3>Testar Chat</h3>
              <div class="chat-interface">
                <div style="display: flex; gap: 1rem; margin-bottom: 1rem;">
                  <div style="flex: 1;">
                    <div class="field-label">Modelo</div>
                    <select id="demoModelSelect"></select>
                  </div>
                </div>
                <div>
                  <div class="field-label">Prompt Demo</div>
                  <textarea id="demoPrompt" style="min-height: 80px;">Olá! Como você pode me ajudar hoje?</textarea>
                </div>
                <div style="display: flex; justify-content: flex-end;">
                  <button id="demoRunChat" style="width: 150px;">Enviar</button>
                </div>
                <div class="field-label">Resposta</div>
                <div id="demoChatResponse" class="chat-response">Aguardando prompt...</div>
                <div id="demoChatStats" style="font-size: 0.75rem; color: var(--muted); text-align: right;"></div>
              </div>
            </section>

            <section>
              <h3>Testar RAG</h3>
              <div class="chat-interface">
                <div style="margin-bottom: 1rem;">
                  <div class="field-label">Documentos Disponíveis (Demo)</div>
                  <div id="demoRagDocs" style="font-size: 0.875rem; background: var(--bg); padding: 0.5rem; border-radius: 0.25rem;">Carregando...</div>
                </div>
                <div>
                  <div class="field-label">Pergunta Demo</div>
                  <textarea id="demoRagQuery" style="min-height: 80px;">Quais produtos a empresa demo oferece?</textarea>
                </div>
                <div style="display: flex; justify-content: flex-end;">
                  <button id="demoRunRag" style="width: 150px;">Consultar Documento</button>
                </div>
                <div class="field-label">Resposta RAG</div>
                <div id="demoRagResponse" class="chat-response">Aguardando consulta...</div>
              </div>
            </section>
          </div>
        </div>
"""
content = content.replace('      <div class="content-area">', '      <div class="content-area">\n' + demo_tab)

# 3. Add references to new elements in state & els
state_add = """        demoMode: false,
"""
content = content.replace('apiKey: \'\',', 'apiKey: \'\',\n' + state_add)

els_add = """        navDemoTab: document.getElementById('navDemoTab'),
        demoClientStatus: document.getElementById('demoClientStatus'),
        demoApiKeyInfo: document.getElementById('demoApiKeyInfo'),
        demoModelSelect: document.getElementById('demoModelSelect'),
        demoPrompt: document.getElementById('demoPrompt'),
        demoRunChat: document.getElementById('demoRunChat'),
        demoChatResponse: document.getElementById('demoChatResponse'),
        demoChatStats: document.getElementById('demoChatStats'),
        demoRagDocs: document.getElementById('demoRagDocs'),
        demoRagQuery: document.getElementById('demoRagQuery'),
        demoRunRag: document.getElementById('demoRunRag'),
        demoViewInvoices: document.getElementById('demoViewInvoices'),
"""
content = content.replace('sidebarNav: document.getElementById(\'sidebarNav\'),', 'sidebarNav: document.getElementById(\'sidebarNav\'),\n' + els_add)

# 4. Modify initPortal to handle demo mode
init_portal_add = """
        state.demoMode = me.demo_mode === true;
        if (state.demoMode) {
          els.navDemoTab.style.display = 'flex';
          switchTab('demo');
        }
        
        renderDemoInfo(me, usage);
"""
content = content.replace('renderOverview(me, usage);', 'renderOverview(me, usage);\n' + init_portal_add)
content = content.replace('renderModelSelects();', 'renderModelSelects();\n        renderDemoModelSelect();')

# 5. Add new functions for demo tab
demo_functions = """
      function renderDemoModelSelect() {
        if (!els.demoModelSelect) return;
        els.demoModelSelect.innerHTML = state.models.map(m => `<option value="${m.id}">${m.display_name} (${m.id})</option>`).join('');
      }

      async function renderDemoInfo(me, usage) {
        if (!state.demoMode) return;
        
        const m = usage.monthly_usage;
        const pct = Math.min(100, (m.used_tokens / m.quota) * 100);
        
        els.demoClientStatus.innerHTML = `
          <div class="field"><div class="field-label">Cliente</div><div class="field-value">${me.name}</div></div>
          <div class="field"><div class="field-label">Plano Demo</div><div class="field-value">${me.plan.name} (${me.plan.currency} ${me.plan.monthly_price})</div></div>
          <div class="field"><div class="field-label">Consumo Mês</div><div class="field-value">${m.used_tokens.toLocaleString()} / ${m.quota.toLocaleString()} tokens (${pct.toFixed(1)}%)</div></div>
          <div class="field"><div class="field-label">Billing Local</div><div class="field-value"><span class="badge ${me.billing_status === 'active' ? 'badge-active' : 'badge-warning'}">${me.billing_status.toUpperCase()}</span></div></div>
        `;
        
        try {
          const keys = await apiFetch('/portal/api-keys');
          if (keys && keys.length > 0) {
             const k = keys[0];
             els.demoApiKeyInfo.innerHTML = `Prefixo da Chave: <strong>${k.key_prefix}...</strong><br>Status: ${k.is_active ? 'Ativa' : 'Inativa'}`;
          } else {
             els.demoApiKeyInfo.innerHTML = 'Nenhuma chave encontrada. Por favor, crie uma na aba "Minha API Key".';
          }
        } catch(e) {}
        
        loadDemoRagDocs();
      }
      
      async function loadDemoRagDocs() {
        try {
          const files = await apiFetch('/client/rag/documents');
          if (files && files.data && files.data.length > 0) {
            els.demoRagDocs.innerHTML = files.data.map(f => `• ${esc(f.original_filename)} (${f.status})`).join('<br>');
          } else {
            els.demoRagDocs.innerHTML = 'Nenhum documento RAG encontrado.';
          }
        } catch(e) {
          els.demoRagDocs.innerHTML = 'Erro ao carregar documentos RAG.';
        }
      }

      if (els.demoViewInvoices) {
        els.demoViewInvoices.addEventListener('click', async () => {
           switchTab('overview');
           setTimeout(() => {
             const btn = document.getElementById('viewInvoicesBtn');
             if (btn) btn.click();
           }, 100);
        });
      }

      if (els.demoRunChat) {
        els.demoRunChat.addEventListener('click', async () => {
          const prompt = els.demoPrompt.value.trim();
          if (!prompt) return;
          
          els.demoRunChat.disabled = true;
          els.demoChatResponse.textContent = 'Processando chat demo...';
          const start = performance.now();
          
          try {
            const result = await apiFetch('/portal/test-chat', {
              method: 'POST',
              body: JSON.stringify({
                prompt,
                model: els.demoModelSelect.value,
                max_tokens: 512
              })
            });
            const latency = (performance.now() - start).toFixed(0);
            els.demoChatResponse.textContent = result.text;
            els.demoChatStats.textContent = `Latência: ${latency}ms | Modelo: ${result.model} | Cache: ${result.cached ? 'Sim' : 'Não'}`;
          } catch (err) {
            els.demoChatResponse.innerHTML = `<span style="color: var(--danger);">Erro: ${err.message}</span>`;
          } finally {
            els.demoRunChat.disabled = false;
          }
        });
      }

      if (els.demoRunRag) {
        els.demoRunRag.addEventListener('click', async () => {
          const question = els.demoRagQuery.value.trim();
          if (!question) return;
          
          els.demoRunRag.disabled = true;
          els.demoRagResponse.textContent = 'Consultando RAG demo...';
          try {
            const result = await apiFetch('/client/rag/query', {
              method: 'POST',
              body: JSON.stringify({ question, top_k: 3 })
            });
            let ans = result.answer;
            if (result.sources && result.sources.length > 0) {
              ans += '\\n\\nFontes:\\n' + result.sources.map(s => `- ${s.filename}`).join('\\n');
            }
            els.demoRagResponse.textContent = ans;
          } catch (err) {
            els.demoRagResponse.innerHTML = `<span style="color: var(--danger);">Erro: ${err.message}</span>`;
          } finally {
            els.demoRunRag.disabled = false;
          }
        });
      }
"""
content = content.replace('window.deleteFile = async (id) => {', demo_functions + '\n      window.deleteFile = async (id) => {')

with open('control_plane/app/static/portal/index.html', 'w') as f:
    f.write(content)
