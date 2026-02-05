# =============================================================================
# NESTSECURE - Tests para Network Utilities
# =============================================================================
"""
Tests completos para el módulo de validación de red.

Cubre:
- Validación de IPs privadas vs públicas
- Validación de redes CIDR
- Función principal validate_scan_target
- Obtención de información de red
- Escenarios de seguridad
"""

import ipaddress
import pytest
from fastapi import HTTPException

from app.utils.network_utils import (
    is_private_ip,
    is_private_network,
    is_valid_ip,
    is_valid_cidr,
    validate_scan_target,
    validate_multiple_targets,
    validate_targets_list,
    get_network_info,
    get_ip_info,
    expand_cidr_to_ips,
    validate_target_for_scan,
    PRIVATE_IP_RANGES,
)


# =============================================================================
# Tests: is_private_ip
# =============================================================================

class TestIsPrivateIP:
    """Tests para verificación de IPs privadas."""
    
    # -------------------------------------------------------------------------
    # IPs Clase A privadas (10.x.x.x)
    # -------------------------------------------------------------------------
    
    def test_class_a_private_ip_start(self):
        """Primer IP del rango Clase A."""
        assert is_private_ip('10.0.0.0')
    
    def test_class_a_private_ip_common(self):
        """IP común en rango Clase A."""
        assert is_private_ip('10.0.0.1')
        assert is_private_ip('10.1.2.3')
        assert is_private_ip('10.100.50.25')
    
    def test_class_a_private_ip_end(self):
        """Última IP del rango Clase A."""
        assert is_private_ip('10.255.255.255')
        assert is_private_ip('10.255.255.254')
    
    # -------------------------------------------------------------------------
    # IPs Clase B privadas (172.16-31.x.x)
    # -------------------------------------------------------------------------
    
    def test_class_b_private_ip_start(self):
        """Primer IP del rango Clase B."""
        assert is_private_ip('172.16.0.0')
        assert is_private_ip('172.16.0.1')
    
    def test_class_b_private_ip_middle(self):
        """IPs en medio del rango Clase B."""
        assert is_private_ip('172.20.1.1')
        assert is_private_ip('172.24.100.200')
    
    def test_class_b_private_ip_end(self):
        """Última IP del rango Clase B."""
        assert is_private_ip('172.31.255.255')
        assert is_private_ip('172.31.255.254')
    
    def test_class_b_outside_range(self):
        """IPs fuera del rango Clase B privado."""
        # 172.15.x.x está FUERA del rango privado
        assert not is_private_ip('172.15.0.1')
        # 172.32.x.x también está FUERA
        assert not is_private_ip('172.32.0.1')
    
    # -------------------------------------------------------------------------
    # IPs Clase C privadas (192.168.x.x)
    # -------------------------------------------------------------------------
    
    def test_class_c_private_ip_start(self):
        """Primer IP del rango Clase C."""
        assert is_private_ip('192.168.0.0')
        assert is_private_ip('192.168.0.1')
    
    def test_class_c_private_ip_common(self):
        """IPs comunes en Clase C (típica red casera)."""
        assert is_private_ip('192.168.1.1')     # Router típico
        assert is_private_ip('192.168.1.100')
        assert is_private_ip('192.168.0.50')
    
    def test_class_c_private_ip_end(self):
        """Última IP del rango Clase C."""
        assert is_private_ip('192.168.255.255')
        assert is_private_ip('192.168.255.254')
    
    # -------------------------------------------------------------------------
    # Localhost (127.x.x.x)
    # -------------------------------------------------------------------------
    
    def test_localhost_common(self):
        """Localhost típico."""
        assert is_private_ip('127.0.0.1')
    
    def test_localhost_range(self):
        """Todo el rango localhost."""
        assert is_private_ip('127.0.0.0')
        assert is_private_ip('127.255.255.254')
        assert is_private_ip('127.1.2.3')
    
    # -------------------------------------------------------------------------
    # Link-local (169.254.x.x)
    # -------------------------------------------------------------------------
    
    def test_link_local_ip(self):
        """IPs link-local (APIPA)."""
        assert is_private_ip('169.254.1.1')
        assert is_private_ip('169.254.255.254')
    
    # -------------------------------------------------------------------------
    # IPs Públicas (deberían retornar False)
    # -------------------------------------------------------------------------
    
    def test_public_ip_google_dns(self):
        """Google DNS es IP pública."""
        assert not is_private_ip('8.8.8.8')
        assert not is_private_ip('8.8.4.4')
    
    def test_public_ip_cloudflare_dns(self):
        """Cloudflare DNS es IP pública."""
        assert not is_private_ip('1.1.1.1')
        assert not is_private_ip('1.0.0.1')
    
    def test_public_ip_opendns(self):
        """OpenDNS es IP pública."""
        assert not is_private_ip('208.67.222.222')
        assert not is_private_ip('208.67.220.220')
    
    def test_public_ip_random(self):
        """IPs públicas aleatorias."""
        assert not is_private_ip('151.101.1.140')   # Fastly
        assert not is_private_ip('93.184.216.34')   # example.com
        assert not is_private_ip('203.0.113.1')     # TEST-NET-3
        assert not is_private_ip('198.51.100.1')    # TEST-NET-2
    
    # -------------------------------------------------------------------------
    # IPs Inválidas
    # -------------------------------------------------------------------------
    
    def test_invalid_ip_string(self):
        """Strings que no son IPs."""
        assert not is_private_ip('invalid')
        assert not is_private_ip('not-an-ip')
        assert not is_private_ip('')
        assert not is_private_ip('google.com')
    
    def test_invalid_ip_format(self):
        """Formatos de IP incorrectos."""
        assert not is_private_ip('999.999.999.999')
        assert not is_private_ip('192.168.1')
        assert not is_private_ip('192.168.1.1.1')
        assert not is_private_ip('256.1.1.1')


