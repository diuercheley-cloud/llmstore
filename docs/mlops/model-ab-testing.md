# Model A/B Testing

O framework de A/B Testing permite comparar diferentes modelos, backends ou políticas de forma governada, utilizando dados reais de tráfego.

## Configuração

Habilite o recurso no arquivo `.env`:

```env
MODEL_EXPERIMENTS_ENABLED=true
MODEL_AB_TESTING_ENABLED=true
```

## Como funciona

1. **Definição**: Crie um experimento definindo a rota alvo e as variantes (ex: Variante A vs Variante B).
2. **Traffic Split**: Configure o percentual de tráfego para cada variante.
3. **Sticky Assignment**: O sistema garante que um mesmo usuário (se autenticado) sempre veja a mesma variante durante o experimento.
4. **Métricas**: Latência, custo, taxa de erro e scores de avaliação são coletados para cada variante.
5. **Promoção**: Após a análise dos resultados, uma variante pode ser promovida para se tornar a configuração definitiva da rota.

## Endpoints Admin

- `POST /admin/models/experiments`: Cria um novo experimento.
- `GET /admin/models/experiments`: Lista experimentos.
- `POST /admin/models/experiments/{id}/promote`: Promove uma variante.
- `POST /admin/models/experiments/{id}/rollback`: Finaliza o experimento sem promoção.
