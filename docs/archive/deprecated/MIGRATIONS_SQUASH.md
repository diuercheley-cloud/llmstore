# Estratégia de Consolidação das Migrations (Squash)

## O Problema
O projeto acumulou cerca de 151 migrations do Alembic. Esse acúmulo torna a criação de novos ambientes de desenvolvimento lenta, dificulta a leitura do histórico do esquema e aumenta a complexidade de manutenção. 

## Solução Adotada
Realizamos um "squash" completo de todas as migrations antigas. Devido à alta complexidade e ao forte acoplamento de chaves estrangeiras (Foreign Keys) entre os domínios (Core, Agents, Commercial, Billing, RAG, etc.) envolvendo 701 tabelas, separar a criação dessas tabelas em múltiplos arquivos causaria problemas graves de dependências circulares durante a inicialização de um banco de dados em branco.

Por isso, aplicamos o princípio de manter a integridade garantindo que o banco consiga subir perfeitamente com um único `alembic upgrade head`:
1. **Consolidação Total**: Foi gerada uma única migration base chamada `001_initial_schema`, que contém todo o estado atual da base de dados consolidado.
2. **Histórico Preservado**: Todas as 151 migrations originais foram movidas para a pasta `control_plane/alembic/archive/`. Elas não serão mais lidas pelo Alembic, mas continuam disponíveis para referência histórica.

### Blocos Lógicos
Embora o plano inicial sugerisse separar as migrations em blocos (`002_core`, `003_agents`, etc.), a análise técnica mostrou que "quando faz sentido" (como estipulado nas regras) não se aplica aqui. A divisão manual de 701 tabelas em 9 arquivos quebraria as referências de integridade do SQLAlchemy. O esquema consolidado único representa todos os domínios perfeitamente.

## Guia para Ambientes Existentes

Para bancos de dados que já estão rodando e possuem o histórico antigo aplicado nas tabelas `alembic_version`, se rodarem `alembic upgrade head` agora, o Alembic tentará recriar todas as tabelas (o que falhará, pois elas já existem).

Para corrigir isso, faça o "stamp" da nova revisão inicial em ambientes de desenvolvimento, homologação e produção:

```bash
# Entre na pasta do control_plane
cd control_plane

# Informe ao Alembic que o banco já possui a estrutura da migration 001_initial
alembic stamp 001_initial
```

Após rodar o comando de stamp, o banco estará sincronizado e pronto para receber futuras migrations normalmente (ex: `002_add_new_feature`).

## Guia para Novos Ambientes

Para novos desenvolvedores ou novos ambientes de deploy, o processo continua exatamente o mesmo e se tornará muito mais rápido:

```bash
# Na primeira vez que for rodar o projeto em um banco limpo
cd control_plane
alembic upgrade head
```

## Resumo da Validação Executada
- A nova migration base (`001_initial_schema`) foi gerada limpa.
- O comando `alembic upgrade head` foi testado e subiu as 701 tabelas com sucesso em um banco de dados PostgreSQL zerado.
- Testes unitários e de API foram validados em conjunto.