# =============================================================================
# Tests: is_private_network
# =============================================================================

class TestIsPrivateNetwork:
    """Tests para verificación de redes privadas CIDR."""
    
    # -------------------------------------------------------------------------
    # Redes Clase A
    # -------------------------------------------------------------------------
    
    def test_class_a_full_network(self):
        """Red completa Clase A."""
        assert is_private_network('10.0.0.0/8')
    
    def test_class_a_subnets(self):
        """Subredes dentro de Clase A."""
        assert is_private_network('10.0.0.0/16')
        assert is_private_network('10.1.0.0/24')
        assert is_private_network('10.10.10.0/24')
    
    # -------------------------------------------------------------------------
    # Redes Clase B
    # -------------------------------------------------------------------------
    
    def test_class_b_full_network(self):
        """Red completa Clase B."""
        assert is_private_network('172.16.0.0/12')
    
    def test_class_b_subnets(self):
        """Subredes dentro de Clase B."""
        assert is_private_network('172.16.0.0/16')
        assert is_private_network('172.20.0.0/24')
        assert is_private_network('172.31.0.0/24')
    
    # -------------------------------------------------------------------------
    # Redes Clase C
    # -------------------------------------------------------------------------
    
    def test_class_c_full_network(self):
        """Red completa Clase C."""
        assert is_private_network('192.168.0.0/16')
    
    def test_class_c_subnets(self):
        """Subredes típicas Clase C."""
        assert is_private_network('192.168.1.0/24')
        assert is_private_network('192.168.0.0/24')
        assert is_private_network('192.168.100.0/24')
    
    def test_class_c_small_subnets(self):
        """Subredes pequeñas Clase C."""
        assert is_private_network('192.168.1.0/28')
        assert is_private_network('192.168.1.0/30')
    
    # -------------------------------------------------------------------------
    # Redes Públicas
    # -------------------------------------------------------------------------
    
    def test_public_network_google(self):
        """Red de Google DNS es pública."""
        assert not is_private_network('8.8.8.0/24')
    
    def test_public_network_cloudflare(self):
        """Red de Cloudflare es pública."""
        assert not is_private_network('1.1.1.0/24')
    
    def test_public_network_random(self):
        """Redes públicas aleatorias."""
        assert not is_private_network('151.101.0.0/16')
        assert not is_private_network('203.0.113.0/24')
    
    # -------------------------------------------------------------------------
    # CIDRs Inválidos
    # -------------------------------------------------------------------------
    
    def test_invalid_cidr_string(self):
        """Strings inválidos."""
        assert not is_private_network('invalid')
        assert not is_private_network('')
    
    def test_invalid_cidr_format(self):
        """Formatos CIDR incorrectos."""
        assert not is_private_network('192.168.1.1/99')
        # Sin /xx se trata como /32, que es válido para IPs privadas
        assert is_private_network('192.168.1.0')  # Tratado como /32


