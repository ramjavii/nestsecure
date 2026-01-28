# 🔒 NESTSECURE - Sistema de Escaneo de Vulnerabilidades

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
docker-compose up -d

# 4. Ejecutar migraciones
docker-compose exec api alembic upgrade head

# 5. Crear usuario admin
docker-compose exec api python -m app.scripts.create_admin
```

Accede a: `https://localhost` (o IP de tu NUC)

## 📖 Documentación

- [Arquitectura del Sistema](DOCS/architecture/system-design.md)
- [Guía de Instalación](DOCS/deployment/installation.md)
- [API Documentation](http://localhost:8000/docs) (Swagger automático)
- [Guía de Usuario](DOCS/user-guide/getting-started.md)
- [Contexto Completo](CONTEXTO_RESUMEN.md)

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
# Backend
cd backend
pytest

# Frontend
cd frontend
npm test
```

## 📊 Roadmap

- [x] Fase 1: Backend core + Autenticación
- [x] Fase 2: Motor de escaneo (Nmap, OpenVAS)
- [x] Fase 3: Frontend Dashboard
- [x] Fase 4: Reportes y Alertas
- [ ] Fase 5: Integración ZAP y Nuclei
- [ ] Fase 6: Compliance templates (PCI-DSS, ISO 27001)
- [ ] Fase 7: API pública para integraciones
- [ ] Fase 8: Agent-based scanning

## 🤝 Contribución

Este es un proyecto privado. Para contribuir:

1. Crear un branch: `git checkout -b feature/nueva-funcionalidad`
2. Commit cambios: `git commit -am 'Add: nueva funcionalidad'`
3. Push al branch: `git push origin feature/nueva-funcionalidad`
4. Crear Pull Request

## 📝 Licencia

Propietario - Todos los derechos reservados © 2025

## 👥 Equipo

Desarrollado por el equipo de NESTSECURE

## 📞 Soporte

Para soporte, contactar a: security@nestsecure.io

---

**Nota:** Este sistema debe ser usado únicamente con autorización explícita para escanear las redes objetivo. El uso no autorizado puede ser ilegal.
