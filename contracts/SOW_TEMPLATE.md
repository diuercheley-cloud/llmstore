# Statement of Work (SOW) — Local AI Appliance

> **AVISO JURÍDICO:** Este documento é um **template genérico** fornecido apenas para fins de referência e pré-alinhamento comercial. Não constitui aconselhamento jurídico, não cria vínculo contratual e **não dispensa revisão por assessoria jurídica qualificada**. Cada contrato deve ser adaptado à legislação aplicável, ao regime tributário das partes e às particularidades do projeto. O uso deste template não garante compliance automático com qualquer norma ou regulação.

## 1. Partes

- **Contratante:** [Nome da Empresa Contratante], inscrita no CNPJ/CPF sob nº [00.000.000/0001-00], com sede na [Endereço completo], doravante denominada **CONTRATANTE**.
- **Contratada:** [Nome da Empresa Prestadora], inscrita no CNPJ/CPF sob nº [00.000.000/0001-00], com sede na [Endereço completo], doravante denominada **CONTRATADA**.

## 2. Escopo

Implantação do **LLM Inference Stack** em modo **Local Appliance** no ambiente da CONTRATANTE, incluindo:

- Instalação e configuração dos serviços containerizados (Control Plane, Data Plane, modelos de inferência).
- Configuração de autenticação, multi-tenancy e controle de acesso.
- Ativação dos módulos contratados (RAG, TTS, Embeddings, visão computacional, conforme plano).
- Integração com sistemas de identidade existentes, se aplicável e previamente acordado.
- Testes de funcionamento e validação dos endpoints de inferência.
- Treinamento da equipe técnica da CONTRATANTE para operação do ambiente.

## 3. Fora do Escopo

O presente SOW **não** contempla:

- Desenvolvimento ou personalização de front-end / interface do usuário.
- Integração com sistemas legados da CONTRATANTE não previamente mapeados.
- Criação ou fine-tuning de modelos de linguagem proprietários.
- **Processamento de pagamentos reais via PSP ou PIX.** O módulo de faturamento opera exclusivamente em modo simulado/local.
- Garantia de desempenho em hardware não especificado ou fora dos requisitos mínimos.
- Suporte 24x7 a menos que explicitamente contratado em plano específico (ver cláusula de suporte).
- Compliance com regulações setoriais específicas (ex.: LGPD, HIPAA, SOX) sem avaliação jurídica complementar.
- Serviços de consultoria jurídica, contábil ou regulatória.

## 4. Entregáveis

| Item | Descrição | Critério de Aceitação |
|------|-----------|----------------------|
| E1 | Ambiente Local Appliance instalado e funcional | Todos os containers rodando, health check OK |
| E2 | Endpoints de inferência operacionais | Resposta 200 em `/v1/chat/completions` com modelo carregado |
| E3 | Módulos contratados ativados | Conforme plano contratado (RAG, TTS, etc.) |
| E4 | Documentação de operação | Guia de operação local entregue |
| E5 | Treinamento da equipe | Sessão de transferência de conhecimento realizada |

## 5. Ambiente Local

A implantação ocorrerá em infraestrutura fornecida pela CONTRATANTE, atendendo aos seguintes requisitos mínimos:

- **Sistema Operacional:** Ubuntu 22.04 LTS ou superior (x86_64).
- **Docker:** Docker Engine 24+ com Docker Compose V2.
- **CPU:** 8+ cores x86_64 com suporte a AVX2.
- **RAM:** 32 GB mínimo (64 GB recomendado para planos Pro/Enterprise).
- **Armazenamento:** SSD NVMe com 100 GB + espaço para modelos.
- **GPU (opcional):** NVIDIA GPU com 8 GB+ VRAM e drivers CUDA 12.x.
- **Rede:** Acesso à internet para download inicial de imagens e modelos.

> O não atendimento aos requisitos mínimos poderá impactar o desempenho e a estabilidade do sistema, e a CONTRATADA não poderá ser responsabilizada por tais impactos.

## 6. Requisitos do Cliente

A CONTRATANTE se responsabiliza por:

- Disponibilizar a infraestrutura e o acesso administrativo ao ambiente.
- Fornecer licenças de sistema operacional e software de base, quando aplicável.
- Designar um ponto focal técnico para acompanhamento da implantação.
- Garantir conectividade de rede e acesso à internet para downloads.
- Realizar backups dos dados existentes antes do início da implantação.
- Obter todas as licenças e autorizações necessárias para uso dos modelos e dados.

## 7. Cronograma

| Fase | Atividade | Prazo Estimado |
|------|-----------|----------------|
| F1 | Preparação do ambiente (checklist de requisitos) | D + 0 a D + 2 |
| F2 | Implantação e configuração dos serviços | D + 3 a D + 7 |
| F3 | Ativação de módulos e testes | D + 8 a D + 10 |
| F4 | Treinamento e transferência de conhecimento | D + 11 a D + 12 |
| F5 | Homologação e aceite final | D + 13 a D + 15 |

