// Auth types
export interface User {
  id: string;
  email: string;
  full_name: string;
  first_name?: string;
  last_name?: string;
  avatar?: string;
  role: 'viewer' | 'analyst' | 'operator' | 'admin';
  organization_id: string;
  is_active: boolean;
  is_superuser?: boolean;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface Organization {
  id: string;
  name: string;
  created_at: string;
}

// Scan types
export type ScanType = 'discovery' | 'port_scan' | 'vulnerability' | 'full';
export type ScanStatus = 'pending' | 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface Scan {
  id: string;
  name: string;
  description?: string;
  scan_type: ScanType;
  status: ScanStatus;
  progress: number;
  targets: string[];
  port_range?: string;
  total_hosts_scanned: number;
  total_hosts_up: number;
  total_services_found: number;
  total_vulnerabilities: number;
  vuln_critical: number;
  vuln_high: number;
  vuln_medium: number;
  vuln_low: number;
  duration_seconds?: number;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  results?: Record<string, unknown>;
}

export interface CreateScanPayload {
  name: string;
  description?: string;
  scan_type: ScanType;
  targets: string[];
  port_range?: string;
  scheduled?: boolean;
  cron_expression?: string;
}

// Asset types
export type AssetType = 'server' | 'workstation' | 'network_device' | 'iot' | 'other';
export type Criticality = 'critical' | 'high' | 'medium' | 'low';
export type AssetStatus = 'active' | 'inactive' | 'maintenance';

export interface Asset {
  id: string;
  ip_address: string;
  hostname: string | null;
  name?: string; // Display name, fallback to hostname or ip_address
  type?: AssetType; // Alias for asset_type
  mac_address: string | null;
  operating_system: string | null;
  asset_type: AssetType;
  criticality: Criticality;
  status: AssetStatus;
  risk_score: number;
  is_reachable: boolean;
  tags: string[];
  description?: string;
  last_seen_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateAssetPayload {
  ip_address: string;
  hostname?: string;
  mac_address?: string;
  operating_system?: string;
  asset_type: AssetType;
  criticality: Criticality;
  tags?: string[];
  description?: string;
}

export interface Service {
  id: string;
  asset_id: string;
  port: number;
  protocol: 'tcp' | 'udp';
  service_name: string;
  version: string | null;
  state: 'open' | 'closed' | 'filtered';
  banner: string | null;
  detected_at: string;
}

// Vulnerability types
export type Severity = 'critical' | 'high' | 'medium' | 'low' | 'info';
export type VulnStatus = 'open' | 'in_progress' | 'resolved' | 'false_positive' | 'accepted';
export type VulnerabilityStatus = VulnStatus;

export interface Vulnerability {
  id: string;
  name: string;
  title?: string; // Alias for name
  description: string;
  severity: Severity;
  status: VulnStatus;
  cve_id: string | null;
  cvss_score: number | null;
  cvss_vector: string | null;
  cwe_id: string | null;
  asset_id: string;
  asset?: Asset;
  service_id?: string;
  service?: Service;
  solution: string | null;
  remediation?: string | null;
  references: string[];
  evidence?: string;
  exploit_available: boolean;
  detected_at: string;
  updated_at: string;
  resolved_at?: string | null;
  scan?: {
    id: string;
    name: string;
    type?: string;
    started_at?: string;
  };
}

// Scan Results types
export interface ScanVulnerabilitySummary {
  id: string;
  name: string;
  severity: number;
  severity_class: Severity;
  host: string;
  port: number | null;
  cve_ids: string[];
}

export interface ScanResultsSummary {
  total: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  info: number;
  hosts_scanned: number;
  hosts_up: number;
}

export interface ScanResultsResponse {
  scan_id: string;
  status: ScanStatus;
  summary: ScanResultsSummary;
  vulnerabilities: ScanVulnerabilitySummary[];
  total_vulnerabilities: number;
}

// Scan Hosts types
export interface ScanServiceSummary {
  id: string;
  port: number;
  protocol: 'tcp' | 'udp';
  service_name: string | null;
  version: string | null;
  state: 'open' | 'closed' | 'filtered';
}

export interface ScanHost {
  id: string;
  ip_address: string;
  hostname: string | null;
  operating_system: string | null;
  status: AssetStatus;
  services_count: number;
  vulnerabilities_count: number;
  vuln_critical: number;
  vuln_high: number;
  services: ScanServiceSummary[];
}

export interface ScanHostsResponse {
  scan_id: string;
  total_hosts: number;
  hosts: ScanHost[];
}

// Scan Logs types
export interface ScanLogEntry {
  timestamp: string;
  level: 'info' | 'warning' | 'error' | 'success' | 'debug';
  message: string;
}

export interface ScanLogsResponse {
  scan_id: string;
  status: ScanStatus;
  current_phase: string | null;
  logs: ScanLogEntry[];
}

export interface UpdateVulnerabilityPayload {
  status?: VulnStatus;
  assigned_to?: string;
}

// Dashboard types
export interface DashboardStats {
  assets: {
    total: number;
    active: number;
    inactive: number;
    by_type: Record<AssetType, number>;
  };
  services: {
    total: number;
    open: number;
  };
  vulnerabilities: {
    total: number;
    critical: number;
    high: number;
    medium: number;
    low: number;
    info: number;
    open: number;
    fixed: number;
  };
  scans: {
    total: number;
    running: number;
    completed: number;
  };
  risk_score: number;
}

export interface VulnerabilityTrend {
  date: string;
  critical: number;
  high: number;
  medium: number;
  low: number;
  info: number;
}

// API response types
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ApiError {
  detail: string;
  status_code: number;
}

// Health check
export interface HealthStatus {
  status: 'healthy' | 'unhealthy';
  services: {
    database: 'connected' | 'disconnected';
    gvm: 'connected' | 'disconnected';
    nmap: 'available' | 'unavailable';
    nuclei: 'available' | 'unavailable';
  };
}

// =============================================================================
// CVE Types
// =============================================================================

export type CVESeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'NONE';

export interface CVEReference {
  url: string;
  source: string;
  tags: string[];
}

export interface AffectedProduct {
  cpe: string;
  vendor?: string;
  product?: string;
  version_start?: string;
  version_end?: string;
}

export interface CVE {
  id: string;
  cve_id: string;
  description: string;
  cvss_v3_score: number | null;
  cvss_v3_vector: string | null;
  cvss_v3_severity: CVESeverity | null;
  cvss_v2_score: number | null;
  cvss_v2_vector: string | null;
  cwe_ids: string[];
  references: CVEReference[];
  exploit_available: boolean;
  in_cisa_kev: boolean;
  epss_score: number | null;
  epss_percentile: number | null;
  published_date: string;
  last_modified_date: string;
  affected_products: AffectedProduct[];
  hit_count: number;
  created_at: string;
  updated_at: string;
}

export interface CVEMinimal {
  cve_id: string;
  cvss_v3_score: number | null;
  cvss_v3_severity: CVESeverity | null;
  exploit_available: boolean;
  in_cisa_kev: boolean;
}

export interface CVESearchParams {
  search?: string;
  severity?: CVESeverity;
  min_cvss?: number;
  max_cvss?: number;
  has_exploit?: boolean;
  in_cisa_kev?: boolean;
  vendor?: string;
  product?: string;
  published_after?: string;
  published_before?: string;
  page?: number;
  page_size?: number;
}

export interface CVEStats {
  total_cves: number;
  by_severity: Record<CVESeverity, number>;
  with_exploits: number;
  in_kev: number;
  avg_cvss: number | null;
  last_sync: string | null;
  sync_status: 'idle' | 'running' | 'failed';
}

export interface CVESyncRequest {
  days_back?: number;
  full_sync?: boolean;
}

export interface CVESyncStatus {
  status: 'idle' | 'running' | 'completed' | 'failed';
  last_sync: string | null;
  cves_synced: number;
  errors: string[];
  progress?: number;
}

export interface CVELookupRequest {
  cve_ids: string[];
}

export interface CVELookupResponse {
  found: CVE[];
  not_found: string[];
}
