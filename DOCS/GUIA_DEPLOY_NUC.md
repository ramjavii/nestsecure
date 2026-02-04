# 🚀 Guía de Despliegue de NestSecure en Intel NUC

Esta guía te llevará paso a paso por el proceso de despliegue de NestSecure en tu Intel NUC.

## 📋 Requisitos Previos

### Hardware
- Intel NUC (o similar) con mínimo 8GB RAM (recomendado 16GB)
- Mínimo 50GB de espacio en disco (recomendado SSD)
- Conexión a la red local que deseas escanear

### Software en el NUC
- Ubuntu Server 22.04 LTS (recomendado) o Debian 12
- Acceso SSH al NUC
- Usuario con permisos sudo

---

## 📦 Paso 1: Preparar el Sistema Operativo

### 1.1 Conectarse al NUC por SSH
```bash
ssh usuario@IP_DEL_NUC
# Ejemplo: ssh fabian@192.168.1.100
```

### 1.2 Actualizar el sistema
```bash
sudo apt update && sudo apt upgrade -y
```

### 1.3 Instalar dependencias básicas
```bash
sudo apt install -y curl git wget nano htop
```

---

## 🐳 Paso 2: Instalar Docker

### 2.1 Instalar Docker Engine
```bash
# Añadir repositorio oficial de Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Añadir tu usuario al grupo docker (para no usar sudo)
sudo usermod -aG docker $USER

# Aplicar cambios de grupo (o reconectar SSH)
newgrp docker
```

### 2.2 Verificar instalación
```bash
docker --version
# Debería mostrar: Docker version 24.x.x o superior

docker compose version
# Debería mostrar: Docker Compose version v2.x.x
```

---

## 📂 Paso 3: Clonar el Proyecto

### 3.1 Clonar el repositorio
```bash
cd ~
git clone https://github.com/TU_USUARIO/NESTSECURE.git
cd NESTSECURE
```

> 📝 **Alternativa**: Si no tienes el repo en GitHub, puedes copiarlo desde tu Mac:
> ```bash
> # Desde tu Mac:
> scp -r ~/Desktop/NESTSECURE usuario@IP_NUC:~/
> ```

---

## ⚙️ Paso 4: Configurar Variables de Entorno

### 4.1 Crear archivo .env desde la plantilla
```bash
cp .env.production.example .env
```

### 4.2 Editar configuración
```bash
nano .env
```

### 4.3 Modificar estos valores OBLIGATORIOS:

```env
# IP del NUC en tu red
NUC_IP=192.168.1.100  # <-- Cambia por la IP real de tu NUC

# PostgreSQL - CAMBIA LA CONTRASEÑA
POSTGRES_PASSWORD=TuContraseñaSegura123!

# Secret Key - GENERA UNA NUEVA
# Ejecuta: openssl rand -hex 32
SECRET_KEY=pega_aqui_el_resultado_de_openssl

# CORS - Ajusta según tu red
BACKEND_CORS_ORIGINS=["http://localhost","http://192.168.1.100"]
```

### 4.4 Generar Secret Key
```bash
# Ejecuta esto y copia el resultado al .env
openssl rand -hex 32
```

Guarda el archivo con `Ctrl+O`, Enter, `Ctrl+X`.

---

## 🔨 Paso 5: Construir e Iniciar los Servicios

### 5.1 Construir las imágenes Docker
```bash
# Esto tardará 5-15 minutos la primera vez
docker compose -f docker-compose.prod.yml build
```

### 5.2 Iniciar todos los servicios
```bash
docker compose -f docker-compose.prod.yml up -d
```

### 5.3 Verificar que todo está corriendo
```bash
docker compose -f docker-compose.prod.yml ps
```

Deberías ver algo así:
```
NAME                         STATUS              PORTS
nestsecure_api               running (healthy)   127.0.0.1:8000->8000/tcp
nestsecure_beat              running             
nestsecure_celery_scanning   running             
nestsecure_frontend          running (healthy)   127.0.0.1:3000->3000/tcp
nestsecure_nginx             running             0.0.0.0:80->80/tcp
nestsecure_postgres          running (healthy)   127.0.0.1:5432->5432/tcp
nestsecure_redis             running (healthy)   127.0.0.1:6379->6379/tcp
nestsecure_worker            running             
```

---

## 🗃️ Paso 6: Inicializar la Base de Datos

### 6.1 Ejecutar migraciones
```bash
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
```

### 6.2 Crear usuario administrador
```bash
docker compose -f docker-compose.prod.yml exec api python -m app.scripts.create_admin
```

> 📝 **Credenciales por defecto**:
> - Email: `admin@nestsecure.com`
> - Password: `Admin123!`
> 
> ⚠️ **IMPORTANTE**: Cambia la contraseña después del primer login

---

## 🌐 Paso 7: Acceder a la Aplicación

### 7.1 Desde cualquier dispositivo en tu red local

Abre un navegador y ve a:
```
http://IP_DEL_NUC
# Ejemplo: http://192.168.1.100
```

### 7.2 Iniciar sesión
- Email: `admin@nestsecure.com`
- Password: `Admin123!`

