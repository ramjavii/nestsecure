'use client';

/**
 * Botón para correlacionar servicios con CVEs
 * 
 * Puede usarse para:
 * - Correlacionar un servicio individual
 * - Correlacionar todos los servicios de un scan
 * - Correlacionar todos los servicios de un asset
 */

import { useState } from 'react';
import { Loader2, Link2, AlertCircle, CheckCircle2 } from 'lucide-react';
import { Button, type ButtonProps } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import {
  useCorrelateService,
  useCorrelateScan,
  useCorrelateAsset,
  type CorrelationResult,
  type ScanCorrelationResult,
} from '@/hooks/use-correlation';

// ===========================================================================
// TYPES
// ===========================================================================

type CorrelationType = 'service' | 'scan' | 'asset';

interface CorrelateButtonProps extends Omit<ButtonProps, 'onClick'> {
  /** Tipo de correlación */
  type: CorrelationType;
  /** ID del recurso (service_id, scan_id, asset_id) */
  resourceId: string;
  /** Nombre para mostrar (opcional) */
  resourceName?: string;
  /** Callback cuando completa */
  onComplete?: (result: CorrelationResult | ScanCorrelationResult) => void;
}

// ===========================================================================
// COMPONENT
// ===========================================================================

export function CorrelateButton({
  type,
  resourceId,
  resourceName,
  onComplete,
  ...buttonProps
}: CorrelateButtonProps) {
  const [showDialog, setShowDialog] = useState(false);
  const [autoCreate, setAutoCreate] = useState(true);
  const [result, setResult] = useState<CorrelationResult | ScanCorrelationResult | null>(null);
  
  const correlateService = useCorrelateService();
  const correlateScan = useCorrelateScan();
  const correlateAsset = useCorrelateAsset();
  
  const isLoading = 
    correlateService.isPending || 
    correlateScan.isPending || 
    correlateAsset.isPending;
  
  const handleCorrelate = async () => {
    try {
      let res;
      
      switch (type) {
        case 'service':
          res = await correlateService.mutateAsync({
            serviceId: resourceId,
            autoCreateVuln: autoCreate,
          });
          break;
        case 'scan':
          res = await correlateScan.mutateAsync({
            scanId: resourceId,
            autoCreate,
          });
          break;
        case 'asset':
          res = await correlateAsset.mutateAsync({
            assetId: resourceId,
            autoCreate,
          });
          break;
      }
      
      setResult(res);
      onComplete?.(res);
    } catch {
      // Error handled by mutation
    }
  };
  
  const getTypeLabel = () => {
    switch (type) {
      case 'service':
        return 'servicio';
      case 'scan':
        return 'scan';
      case 'asset':
        return 'asset';
    }
  };
  
  return (
    <>
      <Button
        variant="outline"
        size="sm"
        onClick={() => setShowDialog(true)}
        disabled={isLoading}
        {...buttonProps}
      >
        {isLoading ? (
          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
        ) : (
          <Link2 className="h-4 w-4 mr-2" />
        )}
        Correlacionar CVEs
      </Button>
      
      <Dialog open={showDialog} onOpenChange={setShowDialog}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Correlacionar con CVEs</DialogTitle>
            <DialogDescription>
              Buscar vulnerabilidades conocidas (CVEs) para{' '}
              {type === 'scan' 
                ? 'todos los servicios detectados en este scan'
                : type === 'asset'
                ? 'todos los servicios de este asset'
                : 'este servicio'
              }
              {resourceName && ` (${resourceName})`}.
            </DialogDescription>
          </DialogHeader>
          
          {!result ? (
            <>
              <div className="space-y-4 py-4">
                <Alert>
                  <AlertCircle className="h-4 w-4" />
                  <AlertTitle>¿Cómo funciona?</AlertTitle>
                  <AlertDescription className="text-sm">
                    <ol className="list-decimal list-inside space-y-1 mt-2">
                      <li>Se construye un CPE desde el producto/versión detectados</li>
                      <li>Se buscan CVEs relacionados en NVD (National Vulnerability Database)</li>
                      <li>Se crean vulnerabilidades automáticamente vinculadas al {getTypeLabel()}</li>
                    </ol>
                  </AlertDescription>
                </Alert>
                
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="auto-create"
                    checked={autoCreate}
                    onCheckedChange={(checked) => setAutoCreate(checked === true)}
                  />
                  <Label htmlFor="auto-create" className="text-sm">
                    Crear vulnerabilidades automáticamente
                  </Label>
                </div>
              </div>
              
              <DialogFooter>
                <Button variant="outline" onClick={() => setShowDialog(false)}>
                  Cancelar
                </Button>
                <Button onClick={handleCorrelate} disabled={isLoading}>
                  {isLoading ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Buscando CVEs...
                    </>
                  ) : (
                    <>
                      <Link2 className="h-4 w-4 mr-2" />
                      Correlacionar
                    </>
                  )}
                </Button>
              </DialogFooter>
            </>
          ) : (
            <CorrelationResultView 
              result={result} 
              type={type}
              onClose={() => {
                setShowDialog(false);
                setResult(null);
              }}
            />
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}

// ===========================================================================
// RESULT VIEW
// ===========================================================================

interface CorrelationResultViewProps {
  result: CorrelationResult | ScanCorrelationResult;
  type: CorrelationType;
  onClose: () => void;
}

function CorrelationResultView({ result, type, onClose }: CorrelationResultViewProps) {
  const isScanResult = 'services_processed' in result;
  
  return (
    <>
      <div className="space-y-4 py-4">
        <Alert variant={result.status === 'success' ? 'default' : 'destructive'}>
          {result.status === 'success' ? (
            <CheckCircle2 className="h-4 w-4 text-green-600" />
          ) : (
            <AlertCircle className="h-4 w-4" />
          )}
          <AlertTitle>
            {result.status === 'success' 
              ? 'Correlación completada' 
              : result.status === 'no_cpe'
              ? 'Sin CPE disponible'
              : result.status === 'no_cves'
              ? 'Sin CVEs encontrados'
              : 'Error en correlación'
            }
          </AlertTitle>
          <AlertDescription>
            {'error' in result && result.error && (
              <p className="text-sm text-red-600">{result.error}</p>
            )}
          </AlertDescription>
        </Alert>
        
        <div className="grid grid-cols-2 gap-4">
          {isScanResult ? (
            <>
              <StatCard
                label="Servicios procesados"
                value={(result as ScanCorrelationResult).services_processed}
              />
              <StatCard
                label="Con CPE válido"
                value={(result as ScanCorrelationResult).services_with_cpe}
              />
              <StatCard
                label="CVEs encontrados"
                value={(result as ScanCorrelationResult).cves_found}
                highlight
              />
              <StatCard
                label="Vulnerabilidades creadas"
                value={(result as ScanCorrelationResult).vulnerabilities_created}
                highlight
              />
            </>
          ) : (
            <>
              <div className="col-span-2">
                <Label className="text-sm text-muted-foreground">CPE</Label>
                <p className="font-mono text-xs mt-1 p-2 bg-muted rounded">
                  {(result as CorrelationResult).cpe || 'No disponible'}
                </p>
              </div>
              <StatCard
                label="CVEs encontrados"
                value={(result as CorrelationResult).cves_found}
                highlight
              />
              <StatCard
                label="Vulnerabilidades creadas"
                value={(result as CorrelationResult).vulnerabilities_created}
                highlight
              />
            </>
          )}
        </div>
        
        {/* Lista de CVEs encontrados */}
        {'cves' in result && result.cves && result.cves.length > 0 && (
          <div>
            <Label className="text-sm text-muted-foreground">CVEs encontrados</Label>
            <div className="flex flex-wrap gap-1 mt-2">
              {result.cves.map((cve) => (
                <Badge key={cve} variant="secondary" className="font-mono text-xs">
                  {cve}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </div>
      
      <DialogFooter>
        <Button onClick={onClose}>Cerrar</Button>
      </DialogFooter>
    </>
  );
}

// ===========================================================================
// STAT CARD
// ===========================================================================

interface StatCardProps {
  label: string;
  value: number;
  highlight?: boolean;
}

function StatCard({ label, value, highlight }: StatCardProps) {
  return (
    <div className={`p-3 rounded-lg ${highlight ? 'bg-primary/10' : 'bg-muted'}`}>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className={`text-2xl font-bold ${highlight ? 'text-primary' : ''}`}>
        {value}
      </p>
    </div>
  );
}