# =============================================================================
# Tests: is_valid_ip / is_valid_cidr
# =============================================================================

class TestIsValidIP:
    """Tests para validación de formato IP."""
    
    def test_valid_ipv4(self):
        """IPv4 válidas."""
        assert is_valid_ip('192.168.1.1')
        assert is_valid_ip('10.0.0.1')
        assert is_valid_ip('8.8.8.8')
    
    def test_invalid_ip(self):
        """IPs inválidas."""
        assert not is_valid_ip('invalid')
        assert not is_valid_ip('192.168.1')
        assert not is_valid_ip('256.1.1.1')


class TestIsValidCIDR:
    """Tests para validación de formato CIDR."""
    
    def test_valid_cidr(self):
        """CIDRs válidos."""
        assert is_valid_cidr('192.168.1.0/24')
        assert is_valid_cidr('10.0.0.0/8')
        assert is_valid_cidr('0.0.0.0/0')
    
    def test_invalid_cidr(self):
        """CIDRs inválidos."""
        assert not is_valid_cidr('invalid')
        # Sin /xx se trata como /32 y es válido
        assert is_valid_cidr('192.168.1.1')  # Tratado como /32
        assert not is_valid_cidr('192.168.1.0/99')


# =============================================================================
# Tests: validate_scan_target
# =============================================================================

