#### Docker Compose Structure
```yaml
version: '3.8'

services:
  # API principal
  api:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: nestsecure_api
    restart: unless-stopped
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
      - DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
    volumes:
      - backend_logs:/app/logs
      - backend_reports:/app/reports
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
    networks:
      - nestsecure_network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Celery Worker
  worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: nestsecure_worker
    restart: unless-stopped
    command: celery -A app.workers.celery_app worker --loglevel=info --concurrency=2
    environment:
      - DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/1
      - CELERY_RESULT_BACKEND=redis://redis:6379/2
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock  # For running scan containers
      - ./data/scans:/app/scans
    depends_on:
      - postgres
      - redis
    networks:
      - nestsecure_network
      - scan_network

  # Celery Beat (Scheduler)
  beat:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: nestsecure_beat
    restart: unless-stopped
    command: celery -A app.workers.celery_app beat --loglevel=info
    environment:
      - DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/1
      - CELERY_RESULT_BACKEND=redis://redis:6379/2
    depends_on:
      - worker
    networks:
      - nestsecure_network

  # Celery Flower (Monitoring)
  flower:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: nestsecure_flower
    restart: unless-stopped
    command: celery -A app.workers.celery_app flower --port=5555
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/1
    ports:
      - "5555:5555"
    depends_on:
      - redis
      - worker
    networks:
      - nestsecure_network

  # PostgreSQL Database
  postgres:
    image: timescale/timescaledb:latest-pg15
    container_name: nestsecure_postgres
    restart: unless-stopped
    environment:
      - POSTGRES_DB=${POSTGRES_DB}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/init-db.sql:ro
    ports:
      - "5432:5432"
    networks:
      - nestsecure_network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis
  redis:
    image: redis:7-alpine
    container_name: nestsecure_redis
    restart: unless-stopped
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    networks:
      - nestsecure_network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # OpenVAS Scanner
  openvas:
    image: greenbone/openvas-scanner:latest
    container_name: nestsecure_openvas
    restart: unless-stopped
    environment:
      - PASSWORD=${OPENVAS_PASSWORD}
    volumes:
      - openvas_data:/var/lib/openvas
    ports:
      - "9390:9390"
    networks:
      - scan_network

  # Nginx (Reverse Proxy + Frontend)
  nginx:
    image: nginx:alpine
    container_name: nestsecure_nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./frontend/dist:/usr/share/nginx/html
      - ./docker/nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./docker/nginx/ssl:/etc/nginx/ssl
    depends_on:
      - api
    networks:
      - nestsecure_network
      # Nota: el frontend está en planeamiento. El servicio Nginx puede ejecutarse como reverse proxy y servirá contenido vacío hasta que exista `frontend/dist`.

volumes:
  postgres_data:
  redis_data:
  openvas_data:
  backend_logs:
  backend_reports:

networks:
  nestsecure_network:
    driver: bridge
  scan_network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16