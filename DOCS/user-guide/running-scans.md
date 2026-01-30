# Ejecutar Escaneos - Guía de Usuario

## Visión General

NESTSECURE permite ejecutar diferentes tipos de escaneos de red para descubrir hosts, servicios y vulnerabilidades en tu infraestructura.

## Tipos de Escaneo Disponibles

| Tipo | Descripción | Duración Aproximada | Uso |
|------|-------------|---------------------|-----|
| `quick` | Top 100 puertos más comunes | 1-5 min por host | Reconocimiento rápido |
| `full` | Todos los puertos (1-65535) | 15-30 min por host | Auditoría completa |
| `targeted` | Puertos específicos | Variable | Verificación específica |
| `port_scan` | Solo descubrimiento | 30 seg - 2 min | Inventario de red |
| `vuln_scan` | Búsqueda de vulnerabilidades | 10-30 min por host | Análisis de seguridad |
| `compliance` | Verificación de cumplimiento | 5-15 min | Auditoría de compliance |

## Crear un Escaneo

### Via API

```bash
# 1. Obtener token de autenticación
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=Password123!" | jq -r '.access_token')

# 2. Crear escaneo
curl -X POST "http://localhost:8000/api/v1/scans" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Escaneo de red corporativa",
    "scan_type": "quick",
    "targets": ["192.168.1.0/24"]
  }'
```

### Respuesta

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Escaneo de red corporativa",
  "scan_type": "quick",
  "status": "pending",
  "targets": ["192.168.1.0/24"],
  "created_at": "2026-01-30T10:00:00Z",
  "created_by": {
    "id": "...",
    "email": "admin@example.com",
    "full_name": "Admin User"
  }
}
```

## Formatos de Targets

NESTSECURE acepta múltiples formatos para especificar los objetivos:

### IP Individual

```json
{
  "targets": ["192.168.1.100"]
}
```

### Rango CIDR

```json
{
  "targets": ["192.168.1.0/24"]
}
```

### Rango de IPs

```json
{
  "targets": ["192.168.1.1-50"]
}
```

### Hostname

```json
{
  "targets": ["servidor.ejemplo.com"]
}
```

### Múltiples Targets

```json
{
  "targets": [
    "192.168.1.0/24",
    "10.0.0.1-100",
    "webserver.local",
    "192.168.2.50"
  ]
}
```

## Opciones Avanzadas

### Puertos Específicos

```json
{
  "name": "Scan de servicios web",
  "scan_type": "targeted",
  "targets": ["192.168.1.0/24"],
  "options": {
    "ports": "80,443,8080,8443"
  }
}
```

### Velocidad de Escaneo

```json
{
  "options": {
    "timing": "T4"  // T0-T5 (T0=lento, T5=agresivo)
  }
}
```

**Niveles de timing:**
| Nivel | Nombre | Uso |
|-------|--------|-----|
| T0 | Paranoid | IDS evasion |
| T1 | Sneaky | IDS evasion |
| T2 | Polite | Reduce carga |
| T3 | Normal | Default |
| T4 | Aggressive | Rápido |
| T5 | Insane | Muy rápido, puede perder resultados |

### Detección de Versiones

```json
{
  "options": {
    "version_detection": true,
    "version_intensity": 7  // 0-9
  }
}
```

### Detección de OS

```json
{
  "options": {
    "os_detection": true
  }
}
```

## Monitorear Progreso

### Obtener Estado del Escaneo

```bash
curl -X GET "http://localhost:8000/api/v1/scans/{scan_id}" \
  -H "Authorization: Bearer $TOKEN"
```

### Obtener Progreso en Tiempo Real

```bash
curl -X GET "http://localhost:8000/api/v1/scans/{scan_id}/progress" \
  -H "Authorization: Bearer $TOKEN"
```

**Respuesta:**

```json
{
  "status": "running",
  "progress_percent": 45,
  "current_target": "192.168.1.50",
  "targets_completed": 45,
  "targets_total": 254,
  "assets_found": 32,
  "services_found": 156,
  "vulnerabilities_found": 12,
  "elapsed_time": "00:05:32",
  "estimated_remaining": "00:06:45"
}
```

## Listar Escaneos

### Todos los Escaneos

```bash
curl -X GET "http://localhost:8000/api/v1/scans" \
  -H "Authorization: Bearer $TOKEN"
```

### Filtrar por Estado

```bash
# Solo escaneos en ejecución
curl -X GET "http://localhost:8000/api/v1/scans?status=running" \
  -H "Authorization: Bearer $TOKEN"

# Solo completados
curl -X GET "http://localhost:8000/api/v1/scans?status=completed" \
  -H "Authorization: Bearer $TOKEN"
