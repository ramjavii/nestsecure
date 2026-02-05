import { useAuthStore } from './stores/auth-store';
import type {
  LoginCredentials,
  LoginResponse,
  User,
  Scan,
  CreateScanPayload,
  Asset,
  CreateAssetPayload,
  Vulnerability,
  UpdateVulnerabilityPayload,
  DashboardStats,
  VulnerabilityTrend,
  HealthStatus,
  Service,
  ScanResultsResponse,
  ScanHostsResponse,
  ScanLogsResponse,
  CVE,
  CVEMinimal,
  CVESearchParams,
  CVEStats,
  CVESyncRequest,
  CVESyncStatus,
  CVELookupResponse,
  PaginatedResponse,
} from '@/types';

/**
 * Obtener la URL base de la API según el entorno
 * - En el servidor (SSR): usar la URL interna de Docker (backend:8000)
 * - En el cliente (browser): usar localhost o la URL pública
 */
function getApiBaseUrl(): string {
  // En el cliente (browser)
  if (typeof window !== 'undefined') {
    // Usar la URL del browser (configurada en env o localhost)
    return process.env.NEXT_PUBLIC_BROWSER_API_URL || 
           process.env.NEXT_PUBLIC_API_URL || 
           'http://localhost:8000/api/v1';
  }
  
  // En el servidor (SSR/API routes) - usar URL interna de Docker
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
}

