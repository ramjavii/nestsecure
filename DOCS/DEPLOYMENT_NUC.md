# 🖥️ NESTSECURE - Guía de Deployment en Intel NUC

Esta guía te ayudará a desplegar NESTSECURE en tu Intel NUC para producción.

---

## 📋 ÍNDICE

1. [Requisitos de Hardware](#requisitos-de-hardware)
2. [Preparación del Sistema](#preparación-del-sistema)
3. [Instalación de Dependencias](#instalación-de-dependencias)
4. [Configuración de Red](#configuración-de-red)
5. [Seguridad](#seguridad)
6. [Deployment](#deployment)
7. [Post-Deployment](#post-deployment)
8. [Mantenimiento](#mantenimiento)
9. [Troubleshooting](#troubleshooting)

---

## 💻 REQUISITOS DE HARDWARE

### Mínimos Recomendados para NUC

| Componente | Mínimo | Recomendado | Notas |
|------------|--------|-------------|-------|
| CPU | Intel i5 8th Gen | Intel i7 10th Gen+ | OpenVAS es CPU-intensive |
| RAM | 16GB | 32GB | GVM requiere 4-6GB |
| Storage | 256GB SSD | 512GB NVMe | Para datos + GVM feeds |
| Network | 1 Gbps | 1 Gbps | |

### Estimación de Uso de Recursos

```
PostgreSQL:     2-4 GB RAM
Redis:          512 MB RAM
GVM/OpenVAS:    4-6 GB RAM
Backend:        1-2 GB RAM
Celery Workers: 2-3 GB RAM
Nginx:          256 MB RAM
----------------------------
Total:          ~10-16 GB RAM
```

---

## 🛠️ PREPARACIÓN DEL SISTEMA

### 1. Instalar Ubuntu Server 22.04 LTS

```bash
# Descargar desde: https://ubuntu.com/download/server
# Crear USB booteable con Rufus (Windows) o dd (Linux/Mac)

# En NUC:
# 1. Boot desde USB
# 2. Seguir instalación mínima
# 3. Habilitar OpenSSH durante instalación
# 4. NO instalar Docker durante instalación (lo haremos manual)
```

### 2. Configuración Inicial

```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar herramientas básicas
sudo apt install -y \
    curl \
    wget \
    git \
    vim \
    htop \
    net-tools \
    ufw \
    fail2ban \
    unattended-upgrades

# Configurar timezone
sudo timedatectl set-timezone America/Mexico_City  # Ajusta a tu zona

# Configurar hostname
sudo hostnamectl set-hostname nestsecure
```

### 3. Crear Usuario de Aplicación

```bash
# Crear usuario sin sudo (más seguro)
sudo adduser nestsecure --disabled-password

# Crear grupo docker y agregar usuario
sudo groupadd docker
sudo usermod -aG docker $USER
sudo usermod -aG docker nestsecure

# Recargar grupos
newgrp docker
```

---

## 📦 INSTALACIÓN DE DEPENDENCIAS

### Docker Engine

```bash
# Remover versiones antiguas
sudo apt remove docker docker-engine docker.io containerd runc

# Instalar dependencias
sudo apt install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Agregar GPG key de Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Agregar repositorio
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Instalar Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Verificar instalación
docker --version
docker compose version

# Habilitar Docker al inicio
sudo systemctl enable docker
sudo systemctl start docker

# Probar Docker
docker run hello-world
```

### Node.js (para build del frontend)

```bash
# Instalar NVM
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash

# Cargar NVM
source ~/.bashrc

# Instalar Node.js LTS
nvm install --lts
nvm use --lts

# Verificar
node --version
npm --version
```

---

## 🌐 CONFIGURACIÓN DE RED

### 1. IP Estática

```bash
# Editar Netplan
sudo vim /etc/netplan/00-installer-config.yaml

# Configuración de ejemplo:
network:
  version: 2
  renderer: networkd
  ethernets:
    enp0s1:  # Ajusta al nombre de tu interface
      dhcp4: no
      addresses:
        - 192.168.1.100/24  # Tu IP estática
      gateway4: 192.168.1.1  # Tu gateway
      nameservers:
        addresses:
          - 8.8.8.8
          - 8.8.4.4

# Aplicar cambios
sudo netplan apply

# Verificar
ip addr show
```

### 2. DNS Local (Opcional)

```bash
# Editar /etc/hosts en tu máquina de desarrollo
sudo vim /etc/hosts

# Agregar:
192.168.1.100  nestsecure.local
```

### 3. Firewall (UFW)

```bash
# Habilitar UFW
sudo ufw enable

# Permitir SSH desde tu red local solamente
sudo ufw allow from 192.168.1.0/24 to any port 22

# Permitir HTTP y HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Ver reglas
sudo ufw status verbose

# Denegar todo lo demás (default)
sudo ufw default deny incoming
sudo ufw default allow outgoing
```

---

## 🔒 SEGURIDAD

### 1. SSH Hardening

```bash
# Editar configuración SSH
sudo vim /etc/ssh/sshd_config

# Cambiar:
PermitRootLogin no
PasswordAuthentication no  # Después de configurar SSH keys
PubkeyAuthentication yes
Port 2222  # Cambiar puerto (opcional)
MaxAuthTries 3
MaxSessions 5
ClientAliveInterval 300
ClientAliveCountMax 2

# Reiniciar SSH
sudo systemctl restart sshd
```

### 2. SSH Keys

```bash
# En tu máquina local, generar key pair
ssh-keygen -t ed25519 -C "tu-email@example.com"

# Copiar a NUC
ssh-copy-id -i ~/.ssh/id_ed25519.pub user@192.168.1.100

# Probar conexión
ssh user@192.168.1.100
```

### 3. Fail2Ban

```bash
# Instalar (ya instalado arriba)
sudo apt install fail2ban -y

# Crear configuración local
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
sudo vim /etc/fail2ban/jail.local

# Configurar SSH jail:
[sshd]
enabled = true
port = 2222  # Si cambiaste el puerto
maxretry = 3
bantime = 3600
findtime = 600

# Iniciar Fail2Ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# Ver bans activos
sudo fail2ban-client status sshd
```

### 4. Actualizaciones Automáticas

```bash
# Configurar unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades

# Editar configuración
sudo vim /etc/apt/apt.conf.d/50unattended-upgrades

# Asegurar que estas líneas estén descomentadas:
"${distro_id}:${distro_codename}-security";
"${distro_id}:${distro_codename}-updates";

# Habilitar actualizaciones automáticas
sudo systemctl enable unattended-upgrades
sudo systemctl start unattended-upgrades
```

---

## 🚀 DEPLOYMENT

### 1. Clonar Repositorio

```bash
# Conectarse a NUC
ssh user@192.168.1.100

# Clonar repo
cd /opt
sudo git clone https://github.com/tu-usuario/nestsecure.git
sudo chown -R nestsecure:nestsecure nestsecure
cd nestsecure
```

### 2. Configurar Variables de Entorno

```bash
# Copiar template
cp .env.production.example .env.production

# Editar con tus valores
vim .env.production

# Generar secrets seguros:
python3 -c "import secrets; print(secrets.token_urlsafe(32))"  # SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(32))"  # JWT_SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(16))"  # DB_PASSWORD
```

**Valores importantes a configurar:**

```bash
# .env.production
ENVIRONMENT=production

# Secrets (generar con comando de arriba)
SECRET_KEY=tu-secret-key-generado
JWT_SECRET_KEY=tu-jwt-secret-generado
DB_PASSWORD=tu-db-password-generado
REDIS_PASSWORD=tu-redis-password-generado
GVM_ADMIN_PASSWORD=tu-gvm-password-generado

# URLs
DATABASE_URL=postgresql+asyncpg://nestsecure:${DB_PASSWORD}@postgres:5432/nestsecure
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0

# CORS (tu IP o dominio)
CORS_ORIGINS=https://nestsecure.local,https://192.168.1.100

# Email (opcional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu-email@gmail.com
SMTP_PASSWORD=tu-app-password
```

### 3. SSL Certificates

#### Opción A: Self-Signed (para red local)

```bash
# Crear directorio
mkdir -p nginx/ssl

# Generar certificado self-signed
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/key.pem \
  -out nginx/ssl/cert.pem \
  -subj "/C=MX/ST=Estado/L=Ciudad/O=NestSecure/CN=nestsecure.local"

# Verificar
openssl x509 -in nginx/ssl/cert.pem -text -noout
```

#### Opción B: Let's Encrypt (si tienes dominio público)

```bash
# Instalar certbot
sudo apt install certbot python3-certbot-nginx -y

# Obtener certificado
sudo certbot certonly --standalone -d tu-dominio.com

# Certificados estarán en:
# /etc/letsencrypt/live/tu-dominio.com/fullchain.pem
# /etc/letsencrypt/live/tu-dominio.com/privkey.pem

# Configurar renovación automática
sudo certbot renew --dry-run
```

### 4. Build Frontend

```bash
cd frontend

# Instalar dependencias
npm install

# Build para producción
npm run build

# El output estará en frontend/dist/
ls -la dist/
```

### 5. Deploy con Docker

```bash
# Volver a raíz
cd /opt/nestsecure

# Dar permisos al script
chmod +x deploy.sh

# Ejecutar deployment
./deploy.sh

# O manualmente:
docker compose -f docker-compose.prod.yml build --no-cache
docker compose -f docker-compose.prod.yml up -d
```

### 6. Verificar Deployment

```bash
# Ver logs
docker compose -f docker-compose.prod.yml logs -f

# Ver servicios corriendo
docker compose -f docker-compose.prod.yml ps

# Health checks
curl http://localhost/health
curl http://localhost/api/v1/health

# Verificar GVM (espera 10-15 min la primera vez)
docker compose -f docker-compose.prod.yml exec gvm gvm-cli --gmp-username admin --gmp-password $GVM_ADMIN_PASSWORD socket --socketpath /run/gvmd/gvmd.sock --xml "<get_version/>"
```

---

## 🔧 POST-DEPLOYMENT

### 1. Crear Usuario Admin

```bash
# Acceder al container backend
docker compose -f docker-compose.prod.yml exec backend bash

# Ejecutar script de creación de superuser
python -m app.scripts.create_superuser

# Ingresar datos:
# Email: admin@nestsecure.local
# Password: (tu password seguro)
# Full Name: Administrator

# Salir
exit
```

### 2. Configurar Backups Automáticos

```bash
# Crear script de backup
sudo vim /opt/nestsecure/scripts/backup.sh
```

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/opt/backups/nestsecure"
DATE=$(date +%Y%m%d_%H%M%S)
COMPOSE_FILE="/opt/nestsecure/docker-compose.prod.yml"

mkdir -p $BACKUP_DIR

# Backup PostgreSQL
docker compose -f $COMPOSE_FILE exec -T postgres pg_dump -U nestsecure nestsecure | gzip > "$BACKUP_DIR/postgres_$DATE.sql.gz"

# Backup volúmenes Docker
docker run --rm -v nestsecure_postgres_data:/data -v $BACKUP_DIR:/backup alpine tar czf /backup/postgres_data_$DATE.tar.gz -C /data .
docker run --rm -v nestsecure_gvm_data:/data -v $BACKUP_DIR:/backup alpine tar czf /backup/gvm_data_$DATE.tar.gz -C /data .

# Backup .env
cp /opt/nestsecure/.env.production "$BACKUP_DIR/env_$DATE"

# Retener solo últimos 7 días
find $BACKUP_DIR -name "*.gz" -mtime +7 -delete
find $BACKUP_DIR -name "env_*" -mtime +7 -delete

echo "Backup completado: $DATE"
```

```bash
# Dar permisos
chmod +x /opt/nestsecure/scripts/backup.sh

# Configurar cron
crontab -e

# Agregar backup diario a las 2 AM
0 2 * * * /opt/nestsecure/scripts/backup.sh >> /var/log/nestsecure-backup.log 2>&1
```

### 3. Configurar Logs Rotation

```bash
# Crear configuración logrotate
sudo vim /etc/logrotate.d/nestsecure
```

```
/var/log/nestsecure*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    missingok
    create 0644 nestsecure nestsecure
}
```

### 4. Monitoreo con Prometheus (Opcional)

```bash
# Prometheus ya está incluido en docker-compose.prod.yml
# Acceder a: http://192.168.1.100:9090

# Para alertas, configurar AlertManager:
# Ver: https://prometheus.io/docs/alerting/latest/alertmanager/
```

---

## 🔄 MANTENIMIENTO

### Actualizar Sistema

```bash
# Conectarse a NUC
ssh user@192.168.1.100

# Navegar al proyecto
cd /opt/nestsecure

# Pull cambios
git pull origin main

# Rebuild
docker compose -f docker-compose.prod.yml build --no-cache

# Restart servicios
docker compose -f docker-compose.prod.yml up -d

# Verificar
docker compose -f docker-compose.prod.yml ps
```

### Ver Logs

```bash
# Todos los servicios
docker compose -f docker-compose.prod.yml logs -f

# Servicio específico
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f gvm

# Últimas 100 líneas
docker compose -f docker-compose.prod.yml logs --tail=100 backend
```

### Monitoreo de Recursos

```bash
# CPU, RAM, Disk
htop

# Docker stats
docker stats

# Disk usage
df -h
docker system df
```

### Limpiar Docker

```bash
# Remover containers detenidos
docker container prune -f

# Remover imágenes sin usar
docker image prune -a -f

# Remover volúmenes sin usar (¡CUIDADO!)
docker volume prune -f

# Todo de una vez
docker system prune -a --volumes -f
```

---

## 🐛 TROUBLESHOOTING

### GVM no inicia

```bash
# Ver logs de GVM
docker compose -f docker-compose.prod.yml logs gvm

# GVM tarda 10-15 min en iniciar la primera vez
# Esperar a ver: "All services started successfully"

# Verificar memoria disponible
free -h

# Si falta RAM, reducir workers de Celery en docker-compose.prod.yml:
# --concurrency=1 en lugar de 2
```

### Backend no conecta a DB

```bash
# Verificar PostgreSQL
docker compose -f docker-compose.prod.yml exec postgres psql -U nestsecure -d nestsecure -c "SELECT 1;"

# Ver logs de backend
docker compose -f docker-compose.prod.yml logs backend

# Verificar variables de entorno
docker compose -f docker-compose.prod.yml exec backend env | grep DATABASE_URL
```

### Redis connection refused

```bash
# Verificar Redis
docker compose -f docker-compose.prod.yml exec redis redis-cli ping

# Si hay password:
docker compose -f docker-compose.prod.yml exec redis redis-cli -a $REDIS_PASSWORD ping

# Reiniciar Redis
docker compose -f docker-compose.prod.yml restart redis
```

### Frontend muestra 502 Bad Gateway

```bash
# Verificar Nginx
docker compose -f docker-compose.prod.yml exec nginx nginx -t

# Ver logs de Nginx
docker compose -f docker-compose.prod.yml logs nginx

# Verificar backend está corriendo
docker compose -f docker-compose.prod.yml ps backend

# Verificar health del backend
curl http://localhost:8000/health
```

### Scans no se ejecutan

```bash
# Verificar Celery workers
docker compose -f docker-compose.prod.yml ps | grep celery

# Ver logs de Celery
docker compose -f docker-compose.prod.yml logs celery_worker_scanning

# Verificar Redis (broker)
docker compose -f docker-compose.prod.yml exec redis redis-cli -a $REDIS_PASSWORD info

# Ver tasks en Redis
docker compose -f docker-compose.prod.yml exec redis redis-cli -a $REDIS_PASSWORD keys '*celery*'

# Reiniciar workers
docker compose -f docker-compose.prod.yml restart celery_worker_scanning
```

### Disk lleno

```bash
# Ver uso de disco
df -h

# Ver uso de Docker
docker system df

# Limpiar logs de Docker
sudo sh -c "truncate -s 0 /var/lib/docker/containers/**/*-json.log"

# Configurar log rotation para Docker
sudo vim /etc/docker/daemon.json
```

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

```bash
# Reiniciar Docker
sudo systemctl restart docker
```

---

## 📊 MÉTRICAS DE RENDIMIENTO

### Tiempos Esperados

| Operación | Tiempo Esperado |
|-----------|-----------------|
| Inicio completo del stack | 2-3 minutos |
| GVM primera inicialización | 10-15 minutos |
| Login | < 500ms |
| Carga de dashboard | < 1s |
| API response promedio | < 200ms |
| Scan discovery (red /24) | 5-10 minutos |
| Scan OpenVAS full | 30-60 minutos |

---

## 🔗 RECURSOS ÚTILES

- **Documentación Backend:** [DOCS/DESARROLLO/README.md](DOCS/DESARROLLO/README.md)
- **Plan Fase 2:** [DOCS/DESARROLLO/FASE_02_PLAN_COMPLETO.md](DOCS/DESARROLLO/FASE_02_PLAN_COMPLETO.md)
- **Docker Compose:** [docker-compose.prod.yml](../docker-compose.prod.yml)
- **Nginx Config:** [nginx/nginx.conf](../nginx/nginx.conf)

---

## ✅ CHECKLIST DE DEPLOYMENT

```markdown
## Pre-Deployment
- [ ] NUC tiene mínimo 16GB RAM
- [ ] Ubuntu Server 22.04 LTS instalado
- [ ] Docker y Docker Compose instalados
- [ ] IP estática configurada
- [ ] DNS configurado (opcional)
- [ ] Firewall UFW configurado
- [ ] SSH hardening aplicado
- [ ] SSH keys configurados
- [ ] Fail2Ban configurado

## Deployment
- [ ] Repositorio clonado en /opt/nestsecure
- [ ] .env.production configurado con secrets únicos
- [ ] SSL certificates generados (self-signed o Let's Encrypt)
- [ ] Frontend buildeado (npm run build)
- [ ] Docker images buildeadas
- [ ] Containers iniciados correctamente
- [ ] Health checks pasando

## Post-Deployment
- [ ] Usuario admin creado
- [ ] Login exitoso en frontend
- [ ] Dashboard carga correctamente
- [ ] Scans de prueba ejecutándose
- [ ] Backups automáticos configurados
- [ ] Logs rotation configurado
- [ ] Monitoreo configurado (opcional)

## Validation
- [ ] Backend API responde
- [ ] Frontend accesible via HTTPS
- [ ] GVM funcionando
- [ ] Celery workers procesando
- [ ] PostgreSQL aceptando conexiones
- [ ] Redis operativo
- [ ] Prometheus scraping métricas

## Security
- [ ] Passwords únicos generados
- [ ] SSH solo con keys
- [ ] Root login deshabilitado
- [ ] Firewall activo
- [ ] Rate limiting funcionando
- [ ] HTTPS funcionando
- [ ] Security headers configurados
```

---

**¡Deployment exitoso!** 🎉

Para soporte, abre un issue en GitHub o consulta la [documentación completa](README.md).
