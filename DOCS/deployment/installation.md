# Guía de Instalación - NESTSECURE

## Requisitos del Sistema

### Hardware Mínimo

| Componente | Mínimo | Recomendado |
|------------|--------|-------------|
| CPU | Intel i5 / 4 cores | Intel i7 / 8 cores |
| RAM | 16 GB | 32 GB |
| Almacenamiento | 100 GB SSD | 500 GB NVMe |
| Red | 1 Gbps | 10 Gbps |

### Software Requerido

- **Sistema Operativo:** Ubuntu 22.04 LTS, Debian 12, o macOS 13+
- **Docker:** 24.0+
- **Docker Compose:** 2.23+
- **Git:** 2.30+

### Verificar Requisitos

```bash
# Verificar Docker
docker --version
# Docker version 24.0.0 o superior

# Verificar Docker Compose
docker compose version
# Docker Compose version v2.23.0 o superior

# Verificar Git
git --version
# git version 2.30.0 o superior
```

## Instalación Rápida (Recomendada)

### 1. Clonar el Repositorio

```bash
git clone https://github.com/tu-usuario/nestsecure.git
cd nestsecure
```

### 2. Configurar Variables de Entorno

```bash
# Copiar template
cp .env.example .env

# Editar configuración
nano .env
```

**Variables esenciales:**

```env
# Base de datos
POSTGRES_USER=nestsecure
POSTGRES_PASSWORD=TuPasswordSeguro123!
POSTGRES_DB=nestsecure

# Redis
REDIS_PASSWORD=TuRedisPassword123!

# Seguridad (CAMBIAR EN PRODUCCIÓN)
SECRET_KEY=tu-clave-secreta-de-minimo-32-caracteres

# Entorno
ENVIRONMENT=production  # o 'development' para desarrollo
DEBUG=false
```

### 3. Iniciar Servicios

```bash
# Modo producción
docker compose up -d

# Modo desarrollo (con hot-reload)
docker compose -f docker-compose.dev.yml up -d
```

### 4. Verificar Instalación

```bash
# Ver estado de contenedores
docker compose ps

# Ver logs
docker compose logs -f backend

# Verificar health
curl http://localhost:8000/health
```

### 5. Ejecutar Migraciones

Las migraciones se ejecutan automáticamente al iniciar. Para ejecutarlas manualmente:

```bash
docker compose exec backend alembic upgrade head
```

### 6. Crear Usuario Administrador

```bash
# Crear usuario demo
docker compose exec backend python scripts/create_demo.py

# Credenciales por defecto:
# Email: admin@nestsecure.local
# Password: Admin123!
```

### 7. Acceder al Sistema

- **API:** http://localhost:8000
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## Instalación Manual (Desarrollo)

### Backend

```bash
# Entrar al directorio
cd backend

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# o: venv\Scripts\activate  # Windows

# Instalar dependencias
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Para desarrollo

# Configurar variables
export DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/nestsecure"
export REDIS_URL="redis://localhost:6379/0"
export SECRET_KEY="tu-clave-secreta"

# Ejecutar migraciones
alembic upgrade head

# Iniciar servidor
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend (Próximamente)

```bash
cd frontend

# Instalar dependencias
npm install

# Modo desarrollo
npm run dev

# Build producción
npm run build
```

### Base de Datos

```bash
# PostgreSQL con Docker
docker run -d \
  --name nestsecure-postgres \
  -e POSTGRES_USER=nestsecure \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=nestsecure \
  -p 5432:5432 \
  -v nestsecure-postgres-data:/var/lib/postgresql/data \
  timescale/timescaledb:latest-pg15
```

### Redis

```bash
# Redis con Docker
docker run -d \
  --name nestsecure-redis \
  -p 6379:6379 \
  redis:7-alpine
```

### Celery Workers

```bash
cd backend
source venv/bin/activate

# Worker principal
celery -A app.core.celery_app worker -l info

# Worker de escaneo (cola específica)
celery -A app.core.celery_app worker -Q scanning -l info

# Celery Beat (tareas programadas)
celery -A app.core.celery_app beat -l info
```

## Configuración de Producción

### Nginx como Reverse Proxy

```nginx
# /etc/nginx/sites-available/nestsecure

upstream backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name nestsecure.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name nestsecure.example.com;

    ssl_certificate /etc/ssl/certs/nestsecure.crt;
    ssl_certificate_key /etc/ssl/private/nestsecure.key;

    # API
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Health checks
    location /health {
        proxy_pass http://backend;
    }

    # Frontend (cuando esté listo)
    location / {
        root /var/www/nestsecure;
        try_files $uri $uri/ /index.html;
    }
}
```

### SSL con Let's Encrypt

```bash
# Instalar certbot
sudo apt install certbot python3-certbot-nginx

