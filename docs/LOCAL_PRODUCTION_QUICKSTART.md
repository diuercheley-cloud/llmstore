---
owner: platform-ops
status: consolidated
---

# Local Production Quickstart

> **Novo Instalador (Recomendado):** Use os comandos abaixo para uma configuração guiada e instalação completa:
> ```bash
> make configure-local
> make install-local
> ```
> O comando `configure-local` ajuda a configurar o ambiente (.env.local, GPU/CPU, portas) e o `install-local` realiza todos os pré-checks e validações necessários.

Para mais detalhes sobre o processo de primeira execução, veja o [First Run Local](./FIRST_RUN_LOCAL.md).

Versão curta para subir e testar o ambiente rapidamente.

## 1. Subir a Stack
```bash
./scripts/local-production-up.sh
```
Aguarde até ver a mensagem `--- LOCAL PRODUCTION READY ---`.

## 2. Validar
```bash
make validate-local-production
```

## 3. Testar Chat
Use a API Key gerada no passo 1 (veja no console):
```bash
export API_KEY=sk-local-...
./scripts/test-chat.sh
```

## 4. Acessar UIs
- **Landing Page:** http://localhost:18080
- **Portal do Cliente:** http://localhost:18080/client-portal
- **Admin Dashboard:** http://localhost:18080/admin-dashboard
- **Admin Lab:** http://localhost:18080/admin-lab

## 5. Parar
```bash
make down
```
ou
```bash
docker compose down
```

---

## LOCAL_APPLIANCE_MODE

Este sistema opera por padrão em **LOCAL_APPLIANCE_MODE=true**. Este modo garante configurações seguras para uso local, como faturamento manual, CORS restrito a localhost e validações de segurança automáticas.

Para mais detalhes, consulte o guia de [LOCAL_APPLIANCE_MODE](LOCAL_APPLIANCE_MODE.md).
