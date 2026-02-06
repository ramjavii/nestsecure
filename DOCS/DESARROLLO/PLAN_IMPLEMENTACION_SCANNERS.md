# Plan Estratégico: Implementación de Scanners (Nuclei, ZAP, OpenVAS)

**Fecha**: 6 de febrero de 2026  
**Objetivo**: Activar y configurar scanners de seguridad reales en NestSecure  
**Estado Actual**: Todos los scanners en modo mock (simulación)

---

## 📊 Estado Actual

### Scanners Disponibles

| Scanner | Estado | Modo | Worker | Endpoint |
|---------|--------|------|--------|----------|
| Nmap | ✅ Funcional | Real | `nmap_worker.py` | `/api/v1/scans` |
| Nuclei | ⚠️ Mock | Simulación | `nuclei_worker.py` | `/api/v1/scans` |
| ZAP | ⚠️ Mock | Simulación | `zap_worker.py` | `/api/v1/scans` |
| OpenVAS | ⚠️ Mock | Simulación | `openvas_worker.py` | `/api/v1/scans` |

### Razones del Modo Mock

1. **Nuclei**: Binario no instalado en contenedor
2. **ZAP**: Servicio ZAP no configurado
3. **OpenVAS**: GVM/OpenVAS no desplegado

---

## 🎯 Fase 1: Nuclei Scanner (PRIORIDAD ALTA)

### ¿Por qué Nuclei primero?

- ✅ Más fácil de instalar (binario Go simple)
- ✅ Sin dependencias externas pesadas
- ✅ Templates actualizados automáticamente
- ✅ Mejor para vulnerabilidades web modernas
- ✅ Worker ya implementado y funcional

### Requisitos

- **Binary**: `nuclei` (Go)
- **Templates**: Repositorio de ProjectDiscovery
- **Espacio**: ~500MB para templates
- **Red**: Acceso a targets HTTP/HTTPS

### Plan de Implementación

#### 1.1 Actualizar Dockerfile del Backend

```dockerfile
# En backend/Dockerfile, después de instalar nmap
RUN apt-get update && apt-get install -y \
    nmap \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Instalar Nuclei
RUN wget -qO- https://github.com/projectdiscovery/nuclei/releases/latest/download/nuclei_linux_amd64.zip \
    -O /tmp/nuclei.zip && \
    unzip /tmp/nuclei.zip -d /usr/local/bin/ && \
    chmod +x /usr/local/bin/nuclei && \
    rm /tmp/nuclei.zip

# Crear directorio para templates
RUN mkdir -p /opt/nuclei-templates

# Descargar templates iniciales (opcional, se actualizan automáticamente)
RUN nuclei -update-templates -update-template-dir /opt/nuclei-templates
```

#### 1.2 Variables de Entorno

```yaml
# En docker-compose.dev.yml, sección backend y celery_worker
environment:
  - NUCLEI_PATH=/usr/local/bin/nuclei
  - NUCLEI_TEMPLATES_PATH=/opt/nuclei-templates
  - NUCLEI_TIMEOUT=1800
  - NUCLEI_RATE_LIMIT=150
  - NUCLEI_MOCK_MODE=false  # ← IMPORTANTE: Desactivar mock
```

#### 1.3 Validación

```bash
# Verificar instalación en contenedor
docker exec nestsecure_backend_dev nuclei -version

# Test básico
docker exec nestsecure_backend_dev nuclei -u http://example.com -t cves/
```

#### 1.4 Input Requirements

**Frontend debe aceptar**:
- ✅ `http://192.168.15.50`
- ✅ `https://example.com`
- ✅ `http://192.168.15.0/24` (multiple targets)
- ❌ Solo IP sin protocolo (debe convertirse)

**Conversión automática**: Si no tiene protocolo, asumir `http://`

#### 1.5 Testing

1. Crear scan tipo `nuclei` con target `http://testphp.vulnweb.com`
2. Verificar logs de celery
3. Confirmar vulnerabilidades en DB
4. Validar que no haya errores de "NoneType"

**Tiempo estimado**: 2-3 horas

---

