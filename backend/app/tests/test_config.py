# =============================================================================
# NESTSECURE - Tests de Configuración
# =============================================================================
"""
Tests para el módulo de configuración (config.py).

Cobertura:
- Carga de configuración desde Settings
- Validación de valores
- Propiedades computadas
- Funciones de utilidad
"""

import os
import pytest
from unittest.mock import patch

from app.config import Settings, get_settings, get_database_settings, get_redis_settings


# =============================================================================
# Tests de Settings básicos
# =============================================================================
class TestSettingsBasic:
    """Tests básicos de Settings."""
    
    def test_settings_loads_defaults(self):
        """
        DADO: No hay variables de entorno configuradas
        CUANDO: Se instancia Settings
        ENTONCES: Usa valores por defecto
        """
        settings = Settings()
        
        assert settings.APP_NAME == "NestSecure"
        assert settings.APP_VERSION == "1.0.0"
        assert settings.ENVIRONMENT == "development"
    
    def test_settings_app_version_format(self):
        """
        DADO: Settings con versión
        CUANDO: Se accede a APP_VERSION
        ENTONCES: Tiene formato semver
        """
        settings = Settings()
        
        # Formato: X.Y.Z
        parts = settings.APP_VERSION.split(".")
        assert len(parts) == 3
        assert all(part.isdigit() for part in parts)
    
    def test_settings_debug_default_true_in_development(self):
        """
        DADO: Settings en desarrollo
        CUANDO: Se accede a DEBUG
        ENTONCES: Es True por defecto
        """
        settings = Settings(ENVIRONMENT="development")
        
        assert settings.DEBUG is True


# =============================================================================
# Tests de validación de ENVIRONMENT
# =============================================================================
class TestEnvironmentValidation:
    """Tests para validación del entorno."""
    
    def test_valid_environments(self):
        """
        DADO: Entornos válidos
        CUANDO: Se crea Settings con cada uno
        ENTONCES: No lanza error
        """
        valid_envs = ["development", "staging", "production", "testing"]
        
        for env in valid_envs:
            settings = Settings(ENVIRONMENT=env)
            assert settings.ENVIRONMENT == env
    
    def test_invalid_environment_raises_error(self):
        """
        DADO: Un entorno inválido
        CUANDO: Se crea Settings
        ENTONCES: Lanza ValueError
        """
        with pytest.raises(ValueError):
            Settings(ENVIRONMENT="invalid_env")
    
    def test_environment_is_lowercased(self):
        """
        DADO: Entorno en mayúsculas
        CUANDO: Se crea Settings
        ENTONCES: Se convierte a minúsculas
        """
        settings = Settings(ENVIRONMENT="DEVELOPMENT")
        
        assert settings.ENVIRONMENT == "development"


# =============================================================================
# Tests de propiedades de entorno
# =============================================================================
class TestEnvironmentProperties:
    """Tests para propiedades is_development, is_production, etc."""
    
    def test_is_development_true_in_dev(self):
        """
        DADO: ENVIRONMENT="development"
        CUANDO: Se accede a is_development
        ENTONCES: Retorna True
        """
        settings = Settings(ENVIRONMENT="development")
        
        assert settings.is_development is True
        assert settings.is_production is False
        assert settings.is_testing is False
    
    def test_is_production_true_in_prod(self):
        """
        DADO: ENVIRONMENT="production"
        CUANDO: Se accede a is_production
        ENTONCES: Retorna True
        """
        settings = Settings(ENVIRONMENT="production")
        
        assert settings.is_production is True
        assert settings.is_development is False
    
    def test_is_testing_true_in_test(self):
        """
        DADO: ENVIRONMENT="testing"
        CUANDO: Se accede a is_testing
        ENTONCES: Retorna True
        """
        settings = Settings(ENVIRONMENT="testing")
        
        assert settings.is_testing is True


# =============================================================================
# Tests de URLs de base de datos
# =============================================================================
class TestDatabaseURLs:
    """Tests para generación de URLs de base de datos."""
    
    def test_database_url_async_default(self):
        """
        DADO: Settings con valores por defecto de PostgreSQL
        CUANDO: Se accede a database_url_async
        ENTONCES: Genera URL con asyncpg driver
        """
        settings = Settings()
        url = settings.database_url_async
        
        assert "postgresql+asyncpg://" in url
        assert settings.POSTGRES_USER in url
        assert settings.POSTGRES_DB in url
    
    def test_database_url_sync_default(self):
        """
        DADO: Settings con valores por defecto
        CUANDO: Se accede a database_url_sync
        ENTONCES: Genera URL sin driver async
        """
        settings = Settings()
        url = settings.database_url_sync
        
        assert "postgresql://" in url
        assert "+asyncpg" not in url
    
    def test_database_url_respects_env_var(self):
        """
        DADO: DATABASE_URL especificada explícitamente
        CUANDO: Se accede a database_url_async
        ENTONCES: Usa el valor especificado
        """
        custom_url = "postgresql+asyncpg://custom:pass@db:5432/custom_db"
        settings = Settings(DATABASE_URL=custom_url)
        
        assert settings.database_url_async == custom_url