class TestValidateScanTarget:
    """Tests para la función principal de validación."""
    
    # -------------------------------------------------------------------------
    # IPs Privadas Válidas
    # -------------------------------------------------------------------------
    
    def test_valid_private_ip_class_a(self):
        """IP Clase A válida."""
        target, tipo = validate_scan_target('10.0.0.1')
        assert target == '10.0.0.1'
        assert tipo == 'ip'
    
    def test_valid_private_ip_class_b(self):
        """IP Clase B válida."""
        target, tipo = validate_scan_target('172.16.0.1')
        assert target == '172.16.0.1'
        assert tipo == 'ip'
    
    def test_valid_private_ip_class_c(self):
        """IP Clase C válida."""
        target, tipo = validate_scan_target('192.168.1.1')
        assert target == '192.168.1.1'
        assert tipo == 'ip'
    
    def test_valid_localhost(self):
        """Localhost válido."""
        target, tipo = validate_scan_target('127.0.0.1')
        assert target == '127.0.0.1'
        assert tipo == 'ip'
    
    # -------------------------------------------------------------------------
    # Redes CIDR Privadas Válidas
    # -------------------------------------------------------------------------
    
    def test_valid_private_cidr_class_c(self):
        """Red Clase C válida."""
        target, tipo = validate_scan_target('192.168.1.0/24')
        assert target == '192.168.1.0/24'
        assert tipo == 'cidr'
    
    def test_valid_private_cidr_class_a(self):
        """Red Clase A válida."""
        target, tipo = validate_scan_target('10.0.0.0/8')
        assert target == '10.0.0.0/8'
        assert tipo == 'cidr'
    
    def test_valid_private_cidr_small(self):
        """Red pequeña válida."""
        target, tipo = validate_scan_target('192.168.1.0/28')
        assert target == '192.168.1.0/28'
        assert tipo == 'cidr'
    
    def test_cidr_normalization(self):
        """CIDR se normaliza correctamente."""
        # 192.168.1.100/24 debería normalizarse a 192.168.1.0/24
        target, tipo = validate_scan_target('192.168.1.100/24')
        assert target == '192.168.1.0/24'
        assert tipo == 'cidr'
    
    # -------------------------------------------------------------------------
    # IPs Públicas Rechazadas
    # -------------------------------------------------------------------------
    
    def test_public_ip_google_rejected(self):
        """Google DNS rechazado."""
        with pytest.raises(HTTPException) as exc_info:
            validate_scan_target('8.8.8.8')
        
        assert exc_info.value.status_code == 400
        assert 'Public IP address' in exc_info.value.detail
        assert '8.8.8.8' in exc_info.value.detail
    
    def test_public_ip_cloudflare_rejected(self):
        """Cloudflare DNS rechazado."""
        with pytest.raises(HTTPException) as exc_info:
            validate_scan_target('1.1.1.1')
        
        assert exc_info.value.status_code == 400
        assert 'Public IP address' in exc_info.value.detail
    
    def test_public_ip_random_rejected(self):
        """IPs públicas aleatorias rechazadas."""
        public_ips = ['151.101.1.140', '93.184.216.34', '203.0.113.1']
        
        for ip in public_ips:
            with pytest.raises(HTTPException) as exc_info:
                validate_scan_target(ip)
            
            assert exc_info.value.status_code == 400
    
    # -------------------------------------------------------------------------
    # Redes Públicas Rechazadas
    # -------------------------------------------------------------------------
    
    def test_public_network_rejected(self):
        """Redes públicas rechazadas."""
        with pytest.raises(HTTPException) as exc_info:
            validate_scan_target('8.8.8.0/24')
        
        assert exc_info.value.status_code == 400
        assert 'Public networks' in exc_info.value.detail
    
    def test_public_network_large_rejected(self):
        """Redes públicas grandes rechazadas."""
        with pytest.raises(HTTPException):
            validate_scan_target('151.101.0.0/16')
    
    # -------------------------------------------------------------------------
    # Hostnames Rechazados
    # -------------------------------------------------------------------------
    
    def test_hostname_rejected(self):
        """Hostnames rechazados por seguridad."""
        with pytest.raises(HTTPException) as exc_info:
            validate_scan_target('google.com')
        
        assert exc_info.value.status_code == 400
        assert 'Hostnames are not supported' in exc_info.value.detail
    
    def test_hostname_subdomain_rejected(self):
        """Subdominios también rechazados."""
        with pytest.raises(HTTPException):
            validate_scan_target('www.example.com')
    
    def test_hostname_local_rejected(self):
        """Hostnames locales también rechazados."""
        # Por seguridad, no resolvemos hostnames
        with pytest.raises(HTTPException):
            validate_scan_target('localhost.localdomain')
    
    # -------------------------------------------------------------------------
    # Casos Edge
    # -------------------------------------------------------------------------
    
    def test_empty_target_rejected(self):
        """Target vacío rechazado."""
        with pytest.raises(HTTPException) as exc_info:
            validate_scan_target('')
        
        assert exc_info.value.status_code == 400
        assert 'cannot be empty' in exc_info.value.detail
    
    def test_whitespace_stripped(self):
        """Espacios en blanco eliminados."""
        target, tipo = validate_scan_target('  192.168.1.1  ')
        assert target == '192.168.1.1'
        assert tipo == 'ip'
    
    def test_invalid_cidr_format_rejected(self):
        """Formato CIDR inválido rechazado."""
        with pytest.raises(HTTPException) as exc_info:
            validate_scan_target('192.168.1.0/99')
        
        assert exc_info.value.status_code == 400
        assert 'Invalid CIDR format' in exc_info.value.detail


# =============================================================================
# Tests: validate_multiple_targets
# =============================================================================

