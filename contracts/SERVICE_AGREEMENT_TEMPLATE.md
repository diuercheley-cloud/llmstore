# Service Agreement — Local AI Appliance

> **AVISO JURÍDICO:** Este documento é um **template genérico** fornecido apenas para fins de referência e pré-alinhamento comercial. Não constitui aconselhamento jurídico, não cria vínculo contratual e **não dispensa revisão por assessoria jurídica qualificada**. Cada contrato deve ser adaptado à legislação aplicável, ao regime tributário das partes e às particularidades do projeto. O uso deste template não garante compliance automático com qualquer norma ou regulação.

## 1. Prestação de Serviço

A CONTRATADA fornecerá à CONTRATANTE o licenciamento de uso do **LLM Inference Stack** em modo **Local Appliance**, conforme o plano contratado, incluindo:

- Disponibilização do software em formato de imagens Docker e scripts de implantação.
- Acesso aos módulos e funcionalidades previstos no plano.
- Atualizações de versão durante a vigência do contrato, conforme política de release.
- Suporte técnico nos níveis definidos no plano ou SOW específico.

O software é instalado no ambiente da CONTRATANTE e opera localmente, sem dependência de infraestrutura externa da CONTRATADA após a implantação inicial.

## 2. Responsabilidade das Partes

### 2.1. Responsabilidades da CONTRATADA

- Entregar o software em condições de funcionamento conforme especificações técnicas.
- Corrigir falhas comprovadas no software dentro dos prazos de SLA definidos.
- Manter a documentação técnica atualizada.
- Não acessar, coletar ou transmitir dados da CONTRATANTE sem autorização expressa.

### 2.2. Responsabilidades da CONTRATANTE

- Manter a infraestrutura dentro dos requisitos mínimos especificados.
- Não realizar engenharia reversa, modificação não autorizada ou redistribuição do software.
- Manter a equipe técnica treinada para operação do sistema.
- Responsabilizar-se pelo conteúdo processado pelo sistema, incluindo dados de entrada e saída dos modelos.
- Obter as licenças necessárias para uso de modelos proprietários ou dados de terceiros.

## 3. Disponibilidade Local

O sistema opera integralmente no ambiente da CONTRATANTE. A disponibilidade do serviço depende diretamente:

- Da infraestrutura fornecida pela CONTRATANTE (hardware, energia, rede).
- Da correta operação do ambiente Docker e sistema operacional subjacente.
- Da aplicação de atualizações e manutenções no ambiente pela CONTRATANTE.

A CONTRATADA **não oferece SLA de disponibilidade** que dependa de fatores fora de seu controle. Caso um SLA específico seja necessário, este deverá ser formalizado em adendo contratual específico com condições, métricas e compensações claramente definidas.

## 4. Manutenção

- A CONTRATADA disponibilizará atualizações corretivas (security patches, bug fixes) por meio do canal de releases.
- A CONTRATANTE é responsável por aplicar as atualizações no seu ambiente.
- Manutenções programadas (upgrades de versão) serão comunicadas com antecedência mínima de [15] dias corridos.
- A CONTRATADA poderá solicitar acesso remoto ao ambiente para fins de diagnóstico, mediante autorização prévia da CONTRATANTE.

## 5. Atualização

- Atualizações de versão menor (patches) são inclusas no plano contratado.
- Atualizações de versão maior (major releases) podem estar sujeitas a custos adicionais, conforme política vigente.
- A CONTRATANTE poderá optar por não aplicar atualizações, assumindo os riscos de segurança e compatibilidade.
- A CONTRATADA não se responsabiliza por falhas decorrentes da não aplicação de atualizações disponíveis.

## 6. Propriedade dos Dados

- Todos os dados inseridos, processados ou gerados pela CONTRATANTE no sistema permanecem de propriedade exclusiva da CONTRATANTE.
- A CONTRATADA não adquire qualquer direito sobre os dados da CONTRATANTE.
- A CONTRATADA não utilizará os dados da CONTRATANTE para treinamento ou fine-tuning de modelos, salvo acordo expresso em contrário.
- Mediante término do contrato, a CONTRATADA fornecerá instruções para exportação dos dados pela CONTRATANTE.

## 7. Exclusões

**Processamento de pagamentos reais via PSP ou PIX está excluído.** O módulo de faturamento incluso no software opera exclusivamente em modo simulado/local para demonstração e não realiza transações financeiras reais.

A CONTRATADA **não será responsabilizada** por:

- Danos decorrentes de caso fortuito ou força maior.
- Falhas causadas por modificações não autorizadas no software.
- Perdas resultantes de uso inadequado do sistema pela CONTRATANTE.
- Decisões tomadas com base nas saídas dos modelos de linguagem (incluindo, mas não se limitando a alucinações, vieses ou imprecisões).
- Interrupções causadas por manutenção na infraestrutura da CONTRATANTE.
- Violações de dados decorrentes de falhas de segurança no ambiente da CONTRATANTE.
- Danos indiretos, incidentais, especiais ou consequenciais.

## 8. Pagamento

**[A inserir — cláusula de pagamento a ser redigida pelo departamento jurídico]**

*Template sugerido: A CONTRATANTE pagará à CONTRATADA o valor de [R$ X.XXX,XX] mensais a título de licenciamento e suporte, com vencimento no dia [XX] de cada mês, mediante emissão de nota fiscal. Reajustes serão aplicados conforme [IGPM/IPCA]. Multa por atraso de [X]% sobre o valor devido.*

## 9. Rescisão

**[A inserir — cláusula de rescisão a ser redigida pelo departamento jurídico]**

*Template sugerido: Qualquer parte poderá rescindir o presente contrato mediante notificação prévia de [30] dias. Em caso de descumprimento grave não sanado em [15] dias, a parte inocente poderá rescindir imediatamente. Efeitos da rescisão: [devolução de dados, cessaçao de uso, pagamento de verbas residuais].*

## 10. Disposições Gerais

- Este contrato é regido pelas leis da República Federativa do Brasil.
- Fica eleito o foro da comarca de [Cidade/UF] para dirimir quaisquer controvérsias.
- Qualquer alteração deste contrato deve ser feita por escrito e assinada por ambas as partes.
- Este template não substitui nem se sobrepõe a acordos de confidencialidade (NDA) ou contratos de SOW específicos.

## 11. Revisão Jurídica Obrigatória

**ESTE DOCUMENTO É UM TEMPLATE E DEVE SER REVISADO POR ASSESSORIA JURÍDICA QUALIFICADA ANTES DE QUALQUER ASSINATURA.**

- As cláusulas de pagamento, rescisão e propriedade intelectual não são definitivas e requerem redação por profissional habilitado.
- A CONTRATADA não oferece aconselhamento jurídico por meio deste template.
- Nenhuma garantia absoluta de compliance regulatório é fornecida.
- Recomenda-se a consulta a um advogado especializado em direito contratual e tecnologia antes da celebração.

---

*Template Service Agreement v1.0 — Gerado em {{DATE}} — O conteúdo deste arquivo é um modelo de referência e não constitui documento contratual válido sem revisão jurídica.*
