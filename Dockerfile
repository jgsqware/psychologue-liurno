# syntax=docker/dockerfile:1.7
# psyneupre — vitrine statique (Céline Liurno, psychologue & sexologue à Plainevaux/Neupré).
# Aucun build : index.html + styles.css sont servis tels quels par nginx:alpine non-root.

FROM nginx:1.27-alpine

# Notre config (écoute :8145, chemins temp sous /tmp pour tourner non-root).
COPY nginx.conf /etc/nginx/nginx.conf

# Le site statique.
COPY index.html styles.css /usr/share/nginx/html/

# nginx:alpine embarque l'utilisateur non privilégié `nginx` (UID 101). On rend
# les chemins runtime accessibles en écriture puis on lâche root.
RUN mkdir -p /tmp/nginx-client && \
    chown -R nginx:nginx /usr/share/nginx/html /var/cache/nginx /tmp && \
    chmod -R g+w /var/cache/nginx

USER nginx
EXPOSE 8145

HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -q --spider http://127.0.0.1:8145/healthz || exit 1

CMD ["nginx", "-g", "daemon off;"]