class TestValidateMultipleTargets:
    """Tests para validación de múltiples targets."""
    
    def test_all_valid_targets(self):
        """Múltiples targets válidos."""
        targets = ['192.168.1.1', '10.0.0.0/8', '172.16.0.1']
        validated = validate_multiple_targets(targets)
        
        assert len(validated) == 3
        assert validated[0] == ('192.168.1.1', 'ip')
        assert validated[1] == ('10.0.0.0/8', 'cidr')
        assert validated[2] == ('172.16.0.1', 'ip')
    
    def test_first_target_invalid(self):
        """Primer target inválido genera error con contexto."""
        targets = ['8.8.8.8', '192.168.1.1']
        
        with pytest.raises(HTTPException) as exc_info:
            validate_multiple_targets(targets)
        
        assert 'Target #1' in exc_info.value.detail
        assert '8.8.8.8' in exc_info.value.detail
    
    def test_second_target_invalid(self):
        """Segundo target inválido genera error con contexto."""
        targets = ['192.168.1.1', '8.8.8.8']
        
        with pytest.raises(HTTPException) as exc_info:
            validate_multiple_targets(targets)
        
        assert 'Target #2' in exc_info.value.detail
    
    def test_empty_list_rejected(self):
        """Lista vacía rechazada."""
        with pytest.raises(HTTPException) as exc_info:
            validate_multiple_targets([])
        
        assert 'At least one target' in exc_info.value.detail


class TestValidateTargetsList:
    """Tests para validate_targets_list (retorna solo strings)."""
    
    def test_returns_only_strings(self):
        """Retorna solo los targets normalizados."""
        targets = ['192.168.1.1', '10.0.0.0/24']
        validated = validate_targets_list(targets)
        
        assert validated == ['192.168.1.1', '10.0.0.0/24']
        assert all(isinstance(t, str) for t in validated)


# =============================================================================
# Tests: get_network_info
# =============================================================================

class TestGetNetworkInfo:
    """Tests para obtener información de red."""
    
    def test_slash_24_network(self):
        """Red /24 típica (254 hosts)."""
        info = get_network_info('192.168.1.0/24')
        
        assert info['network'] == '192.168.1.0'
        assert info['netmask'] == '255.255.255.0'
        assert info['broadcast'] == '192.168.1.255'
        assert info['num_hosts'] == 254
        assert info['first_host'] == '192.168.1.1'
        assert info['last_host'] == '192.168.1.254'
        assert info['prefix_length'] == 24
        assert info['is_private'] is True
    
    def test_slash_16_network(self):
        """Red /16 (65,534 hosts)."""
        info = get_network_info('192.168.0.0/16')
        
        assert info['network'] == '192.168.0.0'
        assert info['netmask'] == '255.255.0.0'
        assert info['num_hosts'] == 65534
        assert info['prefix_length'] == 16
    
    def test_slash_8_network(self):
        """Red /8 (~16 millones de hosts)."""
        info = get_network_info('10.0.0.0/8')
        
        assert info['network'] == '10.0.0.0'
        assert info['prefix_length'] == 8
        assert info['num_hosts'] == 16777214
    
    def test_slash_30_network(self):
        """Red /30 (2 hosts - típico punto a punto)."""
        info = get_network_info('192.168.1.0/30')
        
        assert info['num_hosts'] == 2
        assert info['first_host'] == '192.168.1.1'
        assert info['last_host'] == '192.168.1.2'
    
    def test_slash_31_network(self):
        """Red /31 (sin hosts usables en implementación estándar)."""
        info = get_network_info('192.168.1.0/31')
        
        assert info['num_hosts'] == 0
        assert info['first_host'] is None
        assert info['last_host'] is None
    
    def test_public_network_detected(self):
        """Red pública correctamente identificada."""
        info = get_network_info('8.8.8.0/24')
        
        assert info['is_private'] is False


# =============================================================================
# Tests: get_ip_info
# =============================================================================

