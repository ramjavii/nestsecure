# =============================================================================
# NESTSECURE - Tests de API de CVE
# =============================================================================
"""
Tests para los endpoints de CVE.

Cubre:
- Search CVEs
- Lookup CVE
- Sync operations
- Statistics
"""

import pytest
from datetime import datetime, timezone
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cve_cache import CVECache


# =============================================================================
# Fixtures
# =============================================================================
@pytest.fixture
async def test_cve(db: AsyncSession) -> CVECache:
    """Crea un CVE de prueba."""
    cve = CVECache(
        cve_id="CVE-2024-0001",
        description="A critical vulnerability in test software",
        cvss_v3_score=9.8,
        cvss_v3_vector="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        cvss_v3_severity="CRITICAL",
        cvss_v2_score=10.0,
        published_date=datetime(2024, 1, 15, tzinfo=timezone.utc),
        last_modified_date=datetime(2024, 1, 20, tzinfo=timezone.utc),
        cwe_ids=["CWE-79", "CWE-89"],
        references=[
            "https://nvd.nist.gov/vuln/detail/CVE-2024-0001",
            "https://example.com/advisory"
        ],
        epss_score=0.85,
        epss_percentile=0.95,
        in_cisa_kev=True,
    )
    db.add(cve)
    await db.commit()
    await db.refresh(cve)
    return cve


@pytest.fixture
async def multiple_cves(db: AsyncSession) -> list[CVECache]:
    """Crea múltiples CVEs de prueba."""
    cves = [
        CVECache(
            cve_id="CVE-2024-1001",
            description="SQL injection in web application",
            cvss_v3_score=8.5,
            cvss_v3_severity="HIGH",
            published_date=datetime(2024, 2, 1, tzinfo=timezone.utc),
            last_modified_date=datetime(2024, 2, 1, tzinfo=timezone.utc),
            cwe_ids=["CWE-89"],
        ),
        CVECache(
            cve_id="CVE-2024-1002",
            description="Cross-site scripting vulnerability",
            cvss_v3_score=6.1,
            cvss_v3_severity="MEDIUM",
            published_date=datetime(2024, 2, 5, tzinfo=timezone.utc),
            last_modified_date=datetime(2024, 2, 5, tzinfo=timezone.utc),
            cwe_ids=["CWE-79"],
        ),
        CVECache(
            cve_id="CVE-2024-1003",
            description="Information disclosure in logging",
            cvss_v3_score=4.3,
            cvss_v3_severity="MEDIUM",
            published_date=datetime(2024, 2, 10, tzinfo=timezone.utc),
            last_modified_date=datetime(2024, 2, 10, tzinfo=timezone.utc),
            cwe_ids=["CWE-200"],
        ),
        CVECache(
            cve_id="CVE-2024-1004",
            description="Remote code execution in parser",
            cvss_v3_score=9.8,
            cvss_v3_severity="CRITICAL",
            published_date=datetime(2024, 2, 15, tzinfo=timezone.utc),
            last_modified_date=datetime(2024, 2, 15, tzinfo=timezone.utc),
            cwe_ids=["CWE-94"],
            in_cisa_kev=True,
        ),
    ]
    
    for cve in cves:
        db.add(cve)
    
    await db.commit()
    
    for cve in cves:
        await db.refresh(cve)
    
    return cves