# =============================================================================
# Tests de Redis URLs
# =============================================================================
class TestRedisURLs:
    """Tests para generación de URLs de Redis."""
    
    def test_redis_url_default(self):
        """
        DADO: Settings con valores por defecto de Redis
        CUANDO: Se accede a redis_url
        ENTONCES: Genera URL correcta
        """
        settings = Settings()
        url = settings.redis_url
        
        assert url.startswith("redis://")
        assert str(settings.REDIS_PORT) in url
    
    def test_celery_broker_url_default(self):
        """
        DADO: Settings con valores por defecto
        CUANDO: Se accede a celery_broker
        ENTONCES: Usa Redis DB 1
        """
        settings = Settings()
        url = settings.celery_broker
        
        assert url.endswith("/1")  # DB 1 para broker
    
    def test_celery_backend_url_default(self):
        """
        DADO: Settings con valores por defecto
        CUANDO: Se accede a celery_backend
        ENTONCES: Usa Redis DB 2
        """
        settings = Settings()
        url = settings.celery_backend
        
        assert url.endswith("/2")  # DB 2 para backend


# =============================================================================
# Tests de CORS parsing
# =============================================================================
class TestCORSParsing:
    """Tests para parsing de CORS origins."""
    
    def test_cors_parses_json_array(self):
        """
        DADO: CORS origins como JSON array string
        CUANDO: Se parsea
        ENTONCES: Se convierte a lista Python
        """
        settings = Settings(
            BACKEND_CORS_ORIGINS='["http://localhost:3000","http://localhost:5173"]'
        )
        
        origins = settings.BACKEND_CORS_ORIGINS
        assert isinstance(origins, list)
        assert "http://localhost:3000" in origins
        assert "http://localhost:5173" in origins
    
    def test_cors_accepts_list_directly(self):
        """
        DADO: CORS origins como lista
        CUANDO: Se accede
        ENTONCES: Se mantiene como lista
        """
        settings = Settings(
            BACKEND_CORS_ORIGINS=["http://example.com"]
        )
        
        assert settings.BACKEND_CORS_ORIGINS == ["http://example.com"]


# =============================================================================
# Tests de funciones de utilidad
# =============================================================================
class TestUtilityFunctions:
    """Tests para funciones helper de configuración."""
    
    def test_get_settings_returns_settings_instance(self):
        """
        DADO: La función get_settings
        CUANDO: Se llama
        ENTONCES: Retorna instancia de Settings
        """
        settings = get_settings()
        
        assert isinstance(settings, Settings)
    
    def test_get_settings_is_cached(self):
        """
        DADO: Múltiples llamadas a get_settings
        CUANDO: Se comparan instancias
        ENTONCES: Son la misma (cached)
        """
        settings1 = get_settings()
        settings2 = get_settings()
        
        assert settings1 is settings2
    
    def test_get_database_settings_returns_dict(self):
        """
        DADO: La función get_database_settings
        CUANDO: Se llama
        ENTONCES: Retorna diccionario con configuración de DB
        """
        db_settings = get_database_settings()
        
        assert isinstance(db_settings, dict)
        assert "url" in db_settings
        assert "echo" in db_settings
        assert "pool_size" in db_settings
    
    def test_get_redis_settings_returns_dict(self):
        """
        DADO: La función get_redis_settings
        CUANDO: Se llama
        ENTONCES: Retorna diccionario con configuración de Redis
        """
        redis_settings = get_redis_settings()
        
        assert isinstance(redis_settings, dict)
        assert "url" in redis_settings
        assert "host" in redis_settings
        assert "port" in redis_settings


# =============================================================================
# Tests de JWT settings
# =============================================================================
class TestJWTSettings:
    """Tests para configuración de JWT."""
    
    def test_jwt_algorithm_default(self):
        """
        DADO: Settings por defecto
        CUANDO: Se accede a JWT_ALGORITHM
        ENTONCES: Es HS256
        """
        settings = Settings()
        
        assert settings.JWT_ALGORITHM == "HS256"
    
    def test_access_token_expire_minutes_default(self):
        """
        DADO: Settings por defecto
        CUANDO: Se accede a ACCESS_TOKEN_EXPIRE_MINUTES
        ENTONCES: Es 30 minutos
        """
        settings = Settings()
        
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30
    
    def test_refresh_token_expire_days_default(self):
        """
        DADO: Settings por defecto
        CUANDO: Se accede a REFRESH_TOKEN_EXPIRE_DAYS
        ENTONCES: Es 7 días
        """
        settings = Settings()
        
        assert settings.REFRESH_TOKEN_EXPIRE_DAYS == 7
