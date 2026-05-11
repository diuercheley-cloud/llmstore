# Objeções Comuns e Respostas Sugeridas

## Técnicas

| Objeção | Resposta |
|---------|----------|
| "Precisa de GPU cara?" | Funciona em RTX 4050 6GB (R\$ 2.000) ou até CPU. A stack é otimizada para hardware modesto. |
| "Qual a acurácia vs GPT-4?" | Para tarefas específicas com RAG, a acurácia é comparável. Modelos locais têm evoluído rápido (Gemma-4, Llama-4). |
| "E se o modelo alucinar?" | RAG + system prompt + temperatura controlada reduzem alucinações. Recomendamos revisão humana para uso crítico. |
| "Funciona offline?" | 100% local. Sem dependência de internet para inferência. Apenas para instalação inicial. |

## Comerciais

| Objeção | Resposta |
|---------|----------|
| "Quanto custa?" | A partir de R\$ 197/mês para plano demo. Sem custo de API por token. Tudo incluso no plano. |
| "Já uso OpenAI, por que mudar?" | Se seus dados não são sensíveis, OpenAI é ótima. Se você tem LGPD/sigilo/regulação, a inferência local é obrigatória. |
| "Precisa contratar equipe de TI?" | Não. Script de instalação automatizada (make install-local). Dashboard para gestão. Suporte incluso. |
| "E se crescer?" | A stack escala verticalmente (mais GPU) e horizontalmente (múltiplas instâncias). Planos Enterprise acompanham. |

## LGPD / Compliance

| Objeção | Resposta |
|---------|----------|
| "Precisamos de certificações?" | Fornecemos relatório de segurança e readiness. A stack segue boas práticas de segurança. |
| "Onde os dados são armazenados?" | 100% local. Você controla onde os dados estão (seu storage, seu backup, sua política de retenção). |
| "Tem logs de acesso?" | Sim. Todos os eventos são logados com data, hora, cliente e ação. Logs retidos conforme política configurável. |

## Concorrência

| Objeção | Resposta |
|---------|----------|
| "Staxx/Outra empresa faz igual" | Poucas soluções oferecem stack completo: chat + RAG + TTS + embeddings + billing + portal do cliente + dashboard admin em um único pacote local. |
| "Vamos esperar o mercado amadurecer" | Quem começa agora acumula vantagem competitiva. A instalação leva 15 minutos. | 
| "É open source?" | O código é aberto para auditoria. O suporte e pacote comercial incluem garantia e atualizações. |
