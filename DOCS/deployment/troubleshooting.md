# Troubleshooting - NESTSECURE

## API no responde

- Verificar contenedores: `docker compose ps`
- Revisar logs de API: `docker compose logs -f api`
- Probar health: `curl http://localhost:8000/health`

## /docs retorna 404

- Verificar `ENVIRONMENT=production` y `DEBUG=false` en producción.
- En desarrollo, usar `docker-compose.dev.yml` con `DEBUG=true`.

## Migraciones pendientes

- Ejecutar: `docker compose exec api alembic upgrade head`

## Redis no responde

- Verificar contenedor: `docker compose logs -f redis`
- Probar ping: `docker compose exec redis redis-cli ping`

## Celery workers reiniciando

- Logs: `docker compose logs -f worker`
- Verificar módulos y colas en `app.workers.celery_app`.

## Nginx sin servir frontend

- Verificar build en `frontend/dist`.
- Confirmar config en `docker/nginx/nginx.conf`.
