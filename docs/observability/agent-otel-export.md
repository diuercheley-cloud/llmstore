# OpenTelemetry Trace Export

The platform supports exporting agent execution traces using OpenTelemetry (OTel). This enables deep visibility into agent reasoning, tool calls, and model interactions using industry-standard APM tools.

## Configuration

Enable OTel tracing and specific exporters via environment variables:

```bash
AGENT_OTEL_TRACING_ENABLED=true
OTLP_EXPORT_ENABLED=true
JAEGER_EXPORT_ENABLED=true
ZIPKIN_EXPORT_ENABLED=true
```

### Exporter Endpoints

| Exporter | Environment Variable | Default |
|----------|----------------------|---------|
| OTLP | `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://otel-collector:4317` |
| Jaeger | `JAEGER_AGENT_HOST` / `PORT` | `localhost:6831` |
| Zipkin | `ZIPKIN_ENDPOINT` | `http://localhost:9411/api/v2/spans` |

## Exported Data

Every agent run generates a root span. Sub-spans are created for:
- Model reasoning steps.
- Tool executions.
- Memory operations (reads/writes).
- Policy engine evaluations.

Spans include attributes such as `agent_id`, `tenant_id` (hashed), and performance metrics like token usage and latency.