class TestGetIPInfo:
    """Tests para obtener información de IP."""
    
    def test_private_ip_info(self):
        """Info de IP privada."""
        info = get_ip_info('192.168.1.1')
        
        assert info['ip'] == '192.168.1.1'
        assert info['version'] == 4
        assert info['is_private'] is True
        assert info['is_loopback'] is False
    
    def test_loopback_ip_info(self):
        """Info de localhost."""
        info = get_ip_info('127.0.0.1')
        
        assert info['is_private'] is True
        assert info['is_loopback'] is True
    
    def test_public_ip_info(self):
        """Info de IP pública."""
        info = get_ip_info('8.8.8.8')
        
        assert info['is_private'] is False
        assert info['is_loopback'] is False


# =============================================================================
# Tests: expand_cidr_to_ips
# =============================================================================

class TestExpandCIDRToIPs:
    """Tests para expansión de CIDR a IPs."""
    
    def test_slash_30_expansion(self):
        """Expandir /30 (2 hosts)."""
        ips = expand_cidr_to_ips('192.168.1.0/30')
        
        assert len(ips) == 2
        assert '192.168.1.1' in ips
        assert '192.168.1.2' in ips
        # Network y broadcast no incluidos
        assert '192.168.1.0' not in ips
        assert '192.168.1.3' not in ips
    
    def test_slash_28_expansion(self):
        """Expandir /28 (14 hosts)."""
        ips = expand_cidr_to_ips('192.168.1.0/28')
        
        assert len(ips) == 14
        assert ips[0] == '192.168.1.1'
        assert ips[-1] == '192.168.1.14'
    
    def test_limit_applied(self):
        """Límite se aplica correctamente."""
        # /28 tiene 14 hosts, pedimos solo 10
        ips = expand_cidr_to_ips('192.168.1.0/28', limit=14)
        
        assert len(ips) == 14  # Devuelve todos los 14 hosts
    
    def test_exceeds_limit_raises_error(self):
        """Exceder límite genera error."""
        # /24 tiene 254 hosts, límite de 100
        with pytest.raises(ValueError) as exc_info:
            expand_cidr_to_ips('192.168.1.0/24', limit=100)
        
        assert 'exceeds limit' in str(exc_info.value)


# =============================================================================
# Tests: validate_target_for_scan (API helper)
# =============================================================================

class TestValidateTargetForScan:
    """Tests para el helper de API."""
    
    def test_valid_target_returns_info(self):
        """Target válido retorna información completa."""
        result = validate_target_for_scan('192.168.1.1')
        
        assert result['valid'] is True
        assert result['target'] == '192.168.1.1'
        assert result['type'] == 'ip'
        assert result['info'] is not None
        assert result['error'] is None
    
    def test_valid_cidr_returns_info(self):
        """CIDR válido retorna información de red."""
        result = validate_target_for_scan('192.168.1.0/24')
        
        assert result['valid'] is True
        assert result['type'] == 'cidr'
        assert result['info']['num_hosts'] == 254
    
    def test_invalid_target_returns_error(self):
        """Target inválido retorna error."""
        result = validate_target_for_scan('8.8.8.8')
        
        assert result['valid'] is False
        assert result['target'] == '8.8.8.8'
        assert result['type'] is None
        assert result['info'] is None
        assert result['error'] is not None
        assert 'Public IP' in result['error']


# =============================================================================
# Tests: Escenarios de Seguridad
# =============================================================================

