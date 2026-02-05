# =============================================================================
# NESTSECURE - Tests para CPE Utilities
# =============================================================================
"""
Tests unitarios para las utilidades de CPE (Common Platform Enumeration).
"""

import pytest
from app.utils.cpe_utils import (
    CPE,
    parse_cpe,
    is_valid_cpe,
    create_cpe,
    cpe_matches_pattern,
    extract_vendor_product,
    extract_version,
    normalize_cpe,
    cpe_to_human_readable,
    build_cpe_search_query,
    build_cpe_from_service_info,
    get_cpe_confidence,
)


# =============================================================================
# Tests para CPE Dataclass
# =============================================================================

class TestCPEDataclass:
    """Tests para la clase CPE."""
    
    def test_cpe_creation(self):
        """Test crear CPE básico."""
        cpe = CPE(
            part="a",
            vendor="apache",
            product="http_server",
            version="2.4.49",
        )
        
        assert cpe.part == "a"
        assert cpe.vendor == "apache"
        assert cpe.product == "http_server"
        assert cpe.version == "2.4.49"
    
    def test_cpe_part_name(self):
        """Test nombre legible del part."""
        cpe_app = CPE(part="a", vendor="test", product="test")
        cpe_hw = CPE(part="h", vendor="test", product="test")
        cpe_os = CPE(part="o", vendor="test", product="test")
        
        assert cpe_app.part_name == "Application"
        assert cpe_hw.part_name == "Hardware"
        assert cpe_os.part_name == "Operating System"
    
    def test_cpe_to_uri(self):
        """Test conversión a URI CPE 2.3."""
        cpe = CPE(
            part="a",
            vendor="apache",
            product="http_server",
            version="2.4.49",
        )
        
        uri = cpe.to_uri()
        assert uri.startswith("cpe:2.3:a:apache:http_server:2.4.49:")
    
    def test_cpe_to_dict(self):
        """Test conversión a diccionario."""
        cpe = CPE(part="a", vendor="nginx", product="nginx", version="1.18")
        
        d = cpe.to_dict()
        assert d["vendor"] == "nginx"
        assert d["product"] == "nginx"
        assert d["version"] == "1.18"
        assert d["part_name"] == "Application"
    
    def test_cpe_matches(self):
        """Test matching de CPEs."""
        cpe1 = CPE(part="a", vendor="apache", product="http_server", version="2.4.49")
        cpe2 = CPE(part="a", vendor="apache", product="http_server", version="2.4.49")
        cpe3 = CPE(part="a", vendor="nginx", product="nginx", version="1.18")
        
        assert cpe1.matches(cpe2)
        assert not cpe1.matches(cpe3)
    
    def test_cpe_matches_wildcard(self):
        """Test matching con wildcards."""
        pattern = CPE(part="a", vendor="apache", product="*", version="*")
        cpe = CPE(part="a", vendor="apache", product="http_server", version="2.4.49")
        
        assert pattern.matches(cpe)


# =============================================================================
# Tests para parse_cpe
# =============================================================================

class TestParseCPE:
    """Tests para parse_cpe."""
    
    def test_parse_valid_cpe(self):
        """Test parsear CPE válido."""
        cpe_str = "cpe:2.3:a:apache:http_server:2.4.49:*:*:*:*:*:*:*"
        cpe = parse_cpe(cpe_str)
        
        assert cpe is not None
        assert cpe.vendor == "apache"
        assert cpe.product == "http_server"
        assert cpe.version == "2.4.49"
    
    def test_parse_cpe_with_wildcards(self):
        """Test parsear CPE con wildcards."""
        cpe_str = "cpe:2.3:a:*:*:*:*:*:*:*:*:*:*"
        cpe = parse_cpe(cpe_str)
        
        assert cpe is not None
        assert cpe.vendor == "*"
        assert cpe.product == "*"
    
    def test_parse_invalid_cpe(self):
        """Test parsear CPE inválido."""
        assert parse_cpe("") is None
        assert parse_cpe("invalid") is None
        assert parse_cpe("cpe:/a:vendor:product") is None  # CPE 2.2 not supported
    
    def test_parse_cpe_short(self):
        """Test parsear CPE corto."""
        # CPE con menos componentes
        cpe_str = "cpe:2.3:a:vendor:product"
        cpe = parse_cpe(cpe_str)
        # Debería poder manejarlo
        assert cpe is not None


# =============================================================================
# Tests para is_valid_cpe
# =============================================================================

