/**
 * Nuclei Scan Button Component
 * 
 * Button with dialog for initiating Nuclei vulnerability scans.
 * Supports multiple scan profiles and displays real-time progress.
 */

'use client';

import { useState, useEffect } from 'react';
import { 
  Shield, 
  Zap, 
  Bug, 
  Globe, 
  Loader2, 
  CheckCircle, 
  XCircle,
  AlertTriangle,
  ChevronDown,
  Play,
  Square,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  useStartNucleiScan,
  useNucleiQuickScan,
  useNucleiCVEScan,
  useNucleiWebScan,
  useNucleiScanStatus,
  useCancelNucleiScan,
  useNucleiProfiles,
  getSeverityColor,
  getScanStatusColor,
  formatScanDuration,
  getProfileDisplayName,
  type NucleiSeveritySummary,
} from '@/hooks/use-nuclei';

// =============================================================================
// TYPES
// =============================================================================

interface NucleiScanButtonProps {
  target?: string;
  assetId?: string;
  variant?: 'default' | 'outline' | 'ghost' | 'secondary';
  size?: 'default' | 'sm' | 'lg' | 'icon';
  className?: string;
}

interface ScanProgress {
  taskId: string;
  status: string;
  target: string;
  profile: string;
  startedAt: string | null;
  completedAt: string | null;
  summary: NucleiSeveritySummary | null;
  totalFindings: number;
  uniqueCves: string[];
  errorMessage: string | null;
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export function NucleiScanButton({
  target: initialTarget = '',
  assetId,
  variant = 'default',
  size = 'default',
  className,
}: NucleiScanButtonProps) {
  const [open, setOpen] = useState(false);
  const [target, setTarget] = useState(initialTarget);
  const [scanName, setScanName] = useState('');
  const [selectedProfile, setSelectedProfile] = useState('quick');
  const [activeScan, setActiveScan] = useState<ScanProgress | null>(null);

  // Queries
  const { data: profilesData } = useNucleiProfiles();
  
  // Mutations
  const startScan = useStartNucleiScan();
  const quickScan = useNucleiQuickScan();
  const cveScan = useNucleiCVEScan();
  const webScan = useNucleiWebScan();
  const cancelScan = useCancelNucleiScan();

  // Poll scan status when active
  const { data: scanStatus } = useNucleiScanStatus(activeScan?.taskId ?? null, {
    enabled: !!activeScan && !['completed', 'failed', 'cancelled'].includes(activeScan.status),
  });

  // Update active scan when status changes
  useEffect(() => {
    if (scanStatus && activeScan) {
      setActiveScan({
        taskId: scanStatus.task_id,
        status: scanStatus.status,
        target: scanStatus.target,
        profile: scanStatus.profile ?? selectedProfile,
        startedAt: scanStatus.started_at,
        completedAt: scanStatus.completed_at,
        summary: scanStatus.summary,
        totalFindings: scanStatus.total_findings ?? 0,
        uniqueCves: scanStatus.unique_cves ?? [],
        errorMessage: scanStatus.error_message,
      });
    }
  }, [scanStatus, activeScan, selectedProfile]);

  // Update target when prop changes
  useEffect(() => {
    setTarget(initialTarget);
  }, [initialTarget]);

  const handleStartScan = async () => {
    if (!target) return;

    try {
      let result;
      
      switch (selectedProfile) {
        case 'quick':
          result = await quickScan.mutateAsync({ target, scanName: scanName || undefined });
          break;
        case 'cves':
          result = await cveScan.mutateAsync({ target, scanName: scanName || undefined });
          break;
        case 'web':
          result = await webScan.mutateAsync({ target, scanName: scanName || undefined });
          break;
        default:
          result = await startScan.mutateAsync({
            target,
            profile: selectedProfile,
            scan_name: scanName || undefined,
          });
      }

      setActiveScan({
        taskId: result.task_id,
        status: result.status,
        target: result.target,
        profile: result.profile,
        startedAt: null,
        completedAt: null,
        summary: null,
        totalFindings: 0,
        uniqueCves: [],
        errorMessage: null,
      });
    } catch {
      // Error is handled by mutation
    }
  };

  const handleCancel = async () => {
    if (activeScan?.taskId) {
      try {
        await cancelScan.mutateAsync(activeScan.taskId);
        setActiveScan((prev) => prev ? { ...prev, status: 'cancelled' } : null);
      } catch {
        // Error handled by mutation
      }
    }
  };

  const handleClose = () => {
    setOpen(false);
    // Reset state after dialog closes
    setTimeout(() => {
      setActiveScan(null);
      setScanName('');
    }, 300);
  };

  const isLoading = startScan.isPending || quickScan.isPending || cveScan.isPending || webScan.isPending;
  const isScanActive = activeScan && !['completed', 'failed', 'cancelled'].includes(activeScan.status);

  const profiles = profilesData?.profiles ?? [
    { name: 'quick', display_name: 'Quick Scan', description: 'Critical vulnerabilities only (~5 min)', estimated_time: '5 min' },
    { name: 'standard', display_name: 'Standard Scan', description: 'Most templates (~30 min)', estimated_time: '30 min' },
    { name: 'cves', display_name: 'CVE Detection', description: 'Known CVEs only', estimated_time: '15 min' },
    { name: 'web', display_name: 'Web Vulnerabilities', description: 'XSS, SQLi, SSRF, etc.', estimated_time: '20 min' },
    { name: 'full', display_name: 'Full Scan', description: 'All templates (~2+ hours)', estimated_time: '2+ hours' },
  ];

  const getProfileIcon = (name: string) => {
    switch (name) {
      case 'quick': return <Zap className="h-4 w-4" />;
      case 'cves': return <Bug className="h-4 w-4" />;
      case 'web': return <Globe className="h-4 w-4" />;
      case 'full': return <Shield className="h-4 w-4" />;
      default: return <Shield className="h-4 w-4" />;
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant={variant} size={size} className={className}>
          <Shield className="h-4 w-4 mr-2" />
          Nuclei Scan
        </Button>
      </DialogTrigger>

      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Nuclei Vulnerability Scan
          </DialogTitle>
          <DialogDescription>
            Scan targets for known vulnerabilities using Nuclei templates.
          </DialogDescription>
        </DialogHeader>

        {!activeScan ? (
          // SCAN CONFIGURATION
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="target">Target URL or IP</Label>
              <Input
                id="target"
                placeholder="https://example.com or 192.168.1.1"
                value={target}
                onChange={(e) => setTarget(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="scanName">Scan Name (optional)</Label>
              <Input
                id="scanName"
                placeholder="My vulnerability scan"
                value={scanName}
                onChange={(e) => setScanName(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label>Scan Profile</Label>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" className="w-full justify-between">
                    <span className="flex items-center gap-2">
                      {getProfileIcon(selectedProfile)}
                      {getProfileDisplayName(selectedProfile)}
                    </span>
                    <ChevronDown className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent className="w-full">
                  <DropdownMenuLabel>Select Profile</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  {profiles.map((profile) => (
                    <DropdownMenuItem
                      key={profile.name}
                      onClick={() => setSelectedProfile(profile.name)}
                    >
                      <span className="flex items-center gap-2">
                        {getProfileIcon(profile.name)}
                        <span>
                          <div>{profile.display_name}</div>
                          <div className="text-xs text-muted-foreground">
                            {profile.description} ({profile.estimated_time})
                          </div>
                        </span>
                      </span>
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        ) : (
          // SCAN PROGRESS
          <ScanProgressView 
            scan={activeScan}
            onCancel={handleCancel}
            isCancelling={cancelScan.isPending}
          />
        )}

        <DialogFooter>
          {!activeScan ? (
            <>
              <Button variant="outline" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button
                onClick={handleStartScan}
                disabled={!target || isLoading}
              >
                {isLoading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Starting...
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4 mr-2" />
                    Start Scan
                  </>
                )}
              </Button>
            </>
          ) : (
            <>
              {isScanActive ? (
                <Button
                  variant="destructive"
                  onClick={handleCancel}
                  disabled={cancelScan.isPending}
                >
                  {cancelScan.isPending ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <Square className="h-4 w-4 mr-2" />
                  )}
                  Cancel Scan
                </Button>
              ) : (
                <Button onClick={handleClose}>
                  Close
                </Button>
              )}
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// =============================================================================
// SUB-COMPONENTS
// =============================================================================

function ScanProgressView({
  scan,
  onCancel,
  isCancelling,
}: {
  scan: ScanProgress;
  onCancel: () => void;
  isCancelling: boolean;
}) {
  const isRunning = ['queued', 'pending', 'running'].includes(scan.status);
  const isCompleted = scan.status === 'completed';
  const isFailed = scan.status === 'failed';

  return (
    <div className="space-y-4 py-4">
      {/* Status Badge */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {isRunning && <Loader2 className="h-5 w-5 animate-spin text-blue-500" />}
          {isCompleted && <CheckCircle className="h-5 w-5 text-green-500" />}
          {isFailed && <XCircle className="h-5 w-5 text-red-500" />}
          <Badge className={getScanStatusColor(scan.status)}>
            {scan.status.toUpperCase()}
          </Badge>
        </div>
        <Badge variant="outline">{getProfileDisplayName(scan.profile)}</Badge>
      </div>

      {/* Progress Bar (for running scans) */}
      {isRunning && (
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Scanning...</span>
            <span className="text-muted-foreground">
              {formatScanDuration(scan.startedAt, null)}
            </span>
          </div>
          <Progress value={undefined} className="h-2" />
        </div>
      )}

      {/* Target Info */}
      <Card>
        <CardHeader className="py-3">
          <CardTitle className="text-sm font-medium">Target</CardTitle>
        </CardHeader>
        <CardContent className="py-2">
          <code className="text-sm bg-muted px-2 py-1 rounded">{scan.target}</code>
        </CardContent>
      </Card>

      {/* Error Message */}
      {scan.errorMessage && (
        <div className="flex items-start gap-2 p-3 bg-red-50 dark:bg-red-950 rounded-lg">
          <AlertTriangle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-red-700 dark:text-red-300">
            {scan.errorMessage}
          </div>
        </div>
      )}

      {/* Results Summary */}
      {isCompleted && scan.summary && (
        <div className="space-y-3">
          <h4 className="font-medium text-sm">Findings Summary</h4>
          <div className="grid grid-cols-5 gap-2">
            <SeverityCard label="Critical" value={scan.summary.critical} severity="critical" />
            <SeverityCard label="High" value={scan.summary.high} severity="high" />
            <SeverityCard label="Medium" value={scan.summary.medium} severity="medium" />
            <SeverityCard label="Low" value={scan.summary.low} severity="low" />
            <SeverityCard label="Info" value={scan.summary.info} severity="info" />
          </div>

          {/* Duration */}
          <div className="text-sm text-muted-foreground">
            Duration: {formatScanDuration(scan.startedAt, scan.completedAt)}
          </div>

          {/* CVEs Found */}
          {scan.uniqueCves.length > 0 && (
            <div className="space-y-2">
              <h4 className="font-medium text-sm">CVEs Detected ({scan.uniqueCves.length})</h4>
              <div className="flex flex-wrap gap-1">
                {scan.uniqueCves.slice(0, 10).map((cve) => (
                  <Badge key={cve} variant="secondary" className="text-xs">
                    {cve}
                  </Badge>
                ))}
                {scan.uniqueCves.length > 10 && (
                  <Badge variant="outline" className="text-xs">
                    +{scan.uniqueCves.length - 10} more
                  </Badge>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function SeverityCard({
  label,
  value,
  severity,
}: {
  label: string;
  value: number;
  severity: string;
}) {
  return (
    <div className={`text-center p-2 rounded-lg ${getSeverityColor(severity)}`}>
      <div className="text-lg font-bold">{value}</div>
      <div className="text-xs opacity-80">{label}</div>
    </div>
  );
}

export default NucleiScanButton;