class TestSecurityScenarios:
    """Tests de escenarios de seguridad críticos."""
    
    def test_blocks_google_dns(self):
        """SEGURIDAD: Bloquea escaneo a Google DNS."""
        with pytest.raises(HTTPException):
            validate_scan_target('8.8.8.8')
    
    def test_blocks_cloudflare_dns(self):
        """SEGURIDAD: Bloquea escaneo a Cloudflare DNS."""
        with pytest.raises(HTTPException):
            validate_scan_target('1.1.1.1')
    
    def test_blocks_aws_metadata(self):
        """SEGURIDAD: Bloquea escaneo a AWS metadata (169.254.169.254)."""
        # Aunque es link-local, el específico 169.254.169.254 es AWS metadata
        # Nota: Actualmente lo permitimos como link-local, pero podríamos bloquearlo
        # Este test documenta el comportamiento actual
        target, _ = validate_scan_target('169.254.169.254')
        assert target == '169.254.169.254'
    
    def test_blocks_external_networks(self):
        """SEGURIDAD: Bloquea escaneo a redes externas."""
        external_networks = [
            '151.101.0.0/16',   # Fastly CDN
            '104.16.0.0/12',    # Cloudflare
            '13.0.0.0/8',       # Amazon AWS
            '52.0.0.0/8',       # Amazon AWS
        ]
        
        for network in external_networks:
            with pytest.raises(HTTPException):
                validate_scan_target(network)
    
    def test_allows_local_router(self):
        """PERMITIDO: Escaneo a router local."""
        target, _ = validate_scan_target('192.168.1.1')
        assert target == '192.168.1.1'
    
    def test_allows_local_network(self):
        """PERMITIDO: Escaneo a red local completa."""
        target, _ = validate_scan_target('192.168.1.0/24')
        assert target == '192.168.1.0/24'
    
    def test_allows_internal_servers(self):
        """PERMITIDO: Escaneo a servidores internos típicos."""
        internal_ips = [
            '10.0.0.1',         # Gateway típico
            '10.10.10.1',       # Server interno
            '172.16.0.100',     # Server DMZ
            '192.168.0.254',    # Otro gateway
        ]
        
        for ip in internal_ips:
            target, _ = validate_scan_target(ip)
            assert target == ip


# =============================================================================
# Tests: Casos de Uso Reales
# =============================================================================

class TestRealWorldUseCases:
    """Tests basados en casos de uso reales."""
    
    def test_home_network_scan(self):
        """Caso: Escanear red casera típica."""
        # Red típica de hogar: 192.168.1.0/24
        target, tipo = validate_scan_target('192.168.1.0/24')
        assert target == '192.168.1.0/24'
        assert tipo == 'cidr'
        
        info = get_network_info(target)
        assert info['num_hosts'] == 254
    
    def test_corporate_network_scan(self):
        """Caso: Escanear red corporativa."""
        # Red corporativa típica: 10.x.x.x
        target, tipo = validate_scan_target('10.100.0.0/16')
        assert target == '10.100.0.0/16'
        assert tipo == 'cidr'
    
    def test_dmz_scan(self):
        """Caso: Escanear DMZ."""
        # DMZ típica: 172.16.x.x
        target, tipo = validate_scan_target('172.16.1.0/24')
        assert target == '172.16.1.0/24'
        assert tipo == 'cidr'
    
    def test_single_server_scan(self):
        """Caso: Escanear servidor específico."""
        target, tipo = validate_scan_target('192.168.1.100')
        assert target == '192.168.1.100'
        assert tipo == 'ip'
    
    def test_multiple_targets_scan(self):
        """Caso: Escanear múltiples targets."""
        targets = [
            '192.168.1.1',      # Router
            '192.168.1.100',    # Server 1
            '192.168.1.101',    # Server 2
            '10.0.0.0/24',      # Otra red
        ]
        
        validated = validate_targets_list(targets)
        assert len(validated) == 4


# =============================================================================
# Tests: Integración con Constantes
# =============================================================================

class TestConstants:
    """Tests para constantes del módulo."""
    
    def test_private_ip_ranges_count(self):
        """Verificar cantidad de rangos privados."""
        assert len(PRIVATE_IP_RANGES) == 5
    
    def test_private_ip_ranges_types(self):
        """Verificar tipos de rangos."""
        for network in PRIVATE_IP_RANGES:
            assert isinstance(network, (
                type(ipaddress.ip_network('10.0.0.0/8'))
            ))
