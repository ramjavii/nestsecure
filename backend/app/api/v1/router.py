# =============================================================================
# NESTSECURE - Router Agregador API v1
# =============================================================================
"""
Router principal que agrega todos los endpoints de la API v1.

Incluye:
- /auth: Autenticación y tokens JWT
- /users: Gestión de usuarios
- /organizations: Gestión de organizaciones
- /assets: Gestión de assets
- /services: Gestión de servicios
- /dashboard: Estadísticas y resúmenes
- /cve: Caché de CVEs
- /scans: Gestión de escaneos OpenVAS
- /nuclei: Escaneos de vulnerabilidades con Nuclei
"""

from fastapi import APIRouter

from app.api.v1.assets import router as assets_router
from app.api.v1.auth import router as auth_router
from app.api.v1.cve import router as cve_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.network import router as network_router
from app.api.v1.nuclei import router as nuclei_router
from app.api.v1.organizations import router as organizations_router
from app.api.v1.scans import router as scans_router
from app.api.v1.services import router as services_router
from app.api.v1.users import router as users_router
from app.api.v1.vulnerabilities import router as vulnerabilities_router

# Router principal de la API v1
api_router = APIRouter()

# Incluir subrouters
api_router.include_router(
    auth_router,
    prefix="/auth",
    tags=["Autenticación"],
)

api_router.include_router(
    users_router,
    prefix="/users",
    tags=["Usuarios"],
)

api_router.include_router(
    organizations_router,
    prefix="/organizations",
    tags=["Organizaciones"],
)

api_router.include_router(
    assets_router,
    prefix="/assets",
    tags=["Assets"],
)

api_router.include_router(
    services_router,
    prefix="/services",
    tags=["Servicios"],
)

api_router.include_router(
    dashboard_router,
    prefix="/dashboard",
    tags=["Dashboard"],
)

api_router.include_router(
    cve_router,
    prefix="/cve",
    tags=["CVE"],
)

api_router.include_router(
    scans_router,
    prefix="/scans",
    tags=["Scans"],
)

api_router.include_router(
    nuclei_router,
    prefix="/nuclei",
    tags=["Nuclei"],
)

api_router.include_router(
    network_router,
    prefix="/network",
    tags=["Network"],
)

api_router.include_router(
    vulnerabilities_router,
    prefix="/vulnerabilities",
    tags=["Vulnerabilities"],
)

# Health check para la API (útil para load balancers)
@api_router.get(
    "/health",
    tags=["Health"],
    summary="Health check de la API",
)
async def api_health() -> dict:
    """Verifica que la API está funcionando correctamente."""
    return {"status": "healthy", "api_version": "v1"}
