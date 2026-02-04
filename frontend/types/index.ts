// Auth types
export interface User {
  id: string;
  email: string;
  full_name: string;
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
export type ScanType = 'discovery' | 'port_scan' | 'service_scan' | 'vulnerability' | 'full';
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
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
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
export type VulnStatus = 'open' | 'acknowledged' | 'in_progress' | 'fixed' | 'false_positive';

export interface Vulnerability {
  id: string;
  name: string;
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
  references: string[];
  evidence?: string;
  exploit_available: boolean;
  detected_at: string;
  updated_at: string;
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
  data: T[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
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
