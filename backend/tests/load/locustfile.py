# =============================================================================
# NESTSECURE - Tests de Carga con Locust
# =============================================================================
"""
Tests de carga para verificar el rendimiento de la aplicación
bajo diferentes niveles de carga.

Ejecutar con:
    locust -f tests/load/locustfile.py --host=http://localhost:8000

O para ejecución headless:
    locust -f tests/load/locustfile.py --host=http://localhost:8000 \
        --users 100 --spawn-rate 10 --run-time 5m --headless
"""

from locust import HttpUser, task, between, tag
from locust import events
import json
import random
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NestSecureUser(HttpUser):
    """
    Usuario simulado para pruebas de carga de NestSecure.
    Simula el comportamiento típico de un usuario del sistema.
    """
    
    # Tiempo de espera entre tareas (1-5 segundos)
    wait_time = between(1, 5)
    
    # Token de autenticación
    token = None
    
    # IDs de recursos creados para usar en tests
    created_asset_ids = []
    created_scan_ids = []
    
    def on_start(self):
        """Se ejecuta al inicio de cada usuario simulado."""
        self.login()
    
    def login(self):
        """Autenticar usuario y obtener token."""
        response = self.client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@nestsecure.com",
                "password": "Admin123!"
            },
            name="Login"
        )
        
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token")
            logger.info("Usuario autenticado exitosamente")
        else:
            logger.error(f"Error de login: {response.status_code}")
    
    @property
    def headers(self):
        """Headers con autenticación."""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    # =========================================================================
    # Tasks de Dashboard (más frecuentes - peso alto)
    # =========================================================================
    
    @task(10)
    @tag('dashboard', 'read')
    def view_dashboard(self):
        """Ver dashboard principal."""
        with self.client.get(
            "/api/v1/dashboard/stats",
            headers=self.headers,
            name="Dashboard Stats",
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Error: {response.status_code}")
    
    @task(8)
    @tag('dashboard', 'read')
    def view_dashboard_summary(self):
        """Ver resumen del dashboard."""
        with self.client.get(
            "/api/v1/dashboard/summary",
            headers=self.headers,
            name="Dashboard Summary",
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Error: {response.status_code}")
    
    # =========================================================================
    # Tasks de Assets (frecuentes)
    # =========================================================================
    
    @task(7)
    @tag('assets', 'read')
    def list_assets(self):
        """Listar assets."""
        self.client.get(
            "/api/v1/assets",
            headers=self.headers,
            name="List Assets"
        )
    
    @task(5)
    @tag('assets', 'read')
    def list_assets_with_filters(self):
        """Listar assets con filtros."""
        asset_types = ["server", "workstation", "network", "database"]
        criticalities = ["low", "medium", "high", "critical"]
        
        params = {
            "asset_type": random.choice(asset_types),
            "page": random.randint(1, 3),
            "page_size": random.choice([10, 25, 50])
        }
        
        self.client.get(
            "/api/v1/assets",
            params=params,
            headers=self.headers,
            name="List Assets (filtered)"
        )
    
    @task(3)
    @tag('assets', 'write')
    def create_asset(self):
        """Crear un nuevo asset."""
        asset_data = {
            "ip_address": f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
            "hostname": f"load-test-server-{random.randint(1000, 9999)}",
            "asset_type": random.choice(["server", "workstation", "network"]),
            "criticality": random.choice(["low", "medium", "high", "critical"]),
            "status": "active"
        }
        
        with self.client.post(
            "/api/v1/assets",
            json=asset_data,
            headers=self.headers,
            name="Create Asset",
            catch_response=True
        ) as response:
            if response.status_code in [200, 201]:
                data = response.json()
                if "id" in data:
                    self.created_asset_ids.append(data["id"])
                response.success()
            elif response.status_code == 409:
                # IP duplicada - es esperado
                response.success()
            else:
                response.failure(f"Error: {response.status_code}")
    
    @task(2)
    @tag('assets', 'read')
    def get_asset_detail(self):
        """Obtener detalle de un asset."""
        if self.created_asset_ids:
            asset_id = random.choice(self.created_asset_ids)
            self.client.get(
                f"/api/v1/assets/{asset_id}",
                headers=self.headers,
                name="Get Asset Detail"
            )
    
    # =========================================================================
    # Tasks de Scans (moderadas)
    # =========================================================================
    
    @task(5)
    @tag('scans', 'read')
    def list_scans(self):
        """Listar scans."""
        self.client.get(
            "/api/v1/scans",
            headers=self.headers,
            name="List Scans"
        )
    
    @task(3)
    @tag('scans', 'read')
    def list_scans_with_filters(self):
        """Listar scans con filtros."""
        params = {
            "scan_type": random.choice(["nmap", "nuclei"]),
            "status": random.choice(["pending", "running", "completed"]),
            "page": 1,
            "page_size": 10
        }
        
        self.client.get(
            "/api/v1/scans",
            params=params,
            headers=self.headers,
            name="List Scans (filtered)"
        )
    
    @task(2)
    @tag('scans', 'write')
    def create_scan(self):
        """Crear un nuevo scan."""
        scan_data = {
            "name": f"Load Test Scan {random.randint(1000, 9999)}",
            "scan_type": random.choice(["nmap", "nuclei"]),
            "targets": [f"192.168.{random.randint(1,254)}.0/24"],
            "options": {}
        }
        
        with self.client.post(
            "/api/v1/scans",
            json=scan_data,
            headers=self.headers,
            name="Create Scan",
            catch_response=True
        ) as response:
            if response.status_code in [200, 201]:
                data = response.json()
                if "id" in data:
                    self.created_scan_ids.append(data["id"])
                response.success()
            else:
                response.failure(f"Error: {response.status_code}")
    
    @task(2)
    @tag('scans', 'read')
    def get_scan_detail(self):
        """Obtener detalle de un scan."""
        if self.created_scan_ids:
            scan_id = random.choice(self.created_scan_ids)
            self.client.get(
                f"/api/v1/scans/{scan_id}",
                headers=self.headers,
                name="Get Scan Detail"
            )
    
    # =========================================================================
    # Tasks de Vulnerabilities (frecuentes)
    # =========================================================================
    
    @task(6)
    @tag('vulnerabilities', 'read')
    def list_vulnerabilities(self):
        """Listar vulnerabilidades."""
        self.client.get(
            "/api/v1/vulnerabilities",
            headers=self.headers,
            name="List Vulnerabilities"
        )
    
    @task(4)
    @tag('vulnerabilities', 'read')
    def list_vulnerabilities_by_severity(self):
        """Listar vulnerabilidades por severidad."""
        severity = random.choice(["critical", "high", "medium", "low"])
        
        self.client.get(
            f"/api/v1/vulnerabilities?severity={severity}",
            headers=self.headers,
            name="List Vulnerabilities (by severity)"
        )
    
    @task(3)
    @tag('vulnerabilities', 'read')
    def search_vulnerabilities(self):
        """Buscar vulnerabilidades."""
        search_terms = ["CVE-2021", "CVE-2022", "log4j", "sql", "xss"]
        
        self.client.get(
            f"/api/v1/vulnerabilities?search={random.choice(search_terms)}",
            headers=self.headers,
            name="Search Vulnerabilities"
        )
    
    # =========================================================================
    # Tasks de User/Profile (menos frecuentes)
    # =========================================================================
    
    @task(2)
    @tag('user', 'read')
    def get_current_user(self):
        """Obtener perfil del usuario actual."""
        self.client.get(
            "/api/v1/users/me",
            headers=self.headers,
            name="Get Current User"
        )
    
    @task(1)
    @tag('auth', 'read')
    def validate_token(self):
        """Validar token actual."""
        with self.client.get(
            "/api/v1/auth/validate",
            headers=self.headers,
            name="Validate Token",
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:
                response.success()


class NestSecureAdminUser(HttpUser):
    """
    Usuario administrador para pruebas de carga más intensivas.
    Simula operaciones administrativas.
    """
    
    wait_time = between(2, 8)
    weight = 1  # Menos usuarios admin que usuarios normales
    
    token = None
    
    def on_start(self):
        """Login como admin."""
        response = self.client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@nestsecure.com",
                "password": "Admin123!"
            },
            name="Admin Login"
        )
        
        if response.status_code == 200:
            self.token = response.json().get("access_token")
    
    @property
    def headers(self):
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    @task(5)
    @tag('admin', 'read')
    def get_all_users(self):
        """Obtener todos los usuarios (admin)."""
        with self.client.get(
            "/api/v1/users",
            headers=self.headers,
            name="Admin: List Users",
            catch_response=True
        ) as response:
            if response.status_code in [200, 403, 404]:
                response.success()
    
    @task(3)
    @tag('admin', 'read')
    def get_statistics(self):
        """Obtener estadísticas generales."""
        with self.client.get(
            "/api/v1/statistics",
            headers=self.headers,
            name="Admin: Get Statistics",
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
    
    @task(2)
    @tag('admin', 'read')
    def get_audit_logs(self):
        """Obtener logs de auditoría."""
        with self.client.get(
            "/api/v1/audit/logs",
            headers=self.headers,
            name="Admin: Audit Logs",
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:
                response.success()


# =============================================================================
# Event Hooks
# =============================================================================

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Se ejecuta al iniciar el test."""
    logger.info("=" * 60)
    logger.info("INICIANDO TESTS DE CARGA - NESTSECURE")
    logger.info("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Se ejecuta al finalizar el test."""
    logger.info("=" * 60)
    logger.info("TESTS DE CARGA FINALIZADOS")
    logger.info("=" * 60)
    
    # Resumen de estadísticas
    stats = environment.stats
    
    logger.info(f"Total requests: {stats.total.num_requests}")
    logger.info(f"Failed requests: {stats.total.num_failures}")
    logger.info(f"Avg response time: {stats.total.avg_response_time:.2f}ms")
    logger.info(f"Median response time: {stats.total.median_response_time}ms")
    logger.info(f"95%ile response time: {stats.total.get_response_time_percentile(0.95)}ms")
    logger.info(f"99%ile response time: {stats.total.get_response_time_percentile(0.99)}ms")
    logger.info(f"Requests/s: {stats.total.current_rps:.2f}")


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, context, exception, **kwargs):
    """Se ejecuta después de cada request."""
    if exception:
        logger.warning(f"Request failed: {name} - {exception}")
    elif response.status_code >= 500:
        logger.error(f"Server error: {name} - {response.status_code}")