class TestIsValidCPE:
    """Tests para is_valid_cpe."""
    
    def test_valid_cpe(self):
        """Test CPE válido."""
        assert is_valid_cpe("cpe:2.3:a:apache:http_server:2.4.49:*:*:*:*:*:*:*")
        assert is_valid_cpe("cpe:2.3:o:linux:linux_kernel:5.10:*:*:*:*:*:*:*")
    
    def test_invalid_cpe(self):
        """Test CPE inválido."""
        assert not is_valid_cpe("")
        assert not is_valid_cpe("not a cpe")
        assert not is_valid_cpe("cpe:/a:vendor:product")


# =============================================================================
# Tests para create_cpe
# =============================================================================

class TestCreateCPE:
    """Tests para create_cpe."""
    
    def test_create_basic_cpe(self):
        """Test crear CPE básico."""
        cpe = create_cpe(part="a", vendor="Apache", product="HTTP Server", version="2.4.49")
        
        assert cpe.part == "a"
        assert cpe.vendor == "apache"  # Lowercase
        assert cpe.product == "http_server"  # Spaces to underscores
        assert cpe.version == "2.4.49"
    
    def test_create_cpe_normalizes_names(self):
        """Test que create_cpe normaliza nombres."""
        cpe = create_cpe(part="a", vendor="Nginx Inc", product="NGINX", version="1.18.0")
        
        assert cpe.vendor == "nginx_inc"
        assert cpe.product == "nginx"


# =============================================================================
# Tests para extract_vendor_product
# =============================================================================

class TestExtractVendorProduct:
    """Tests para extract_vendor_product."""
    
    def test_extract_from_valid_cpe(self):
        """Test extraer vendor/product de CPE válido."""
        result = extract_vendor_product("cpe:2.3:a:apache:http_server:2.4.49:*:*:*:*:*:*:*")
        
        assert result is not None
        assert result == ("apache", "http_server")
    
    def test_extract_from_invalid_cpe(self):
        """Test extraer de CPE inválido."""
        result = extract_vendor_product("invalid")
        assert result is None


# =============================================================================
# Tests para extract_version
# =============================================================================

class TestExtractVersion:
    """Tests para extract_version."""
    
    def test_extract_version(self):
        """Test extraer versión."""
        version = extract_version("cpe:2.3:a:apache:http_server:2.4.49:*:*:*:*:*:*:*")
        assert version == "2.4.49"
    
    def test_extract_version_wildcard(self):
        """Test extraer versión wildcard."""
        version = extract_version("cpe:2.3:a:apache:http_server:*:*:*:*:*:*:*:*")
        assert version is None


# =============================================================================
# Tests para normalize_cpe
# =============================================================================

class TestNormalizeCPE:
    """Tests para normalize_cpe."""
    
    def test_normalize_valid(self):
        """Test normalizar CPE válido."""
        cpe_str = "cpe:2.3:a:apache:http_server:2.4.49:*:*:*:*:*:*:*"
        normalized = normalize_cpe(cpe_str)
        
        assert normalized is not None
        assert normalized.startswith("cpe:2.3:")
    
    def test_normalize_invalid(self):
        """Test normalizar CPE inválido."""
        assert normalize_cpe("invalid") is None


# =============================================================================
# Tests para cpe_to_human_readable
# =============================================================================

class TestCPEToHumanReadable:
    """Tests para cpe_to_human_readable."""
    
    def test_convert_to_readable(self):
        """Test convertir a formato legible."""
        cpe_str = "cpe:2.3:a:apache:http_server:2.4.49:*:*:*:*:*:*:*"
        readable = cpe_to_human_readable(cpe_str)
        
        assert "Apache" in readable
        assert "Http Server" in readable or "Http_server" in readable
        assert "2.4.49" in readable
    
    def test_convert_without_version(self):
        """Test convertir sin versión."""
        cpe_str = "cpe:2.3:a:nginx:nginx:*:*:*:*:*:*:*:*"
        readable = cpe_to_human_readable(cpe_str)
        
        assert "Nginx" in readable


# =============================================================================
# Tests para build_cpe_search_query
# =============================================================================

class TestBuildCPESearchQuery:
    """Tests para build_cpe_search_query."""
    
    def test_build_with_all_params(self):
        """Test construir query con todos los parámetros."""
        query = build_cpe_search_query(vendor="apache", product="http_server", version="2.4.49")
        
        assert "apache" in query
        assert "http_server" in query
        assert "2.4.49" in query
    
    def test_build_without_version(self):
        """Test construir query sin versión."""
        query = build_cpe_search_query(vendor="nginx", product="nginx")
        
        assert "nginx" in query
        assert "*" in query  # Version wildcard


# =============================================================================
# Tests para build_cpe_from_service_info
# =============================================================================

