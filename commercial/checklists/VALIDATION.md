# Validation Checklist

- [ ] End-to-end inference successful (curl/dashboard).
- [ ] RBAC policies restrict non-admin users.
- [ ] Rate limits triggered and verified (429 response).
- [ ] Audit logs show correct activity (create/delete/execute).
- [ ] Dashboard displays accurate node and model status.
- [ ] Failover test: Stop one Data Plane node, verify traffic rerouting.
- [ ] Performance test: Throughput and Latency within 10% of expectations.
