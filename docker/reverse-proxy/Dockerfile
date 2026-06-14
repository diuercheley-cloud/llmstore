FROM nginx:1.27-alpine

RUN apk add --no-cache bash curl gettext

COPY docker/reverse-proxy/nginx-http.conf /templates/nginx-http.conf
COPY docker/reverse-proxy/nginx-tls.conf /templates/nginx-tls.conf
COPY docker/reverse-proxy/entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh \
    && chown -R nginx:nginx /templates /entrypoint.sh

# nginx image runs as nginx user by default when PID 1 is nginx.
# Entrypoint runs as root for signal handling, then drops to nginx user.
# Explicit USER directive ensures non-root runtime.

USER nginx

STOPSIGNAL SIGQUIT

ENTRYPOINT ["/entrypoint.sh"]
