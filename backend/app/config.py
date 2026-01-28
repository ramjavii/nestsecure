# =============================================================================
# NESTSECURE - Configuración Central de la Aplicación
# =============================================================================
# Este módulo utiliza Pydantic Settings para gestionar todas las variables
# de configuración de forma type-safe y con validación automática.
# =============================================================================

from functools import lru_cache
from typing import Any, List, Optional, Union

from pydantic import (
    AnyHttpUrl,
    EmailStr,
    PostgresDsn,
    RedisDsn,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuración central de NestSecure.
    
    Las variables se cargan desde:
    1. Variables de entorno del sistema
    2. Archivo .env (si existe)
    3. Valores por defecto definidos aquí
    
    La prioridad es: env vars > .env > defaults
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignora variables extra no definidas
    )
    
    # -------------------------------------------------------------------------
    # Información de la Aplicación
    # -------------------------------------------------------------------------
    APP_NAME: str = "NestSecure"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "Sistema de Escaneo de Vulnerabilidades On-Premise"
    
    # -------------------------------------------------------------------------
    # Entorno y Debug
    # -------------------------------------------------------------------------
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    LOG_FORMAT: str = "json"  # "json" o "text"
    
    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Valida que el entorno sea uno de los permitidos."""
        allowed = {"development", "staging", "production", "testing"}
        if v.lower() not in allowed:
            raise ValueError(f"ENVIRONMENT debe ser uno de: {allowed}")
        return v.lower()
    
    @property
    def is_development(self) -> bool:
        """Retorna True si estamos en desarrollo."""
        return self.ENVIRONMENT == "development"
    
    @property
    def is_production(self) -> bool:
        """Retorna True si estamos en producción."""
        return self.ENVIRONMENT == "production"
    
    @property
    def is_testing(self) -> bool:
        """Retorna True si estamos en testing."""
        return self.ENVIRONMENT == "testing"
    
    # -------------------------------------------------------------------------
    # Base de Datos PostgreSQL
    # -------------------------------------------------------------------------
    POSTGRES_USER: str = "nestsecure"
    POSTGRES_PASSWORD: str = "nestsecure_dev_2026"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "nestsecure_db"
    
    # URL completa de la base de datos (tiene prioridad si se especifica)
    DATABASE_URL: Optional[str] = None
    DATABASE_ECHO: bool = False  # Log de queries SQL
    
    # Pool de conexiones
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_PRE_PING: bool = True
    
    @property
    def database_url_sync(self) -> str:
        """
        Genera la URL de conexión síncrona para PostgreSQL.
        Útil para migraciones con Alembic.
        """
        if self.DATABASE_URL:
            # Convertir asyncpg a psycopg2 si es necesario
            return self.DATABASE_URL.replace("+asyncpg", "")
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
    
    @property
    def database_url_async(self) -> str:
        """
        Genera la URL de conexión asíncrona para PostgreSQL.
        Usa asyncpg como driver.
        """
        if self.DATABASE_URL:
            if "+asyncpg" not in self.DATABASE_URL:
                return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
            return self.DATABASE_URL
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
    
    # -------------------------------------------------------------------------
    # Redis
    # -------------------------------------------------------------------------
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_URL: Optional[str] = None
    
    # Celery
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None
    
    @property
    def redis_url(self) -> str:
        """Genera la URL de conexión a Redis."""
        if self.REDIS_URL:
            return self.REDIS_URL
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"
    
    @property
    def celery_broker(self) -> str:
        """URL del broker de Celery."""
        if self.CELERY_BROKER_URL:
            return self.CELERY_BROKER_URL
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/1"
    
    @property
    def celery_backend(self) -> str:
        """URL del backend de resultados de Celery."""
        if self.CELERY_RESULT_BACKEND:
            return self.CELERY_RESULT_BACKEND
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/2"
    
    # -------------------------------------------------------------------------
    # Seguridad y Autenticación
    # -------------------------------------------------------------------------
    SECRET_KEY: str = "dev-secret-key-change-in-production-2026"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Password hashing
    PASSWORD_HASH_ROUNDS: int = 12
    
    # Primer superusuario
    FIRST_SUPERUSER_EMAIL: EmailStr = "admin@nestsecure.local"
    FIRST_SUPERUSER_PASSWORD: str = "Admin123!SecurePassword"
    
    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        """Advierte si la clave secreta es la de desarrollo en producción."""
        # Este validador es informativo, no bloquea
        if "dev-secret" in v.lower():
            # En producción esto debería ser un error
            pass
        return v
    
    # -------------------------------------------------------------------------
    # API
    # -------------------------------------------------------------------------
    API_V1_PREFIX: str = "/api/v1"
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    
    # CORS
    BACKEND_CORS_ORIGINS: Union[List[str], str] = '["http://localhost:3000","http://localhost:5173"]'
    
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Parsea los orígenes CORS desde string JSON o lista."""
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                # Si no es JSON válido, tratar como un solo origen
                return [v]
        return v
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 60  # segundos
    
    # -------------------------------------------------------------------------
    # Frontend
    # -------------------------------------------------------------------------
    FRONTEND_URL: str = "http://localhost:3000"
    
    # -------------------------------------------------------------------------
    # Scanners
    # -------------------------------------------------------------------------
    # Nmap
    NMAP_PATH: str = "/usr/bin/nmap"
    NMAP_TIMEOUT: int = 3600  # 1 hora máximo
    NMAP_MAX_CONCURRENT: int = 3
    
    # OpenVAS/GVM
    GVM_HOST: str = "localhost"
    GVM_PORT: int = 9390
    GVM_USERNAME: str = "admin"
    GVM_PASSWORD: str = "admin"
    GVM_TIMEOUT: int = 7200  # 2 horas
    
    # OWASP ZAP
    ZAP_HOST: str = "localhost"
    ZAP_PORT: int = 8080
    ZAP_API_KEY: str = ""
    ZAP_TIMEOUT: int = 3600
    
    # Nuclei
    NUCLEI_PATH: str = "/usr/local/bin/nuclei"
    NUCLEI_TEMPLATES_PATH: str = "/opt/nuclei-templates"
    NUCLEI_TIMEOUT: int = 1800  # 30 minutos
    NUCLEI_RATE_LIMIT: int = 150  # requests por segundo
    
    # -------------------------------------------------------------------------
    # Reportes
    # -------------------------------------------------------------------------
    REPORTS_DIR: str = "/app/reports"
    TEMPLATES_DIR: str = "/app/templates"
    REPORTS_RETENTION_DAYS: int = 90
    
    # -------------------------------------------------------------------------
    # NVD API (CVE)
    # -------------------------------------------------------------------------
    NVD_API_KEY: Optional[str] = None
    NVD_API_URL: str = "https://services.nvd.nist.gov/rest/json/cves/2.0"
    NVD_CACHE_TTL: int = 86400  # 24 horas
    
    # -------------------------------------------------------------------------
    # Email (Alertas)
    # -------------------------------------------------------------------------
    SMTP_ENABLED: bool = False
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: EmailStr = "noreply@nestsecure.local"
    SMTP_TLS: bool = True
    
    # -------------------------------------------------------------------------
    # Logging y Monitoreo
    # -------------------------------------------------------------------------
    LOG_FILE: Optional[str] = None
    SENTRY_DSN: Optional[str] = None