const API_BASE_URL = getApiBaseUrl();

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const { accessToken, refreshToken, setTokens, logout } = useAuthStore.getState();

    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (accessToken) {
      (headers as Record<string, string>)['Authorization'] = `Bearer ${accessToken}`;
    }

    let response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers,
    });

    // Handle 401 - try to refresh token
    if (response.status === 401 && refreshToken) {
      try {
        const refreshResponse = await fetch(`${this.baseUrl}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });

        if (refreshResponse.ok) {
          const tokens: LoginResponse = await refreshResponse.json();
          setTokens(tokens.access_token, tokens.refresh_token);
          
          // Retry original request with new token
          (headers as Record<string, string>)['Authorization'] = `Bearer ${tokens.access_token}`;
          response = await fetch(`${this.baseUrl}${endpoint}`, {
            ...options,
            headers,
          });
        } else {
          logout();
          if (typeof window !== 'undefined') {
            window.location.href = '/login';
          }
          throw new Error('Session expired');
        }
      } catch {
        logout();
        if (typeof window !== 'undefined') {
          window.location.href = '/login';
        }
        throw new Error('Session expired');
      }
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // Auth
  async login(credentials: LoginCredentials): Promise<LoginResponse> {
    // El backend tiene /auth/login/json para JSON body
    return this.request<LoginResponse>('/auth/login/json', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });
  }

  async refreshToken(refreshToken: string): Promise<LoginResponse> {
    return this.request<LoginResponse>('/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  }

  async getMe(): Promise<User> {
    return this.request<User>('/auth/me');
  }

  // Dashboard
  async getDashboardStats(): Promise<DashboardStats> {
    return this.request<DashboardStats>('/dashboard/stats');
  }

  async getRecentScans(): Promise<Scan[]> {
    return this.request<Scan[]>('/dashboard/recent-scans');
  }

  async getRecentAssets(): Promise<Asset[]> {
    return this.request<Asset[]>('/dashboard/recent-assets');
  }

  async getVulnerabilityTrend(): Promise<VulnerabilityTrend[]> {
    return this.request<VulnerabilityTrend[]>('/dashboard/vulnerability-trend');
  }

  // Scans
  async getScans(params?: { status?: string; type?: string; search?: string; page?: number; page_size?: number }): Promise<{ items: Scan[]; total: number; page: number; pages: number }> {
    const searchParams = new URLSearchParams();
    if (params?.status) searchParams.append('status', params.status);
    if (params?.type) searchParams.append('scan_type', params.type);
    if (params?.search) searchParams.append('search', params.search);
    if (params?.page) searchParams.append('page', params.page.toString());
    if (params?.page_size) searchParams.append('page_size', params.page_size.toString());
    
    const query = searchParams.toString();
    return this.request<{ items: Scan[]; total: number; page: number; pages: number }>(`/scans${query ? `?${query}` : ''}`);
  }

  async getScan(id: string): Promise<Scan> {
    return this.request<Scan>(`/scans/${id}`);
  }

  async createScan(payload: CreateScanPayload): Promise<Scan> {
    return this.request<Scan>('/scans', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async stopScan(id: string): Promise<Scan> {
    return this.request<Scan>(`/scans/${id}/stop`, {
      method: 'POST',
    });
  }

  async deleteScan(id: string): Promise<void> {
    return this.request<void>(`/scans/${id}`, {
      method: 'DELETE',
    });
  }

  async getScanResults(id: string, params?: { page?: number; page_size?: number; min_severity?: number }): Promise<ScanResultsResponse> {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.append('page', params.page.toString());
    if (params?.page_size) searchParams.append('page_size', params.page_size.toString());
    if (params?.min_severity) searchParams.append('min_severity', params.min_severity.toString());
    
    const query = searchParams.toString();
    return this.request<ScanResultsResponse>(`/scans/${id}/results${query ? `?${query}` : ''}`);
  }

  async getScanHosts(id: string): Promise<ScanHostsResponse> {
    return this.request<ScanHostsResponse>(`/scans/${id}/hosts`);
  }

  async getScanLogs(id: string): Promise<ScanLogsResponse> {
    return this.request<ScanLogsResponse>(`/scans/${id}/logs`);
  }

  // Assets
  async getAssets(params?: { 
    type?: string; 
    criticality?: string; 
    status?: string;
    search?: string;
    page?: number;
    page_size?: number;
  }): Promise<{ items: Asset[]; total: number; page: number; pages: number }> {
    const searchParams = new URLSearchParams();
    if (params?.type) searchParams.append('type', params.type);
    if (params?.criticality) searchParams.append('criticality', params.criticality);
    if (params?.status) searchParams.append('status', params.status);
    if (params?.search) searchParams.append('search', params.search);
    if (params?.page) searchParams.append('page', params.page.toString());
    if (params?.page_size) searchParams.append('page_size', params.page_size.toString());
    
    const query = searchParams.toString();
    return this.request<{ items: Asset[]; total: number; page: number; pages: number }>(`/assets${query ? `?${query}` : ''}`);
  }

  async getAsset(id: string): Promise<Asset> {
    return this.request<Asset>(`/assets/${id}`);
  }

  async createAsset(payload: CreateAssetPayload): Promise<Asset> {
    return this.request<Asset>('/assets', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async updateAsset(id: string, payload: Partial<CreateAssetPayload>): Promise<Asset> {
    return this.request<Asset>(`/assets/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
  }

  async deleteAsset(id: string): Promise<void> {
    return this.request<void>(`/assets/${id}`, {
      method: 'DELETE',
    });
  }

  async getAssetServices(id: string): Promise<Service[]> {
    return this.request<Service[]>(`/assets/${id}/services`);
  }

  async getAssetVulnerabilities(id: string): Promise<Vulnerability[]> {
    return this.request<Vulnerability[]>(`/assets/${id}/vulnerabilities`);
  }

  async getAssetScans(id: string): Promise<Scan[]> {
    return this.request<Scan[]>(`/assets/${id}/scans`);
  }

  // Vulnerabilities
  async getVulnerabilities(params?: {
    severity?: string;
    status?: string;
    search?: string;
    sort_by?: string;
    sort_order?: 'asc' | 'desc';
  }): Promise<Vulnerability[]> {
    const searchParams = new URLSearchParams();
    if (params?.severity) searchParams.append('severity', params.severity);
    if (params?.status) searchParams.append('status', params.status);
    if (params?.search) searchParams.append('search', params.search);
    if (params?.sort_by) searchParams.append('sort_by', params.sort_by);
    if (params?.sort_order) searchParams.append('sort_order', params.sort_order);
    
    const query = searchParams.toString();
    return this.request<Vulnerability[]>(`/vulnerabilities${query ? `?${query}` : ''}`);
  }

  async getVulnerability(id: string): Promise<Vulnerability> {
    return this.request<Vulnerability>(`/vulnerabilities/${id}`);
  }

  async updateVulnerability(id: string, payload: UpdateVulnerabilityPayload): Promise<Vulnerability> {
    return this.request<Vulnerability>(`/vulnerabilities/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
  }

  // Users
  async getUsers(): Promise<User[]> {
    return this.request<User[]>('/users');
  }

  // Health
  async getHealthStatus(): Promise<HealthStatus> {
    return this.request<HealthStatus>('/health/services');
  }

  // ==========================================================================
  // CVE Endpoints
  // ==========================================================================

  /**
   * Search CVEs with filters and pagination
   */
  async searchCVEs(params?: CVESearchParams): Promise<PaginatedResponse<CVEMinimal>> {
    const searchParams = new URLSearchParams();
    
    if (params?.search) searchParams.append('search', params.search);
    if (params?.severity) searchParams.append('severity', params.severity);
    if (params?.min_cvss !== undefined) searchParams.append('min_cvss', params.min_cvss.toString());
    if (params?.max_cvss !== undefined) searchParams.append('max_cvss', params.max_cvss.toString());
    if (params?.has_exploit !== undefined) searchParams.append('has_exploit', params.has_exploit.toString());
    if (params?.in_cisa_kev !== undefined) searchParams.append('in_cisa_kev', params.in_cisa_kev.toString());
    if (params?.vendor) searchParams.append('vendor', params.vendor);
    if (params?.product) searchParams.append('product', params.product);
    if (params?.published_after) searchParams.append('published_after', params.published_after);
    if (params?.published_before) searchParams.append('published_before', params.published_before);
    if (params?.page) searchParams.append('page', params.page.toString());
    if (params?.page_size) searchParams.append('page_size', params.page_size.toString());
    
    const query = searchParams.toString();
    return this.request<PaginatedResponse<CVEMinimal>>(`/cve${query ? `?${query}` : ''}`);
  }

  /**
   * Get a specific CVE by ID (e.g., CVE-2024-1234)
   */
  async getCVE(cveId: string): Promise<CVE> {
    return this.request<CVE>(`/cve/${encodeURIComponent(cveId)}`);
  }

  /**
   * Lookup multiple CVEs at once
   */
  async lookupCVEs(cveIds: string[]): Promise<CVELookupResponse> {
    return this.request<CVELookupResponse>('/cve/lookup', {
      method: 'POST',
      body: JSON.stringify({ cve_ids: cveIds }),
    });
  }

  /**
   * Get CVE statistics
   */
  async getCVEStats(): Promise<CVEStats> {
    return this.request<CVEStats>('/cve/stats');
  }

  /**
   * Trigger CVE sync from NVD (Admin only)
   */
  async syncCVEs(params?: CVESyncRequest): Promise<{ message: string; task_id: string }> {
    return this.request<{ message: string; task_id: string }>('/cve/sync', {
      method: 'POST',
      body: JSON.stringify(params || {}),
    });
  }

  /**
   * Get CVE sync status
   */
  async getCVESyncStatus(): Promise<CVESyncStatus> {
    return this.request<CVESyncStatus>('/cve/sync/status');
  }

  /**
   * Get CVEs related to a specific vulnerability
   */
  async getVulnerabilityCVE(vulnerabilityId: string): Promise<CVE | null> {
    try {
      return await this.request<CVE>(`/vulnerabilities/${vulnerabilityId}/cve`);
    } catch {
      return null;
    }
  }

  /**
   * Get trending CVEs (most accessed/critical)
   */
  async getTrendingCVEs(limit: number = 10): Promise<CVEMinimal[]> {
    return this.request<CVEMinimal[]>(`/cve/trending?limit=${limit}`);
  }

  /**
   * Get CVEs in CISA KEV (Known Exploited Vulnerabilities)
   */
  async getKEVCVEs(params?: { page?: number; page_size?: number }): Promise<PaginatedResponse<CVEMinimal>> {
    const searchParams = new URLSearchParams();
    searchParams.append('in_cisa_kev', 'true');
    if (params?.page) searchParams.append('page', params.page.toString());
    if (params?.page_size) searchParams.append('page_size', params.page_size.toString());
    
    return this.request<PaginatedResponse<CVEMinimal>>(`/cve?${searchParams.toString()}`);
  }

  /**
   * Get CVEs with known exploits
   */
  async getExploitableCVEs(params?: { page?: number; page_size?: number }): Promise<PaginatedResponse<CVEMinimal>> {
    const searchParams = new URLSearchParams();
    searchParams.append('has_exploit', 'true');
    if (params?.page) searchParams.append('page', params.page.toString());
    if (params?.page_size) searchParams.append('page_size', params.page_size.toString());
    
    return this.request<PaginatedResponse<CVEMinimal>>(`/cve?${searchParams.toString()}`);
  }

  // ==========================================================================
  // Network Validation
  // ==========================================================================

  /**
   * Validate a scan target (IP or CIDR)
   * Only private networks (RFC 1918) are allowed
   */
  async validateTarget(target: string): Promise<{
    valid: boolean;
    target: string;
    type: 'ip' | 'cidr' | null;
    error: string | null;
    info: Record<string, unknown> | null;
  }> {
    return this.request('/network/validate', {
      method: 'POST',
      body: JSON.stringify({ target }),
    });
  }

  /**
   * Validate multiple scan targets at once
   */
  async validateMultipleTargets(targets: string[]): Promise<{
    valid: boolean;
    targets: Array<{
      valid: boolean;
      target: string;
      type: 'ip' | 'cidr' | null;
      error: string | null;
    }>;
    total: number;
    valid_count: number;
    invalid_count: number;
  }> {
    return this.request('/network/validate-multiple', {
      method: 'POST',
      body: JSON.stringify({ targets }),
    });
  }

  /**
   * Get information about a CIDR network
   */
  async getNetworkInfo(cidr: string): Promise<{
    network: string;
    netmask: string;
    broadcast: string;
    num_hosts: number;
    first_host: string | null;
    last_host: string | null;
    prefix_length: number;
    is_private: boolean;
  }> {
    return this.request(`/network/info/${encodeURIComponent(cidr)}`);
  }

  /**
   * Get allowed private IP ranges for scanning
   */
  async getPrivateRanges(): Promise<{
    description: string;
    ranges: Array<{
      name: string;
      cidr: string;
      range: string;
      hosts: number;
    }>;
  }> {
    return this.request('/network/private-ranges');
  }

  /**
   * Check if an IP is private (can be scanned)
   */
  async checkIP(ip: string): Promise<{
    ip: string;
    is_private: boolean;
    can_scan: boolean;
    details: Record<string, unknown>;
  }> {
    return this.request(`/network/check-ip/${encodeURIComponent(ip)}`);
  }

  // ===========================================================================
  // CORRELATION API
  // ===========================================================================

  /**
   * Correlate a service with CVEs from NVD
   */
  async correlateService(
    serviceId: string,
    options?: { autoCreateVuln?: boolean; maxCves?: number }
  ): Promise<{
    service_id: string;
    cpe: string | null;
    cpe_confidence: number;
    cves_found: number;
    vulnerabilities_created: number;
    status: string;
    cves: string[];
    error: string | null;
  }> {
    return this.request(`/correlation/services/${serviceId}/correlate`, {
      method: 'POST',
      body: JSON.stringify({
        auto_create_vuln: options?.autoCreateVuln ?? true,
        max_cves: options?.maxCves ?? 10,
      }),
    });
  }

  /**
   * Correlate all services of a scan with CVEs
   */
  async correlateScan(
    scanId: string,
    options?: { autoCreate?: boolean; maxCvesPerService?: number }
  ): Promise<{
    scan_id: string;
    services_processed: number;
    services_with_cpe: number;
    cves_found: number;
    vulnerabilities_created: number;
    status: string;
    services: Array<{
      service_id: string;
      cpe: string | null;
      cves_found: number;
      status: string;
    }>;
  }> {
    const params = new URLSearchParams();
    if (options?.autoCreate !== undefined) {
      params.set('auto_create', String(options.autoCreate));
    }
    if (options?.maxCvesPerService) {
      params.set('max_cves_per_service', String(options.maxCvesPerService));
    }
    
    return this.request(`/correlation/scans/${scanId}/correlate?${params}`, {
      method: 'POST',
    });
  }

  /**
   * Correlate all services of an asset with CVEs
   */
  async correlateAsset(
    assetId: string,
    autoCreate: boolean = true
  ): Promise<{
    asset_id: string;
    services_processed: number;
    cves_found: number;
    vulnerabilities_created: number;
    services: Array<{
      service_id: string;
      cpe: string | null;
      cves_found: number;
    }>;
  }> {
    return this.request(
      `/correlation/assets/${assetId}/correlate?auto_create=${autoCreate}`,
      { method: 'POST' }
    );
  }

  /**
   * Get CPE information for a service
   */
  async getServiceCPE(serviceId: string): Promise<{
    service_id: string;
    port: number;
    protocol: string;
    service_name: string | null;
    product: string | null;
    version: string | null;
    cpe: string | null;
    cpe_source: string;
    confidence: number;
  }> {
    return this.request(`/correlation/cpe/${serviceId}`);
  }

  // ==========================================================================
  // NUCLEI SCANNING API
  // ==========================================================================

  /**
   * Start a Nuclei vulnerability scan
   */
  async startNucleiScan(params: {
    target: string;
    profile?: string;
    scan_name?: string;
    timeout?: number;
    tags?: string[];
    severities?: string[];
  }): Promise<{
    task_id: string;
    scan_id: string;
    status: string;
    target: string;
    profile: string;
    message: string;
  }> {
    return this.request('/nuclei/scan', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  }

  /**
   * Get Nuclei scan status
   */
  async getNucleiScanStatus(taskId: string): Promise<{
    task_id: string;
    scan_id: string | null;
    status: string;
    target: string;
    profile: string | null;
    started_at: string | null;
    completed_at: string | null;
    total_findings: number | null;
    unique_cves: string[];
    summary: {
      critical: number;
      high: number;
      medium: number;
      low: number;
      info: number;
      total: number;
    } | null;
    error_message: string | null;
  }> {
    return this.request(`/nuclei/scan/${taskId}`);
  }

  /**
   * Get Nuclei scan results
   */
  async getNucleiScanResults(
    taskId: string,
    options?: {
      page?: number;
      page_size?: number;
      severity?: string;
    }
  ): Promise<{
    task_id: string;
    scan_id: string | null;
    status: string;
    target: string;
    profile: string | null;
    started_at: string | null;
    completed_at: string | null;
    summary: {
      critical: number;
      high: number;
      medium: number;
      low: number;
      info: number;
      total: number;
    };
    findings: Array<{
      template_id: string;
      template_name: string;
      severity: string;
      host: string;
      matched_at: string;
      ip: string | null;
      timestamp: string | null;
      cve: string | null;
      cvss: number | null;
      cwe_id: string | null;
      description: string | null;
      references: string[] | null;
      extracted: string[] | null;
      matcher_name: string | null;
    }>;
    total_findings: number;
    unique_cves: string[];
    page: number;
    page_size: number;
    total_pages: number;
  }> {
    const params = new URLSearchParams();
    if (options?.page) params.set('page', String(options.page));
    if (options?.page_size) params.set('page_size', String(options.page_size));
    if (options?.severity) params.set('severity', options.severity);

    const query = params.toString();
    return this.request(`/nuclei/scan/${taskId}/results${query ? `?${query}` : ''}`);
  }

  /**
   * Get available Nuclei scan profiles
   */
  async getNucleiProfiles(): Promise<{
    profiles: Array<{
      name: string;
      display_name: string;
      description: string;
      estimated_time: string;
      tags: string[];
      severities: string[];
      templates_count: number | null;
    }>;
  }> {
    return this.request('/nuclei/profiles');
  }

  /**
   * Quick Nuclei scan (critical vulnerabilities only)
   */
  async nucleiQuickScan(target: string, scanName?: string): Promise<{
    task_id: string;
    scan_id: string;
    status: string;
    target: string;
    profile: string;
    message: string;
  }> {
    return this.request('/nuclei/quick', {
      method: 'POST',
      body: JSON.stringify({ target, scan_name: scanName }),
    });
  }

  /**
   * CVE-focused Nuclei scan
   */
  async nucleiCVEScan(
    target: string,
    cves?: string[],
    scanName?: string
  ): Promise<{
    task_id: string;
    scan_id: string;
    status: string;
    target: string;
    profile: string;
    message: string;
  }> {
    return this.request('/nuclei/cve', {
      method: 'POST',
      body: JSON.stringify({ target, cves, scan_name: scanName }),
    });
  }

  /**
   * Web vulnerability Nuclei scan
   */
  async nucleiWebScan(target: string, scanName?: string): Promise<{
    task_id: string;
    scan_id: string;
    status: string;
    target: string;
    profile: string;
    message: string;
  }> {
    return this.request('/nuclei/web', {
      method: 'POST',
      body: JSON.stringify({ target, scan_name: scanName }),
    });
  }

  /**
   * Cancel a running Nuclei scan
   */
  async cancelNucleiScan(taskId: string): Promise<{
    task_id: string;
    status: string;
    message: string;
  }> {
    return this.request(`/nuclei/scan/${taskId}/cancel`, {
      method: 'POST',
    });
  }

  /**
   * Get Nuclei scanner health/status
   */
  async getNucleiHealth(): Promise<{
    status: string;
    nuclei_installed: boolean;
    nuclei_version: string | null;
    templates_path: string | null;
    templates_count: number | null;
    last_updated: string | null;
  }> {
    return this.request('/nuclei/health');
  }
}

export const api = new ApiClient(API_BASE_URL);