> **Nota:** Prazos são estimativas e podem variar conforme a disponibilidade da CONTRATANTE, complexidade do ambiente e eventuais dependências externas.

## 8. Critérios de Aceite

A CONTRATADA e a CONTRATANTE deverão utilizar o **Paid Implementation Checklist** (`docs/PAID_IMPLEMENTATION_CHECKLIST.md`) como ferramenta de acompanhamento da implantação. O aceite formal depende da conclusão e validação de todos os itens aplicáveis do checklist.

O aceite do projeto ocorrerá quando todos os entregáveis listados na Seção 4 atenderem aos seguintes critérios:

1. **Teste de sanidade:** `docker compose ps` exibe todos os serviços com status `Up`.
2. **Health check:** Endpoint `/health` retorna HTTP 200.
3. **Inferência funcional:** Chamada a `/v1/chat/completions` retorna resposta válida.
4. **Módulos ativos:** Os módulos contratados respondem conforme especificação.
5. **Documentação entregue:** Guia de operação disponível em formato digital.
6. **Treinamento realizado:** Equipe da CONTRATANTE capacitada para operação.

## 9. Suporte

O suporte será prestado conforme o plano contratado:

| Nível | Horário | Canais | SLA de Resposta |
|-------|---------|--------|-----------------|
| **Basic** | Dias úteis, 8h às 18h (horário comercial) | E-mail | 48h úteis |
| **Pro** | Dias úteis, 8h às 20h | E-mail + Chat | 24h úteis |
| **Enterprise** | 24x7 | E-mail + Chat + Telefone | 4h corridas |

- Atualizações de versão (patches, security fixes) estão inclusas conforme disponibilidade.
- Suporte para falhas decorrentes de modificações não autorizadas no ambiente não está coberto.

## 10. Limitações Técnicas

- O sistema opera em modo **Local Appliance** e não possui alta disponibilidade (HA) embutida a menos que explicitamente contratado.
- A performance de inferência depende diretamente do hardware disponibilizado pela CONTRATANTE.
- Modelos de linguagem podem apresentar alucinações ou respostas imprevisíveis; não há garantia de precisão absoluta.
- O módulo de faturamento é **simulado** e não processa transações financeiras reais.
- A CONTRATADA não se responsabiliza por danos decorrentes de uso inadequado do sistema, incluindo mas não se limitando a decisões baseadas em saídas não verificadas do modelo.

## 11. Segurança

A CONTRATADA se compromete a:

- Utilizar credenciais temporárias durante a implantação, removidas ao término.
- Não extrair, copiar ou reter dados da CONTRATANTE após a conclusão dos serviços.
- Seguir as boas práticas de segurança na configuração (mínimo privilégio, criptografia em trânsito, rotação de chaves).
- Fornecer acesso apenas às pessoas autorizadas indicadas pela CONTRATANTE.

A CONTRATANTE é responsável por:

- Manter o ambiente livre de malwares e acessos não autorizados.
- Aplicar patches de segurança no sistema operacional e Docker.
- Gerenciar o ciclo de vida de credenciais e tokens de acesso.

## 12. Backups

- A CONTRATADA realizará backup da configuração inicial ao final da implantação.
- A CONTRATANTE é responsável por estabelecer e manter uma política de backups recorrentes dos dados e configurações do sistema.
- O script `scripts/backup/backup-local.sh` é fornecido como ferramenta auxiliar, sem garantia de adequação a políticas específicas de retenção ou recuperação de desastres.

## 13. Confidencialidade

**[A inserir — cláusula de confidencialidade a ser redigida pelo departamento jurídico]**

*Template sugerido: As partes comprometem-se a manter em sigilo toda e qualquer informação técnica, comercial, financeira ou operacional compartilhada durante a execução deste SOW, pelo prazo de [X] anos após seu término.*

## 14. LGPD / Proteção de Dados

**[A inserir — cláusula de proteção de dados a ser redigida pelo departamento jurídico em conformidade com a LGPD (Lei 13.709/2018) e demais regulações aplicáveis]**

*Nota: Este template não constitui uma avaliação de impacto à proteção de dados (DPIA) nem substitui a nomeação de um Encarregado (DPO). A adequação à LGPD depende de análise jurídica específica caso a caso.*

## 15. Revisão Jurídica Obrigatória

**ESTE DOCUMENTO É UM TEMPLATE E DEVE SER REVISADO POR ASSESSORIA JURÍDICA QUALIFICADA ANTES DE QUALQUER ASSINATURA.**

- As cláusulas de confidencialidade, LGPD, pagamento, rescisão e propriedade intelectual não são definitivas e requerem redação por profissional habilitado.
- A CONTRATADA não oferece aconselhamento jurídico por meio deste template.
- Nenhuma garantia absoluta de compliance regulatório é fornecida.
- Recomenda-se a consulta a um advogado especializado em direito contratual e tecnologia antes da celebração.

---

*Template SOW v1.0 — Gerado em {{DATE}} — O conteúdo deste arquivo é um modelo de referência e não constitui documento contratual válido sem revisão jurídica.*
