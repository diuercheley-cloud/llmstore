# Agent Memory Isolation

Multi-tenant environments require strict data isolation to prevent cross-tenant data leakage. 

## Mechanisms
1. **Database Tenant Filters**: Every operation to read, write, list, search, or delete memory strictly enforces the `tenant_id` criteria in SQL clauses.
2. **Strict Vector Search Constraints**: Vector searching (`AgentMemoryIndexingService`) will not retrieve data outside the tenant boundary, regardless of the prompt scope or system capabilities.
3. **Export Validation**: Exports are strictly limited to the requesting tenant context, and they omit detected secrets dynamically on export just as an extra layer of defense.
4. **Testing Assurances**: Isolation logic is tested via isolated tests (`test_indexing_nao_mistura_tenants` and `test_memory_tenant_isolation`) which verify that Tenant B cannot access any memory item inserted by Tenant A.
