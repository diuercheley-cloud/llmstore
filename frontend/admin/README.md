# Admin Panel

Painel administrativo do LLM Inference Stack, construído com React 19, TypeScript, Vite, Tailwind CSS 4 e MUI.

## Scripts

```bash
npm run dev          # Iniciar servidor de desenvolvimento
npm run build        # Compilar para produção (tsc + vite build)
npm run lint         # Executar ESLint
npm run test         # Executar testes com Vitest
npm run storybook    # Iniciar Storybook
npm run build-storybook  # Compilar Storybook para produção
```

## Estrutura

```
src/
├── components/     # Componentes reutilizáveis (UI, tabelas, layout)
├── hooks/          # Custom hooks
├── lib/            # Utilitários, API client
├── navigation/     # Config de navegação e rotas
├── pages/          # Páginas do admin por domínio (agents, billing, etc.)
└── routes/         # Definição de rotas do React Router
```

## Requisitos

- Node.js 20+
- npm

## CI/CD

O build e lint são validados no workflow `.github/workflows/ci.yml` (job `test-frontend`).
