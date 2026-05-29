---
owner: platform-ops
status: consolidated
---

# Requisitos do Sistema

Este documento detalha os requisitos para instalação e execução do LLM Inference Stack em ambiente local do cliente.

## Requisitos Mínimos
- **Sistema Operacional:** Linux (Ubuntu 22.04+ recomendado) ou Windows com WSL2.
- **Docker:** Docker Engine 24.0+ e Docker Compose V2.
- **Memória RAM:** 16 GB.
- **Espaço em Disco:** 50 GB livres (para imagens Docker e modelos base).
- **Processador:** CPU x86_64 com suporte a instruções AVX2.

## Requisitos Recomendados
- **Memória RAM:** 32 GB ou superior.
- **Espaço em Disco:** 100 GB+ SSD NVMe (para melhor desempenho de RAG e carregamento de modelos).
- **Aceleração Gráfica (GPU - Opcional, mas altamente recomendada):** Placa de vídeo NVIDIA compatível com CUDA.
- **VRAM Recomendada:** 12 GB+ para execução de modelos 7B-8B quantizados de forma eficiente.

## Portas de Rede
O sistema utiliza as seguintes portas principais que devem estar livres:
- `80` e `443` (Acesso reverso proxy/Caddy).
- `18080` (Acesso interno e painéis de controle, dependendo da configuração).
- Certifique-se de que não há conflitos antes da instalação.

## Modelos e Dependências de Dados
- **Modelos:** A plataforma suporta o formato GGUF para execução local. Modelos devem ser adicionados na pasta `models/` antes de iniciar a inferência pesada.
- **Internet:** Opcional durante o funcionamento diário em modo totalmente isolado, mas requerida inicialmente para download das imagens Docker e scripts (caso não utilize um pacote pre-baixado).

## Limitações Conhecidas
- **Integração Financeira:** Este ambiente possui um simulador local (mock) para testes. **Não há promessa de PSP/PIX real** ou integração com gateways de pagamento ao vivo nesta versão de implantação local.
- **Nuvem:** Não há promessa de cloud gerenciada; a manutenção do hardware físico ou máquina virtual local é de responsabilidade do cliente.
- **Segurança Pública:** O sistema é desenhado para rodar em rede local/VPN (Modo Appliance Local - `LOCAL_APPLIANCE_MODE`). Não exija ou configure domínio público sem um firewall de borda adequado, pois isso não é recomendado por padrão.