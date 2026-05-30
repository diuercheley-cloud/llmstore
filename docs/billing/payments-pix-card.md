# Pagamentos PIX e Cartão

O LLM Inference Stack suporta pagamentos reais utilizando provedores plugáveis. Por padrão, o sistema utiliza um provedor de `mock` para desenvolvimento e testes.

## Provedores Suportados

- **Mock**: Provedor padrão para testes.
- **Stripe**: Suporte global para cartões e PIX.
- **MercadoPago**: Focado em América Latina, suporte robusto para PIX.
- **Asaas**: Provedor brasileiro especializado em automação de cobranças.

## Configuração

Habilite o processamento de pagamentos no seu arquivo `.env`:

```env
PAYMENT_PROCESSING_ENABLED=true
PAYMENT_PROVIDER=stripe # mock|stripe|mercadopago|asaas

PIX_PAYMENT_ENABLED=true
CARD_PAYMENT_ENABLED=true

# API Keys (conforme o provedor escolhido)
STRIPE_API_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
MERCADOPAGO_ACCESS_TOKEN=APP_USR-...
ASAAS_API_KEY=$...
```

## Fluxo de Pagamento PIX

1. O cliente solicita um QR Code via `POST /billing/payments/pix`.
2. O servidor retorna o código PIX e a URL do QR Code.
3. O servidor recebe um webhook do provedor quando o pagamento é confirmado.
4. O saldo ou fatura do cliente é atualizado automaticamente.

## Segurança e Reconciliação

- **Assinatura de Webhooks**: Todos os webhooks recebidos são validados usando o segredo do provedor.
- **Idempotência**: O sistema utiliza chaves de idempotência para evitar cobranças duplicadas.
- **Dados Sensíveis**: O sistema **não armazena** dados de cartão de crédito. Todo o processamento é feito via tokens seguros dos provedores.
- **Trilha de Auditoria**: Todas as tentativas de pagamento e confirmações são registradas no log de auditoria do sistema.
