# Local AI Appliance - Branding & Identity

## Nome da Release/Produto Padrão
**Local AI Appliance**

## Posicionamento
O "Local AI Appliance" é a consolidação da linha v1.6.x (v1.7.0) e representa a transição de um repositório isolado de APIs para um produto completo, empacotado e pronto para implantação on-premise/air-gapped. 

## Tagline Padrão
"Private local AI infrastructure for teams and clients."

## Descrição Curta
"A local, OpenAI-compatible AI appliance with admin, client portal, RAG, TTS, billing, security and readiness tooling."

## Descrição Longa
O Local AI Appliance é uma solução completa de infraestrutura de Inteligência Artificial desenhada para operação estritamente local (on-premise ou air-gapped). Ele inclui inferência compatível com APIs da OpenAI, geração aumentada por recuperação (RAG) multi-tenant, text-to-speech (TTS), e ferramentas robustas de operação, vendas (CRM) e faturamento offline. É a base ideal para empresas que exigem máxima privacidade de dados e controle total sobre seu ciclo de IA, sem depender de nuvens externas.

## Textos para Landing Page
- **Hero Title:** Local AI Appliance
- **Hero Subtitle:** Private local AI infrastructure for teams and clients.
- **Body:** Deliver production-ready AI without compromising data privacy. Includes everything you need: OpenAI-compatible APIs, Client Portal, Admin Dashboard, RAG, TTS, and offline billing tools.

## Textos para Proposta Comercial
- **Produto Ofertado:** Implantação do Local AI Appliance
- **Benefícios Principais:** Privacidade total de dados (air-gapped capacity), ecossistema unificado (API + UI + Billing), previsibilidade de custos operacionais e aderência a regulamentações estritas de conformidade.

## Textos para Capabilities Page
- **Versão:** v1.7.0-local-ai-appliance
- **Destaque:** "Explore the built-in capabilities of the Local AI Appliance."

## v1.8.0 - Hybrid AI Platform

A partir da v1.8.0, o sistema evolui para **Hybrid AI Platform**:
- Multi-provider (local + cloud)
- Providers cloud: OpenAI, Anthropic, DeepSeek, OpenRouter (opcional)
- Cloud providers disabled por padrão, seguros por default
- Sem chaves cloud, tudo continua funcionando local/mock
- Billing em tempo real (próximas etapas)
- Cache inteligente (próximas etapas)

## Limitações que devem aparecer em materiais públicos
- **PSP Real:** Not included / Fora do escopo (Faturamento é manual/offline).
- **PIX Real:** Not included / Fora do escopo (Sem integração direta com bancos).
- **Cloud Managed:** Not included / Fora do escopo (Toda infraestrutura é local/on-premise).
- **External AI APIs:** Optional / Not required depending on setup (O Appliance opera de forma independente).

## Relação com White-Label Local
O nome "Local AI Appliance" é a identidade padrão da versão de lançamento (v1.7.0). No entanto, o sistema mantém suporte total a **White-Label**. Os administradores locais podem sobrescrever os textos públicos (como `product_name`, `company_name`, e `tagline`) no arquivo de configuração `config/branding.json`. Se o arquivo de white-label local estiver presente, ele terá precedência sobre a identidade "Local AI Appliance", garantindo que clientes finais possam aplicar sua própria marca.
