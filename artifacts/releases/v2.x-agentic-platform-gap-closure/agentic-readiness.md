# Agentic Readiness

**Generated at**: 2026-05-30T01:41:54Z
**Status**: ready
**Runtime enabled**: false
**Worker enabled**: false

```
Running hermetic preflight check...
✅ Curl: Found (curl 8.5.0 (x86_64-pc-linux-gnu) libcurl/8.5.0 OpenSSL/3.0.13 zlib/1.3 brotli/1.1.0 zstd/1.5.5 libidn2/2.3.7 libpsl/0.21.2 (+libidn2/2.3.7) libssh/0.10.6/openssl/zlib nghttp2/1.59.0 librtmp/2.3 OpenLDAP/2.6.10)
✅ Docker: Found (Docker version 29.4.3, build 055a478)
✅ Docker Compose: Found (Docker Compose version v5.1.3)
✅ Python: Found (Python 3.12.3)
✅ Node: Found (v22.22.3)
✅ NPM: Found (10.9.8)
Disk Space Free: 865G
✅ Permissions: Writable
==========================================================
✅ PREFLIGHT PASSED: Environment is ready.
==========================================================
----------------------------------------------------------------
  AGENTIC RUNTIME READINESS CHECK (Mode: advisory)
----------------------------------------------------------------
Timestamp: 2026-05-30T01:40:43.114863+00:00
Status:    ready
----------------------------------------------------------------
Detailed Checks:
[PASS] Agent Runtime Enabled: true (OK)
[PASS] LLM Provider Status: {"provider":"gateway","mode":"production"} (LLM provider 'gateway' is valid for 'production' mode.)
[PASS] Agent Executor Execution Mode: {"active_modes":[],"mode":"production"} (AgentExecutor is configured for real execution only.)
[PASS] Execution Plane Enabled: true (OK)
[PASS] Active Workers Heartbeat: 1 (1 active workers in the last 2 minutes.)
[PASS] Execution Queue Depth: 0 (OK)
[PASS] Stuck Agent Runs: 0 (OK)
[PASS] Orphan Execution Leases: 0 (OK)
[PASS] Dead Letter Queue (DLQ): 0 (OK)
[WARN] Memory Policies Configured: 0 (OK)
[PASS] Pending Approvals: 0 (OK)
[PASS] Open Incidents: 0 (OK)
----------------------------------------------------------------
✅ Agentic Runtime is ready for production.
```