```

### Filtrar por Tipo

```bash
curl -X GET "http://localhost:8000/api/v1/scans?scan_type=full" \
  -H "Authorization: Bearer $TOKEN"
```

## Cancelar un Escaneo

```bash
curl -X PATCH "http://localhost:8000/api/v1/scans/{scan_id}/cancel" \
  -H "Authorization: Bearer $TOKEN"
```

**Nota:** Solo se pueden cancelar escaneos en estado `pending` o `running`.

## Ver Resultados

### Vulnerabilidades del Escaneo

```bash
curl -X GET "http://localhost:8000/api/v1/scans/{scan_id}/vulnerabilities" \
  -H "Authorization: Bearer $TOKEN"
```

### Assets Descubiertos

Los assets se crean automáticamente en `/api/v1/assets`.

```bash
# Ver assets del último escaneo
curl -X GET "http://localhost:8000/api/v1/assets?order_by=first_seen&order_desc=true" \
  -H "Authorization: Bearer $TOKEN"
```

## Estadísticas de Escaneos

```bash
curl -X GET "http://localhost:8000/api/v1/scans/stats" \
  -H "Authorization: Bearer $TOKEN"
```

**Respuesta:**

```json
{
  "total_scans": 50,
  "by_status": {
    "completed": 45,
    "running": 2,
    "failed": 2,
    "cancelled": 1
  },
  "by_type": {
    "quick": 30,
    "full": 15,
    "targeted": 5
  },
  "average_duration_minutes": 12.5,
  "total_vulnerabilities_found": 234,
  "total_assets_discovered": 156,
  "last_scan_completed": "2026-01-30T09:45:00Z"
}
```

## Programar Escaneos

### Escaneo Programado

```json
{
  "name": "Escaneo nocturno",
  "scan_type": "full",
  "targets": ["192.168.1.0/24"],
  "scheduled_at": "2026-01-31T02:00:00Z"
}
```

El escaneo quedará en estado `pending` hasta la hora programada.

## Estados del Escaneo

```
pending ──▶ running ──▶ completed
    │          │
    │          └──▶ failed
    │
    └──▶ cancelled
```

| Estado | Descripción |
|--------|-------------|
| `pending` | En cola, esperando workers |
| `running` | En ejecución |
| `completed` | Finalizado exitosamente |
| `failed` | Error durante ejecución |
| `cancelled` | Cancelado por usuario |

## Mejores Prácticas

### 1. Empezar con Quick Scan

Para un primer reconocimiento, usa `quick` para obtener resultados rápidos:

```json
{
  "name": "Reconocimiento inicial",
  "scan_type": "quick",
  "targets": ["192.168.1.0/24"]
}
```

### 2. Full Scan en Horarios de Baja Actividad

Los escaneos completos son intensivos. Programarlos fuera de horario laboral:

```json
{
  "name": "Auditoría completa",
  "scan_type": "full",
  "targets": ["192.168.1.0/24"],
  "scheduled_at": "2026-01-31T02:00:00Z"
}
```

### 3. Segmentar Redes Grandes

Para redes grandes, dividir en subredes:

```json
{
  "name": "Segmento A",
  "targets": ["192.168.1.0/25"]
}
```

```json
{
  "name": "Segmento B", 
  "targets": ["192.168.1.128/25"]
}
```

### 4. Usar Timing Apropiado

- **T2/T3:** Redes de producción sensibles
- **T4:** Redes de desarrollo/testing
- **T5:** Solo en redes aisladas de lab

### 5. Verificar Permisos

Asegúrate de tener autorización por escrito antes de escanear cualquier red.

## Troubleshooting

### El escaneo queda en "pending"

1. Verificar que Celery workers estén corriendo:
   ```bash
   docker compose logs celery
   ```

2. Verificar conexión a Redis:
   ```bash
   redis-cli ping
   ```

### El escaneo falla inmediatamente

1. Verificar logs:
   ```bash
   curl -X GET "http://localhost:8000/api/v1/scans/{scan_id}" \
     -H "Authorization: Bearer $TOKEN"
   ```
   
2. Revisar `error_message` en la respuesta.

### Escaneo muy lento

1. Reducir el rango de targets
2. Usar timing T4 o T5
3. Usar `quick` en lugar de `full`

### No encuentra hosts

1. Verificar conectividad de red
2. Verificar que no haya firewalls bloqueando
3. Probar con un host conocido primero

---

## Próximos Pasos

1. [Ver y gestionar vulnerabilidades](managing-vulnerabilities.md)
2. [Generar reportes](generating-reports.md)
3. [Configurar alertas](../deployment/configuration.md)

---

*Última actualización: 30 Enero 2026*
