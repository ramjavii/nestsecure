#### Docker Compose Structure
```yaml
version: '3.8'

services:
  # Main Application
  api:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: vulnscan-api
    restart: unless-stopped
    environment:
      - DATABASE_URL=postgresql://vulnscan:${DB_PASSWORD}@postgres:5432/vulnscan
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
      - ENVIRONMENT=production
    volumes:
      - ./data/uploads:/app/uploads
      - ./data/reports:/app/reports
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
    networks:
      - vulnscan-network
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
    container_name: vulnscan-worker
    restart: unless-stopped
    command: celery -A app.worker worker --loglevel=info --concurrency=4
    environment:
      - DATABASE_URL=postgresql://vulnscan:${DB_PASSWORD}@postgres:5432/vulnscan
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock  # For running scan containers
      - ./data/scans:/app/scans
    depends_on:
      - postgres
      - redis
    networks:
      - vulnscan-network
      - scan-network  # Separate network for scans

  # Celery Beat (Scheduler)
  beat:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: vulnscan-beat
    restart: unless-stopped
    command: celery -A app.worker beat --loglevel=info
    environment:
      - DATABASE_URL=postgresql://vulnscan:${DB_PASSWORD}@postgres:5432/vulnscan
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    networks:
      - vulnscan-network

  # Celery Flower (Monitoring)
  flower:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: vulnscan-flower
    restart: unless-stopped
    command: celery -A app.worker flower --port=5555
    environment:
      - REDIS_URL=redis://redis:6379/0
    ports:
      - "5555:5555"
    depends_on:
      - redis
    networks:
      - vulnscan-network

  # PostgreSQL Database
  postgres:
    image: timescale/timescaledb:latest-pg15
    container_name: vulnscan-postgres
    restart: unless-stopped
    environment:
      - POSTGRES_DB=vulnscan
      - POSTGRES_USER=vulnscan
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./init-scripts:/docker-entrypoint-initdb.d
    ports:
      - "5432:5432"
    networks:
      - vulnscan-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U vulnscan"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis
  redis:
    image: redis:7-alpine
    container_name: vulnscan-redis
    restart: unless-stopped
    command: redis-server --appendonly yes
    volumes:
      - redis-data:/data
    ports:
      - "6379:6379"
    networks:
      - vulnscan-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # OpenVAS Scanner
  openvas:
    image: greenbone/openvas-scanner:latest
    container_name: vulnscan-openvas
    restart: unless-stopped
    environment:
      - PASSWORD=${OPENVAS_PASSWORD}
    volumes:
      - openvas-data:/var/lib/openvas
    ports:
      - "9390:9390"
    networks:
      - scan-network

  # Nginx (Reverse Proxy + Frontend)
  nginx:
    image: nginx:alpine
    container_name: vulnscan-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./frontend/dist:/usr/share/nginx/html
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - api
    networks:
      - vulnscan-network

volumes:
  postgres-data:
  redis-data:
  openvas-data:

networks:
  vulnscan-network:
    driver: bridge
  scan-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16