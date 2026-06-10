# Appliance Mode Deployment

O modo Appliance transforma o `llm-inference-stack` em uma solução selada e autogerenciada, ideal para deploys On-Premise em ambientes restritos ou Air-Gapped.

## Características do Modo Appliance

- **Zero-Touch Provisioning**: Instalação e configuração inicial via scripts de bootstrap.
- **Air-Gapped Ready**: Não depende de conectividade externa para operação ou atualizações.
- **Configuração Imutável**: Configurações padrão seguras definidas em `appliance.defaults.yaml`.
- **Governança Local**: Auditoria e logs persistidos localmente.

## Procedimento de Instalação (Bootstrap)

O script de bootstrap realiza a validação do hardware, gera tokens de administração iniciais e configura o ambiente Docker/Kubernetes local.

```bash
./scripts/dev/appliance/bootstrap.sh
```

## Atualizações Air-Gapped

As atualizações são distribuídas como bundles assinados contendo manifestos, hashes de arquivos e binários/imagens.

1. **Criação do Bundle** (em máquina com internet):
   ```bash
   python3 scripts/dev/airgap/create_bundle.py --version 1.2.0 --out bundle_1.2.0.stack
   ```

2. **Verificação do Bundle**:
   ```bash
   python3 scripts/dev/airgap/verify_bundle.py --bundle bundle_1.2.0.stack
   ```

3. **Aplicação da Atualização**:
   ```bash
   python3 scripts/dev/airgap/apply_bundle.py --bundle bundle_1.2.0.stack --dry-run
   python3 scripts/dev/airgap/apply_bundle.py --bundle bundle_1.2.0.stack
   ```

## Segurança

- Todos os pacotes são verificados via SHA-256.
- Downgrades são bloqueados por padrão para evitar rollback de correções de segurança.
- Logs de auditoria de atualização são gerados em `/var/log/llm-stack-updates.log`.
