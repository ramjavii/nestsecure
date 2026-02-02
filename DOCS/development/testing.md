# Testing Guide - NESTSECURE

## Overview

NESTSECURE utiliza pytest como framework principal de testing con soporte para:
- Tests unitarios
- Tests de integración
- Tests de base de datos
- Fixtures compartidos
- Coverage reporting

## Estructura de Tests

```
backend/app/tests/
├── __init__.py
├── conftest.py                    # Fixtures globales
├── test_config.py                 # Tests de configuración (24 tests)
├── test_api/
│   ├── __init__.py
│   └── test_health.py            # Tests de health endpoints (14 tests)
├── test_database/
│   ├── __init__.py
│   ├── conftest.py               # Fixtures de DB
│   ├── test_models.py            # Tests de modelos ORM (14 tests)
│   └── test_schemas.py           # Tests de schemas Pydantic (30 tests)
├── test_services/
│   └── test_scan_service.py      # Tests de servicios (scans)
└── test_workers/
    └── test_nmap_worker.py       # Tests de workers (nmap)
```

## Ejecutar Tests

### Todos los Tests

```bash
cd backend
source venv/bin/activate

# Ejecutar todos los tests
pytest

# Con verbose
pytest -v

# Con output de print statements
pytest -s

# Parallel execution (más rápido)
pytest -n auto
```

### Tests Específicos

```bash
# Por módulo
pytest app/tests/test_config.py
pytest app/tests/test_api/test_health.py
pytest app/tests/test_database/

# Por clase
pytest app/tests/test_config.py::TestSettings

# Por test específico
pytest app/tests/test_config.py::TestSettings::test_default_values

# Por marker
pytest -m "not slow"

# Por keyword
pytest -k "organization"
```

### Coverage

```bash
# Ejecutar con coverage
pytest --cov=app

# Con reporte HTML
pytest --cov=app --cov-report=html

# Ver reporte HTML
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux

# Con missing lines
pytest --cov=app --cov-report=term-missing

# Solo un módulo
pytest --cov=app.models --cov-report=html
```

## Configuración (pytest.ini)

```ini
[pytest]
testpaths = app/tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Markers
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow tests
    database: Database tests

# Opciones por defecto
addopts = 
    -v
    --strict-markers
    --disable-warnings
    --tb=short

# Variables de entorno para tests
env =
    ENVIRONMENT=testing
    DATABASE_URL=sqlite+aiosqlite:///:memory:
    SECRET_KEY=test-secret-key-for-testing-only
    REDIS_HOST=localhost
```

## Fixtures

### Fixtures Globales (conftest.py)

```python
@pytest.fixture
def settings() -> Settings:
    """Settings con valores de testing."""
    return get_settings()

@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Cliente HTTP asíncrono para tests de API."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
def response_validator():
    """Helper para validar respuestas HTTP."""
    return ResponseValidator()
```

### Fixtures de Base de Datos (test_database/conftest.py)

```python
@pytest.fixture
async def test_db_engine():
    """Engine SQLite in-memory con StaticPool."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False}
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    await engine.dispose()

@pytest.fixture
async def db_session(test_db_engine):
    """Session de DB para cada test con rollback."""
    session_maker = async_sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with session_maker() as session:
        yield session
        await session.rollback()
```

## Test Categories

### 1. Tests de Configuración (test_config.py)

**24 tests** que validan:
- Valores por defecto
- Variables de entorno
- Validación de tipos
- URLs de base de datos
- Configuración de Redis
- Settings de JWT
- Configuración de CORS

```bash
pytest app/tests/test_config.py -v
```

### 2. Tests de Health Endpoints (test_api/test_health.py)

**14 tests** que validan:
- GET `/health` - Health check básico
- GET `/health/ready` - Readiness con checks de servicios
- GET `/health/live` - Liveness para Kubernetes

```bash
pytest app/tests/test_api/test_health.py -v
```

### 3. Tests de Modelos ORM (test_database/test_models.py)

**14 tests** que validan:

#### Organization Model (4 tests)
- Creación básica
- Valores por defecto
- Timestamps automáticos
- Constraint de slug único

#### User Model (4 tests)
- Creación con organización
- Relación con Organization
- Valores por defecto
- Cascade delete

#### Asset Model (3 tests)
- Creación con organización
- Relación con Organization
- Valores por defecto (risk_score=0.0)

#### Service Model (3 tests)
- Creación con asset
- Relación con Asset
- Valores por defecto (confidence=50)

```bash
pytest app/tests/test_database/test_models.py -v
```

### 4. Tests de Schemas Pydantic (test_database/test_schemas.py)

**30 tests** que validan:

#### Organization Schemas (7 tests)
- Creación válida
- Slug convertido a lowercase
- Slug con pattern válido
- max_assets debe ser positivo
- Update parcial
- Validación de campos requeridos

#### User Schemas (8 tests)
- Creación válida
- Email válido
- Password fuerte (8+ chars, mayúscula, minúscula, número)
- Role válido (owner/admin/analyst/viewer)
- Update de password
- Hash de password

#### Asset Schemas (8 tests)
- Creación válida
- IPv4 válida
- IPv6 válida
- IP inválida rechazada
- MAC address válida
- MAC address inválida rechazada
- Tags normalizadas (lowercase)
- asset_type y criticality válidos

#### Service Schemas (5 tests)
- Creación válida
- Port límites (1-65535)
- Port inválido rechazado
- Protocol convertido a lowercase
- Protocol válido (tcp/udp)

#### Common Schemas (2 tests)
- PaginationParams defaults y offset calculation
- PaginatedResponse creation

```bash
pytest app/tests/test_database/test_schemas.py -v
```

## Test Patterns

### Testing Models

