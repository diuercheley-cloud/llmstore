# Runtime Domain

Este dominio descreve a superficie contratual do plano de runtime.

- `allowed_inputs`: comandos, configuracoes e estados operacionais necessarios para execucao local.
- `emitted_events`: eventos observaveis emitidos por runtime e orquestracao.
- `forbidden_dependencies`: dominios que nao devem se tornar dependencias obrigatorias do runtime.
- `deterministic_requirements`: invariantes para manter comportamento reproduzivel e offline-first.

O objetivo deste package e preparar uma modularizacao forte sem mover implementacoes existentes.

