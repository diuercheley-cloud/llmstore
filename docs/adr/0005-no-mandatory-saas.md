# ADR 0005: No Mandatory SaaS

## Status

Accepted

## Context

O repositorio atende cenarios locais, soberanos e hibridos. Sem uma decisao explicita, funcionalidades novas podem assumir disponibilidade constante de servicos SaaS e quebrar implantacoes desconectadas ou autocontidas.

## Decision

Nenhum componente central da plataforma deve exigir SaaS mandatorio para instalacao, boot, execucao principal, validacao local ou auditoria basica. Integracoes externas podem existir, mas devem ser opcionais, degradaveis e claramente isoladas.

## Consequences

Preserva flexibilidade de deploy e reduz lock-in operacional. Em contrapartida, algumas features precisam de caminhos locais alternativos, mocks ou modos reduzidos para permanecerem utilizaveis.

## Security Notes

Menos dependencias obrigatorias externas reduz acoplamento e risco de indisponibilidade remota, mas nao elimina requisitos de autenticacao, hardening local, saneamento e segregacao de dados.

## Offline Compatibility

Impacto maximo. A decisao formaliza que operacao local e offline-first nao sao casos secundários.

## Determinism Impact

Impacto positivo. Menos dependencia de respostas externas nao deterministicas em fluxos centrais melhora repetibilidade e previsibilidade da plataforma.