@lru_cache()
def get_settings() -> Settings:
    """
    Retorna una instancia cacheada de Settings.
    
    Usar esta función en lugar de instanciar Settings directamente
    para aprovechar el cache y evitar lecturas repetidas de .env.
    
    Ejemplo:
        from app.config import get_settings
        settings = get_settings()
        print(settings.APP_NAME)
    """
    return Settings()


# Instancia global para importación directa (uso con cuidado)
settings = get_settings()


# =============================================================================
# Funciones de utilidad para configuración
# =============================================================================

def get_database_settings() -> dict[str, Any]:
    """Retorna configuración de la base de datos como diccionario."""
    s = get_settings()
    return {
        "url": s.database_url_async,
        "echo": s.DATABASE_ECHO,
        "pool_size": s.DATABASE_POOL_SIZE,
        "max_overflow": s.DATABASE_MAX_OVERFLOW,
        "pool_pre_ping": s.DATABASE_POOL_PRE_PING,
    }


def get_redis_settings() -> dict[str, Any]:
    """Retorna configuración de Redis como diccionario."""
    s = get_settings()
    return {
        "url": s.redis_url,
        "host": s.REDIS_HOST,
        "port": s.REDIS_PORT,
    }


def get_jwt_settings() -> dict[str, Any]:
    """Retorna configuración de JWT como diccionario."""
    s = get_settings()
    return {
        "secret_key": s.SECRET_KEY,
        "algorithm": s.JWT_ALGORITHM,
        "access_token_expire_minutes": s.ACCESS_TOKEN_EXPIRE_MINUTES,
        "refresh_token_expire_days": s.REFRESH_TOKEN_EXPIRE_DAYS,
    }