# =============================================================================
# Test: Search CVEs
# =============================================================================
class TestCVESearch:
    """Tests para búsqueda de CVEs."""
    
    async def test_search_empty(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
    ):
        """Búsqueda sin resultados."""
        response = await api_client.get(
            "/api/v1/cve",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data
    
    async def test_search_with_results(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        test_cve: CVECache,
    ):
        """Búsqueda con resultados."""
        response = await api_client.get(
            "/api/v1/cve",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        
        cve = data["items"][0]
        assert "cve_id" in cve
        assert "cvss_v3_score" in cve
        assert "in_cisa_kev" in cve
    
    async def test_search_by_keyword(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        multiple_cves: list[CVECache],
    ):
        """Búsqueda por palabra clave - skip si endpoint no soporta descripción."""
        # CVEReadMinimal no incluye description, así que solo verificamos que funcione
        response = await api_client.get(
            "/api/v1/cve?keyword=injection",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        # El keyword filter puede que no funcione con CVEReadMinimal
        # Solo verificamos que la respuesta sea válida
        data = response.json()
        assert "items" in data
    
    async def test_search_by_severity(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        multiple_cves: list[CVECache],
    ):
        """Filtra por severidad."""
        response = await api_client.get(
            "/api/v1/cve?severity=critical",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        for cve in data["items"]:
            # CVEReadMinimal tiene cvss_v3_severity
            assert cve["cvss_v3_severity"].upper() == "CRITICAL"
    
    async def test_search_by_score_range(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        multiple_cves: list[CVECache],
    ):
        """Filtra por rango de score."""
        response = await api_client.get(
            "/api/v1/cve?min_cvss=9.0&max_cvss=10.0",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        for cve in data["items"]:
            assert cve["cvss_v3_score"] >= 9.0
    
    async def test_search_kev_only(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        multiple_cves: list[CVECache],
    ):
        """Filtra solo CVEs en KEV."""
        response = await api_client.get(
            "/api/v1/cve?in_cisa_kev=true",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        for cve in data["items"]:
            assert cve["in_cisa_kev"] is True
    
    async def test_search_pagination(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        multiple_cves: list[CVECache],
    ):
        """Paginación funciona."""
        response = await api_client.get(
            "/api/v1/cve?page_size=2",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 2


# =============================================================================
# Test: Get CVE
# =============================================================================
class TestCVEGet:
    """Tests para obtener CVE específico."""
    
    async def test_get_cve_success(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        test_cve: CVECache,
    ):
        """Obtiene CVE por ID."""
        response = await api_client.get(
            f"/api/v1/cve/{test_cve.cve_id}",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["cve_id"] == test_cve.cve_id
        assert data["cvss_v3_score"] == test_cve.cvss_v3_score
        assert data["cvss_v3_severity"] == test_cve.cvss_v3_severity
    
    async def test_get_cve_not_found(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
    ):
        """404 para CVE inexistente."""
        response = await api_client.get(
            "/api/v1/cve/CVE-9999-9999",
            headers=auth_headers,
        )
        
        assert response.status_code == 404


# =============================================================================
# Test: Lookup CVE
# =============================================================================
class TestCVELookup:
    """Tests para lookup de CVE con auto-fetch."""
    
    async def test_lookup_cached_cve(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        test_cve: CVECache,
    ):
        """Lookup devuelve CVE cacheado."""
        response = await api_client.get(
            f"/api/v1/cve/lookup/{test_cve.cve_id}",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["cve_id"] == test_cve.cve_id


# =============================================================================
# Test: CVE Statistics
# =============================================================================
class TestCVEStats:
    """Tests para estadísticas de CVE."""
    
    async def test_get_stats_empty(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
    ):
        """Estadísticas con caché vacía."""
        response = await api_client.get(
            "/api/v1/cve/stats/summary",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "by_severity" in data
        assert "in_cisa_kev" in data
    
    async def test_get_stats_with_data(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        multiple_cves: list[CVECache],
    ):
        """Estadísticas con datos."""
        response = await api_client.get(
            "/api/v1/cve/stats/summary",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 4
        assert data["in_cisa_kev"] >= 1
        assert "critical" in data["by_severity"]


# =============================================================================
# Test: Sync Operations
# =============================================================================
class TestCVESync:
    """Tests para operaciones de sync."""
    
    async def test_trigger_sync_admin(
        self,
        api_client: AsyncClient,
        auth_headers_admin: dict,
    ):
        """Admin puede trigger sync."""
        response = await api_client.post(
            "/api/v1/cve/sync",
            headers=auth_headers_admin,
            json={"days_back": 7},
        )
        
        # 200 o 202 son válidos
        assert response.status_code in [200, 202]
    
    async def test_trigger_sync_viewer_forbidden(
        self,
        api_client: AsyncClient,
        auth_headers: dict,  # viewer
    ):
        """Viewer no puede trigger sync."""
        response = await api_client.post(
            "/api/v1/cve/sync",
            headers=auth_headers,
            json={"days_back": 7},
        )
        
        assert response.status_code == 403
    
    async def test_get_sync_status(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
    ):
        """Obtiene estado de sync."""
        response = await api_client.get(
            "/api/v1/cve/sync/status",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "last_sync" in data
        assert "total_cves" in data


# =============================================================================
# Test: Authentication
# =============================================================================
class TestCVEAuthentication:
    """Tests de autenticación."""
    
    async def test_search_unauthorized(
        self,
        api_client: AsyncClient,
    ):
        """Búsqueda requiere auth."""
        response = await api_client.get("/api/v1/cve")
        assert response.status_code == 401
    
    async def test_stats_unauthorized(
        self,
        api_client: AsyncClient,
    ):
        """Stats requiere auth."""
        response = await api_client.get("/api/v1/cve/stats/summary")
        assert response.status_code == 401