## 🎯 Fase 2: OWASP ZAP Scanner (PRIORIDAD MEDIA)

### ¿Por qué ZAP?

- ✅ Scanner DAST completo
- ✅ Bien documentado
- ✅ API REST robusta
- ⚠️ Requiere servicio separado

### Requisitos

- **Servicio**: Contenedor ZAP standalone
- **API**: ZAP API Key
- **Puerto**: 8080 (configurable)
- **Red**: Network compartida con backend

### Plan de Implementación

#### 2.1 Crear Servicio ZAP

```yaml
# En docker-compose.dev.yml, agregar servicio ZAP
services:
  zap:
    image: ghcr.io/zaproxy/zaproxy:stable
    container_name: nestsecure_zap_dev
    command: zap.sh -daemon -host 0.0.0.0 -port 8080 -config api.key=${ZAP_API_KEY:-changeme}
    ports:
      - "8080:8080"
    networks:
      - nestsecure_network
    environment:
      - ZAP_API_KEY=changeme
    volumes:
      - zap_data:/zap/wrk
    restart: unless-stopped

volumes:
  zap_data:
```

#### 2.2 Variables de Entorno Backend

```yaml
environment:
  - ZAP_HOST=zap  # Nombre del servicio
  - ZAP_PORT=8080
  - ZAP_API_KEY=changeme
  - ZAP_TIMEOUT=3600
  - ZAP_MOCK_MODE=false
```

#### 2.3 Verificar Integración

```python
# En app/integrations/zap/client.py
# Ya existe, solo verificar que conecte
client = ZapClient(
    host=settings.ZAP_HOST,
    port=settings.ZAP_PORT,
    api_key=settings.ZAP_API_KEY,
)
await client.connect()
```

#### 2.4 Input Requirements

**Frontend debe aceptar**:
- ✅ `http://example.com/login`
- ✅ `https://app.example.com`
- ❌ Solo IP sin protocolo (debe tener http/https)

**Validación**: URL debe ser válida y accesible desde ZAP

#### 2.5 Testing

1. Iniciar servicio ZAP
2. Crear scan tipo `zap` con target `http://testphp.vulnweb.com`
3. Monitorear progreso en ZAP UI (http://localhost:8080)
4. Verificar alertas convertidas a vulnerabilidades

**Tiempo estimado**: 3-4 horas

---

## 🎯 Fase 3: OpenVAS/GVM Scanner (PRIORIDAD BAJA)

### ¿Por qué OpenVAS al final?

- ⚠️ Más complejo de instalar
- ⚠️ Requiere múltiples servicios
- ⚠️ Alto consumo de recursos
- ⚠️ Configuración inicial lenta

### Requisitos

- **Servicios**: gvmd, ospd-openvas, postgres, redis
- **Stack**: Docker Compose completo GVM
- **Espacio**: ~5GB para feeds NVT
- **RAM**: Mínimo 4GB recomendado

### Plan de Implementación

#### 3.1 Usar Stack GVM Oficial

```yaml
# Crear docker-compose.openvas.yml
version: '3.8'

services:
  gvm-postgres:
    image: postgres:14
    environment:
      POSTGRES_DB: gvmd
      POSTGRES_USER: gvm
      POSTGRES_PASSWORD: gvm
    volumes:
      - gvm_postgres_data:/var/lib/postgresql/data

  gvm-redis:
    image: redis:7

  gvmd:
    image: greenbone/gvmd:stable
    depends_on:
      - gvm-postgres
      - gvm-redis
    environment:
      - GVMD_POSTGRES_URI=postgresql://gvm:gvm@gvm-postgres:5432/gvmd
    volumes:
      - gvm_data:/var/lib/gvm

  ospd-openvas:
    image: greenbone/ospd-openvas:stable
    depends_on:
      - gvm-redis
    volumes:
      - gvm_data:/var/lib/openvas

  gsa:
    image: greenbone/gsa:stable
    ports:
      - "9392:80"
    depends_on:
      - gvmd

volumes:
  gvm_postgres_data:
  gvm_data:
```

#### 3.2 Configuración GVM

```bash
# Primera vez: Sincronizar feeds
docker exec gvmd greenbone-feed-sync --type all

# Crear usuario admin
docker exec gvmd gvmd --create-user=admin --password=admin
```

#### 3.3 Variables Backend

```yaml
environment:
  - GVM_HOST=gvmd
  - GVM_PORT=9390
  - GVM_USERNAME=admin
  - GVM_PASSWORD=admin
  - GVM_TIMEOUT=7200
  - OPENVAS_MOCK_MODE=false
```

#### 3.4 Input Requirements

**Frontend debe aceptar**:
- ✅ `192.168.15.50`
- ✅ `192.168.15.0/24`
- ✅ `example.com`
- ✅ Rangos: `192.168.15.1-254`

**Sin restricciones de protocolo**

#### 3.5 Testing

1. Verificar feeds actualizados
2. Crear scan tipo `openvas` con target `192.168.15.50`
3. Monitorear progreso (puede tardar 30+ minutos)
4. Verificar report generado en DB

**Tiempo estimado**: 6-8 horas (incluyendo sync de feeds)

---

## 🛠️ Cambios en Frontend

### Modificar Validación de Inputs

#### Archivo: `frontend/components/scans/scan-form-modal.tsx`

```typescript
// Actualizar validación de targets
const validateTargets = (targets: string[], scanType: string) => {
  const errors: string[] = [];
  
  targets.forEach(target => {
    if (scanType === 'zap' || scanType === 'nuclei') {
      // ZAP y Nuclei requieren URLs
      if (!target.startsWith('http://') && !target.startsWith('https://')) {
        errors.push(`${target}: debe incluir protocolo http:// o https://`);
      }
      // Validar URL
      try {
        new URL(target);
      } catch {
        errors.push(`${target}: URL inválida`);
      }
    } else if (scanType === 'openvas' || scanType === 'discovery') {
      // OpenVAS y Nmap aceptan IPs/hostnames
      // Validación de IP, CIDR, hostname
      if (!/^[\w\d\.\-\/]+$/.test(target)) {
        errors.push(`${target}: formato inválido`);
      }
    }
  });
  
  return errors;
};

