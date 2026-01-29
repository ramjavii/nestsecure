# =============================================================================
# NESTSECURE - Router Agregador API v1
# =============================================================================
"""
Router principal que agrega todos los endpoints de la API v1.

Incluye:
- /auth: Autenticación y tokens JWT
- /users: Gestión de usuarios
- /organizations: Gestión de organizaciones
"""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.organizations import router as organizations_router
from app.api.v1.users import router as users_router

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

# Health check para la API (útil para load balancers)
@api_router.get(
    "/health",
    tags=["Health"],
    summary="Health check de la API",
)
async def api_health() -> dict:
    """Verifica que la API está funcionando correctamente."""
    return {"status": "healthy", "api_version": "v1"}