class TestBuildCPEFromServiceInfo:
    """Tests para build_cpe_from_service_info."""
    
    def test_build_from_apache(self):
        """Test construir CPE para Apache."""
        cpe = build_cpe_from_service_info(
            service_name="http",
            product="Apache httpd",
            version="2.4.49"
        )
        
        assert cpe is not None
        assert "apache" in cpe.lower()
        assert "http_server" in cpe.lower()
        assert "2.4.49" in cpe
    
    def test_build_from_nginx(self):
        """Test construir CPE para Nginx."""
        cpe = build_cpe_from_service_info(
            service_name="http",
            product="nginx",
            version="1.18.0"
        )
        
        assert cpe is not None
        assert "nginx" in cpe.lower()
        assert "1.18.0" in cpe
    
    def test_build_from_openssh(self):
        """Test construir CPE para OpenSSH."""
        cpe = build_cpe_from_service_info(
            service_name="ssh",
            product="OpenSSH",
            version="8.9"
        )
        
        assert cpe is not None
        assert "openssh" in cpe.lower()
    
    def test_build_without_product(self):
        """Test sin producto retorna None."""
        cpe = build_cpe_from_service_info(
            service_name="http",
            product=None,
            version="1.0"
        )
        
        assert cpe is None
    
    def test_build_with_existing_cpe(self):
        """Test con CPE existente lo normaliza."""
        existing = "cpe:2.3:a:apache:http_server:2.4.49:*:*:*:*:*:*:*"
        cpe = build_cpe_from_service_info(
            service_name="http",
            product="Apache",
            version="2.4.49",
            existing_cpe=existing
        )
        
        assert cpe is not None
        assert cpe == existing
    
    def test_build_from_mysql(self):
        """Test construir CPE para MySQL."""
        cpe = build_cpe_from_service_info(
            service_name="mysql",
            product="MySQL",
            version="8.0.32"
        )
        
        assert cpe is not None
        assert "mysql" in cpe.lower()
    
    def test_build_from_redis(self):
        """Test construir CPE para Redis."""
        cpe = build_cpe_from_service_info(
            service_name="redis",
            product="Redis",
            version="7.0.5"
        )
        
        assert cpe is not None
        assert "redis" in cpe.lower()


# =============================================================================
# Tests para get_cpe_confidence
# =============================================================================

class TestGetCPEConfidence:
    """Tests para get_cpe_confidence."""
    
    def test_nmap_cpe_high_confidence(self):
        """Test CPE de Nmap tiene alta confianza."""
        confidence = get_cpe_confidence("nmap_cpe", has_version=True)
        assert confidence >= 90
    
    def test_constructed_cpe_with_version(self):
        """Test CPE construido con versión."""
        confidence = get_cpe_confidence("constructed", has_version=True)
        assert 50 <= confidence < 90
    
    def test_constructed_cpe_without_version(self):
        """Test CPE construido sin versión tiene menor confianza."""
        with_version = get_cpe_confidence("constructed", has_version=True)
        without_version = get_cpe_confidence("constructed", has_version=False)
        
        assert without_version < with_version
    
    def test_unknown_source(self):
        """Test fuente desconocida."""
        confidence = get_cpe_confidence("unknown", has_version=True)
        assert 0 <= confidence <= 100


# =============================================================================
# Tests de integración
# =============================================================================

class TestCPEIntegration:
    """Tests de integración para CPE utilities."""
    
    def test_full_workflow_apache(self):
        """Test flujo completo para Apache."""
        # 1. Construir CPE desde info de servicio
        cpe = build_cpe_from_service_info(
            service_name="http",
            product="Apache httpd",
            version="2.4.49"
        )
        
        assert cpe is not None
        
        # 2. Parsear y verificar
        parsed = parse_cpe(cpe)
        assert parsed is not None
        assert parsed.vendor == "apache"
        assert parsed.product == "http_server"
        
        # 3. Convertir a legible
        readable = cpe_to_human_readable(cpe)
        assert "Apache" in readable
    
    def test_full_workflow_nginx(self):
        """Test flujo completo para Nginx."""
        cpe = build_cpe_from_service_info(
            service_name="http",
            product="nginx/1.18.0",
            version="1.18.0"
        )
        
        assert cpe is not None
        parsed = parse_cpe(cpe)
        assert parsed is not None
    
    def test_cpe_matching_workflow(self):
        """Test workflow de matching."""
        # Crear patrón
        pattern = create_cpe(part="a", vendor="apache", product="http_server")
        
        # Crear CPE específico
        specific_cpe = "cpe:2.3:a:apache:http_server:2.4.49:*:*:*:*:*:*:*"
        parsed = parse_cpe(specific_cpe)
        
        # Verificar match
        assert pattern.matches(parsed)