### 7.3 URLs disponibles:
| URL | Descripción |
|-----|-------------|
| `http://IP_NUC/` | Dashboard principal |
| `http://IP_NUC/api/docs` | Documentación API (Swagger) |
| `http://IP_NUC/api/redoc` | Documentación API (ReDoc) |
| `http://IP_NUC/health` | Health check |

---

## 📊 Paso 8: Verificar el Sistema

### 8.1 Verificar logs
```bash
# Todos los servicios
docker compose -f docker-compose.prod.yml logs -f

# Solo un servicio específico
docker compose -f docker-compose.prod.yml logs -f api
docker compose -f docker-compose.prod.yml logs -f frontend
```

### 8.2 Verificar salud de la API
```bash
curl http://localhost:8000/health
# Debería devolver: {"status":"healthy",...}
```

### 8.3 Probar un escaneo
1. Ve al Dashboard
2. Click en "Escaneos" en el menú lateral
3. Click en "Nuevo Escaneo"
4. Ingresa un target de tu red local (ej: `192.168.1.1`)
5. Click en "Iniciar Escaneo"

---

## 🔧 Comandos Útiles

### Gestión de servicios
```bash
# Detener todos los servicios
docker compose -f docker-compose.prod.yml down

# Reiniciar un servicio específico
docker compose -f docker-compose.prod.yml restart api

# Ver uso de recursos
docker stats

# Limpiar recursos no usados
docker system prune -a
```

### Logs y debugging
```bash
# Ver logs en tiempo real
docker compose -f docker-compose.prod.yml logs -f

# Ver logs de los últimos 100 líneas
docker compose -f docker-compose.prod.yml logs --tail=100 api

# Entrar a un contenedor
docker compose -f docker-compose.prod.yml exec api bash
```

### Base de datos
```bash
# Backup de la base de datos
docker compose -f docker-compose.prod.yml exec postgres pg_dump -U nestsecure nestsecure_db > backup_$(date +%Y%m%d).sql

# Restaurar backup
cat backup.sql | docker compose -f docker-compose.prod.yml exec -T postgres psql -U nestsecure nestsecure_db
```

---

## 🔄 Actualizar NestSecure

### Cuando haya una nueva versión:
```bash
cd ~/NESTSECURE

# 1. Detener servicios
docker compose -f docker-compose.prod.yml down

# 2. Obtener última versión
git pull origin main

# 3. Reconstruir imágenes
docker compose -f docker-compose.prod.yml build

# 4. Ejecutar migraciones (si hay)
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml exec api alembic upgrade head

# 5. Reiniciar todo
docker compose -f docker-compose.prod.yml restart
```

---

## 🛡️ Configurar Inicio Automático

### Para que NestSecure inicie al arrancar el NUC:

```bash
# Crear archivo de servicio systemd
sudo nano /etc/systemd/system/nestsecure.service
```

Contenido:
```ini
[Unit]
Description=NestSecure Security Scanner
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/TU_USUARIO/NESTSECURE
ExecStart=/usr/bin/docker compose -f docker-compose.prod.yml up -d
ExecStop=/usr/bin/docker compose -f docker-compose.prod.yml down
User=TU_USUARIO

[Install]
WantedBy=multi-user.target
```

Activar:
```bash
sudo systemctl daemon-reload
sudo systemctl enable nestsecure
sudo systemctl start nestsecure
```

---

## ❓ Solución de Problemas

### El frontend no carga
```bash
# Verificar logs del frontend
docker compose -f docker-compose.prod.yml logs frontend

# Reconstruir frontend
docker compose -f docker-compose.prod.yml build frontend
docker compose -f docker-compose.prod.yml up -d frontend
```

### La API no responde
```bash
# Verificar que la base de datos está lista
docker compose -f docker-compose.prod.yml exec postgres pg_isready -U nestsecure

# Verificar logs de la API
docker compose -f docker-compose.prod.yml logs api
```

### Los escaneos no funcionan
```bash
# Verificar worker de scanning
docker compose -f docker-compose.prod.yml logs celery_worker_scanning

# Verificar que tiene permisos de red
docker compose -f docker-compose.prod.yml exec celery_worker_scanning nmap --version
```

### Problemas de memoria
```bash
# Ver uso de memoria
free -h
docker stats --no-stream

# Si hay poca memoria, reiniciar servicios
docker compose -f docker-compose.prod.yml restart
```

---

## 📞 Soporte

Si tienes problemas:
1. Revisa los logs: `docker compose -f docker-compose.prod.yml logs`
2. Verifica la documentación en `/DOCS`
3. Abre un issue en GitHub

---

## ✅ Checklist de Despliegue

- [ ] Sistema operativo actualizado
- [ ] Docker instalado y funcionando
- [ ] Proyecto clonado
- [ ] Archivo .env configurado con contraseñas seguras
- [ ] Imágenes Docker construidas
- [ ] Servicios iniciados y saludables
- [ ] Base de datos inicializada
- [ ] Usuario admin creado
- [ ] Acceso desde navegador funcionando
- [ ] Primer escaneo de prueba exitoso
- [ ] Inicio automático configurado (opcional)

---

¡Felicidades! 🎉 NestSecure está ahora corriendo en tu NUC.
