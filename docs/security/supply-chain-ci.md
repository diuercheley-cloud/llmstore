# Supply Chain Security

O `llm-inference-stack` implementa práticas de segurança de supply chain para garantir que o software que você executa é exatamente o software que nós construímos.

## Pilares da Segurança

1.  **Software Bill of Materials (SBOM)**: Cada release acompanha um inventário completo de dependências Python e Node. Isso permite auditoria rápida em caso de vulnerabilidades recém-descobertas (Zero-days).
2.  **Reprodutibilidade**:
    *   **Lockfiles**: Utilizamos `package-lock.json` e requisitos fixados para garantir que builds repetidos gerem o mesmo resultado.
    *   **npm ci**: O pipeline utiliza o comando `npm ci` para garantir que as dependências do ambiente de build correspondam exatamente ao lockfile.
3.  **Integridade e Autenticidade**:
    *   **Checksums**: Todos os artefatos possuem hashes SHA-256.
    *   **Assinatura Digital**: Suporte a assinaturas de artefatos para garantir que o pacote não foi adulterado após a build.

## Auditoria de Dependências
Executamos auditorias automáticas em cada PR para detectar pacotes maliciosos ou vulneráveis antes que eles entrem na base de código.