# Obtener certificado
sudo certbot --nginx -d nestsecure.example.com

# Renovación automática
sudo crontab -e
# Agregar: 0 12 * * * /usr/bin/certbot renew --quiet
```

### Systemd Services

**Backend Service:**

```ini
# /etc/systemd/system/nestsecure-backend.service

[Unit]
Description=NESTSECURE Backend
After=network.target postgresql.service redis.service

[Service]
Type=exec
User=nestsecure
Group=nestsecure
WorkingDirectory=/opt/nestsecure/backend
Environment="PATH=/opt/nestsecure/backend/venv/bin"
EnvironmentFile=/opt/nestsecure/.env
ExecStart=/opt/nestsecure/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Celery Worker Service:**

```ini
# /etc/systemd/system/nestsecure-worker.service

[Unit]
Description=NESTSECURE Celery Worker
After=network.target redis.service

[Service]
Type=forking
User=nestsecure
Group=nestsecure
WorkingDirectory=/opt/nestsecure/backend
Environment="PATH=/opt/nestsecure/backend/venv/bin"
EnvironmentFile=/opt/nestsecure/.env
ExecStart=/opt/nestsecure/backend/venv/bin/celery -A app.core.celery_app worker -l info -D
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Firewall

```bash
# UFW (Ubuntu)
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

## Variables de Entorno

### Requeridas

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `DATABASE_URL` | URL de PostgreSQL | `postgresql+psycopg://user:pass@localhost/db` |
| `REDIS_URL` | URL de Redis | `redis://localhost:6379/0` |
| `SECRET_KEY` | Clave para JWT | `min-32-caracteres-aleatorios` |

### Opcionales

| Variable | Default | Descripción |
|----------|---------|-------------|
| `ENVIRONMENT` | `development` | development, staging, production |
| `DEBUG` | `true` | Modo debug |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Duración access token |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Duración refresh token |
| `CORS_ORIGINS` | `*` | Orígenes permitidos (CSV) |
| `NMAP_PATH` | `/usr/bin/nmap` | Ruta a nmap |
| `NMAP_TIMEOUT` | `3600` | Timeout de scans (seg) |

## Verificación de Instalación

### Health Check

```bash
# Check básico
curl http://localhost:8000/health

# Check completo (DB + Redis)
curl http://localhost:8000/health/ready
```

### Tests

```bash
# Ejecutar todos los tests
cd backend
./venv/bin/pytest -v

# Tests específicos
./venv/bin/pytest app/tests/test_api/ -v
```

### Logs

```bash
# Docker
docker compose logs -f backend
docker compose logs -f celery

# Systemd
journalctl -u nestsecure-backend -f
journalctl -u nestsecure-worker -f
```

## Actualizaciones

### Docker

```bash
# Obtener última versión
git pull origin main

# Reconstruir y reiniciar
docker compose down
docker compose build --no-cache
docker compose up -d

# Ejecutar migraciones
docker compose exec backend alembic upgrade head
```

### Manual

```bash
# Obtener última versión
git pull origin main

# Actualizar dependencias
cd backend
source venv/bin/activate
pip install -r requirements.txt

# Ejecutar migraciones
alembic upgrade head

# Reiniciar servicios
sudo systemctl restart nestsecure-backend
sudo systemctl restart nestsecure-worker
```

## Solución de Problemas

### Base de datos no conecta

```bash
# Verificar PostgreSQL
docker compose logs postgres
psql -h localhost -U nestsecure -d nestsecure

# Verificar conexión
curl http://localhost:8000/health/ready
```

### Redis no conecta

```bash
# Verificar Redis
docker compose logs redis
redis-cli ping
```

### Celery workers no inician

```bash
# Ver logs de Celery
docker compose logs celery

# Verificar Redis
redis-cli -h localhost info clients
```

### Permisos de Nmap

```bash
# Nmap necesita permisos de root para algunos scans
sudo setcap cap_net_raw,cap_net_admin+eip /usr/bin/nmap
```

---

## Próximos Pasos

1. [Configurar autenticación](authentication.md)
2. [Explorar la API](endpoints.md)
3. [Ejecutar tu primer scan](../user-guide/running-scans.md)

---

*Última actualización: 30 Enero 2026*
