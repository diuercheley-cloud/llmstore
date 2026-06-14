# Production Server Configuration

For production and enterprise-production environments, the control plane uses **Gunicorn** with **UvicornWorker** to handle multiple concurrent requests efficiently across multiple CPU cores.

## Server Configuration

The following environment variables can be used to tune the production server performance:

| Variable | Description | Default |
|----------|-------------|---------|
| `WEB_CONCURRENCY` | Number of Gunicorn worker processes. | `1` (or `$(nproc)` in Docker) |
| `GUNICORN_TIMEOUT` | Workers silent for more than this many seconds are killed and restarted. | `120` |
| `GUNICORN_KEEPALIVE` | The number of seconds to wait for requests on a Keep-Alive connection. | `5` |

## Execution Logic

The entrypoint logic in the `control-plane` Dockerfile automatically selects the server type based on the `APP_ENV` variable:

- **APP_ENV=production** or **enterprise-production**: Uses Gunicorn with UvicornWorker.
- **Other values**: Uses standard Uvicorn (optimized for development with hot-reload if requested).

## Scalability

To take full advantage of multi-core systems, ensure `WEB_CONCURRENCY` is set appropriately for your hardware (typically `2 x $num_cores + 1` or just `$num_cores`).

In the Quickstart (Local Appliance) mode, `WEB_CONCURRENCY` defaults to `1` to conserve resources, but can be overridden.
