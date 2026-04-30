FROM nginx:1.27-alpine

RUN apk add --no-cache bash curl gettext

COPY docker/reverse-proxy/nginx-http.conf /templates/nginx-http.conf
COPY docker/reverse-proxy/nginx-tls.conf /templates/nginx-tls.conf
COPY docker/reverse-proxy/entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