// Agregar helper text dinámico
const getTargetPlaceholder = (scanType: string) => {
  switch(scanType) {
    case 'zap':
    case 'nuclei':
      return 'http://example.com, https://app.example.com/login';
    case 'openvas':
      return '192.168.1.50, 10.0.0.0/24, example.com';
    default:
      return '192.168.1.0/24, 10.0.0.50';
  }
};

const getTargetHelperText = (scanType: string) => {
  if (scanType === 'zap' || scanType === 'nuclei') {
    return '⚠️ URLs web completas con protocolo (http:// o https://)';
  }
  return 'IPs, rangos CIDR, o hostnames';
};
```

#### Archivo: `frontend/app/(dashboard)/scans/page.tsx`

```typescript
// Agregar badges informativos por tipo de scan
const getScanTypeInfo = (type: string) => {
  const info = {
    nuclei: {
      icon: '🔍',
      label: 'Nuclei Templates',
      description: 'Vulnerabilidades web con templates actualizados',
      inputFormat: 'URLs con http:// o https://'
    },
    zap: {
      icon: '🕷️',
      label: 'OWASP ZAP',
      description: 'DAST completo con spider y active scan',
      inputFormat: 'URLs web completas'
    },
    openvas: {
      icon: '🛡️',
      label: 'OpenVAS/GVM',
      description: 'Escaneo profundo de infraestructura',
      inputFormat: 'IPs, rangos CIDR, hostnames'
    }
  };
  return info[type] || null;
};
```

---

## 📋 Checklist de Implementación

### Fase 1: Nuclei (Semana 1)

- [ ] Actualizar Dockerfile con instalación de Nuclei
- [ ] Configurar variables de entorno
- [ ] Desactivar `NUCLEI_MOCK_MODE`
- [ ] Rebuild contenedores: `docker-compose build backend celery_worker`
- [ ] Verificar instalación: `nuclei -version`
- [ ] Actualizar validación de inputs en frontend
- [ ] Testing con target real
- [ ] Documentar resultados

### Fase 2: ZAP (Semana 2)

- [ ] Agregar servicio ZAP a docker-compose
- [ ] Configurar API key y networking
- [ ] Desactivar `ZAP_MOCK_MODE`
- [ ] Verificar conectividad backend → ZAP
- [ ] Testing con aplicación vulnerable
- [ ] Ajustar timeouts si es necesario
- [ ] Documentar políticas de scan

### Fase 3: OpenVAS (Semana 3-4)

- [ ] Crear docker-compose.openvas.yml
- [ ] Desplegar stack GVM completo
- [ ] Sincronizar feeds NVT (puede tardar horas)
- [ ] Crear usuario admin GVM
- [ ] Configurar conexión desde backend
- [ ] Desactivar `OPENVAS_MOCK_MODE`
- [ ] Testing con scan real (esperar 30+ min)
- [ ] Optimizar configuración de scans

---

## 🔧 Comandos Útiles

### Rebuild Contenedores

```bash
# Rebuild backend con nuevo Dockerfile
docker-compose -f docker-compose.dev.yml build backend celery_worker

