# Prompts de Demonstração

Prompts fictícios para cada cenário comercial. Use com `chat/completions` ou playground.

## 1. Clínica Local

### Resumo de prontuário
```
Faça um resumo deste prontuário em linguagem simples para o paciente:

Paciente: Maria Silva, 45 anos
Diagnóstico: Diabetes tipo 2
Medicações: Metformina 850mg 2x/dia
Última consulta: 10/05/2026 - Glicemia em jejum 128 mg/dL
Observações: Paciente relata tontura ocasional pela manhã.
```

### Protocolo clínico (com RAG)
```
Com base nos protocolos clínicos carregados, qual a conduta recomendada para um paciente com glicemia acima de 200 mg/dL em jejum?
```

### Explicar exame
```
Explique em português claro para um paciente leigo o que significa "colesterol LDL = 145 mg/dL" e quais as recomendações.
```

## 2. Escritório Jurídico

### Análise de cláusula contratual
```
Analise a seguinte cláusula contratual e identifique potenciais riscos para o contratante:

"Cláusula 12 - Penalidades: Em caso de rescisão antecipada sem justa causa, a parte contratante deverá pagar multa equivalente a 80% do valor total remanescente do contrato, corrigido monetariamente pelo IGP-M."

Destaque os pontos de atenção.
```

### Pesquisa de jurisprudência (com RAG)
```
Com base na jurisprudência carregada no sistema, qual o entendimento dos tribunais sobre danos morais por atraso em procedimento estético?
```

### Minuta de petição
```
Gere uma minuta de petição inicial para ação indenizatória por danos materiais e morais decorrentes de negativa indevida de cobertura de plano de saúde para procedimento de emergência.

Dados do caso (fictícios):
- Autor: João Ferreira, 52 anos
- Réu: Plano Saúde Integral Ltda.
- Fato: Negativa de autorização para cirurgia de apendicite aguda em 05/03/2026
- Hospital: Santa Mônica, leito 302
```

## 3. Suporte Técnico

### Resposta a ticket
```
Com base na knowledge base carregada, elabore uma resposta para o seguinte ticket:

Título: Conexão Wi-Fi caindo intermitentemente
Cliente: Empresa ABC Ltda.
Relato: A cada 30 minutos a conexão cai por aproximadamente 2 minutos e volta sozinha. Já trocamos o roteador e o problema persiste.
Modelo do equipamento: TP-Link Archer C80
```

### Troubleshooting
```
O cliente reporta que o sistema está lento após a última atualização (versão 3.2.1). Quais perguntas devo fazer para diagnosticar? Liste em ordem de prioridade.
```

### Resposta técnica (TTS)
```
Texto para TTS: "Olá, aqui é o assistente virtual do SuporteTech. Seu chamado #4521 foi atualizado. Um técnico está verificando o problema de conectidade e retornará em até 30 minutos. Para mais detalhes, acesse nosso portal."
```

## 4. Escola/Treinamento

### Corrigir redação
```
Corrija a seguinte redação de um aluno do 9º ano sobre "Mudanças Climáticas". Aponte erros gramaticais, de coesão e argumentação. Dê uma nota de 0 a 10:

"As mudanças climáticas são um problema global que afeta todos nos. O aquecimento global está causando derretimento das calotas polares e aumento do nível do mar. Muitas espécies estão em risco de extinção. Os governos precisam fazer alguma coisa sobre isso, mas as pessoas também podem ajudar reciclando e economizando energia. É importante que todos se conscientizem sobre a importância de preservar o meio ambiente para as futuras gerações."
```

### Plano de aula (com RAG)
```
Com base no material didático carregado, gere um plano de aula para o 8º ano sobre "Sistema Digestório" com duração de 50 minutos, incluindo objetivos, atividades práticas e avaliação.
```

### Gerar exercícios
```
Gere 5 questões de múltipla escolha sobre a Revolução Industrial para alunos do 8º ano, com nível de dificuldade médio. Inclua o gabarito comentado.
```

## 5. Provedor de API de IA

### Testar compatibilidade OpenAI
```
Liste os modelos disponíveis na API.
```

### Geração criativa
```
Crie um slogan criativo para uma plataforma de IA local que respeita a privacidade dos dados. Use tom profissional e inspirador.
```

### Suporte a múltiplos clientes (testar isolamento)
```
Quem é você e qual empresa te contratou? Explique suas capacidades.
```
