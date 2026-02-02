# =============================================================================
# NESTSECURE - Registro de Archivos Eliminados
# =============================================================================
# 
# Este archivo documenta los archivos que fueron eliminados durante el proceso
# de desarrollo para referencia futura. Algunos de estos archivos contenían
# código que podría ser útil para futuras integraciones.
#
# Fecha: Día 7 (Fase 1 - Refinamiento)
# Razón: Limpieza de código placeholder y consolidación de arquitectura
# =============================================================================

## Scripts de Desarrollo Eliminados

### backend/scripts/
- create_demo_user.py      # Script para crear usuario demo
- create_demo_data.py      # Script para crear datos de demostración
- init_demo.py             # Inicializador de entorno demo
- test_auth.sh             # Script de prueba de autenticación
- test_auth_manual.sh      # Test manual de auth
- test_auth_simple.sh      # Test simplificado de auth


## Modelos Eliminados

### backend/app/models/
- alert_rule.py           # Modelo de reglas de alerta
                          # Contenía: AlertRule, AlertCondition, AlertAction
                          # TODO: Reimplementar en Fase 3 (Alertas)

- audit_log.py            # Log de auditoría
                          # Contenía: AuditLog model
                          # TODO: Reimplementar si se necesita compliance

- report.py               # Modelo de reportes
                          # Contenía: Report, ReportTemplate
                          # TODO: Reimplementar en Fase 4 (Reportes)

- scan_result.py          # Resultados de escaneo (duplicado)
                          # Nota: Consolidado en Vulnerability model


## API Endpoints Eliminados

### backend/app/api/v2/
- Directorio completo     # API v2 experimental
                          # Nota: Se mantuvo solo v1 para simplificar

### backend/app/api/v1/
- scans.py (original)     # Recreado en Día 8 con nueva implementación
- vulnerabilities.py      # TODO: Reimplementar con GVM integration
- alerts.py               # TODO: Reimplementar en Fase 3
- reports.py              # TODO: Reimplementar en Fase 4
- settings.py             # Configuraciones por usuario


## Parsers Eliminados

### backend/app/parsers/
- __init__.py
- nmap_parser.py          # Parser para salida XML de Nmap
                          # Funcionalidad: Parsear host discovery, puertos
                          # TODO: Reimplementar si se agrega Nmap scanner

- nuclei_parser.py        # Parser para salida JSON de Nuclei
                          # Funcionalidad: Vulnerabilidades de templates
                          # TODO: Reimplementar si se agrega Nuclei

- openvas_parser.py       # Parser para OpenVAS
                          # Nota: Reemplazado por GVMParser en Día 8

- zap_parser.py           # Parser para OWASP ZAP
                          # Funcionalidad: Web application scanning
                          # TODO: Reimplementar si se agrega ZAP


## Schemas Eliminados

### backend/app/schemas/
- alert.py                # Schemas de alertas
                          # Contenía: AlertCreate, AlertUpdate, AlertResponse
                          # TODO: Recrear en Fase 3

- report.py               # Schemas de reportes
                          # Contenía: ReportCreate, ReportResponse, ReportFormat
                          # TODO: Recrear en Fase 4


## Services Eliminados

### backend/app/services/
- scanner_service.py      # Orquestador de scanners
                          # Funcionalidad: Dispatch a múltiples scanners
                          # Nota: Reemplazado por GVMClient + Celery workers

- vulnerability_service.py # Servicio de vulnerabilidades
                          # Funcionalidad: CRUD + agregaciones
                          # TODO: Reimplementar con GVM data

- cve_service.py          # Servicio de CVEs
                          # Nota: Movido a cve_cache_service.py

- scan_service.py         # Servicio de scans
                          # Nota: Lógica movida a API endpoints

- notification_service.py # Servicio de notificaciones
                          # Funcionalidad: Email, Slack, Webhook
                          # TODO: Reimplementar en Fase 3

- report_service.py       # Generador de reportes
                          # Funcionalidad: PDF, Excel, CSV
                          # TODO: Reimplementar en Fase 4


## Core Eliminados

### backend/app/core/
- orchestrator.py         # Orquestador de escaneos
                          # Funcionalidad: Scheduling, queue management
                          # Nota: Reemplazado por Celery Beat

- permissions.py          # Sistema de permisos granular
                          # Funcionalidad: RBAC avanzado
                          # Nota: Simplificado a roles básicos

- scheduler.py            # Scheduler de tareas
                          # Nota: Reemplazado por Celery Beat


## Docker Eliminados

### docker/
- backend/Dockerfile      # Dockerfile del backend
                          # Nota: Usando imagen Python base directamente

- frontend/Dockerfile     # Dockerfile del frontend
                          # Nota: Frontend aún no implementado


## Tests Eliminados

### backend/app/tests/
- test_api/test_scans.py (original)          # Recreado con nuevos tests
- test_api/test_vulnerabilities.py           # TODO: Crear nuevos tests
- test_services/test_asset_service.py        # Tests del servicio de assets
- test_services/test_vuln_service.py         # Tests del servicio de vulns
- test_workers/test_openvas_worker.py (orig) # Recreado con GVM integration


## Scripts de Desarrollo Eliminados

### backend/
- benchmark.py            # Script de benchmarking
- seed-db.py              # Seeder de base de datos
- test-scanner.py         # Test de scanners

### scripts/
- generate-certs.sh       # Generador de certificados SSL
- init-db.sh              # Inicializador de base de datos
- install.sh              # Script de instalación


# =============================================================================
# NOTAS PARA FUTURO DESARROLLO
# =============================================================================
#
# 1. NMAP Integration (Día 9+):
#    - Recrear nmap_parser.py basándose en el código original
#    - Crear NmapClient similar a GVMClient
#    - Agregar nmap_worker.py siguiendo patrón de openvas_worker.py
#
# 2. Nuclei Integration (Día 10+):
#    - nuclei_parser.py para JSON output
#    - NucleiClient para template-based scanning
#    - Enfocado en web applications
#
# 3. Alertas (Fase 3):
#    - Recrear alert_rule.py model
#    - notification_service.py para envío
#    - Integrar con webhooks, email, Slack
#
# 4. Reportes (Fase 4):
#    - report.py model con templates
#    - report_service.py para generación
#    - Soportar PDF, Excel, CSV
#
# =============================================================================