# Restart servicios
docker-compose -f docker-compose.dev.yml up -d backend celery_worker
```

### Verificar Instalaciones

```bash
# Nuclei
docker exec nestsecure_backend_dev nuclei -version
docker exec nestsecure_backend_dev nuclei -tl  # List templates

# ZAP
curl http://localhost:8080/JSON/core/view/version/

# OpenVAS
docker exec gvmd gvmd --version
```

### Logs

```bash
# Ver logs de celery worker
docker-compose -f docker-compose.dev.yml logs -f celery_worker

# Ver logs de ZAP
docker logs -f nestsecure_zap_dev

# Ver logs de OpenVAS
docker exec gvmd tail -f /var/log/gvm/gvmd.log
```

---

## 🚨 Consideraciones de Seguridad

### Red Interna

- ✅ Todos los scanners deben estar en red privada Docker
- ✅ Solo exponer puertos necesarios (ZAP UI opcional)
- ✅ Usar API keys fuertes para ZAP

### Rate Limiting

- ⚠️ Nuclei: Configurar `NUCLEI_RATE_LIMIT` para no saturar red
- ⚠️ ZAP: Ajustar políticas de active scan
- ⚠️ OpenVAS: Usar configs moderadas por defecto

### Targets

- ⚠️ **NUNCA** escanear targets sin autorización
- ✅ Validar ownership de targets en frontend
- ✅ Logging completo de scans iniciados

---

## 📊 Métricas de Éxito

### Nuclei

- ✅ Templates actualizados (check versión)
- ✅ Scans completan sin errores
- ✅ Vulnerabilidades persistidas en DB
- ✅ Tiempo promedio < 5min para single target

### ZAP

- ✅ Spider encuentra > 80% de páginas
- ✅ Active scan sin timeout
- ✅ Alertas convertidas a vulnerabilidades
- ✅ Progreso reportado correctamente

### OpenVAS

- ✅ Feeds sincronizados (100%)
- ✅ Scans completan (puede tardar 30-60min)
- ✅ Reports generados en XML/JSON
- ✅ Vulnerabilidades con NVT info

---

## 🎓 Recursos

### Documentación

- [Nuclei Templates](https://github.com/projectdiscovery/nuclei-templates)
- [ZAP API](https://www.zaproxy.org/docs/api/)
- [OpenVAS/GVM](https://greenbone.github.io/docs/latest/)

### Testing Sites

- **Web**: http://testphp.vulnweb.com
- **DVWA**: http://dvwa.co.uk
- **OWASP Juice Shop**: https://owasp.org/www-project-juice-shop/

---

## 📝 Notas Finales

1. **Priorizar Nuclei**: Es el más fácil y útil para empezar
2. **Testing incremental**: Validar cada scanner antes de continuar
3. **Monitoreo**: Revisar logs constantemente durante implementación
4. **Rollback plan**: Mantener modo mock como fallback
5. **Documentación**: Actualizar este plan con hallazgos reales

**Estimación total**: 2-3 semanas para los 3 scanners funcionales en producción
