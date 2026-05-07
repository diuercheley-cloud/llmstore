# Perguntas Frequentes (FAQ) - Demo Local

### Isso roda totalmente sem internet?
Sim. Uma vez que o Docker esteja instalado e o modelo GGUF tenha sido baixado, a stack pode operar em um ambiente 100% "air-gapped" (isolado de redes externas).

### Precisa obrigatoriamente de uma GPU?
Não, o sistema suporta execução apenas em CPU. No entanto, o uso de uma GPU (especialmente NVIDIA via WSL2 ou Linux nativo) aumentará significativamente a velocidade de geração de tokens.

### Posso usar o LM Studio como backend?
Sim. O `llm-inference-stack` pode ser configurado para usar qualquer backend compatível com a API do OpenAI, incluindo o servidor local do LM Studio. Isso é gerenciado através da aba de "Modelos" no Admin Lab.

### Posso trocar o modelo de IA facilmente?
Sim. Basta colocar o arquivo `.gguf` na pasta `models/` e registrá-lo via Admin Lab. Você pode alternar entre modelos (como Gemma, Llama 3, Mistral) sem interromper a disponibilidade da API.

### Os dados processados saem da minha empresa?
Não. Como a stack roda localmente, todos os prompts, respostas e documentos indexados no RAG permanecem dentro da sua infraestrutura privada.

### Tem cobrança via PIX real?
Nesta versão de demonstração local, o faturamento é simulado para fins de demonstração do fluxo financeiro. Para produção, o sistema pode ser estendido com hooks para gateways reais como Asaas ou Stripe.

### Como funciona o billing local/manual?
O sistema contabiliza o uso de tokens por cliente e gera faturas mensalmente (ou sob demanda). O administrador pode marcar essas faturas como pagas manualmente após confirmar o recebimento financeiro fora da plataforma.

### Como a plataforma isola diferentes clientes?
O isolamento é feito através de API Keys vinculadas a Client IDs. Cada cliente possui suas próprias cotas de tokens, limites de taxa (rate limiting) e base de documentos RAG isolada.

### Como faço backup dos dados?
O projeto inclui scripts de backup (`./scripts/backup-local.sh`) que realizam o dump do banco de dados PostgreSQL e preservam as configurações da stack.

### Como posso escalar o sistema no futuro?
Embora esta demo seja local, a arquitetura foi desenhada para ser escalável. Você pode mover o Control Plane para uma VM e ter múltiplos Data Planes (nós de inferência) distribuídos, gerenciados pelo mesmo painel central.
