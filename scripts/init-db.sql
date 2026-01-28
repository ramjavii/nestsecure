-- =============================================================================
-- NESTSECURE - Script de Inicialización de Base de Datos
-- =============================================================================
-- Este script se ejecuta automáticamente cuando se crea el contenedor
-- de PostgreSQL por primera vez.
-- =============================================================================

-- Habilitar extensiones necesarias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";        -- Para búsquedas de texto
CREATE EXTENSION IF NOT EXISTS "btree_gin";      -- Índices GIN

-- Habilitar TimescaleDB si está disponible
DO $$
BEGIN
    CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'TimescaleDB no disponible, continuando sin él';
END
$$;

-- Log de inicialización
DO $$
BEGIN
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'NestSecure Database Initialized';
    RAISE NOTICE 'Timestamp: %', NOW();
    RAISE NOTICE '==============================================';
END
$$;
