# 🔒 NESTSECURE - Sistema de Escaneo de Vulnerabilidades

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-blue.svg)](https://reactjs.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://docker.com)
[![Tests](https://img.shields.io/badge/Tests-Pytest-yellow.svg)](https://pytest.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

Sistema completo de escaneo de vulnerabilidades on-premise para despliegue en Intel NUC. Detecta vulnerabilidades en redes corporativas usando múltiples engines de escaneo (Nmap, OpenVAS, OWASP ZAP, Nuclei) con correlación automática de CVEs y generación de reportes.

## 🎯 Características Principales

- ✅ **Escaneo Multi-Engine:** Nmap, OpenVAS, OWASP ZAP, Nuclei
- ✅ **Correlación CVE Automática:** Integración con NVD API
- ✅ **Dashboard Interactivo:** React + TypeScript con visualizaciones
- ✅ **Reportes Automáticos:** PDF, HTML, Excel con branding personalizable
- ✅ **Sistema de Alertas:** Email, Slack, Webhooks
- ✅ **100% On-Premise:** Data never leaves your network
- ✅ **Deployment Rápido:** Docker Compose, listo en <30 minutos

## 🛠️ Stack Tecnológico

**Backend:**
- Python 3.11+ con FastAPI
- PostgreSQL 15 + TimescaleDB
- Celery + Redis (task queue)
- SQLAlchemy (ORM)

**Frontend:**
- React 18 + TypeScript
- Tailwind CSS + shadcn/ui
- TanStack Query
- Recharts (visualizaciones)

**DevOps:**
- Docker + Docker Compose
- Nginx (reverse proxy)
- GitHub Actions (CI/CD)

## 📁 Estructura del Proyecto

```
nestsecure/
├── backend/         # API REST con FastAPI
├── frontend/        # Aplicación React
├── docker/          # Configuraciones Docker
├── docs/            # Documentación
├── scripts/         # Scripts de utilidad
└── docker-compose.yml
```

## 🚀 Quick Start

### Requisitos
- Docker 24.0+
- Docker Compose 2.23+
- Intel NUC (mínimo i5, 16GB RAM) o servidor Linux

### Instalación

```bash
# 1. Clonar el repositorio
git clone https://github.com/tu-usuario/nestsecure.git
cd nestsecure

# 2. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus configuraciones

# 3. Iniciar servicios
make docker-up

# 4. Ejecutar migraciones (ya incluidas en docker-up)
# Se ejecutan automáticamente al iniciar

# 5. Crear usuario demo
docker exec nestsecure_backend_dev python3 /app/scripts/create_demo.py
# Credenciales: demo@nestsecure.com / Demo123!

# 6. Probar autenticación
./backend/scripts/test_auth_manual.sh
```

Accede a:
- API: `http://localhost:8000`
- Docs: `http://localhost:8000/docs`
- Frontend: `https://localhost` (próximamente)

## 📖 Documentación

### Desarrollo
- [Progreso Diario](DOCS/DESARROLLO/README.md)
- [Día 3: JWT Auth + CRUD](DOCS/DESARROLLO/DIA_03_API_AUTH.md)
- [Guía de Pruebas Auth](DOCS/GUIA_PRUEBAS_AUTH.md)

### Técnica
- [Arquitectura del Sistema](DOCS/architecture/system-design.md)
- [API Documentation](http://localhost:8000/docs) (Swagger automático)
- [Guía de Instalación](DOCS/deployment/installation.md)
- [Testing Guide](DOCS/development/testing.md)

## 🔄 Desarrollo

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## 🧪 Testing

```bash
# Backend - Todos los tests (132)
cd backend
pytest -v

# Backend - Tests específicos
pytest tests/test_auth/ -v
pytest tests/test_api/ -v

# Testing manual de API
./backend/scripts/test_auth_manual.sh

# Frontend (próximamente)
cd frontend
npm test
```

## 📊 Roadmap

- [x] **Fase 1: Backend core + Autenticación** ✅
  - [x] FastAPI con Docker
  - [x] PostgreSQL + SQLAlchemy async
  - [x] JWT authentication
  - [x] Users & Organizations CRUD
  - [x] 132 tests pasando
- [ ] **Fase 2: Motor de escaneo (Nmap, OpenVAS)**
  - [ ] Assets CRUD
  - [ ] Integración Nmap
  - [ ] Celery tasks
  - [ ] CVE correlation
- [ ] **Fase 3: Frontend Dashboard**
- [ ] **Fase 4: Reportes y Alertas**
- [ ] Fase 5: Integración ZAP y Nuclei
- [ ] Fase 6: Compliance templates (PCI-DSS, ISO 27001)
- [ ] Fase 7: API pública para integraciones
- [ ] Fase 8: Agent-based scanning

## 🤝 Contribución

¡Las contribuciones son bienvenidas! Este es un proyecto open source y cualquier ayuda es apreciada.

### Cómo Contribuir

1. **Fork** el proyecto
2. Crea tu **Feature Branch** (`git checkout -b feature/AmazingFeature`)
3. **Commit** tus cambios (`git commit -m 'feat: Add some AmazingFeature'`)
4. **Push** al Branch (`git push origin feature/AmazingFeature`)
5. Abre un **Pull Request**

Lee nuestra [Guía de Contribución](CONTRIBUTING.md) para más detalles.

### Reportar Bugs

Si encuentras un bug, por favor abre un [Issue](https://github.com/ramjavii/nestsecure/issues) con:
- Descripción clara del problema
- Pasos para reproducirlo
- Comportamiento esperado vs actual
- Tu entorno (OS, Python version, Docker version)

## 📝 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para más detalles.

## 👥 Autor

**Fabián Ramos** - [@ramjavii](https://github.com/ramjavii)

## 🙏 Agradecimientos

- A todos los [contribuidores](https://github.com/ramjavii/nestsecure/contributors) que ayudan a mejorar este proyecto
- Comunidad open source de herramientas de seguridad

---

**Nota:** Este sistema debe ser usado únicamente con autorización explícita para escanear las redes objetivo. El uso no autorizado puede ser ilegal.