```python
@pytest.mark.asyncio
async def test_organization_creation(db_session: AsyncSession):
    """
    DADO: Datos válidos de organización
    CUANDO: Se crea una Organization
    ENTONCES: Se guarda correctamente en la DB
    """
    org = Organization(
        name="Test Org",
        slug="test-org",
        max_assets=100
    )
    
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    
    assert org.id is not None
    assert org.name == "Test Org"
    assert org.is_active is True  # Default
```

### Testing Schemas

```python
def test_organization_create_valid():
    """
    DADO: Datos válidos de organización
    CUANDO: Se valida con OrganizationCreate
    ENTONCES: Los datos son aceptados
    """
    data = {
        "name": "Test Organization",
        "slug": "test-org",
        "max_assets": 100
    }
    
    schema = OrganizationCreate(**data)
    
    assert schema.name == "Test Organization"
    assert schema.slug == "test-org"
    assert schema.max_assets == 100
```

### Testing Endpoints

```python
@pytest.mark.asyncio
async def test_health_endpoint(async_client: AsyncClient):
    """
    DADO: API en ejecución
    CUANDO: GET /health
    ENTONCES: Responde con status healthy
    """
    response = await async_client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
```

### Testing Database Relationships

```python
@pytest.mark.asyncio
async def test_organization_users_relationship(db_session: AsyncSession):
    """
    DADO: Una organización con usuarios
    CUANDO: Se accede a org.users
    ENTONCES: Retorna la lista de usuarios
    """
    org = Organization(name="Test", slug="test", max_assets=10)
    db_session.add(org)
    await db_session.flush()
    
    user = User(
        email="test@example.com",
        hashed_password="hashed",
        full_name="Test User",
        role="admin",
        organization_id=org.id
    )
    db_session.add(user)
    await db_session.commit()
    
    await db_session.refresh(org)
    assert len(org.users) == 1
    assert org.users[0].email == "test@example.com"
```

## Best Practices

### 1. Naming Convention

```python
# Tests descriptivos con Given-When-Then
def test_organization_slug_must_be_lowercase():
    """
    DADO: Slug con mayúsculas
    CUANDO: Se valida con OrganizationCreate
    ENTONCES: Se convierte a lowercase automáticamente
    """
    pass
```

### 2. Fixtures Over Setup/Teardown

```python
# ✅ Bueno: Usar fixtures
@pytest.fixture
async def organization(db_session):
    org = Organization(name="Test", slug="test", max_assets=10)
    db_session.add(org)
    await db_session.commit()
    return org

async def test_with_org(organization):
    assert organization.name == "Test"

# ❌ Evitar: Setup/teardown manual
async def test_with_manual_setup():
    # Setup manual
    org = Organization(...)
    # ... test logic
    # Teardown manual
```

### 3. Async Tests

```python
# Usar @pytest.mark.asyncio para tests async
@pytest.mark.asyncio
async def test_async_operation():
    result = await some_async_function()
    assert result is not None
```

### 4. Parametrize para Casos Múltiples

```python
@pytest.mark.parametrize("ip_address,is_valid", [
    ("192.168.1.1", True),
    ("2001:db8::1", True),
    ("invalid", False),
    ("999.999.999.999", False),
])
def test_ip_validation(ip_address, is_valid):
    if is_valid:
        schema = AssetCreate(
            organization_id=uuid4(),
            ip_address=ip_address,
            asset_type="server",
            criticality="high"
        )
        assert schema.ip_address == ip_address
    else:
        with pytest.raises(ValidationError):
            AssetCreate(
                organization_id=uuid4(),
                ip_address=ip_address,
                asset_type="server",
                criticality="high"
            )
```

### 5. Markers para Categorización

```python
@pytest.mark.unit
def test_password_hashing():
    """Test unitario rápido."""
    pass

@pytest.mark.integration
@pytest.mark.slow
async def test_full_workflow():
    """Test de integración que puede tardar."""
    pass

@pytest.mark.database
async def test_complex_query():
    """Test que requiere DB real."""
    pass
```

## CI/CD Integration

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.13'
    
    - name: Install dependencies
      run: |
        cd backend
        pip install -r requirements-dev.txt
    
    - name: Run tests with coverage
      run: |
        cd backend
        pytest --cov=app --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./backend/coverage.xml
```

## Current Test Summary

| Category | Tests | Status |
|----------|-------|--------|
| Configuration | 24 | ✅ Passing |
| Health Endpoints | 14 | ✅ Passing |
| Database Models | 14 | ✅ Passing |
| Pydantic Schemas | 30 | ✅ Passing |
| **Total** | **82** | **✅ All Passing** |

## Coverage Goals

| Module | Current | Target |
|--------|---------|--------|
| app/config.py | ~95% | 95% |
| app/models/ | ~90% | 90% |
| app/schemas/ | ~95% | 95% |
| app/db/ | ~80% | 85% |
| app/core/ | ~75% | 85% |
| **Overall** | **~85%** | **>90%** |

## Troubleshooting

### Tests Failing with DB Connection Error

```bash
# Asegurarse de que PostgreSQL está corriendo
docker-compose -f docker-compose.dev.yml up -d postgres

# O usar SQLite para tests rápidos (ya configurado)
pytest  # Usa SQLite in-memory por defecto
```

### Import Errors

```bash
# Asegurarse de que el PYTHONPATH incluye backend/
export PYTHONPATH="${PYTHONPATH}:/path/to/backend"

# O ejecutar desde el directorio correcto
cd backend && pytest
```

### Slow Tests

```bash
# Skip tests lentos
pytest -m "not slow"

# Ejecutar en paralelo
pytest -n auto

# Solo fast tests
pytest -m "unit"
```

---

*Última actualización: 29 de enero de 2026*
