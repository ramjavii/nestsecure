'use client';

/**
 * NESTSECURE - ZAP Alerts Table Component
 *
 * Tabla para mostrar alertas de OWASP ZAP con filtros y ordenamiento.
 */

import { useState, useMemo } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Search,
  Filter,
  AlertCircle,
  AlertTriangle,
  Info,
  ShieldAlert,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// =============================================================================
// TYPES
// =============================================================================

export interface ZapAlert {
  id: string;
  risk: 'high' | 'medium' | 'low' | 'informational';
  confidence: 'high' | 'medium' | 'low' | 'user_confirmed' | 'false_positive';
  name: string;
  description: string;
  url: string;
  method: string;
  param?: string;
  attack?: string;
  evidence?: string;
  solution?: string;
  reference?: string;
  cwe_id?: number;
  wasc_id?: number;
  plugin_id?: number;
}

interface ZapAlertsTableProps {
  alerts: ZapAlert[];
  isLoading?: boolean;
  className?: string;
}

type SortField = 'risk' | 'confidence' | 'name' | 'url';
type SortOrder = 'asc' | 'desc';

// =============================================================================
// CONSTANTS
// =============================================================================

const RISK_ORDER = {
  high: 4,
  medium: 3,
  low: 2,
  informational: 1,
};

const CONFIDENCE_ORDER = {
  user_confirmed: 5,
  high: 4,
  medium: 3,
  low: 2,
  false_positive: 1,
};

const RISK_CONFIG = {
  high: {
    label: 'Alta',
    variant: 'destructive' as const,
    icon: ShieldAlert,
    className: 'bg-red-500',
  },
  medium: {
    label: 'Media',
    variant: 'default' as const,
    icon: AlertTriangle,
    className: 'bg-orange-500',
  },
  low: {
    label: 'Baja',
    variant: 'default' as const,
    icon: AlertCircle,
    className: 'bg-yellow-500 text-black',
  },
  informational: {
    label: 'Info',
    variant: 'secondary' as const,
    icon: Info,
    className: '',
  },
};

// =============================================================================
// HELPER COMPONENTS
// =============================================================================

function RiskBadge({ risk }: { risk: ZapAlert['risk'] }) {
  const config = RISK_CONFIG[risk];
  const Icon = config.icon;

  return (
    <Badge variant={config.variant} className={cn('gap-1', config.className)}>
      <Icon className="h-3 w-3" />
      {config.label}
    </Badge>
  );
}

function ConfidenceBadge({ confidence }: { confidence: ZapAlert['confidence'] }) {
  const labels = {
    high: 'Alta',
    medium: 'Media',
    low: 'Baja',
    user_confirmed: 'Confirmada',
    false_positive: 'Falso +',
  };

  return (
    <Badge variant="outline">
      {labels[confidence]}
    </Badge>
  );
}

function AlertDetailDialog({ alert }: { alert: ZapAlert }) {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm">
          Ver detalles
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <RiskBadge risk={alert.risk} />
            {alert.name}
          </DialogTitle>
          <DialogDescription>
            {alert.method} {alert.url}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Description */}
          <div>
            <h4 className="font-semibold mb-2">Descripción</h4>
            <p className="text-sm text-muted-foreground">{alert.description}</p>
          </div>

          {/* Details */}
          <div className="grid grid-cols-2 gap-4">
            {alert.param && (
              <div>
                <h4 className="font-semibold text-sm">Parámetro</h4>
                <code className="text-xs bg-muted p-1 rounded">{alert.param}</code>
              </div>
            )}
            {alert.cwe_id && (
              <div>
                <h4 className="font-semibold text-sm">CWE</h4>
                <a
                  href={`https://cwe.mitre.org/data/definitions/${alert.cwe_id}.html`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-primary hover:underline flex items-center gap-1"
                >
                  CWE-{alert.cwe_id}
                  <ExternalLink className="h-3 w-3" />
                </a>
              </div>
            )}
          </div>

          {/* Attack */}
          {alert.attack && (
            <div>
              <h4 className="font-semibold mb-2">Ataque</h4>
              <pre className="text-xs bg-muted p-2 rounded overflow-x-auto">
                {alert.attack}
              </pre>
            </div>
          )}

          {/* Evidence */}
          {alert.evidence && (
            <div>
              <h4 className="font-semibold mb-2">Evidencia</h4>
              <pre className="text-xs bg-muted p-2 rounded overflow-x-auto">
                {alert.evidence}
              </pre>
            </div>
          )}

          {/* Solution */}
          {alert.solution && (
            <div>
              <h4 className="font-semibold mb-2">Solución</h4>
              <p className="text-sm text-muted-foreground">{alert.solution}</p>
            </div>
          )}

          {/* Reference */}
          {alert.reference && (
            <div>
              <h4 className="font-semibold mb-2">Referencias</h4>
              <div className="text-sm space-y-1">
                {alert.reference.split('\n').map((ref, i) => (
                  <a
                    key={i}
                    href={ref.trim()}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block text-primary hover:underline truncate"
                  >
                    {ref.trim()}
                  </a>
                ))}
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

function SortButton({
  field,
  currentField,
  currentOrder,
  onClick,
  children,
}: {
  field: SortField;
  currentField: SortField;
  currentOrder: SortOrder;
  onClick: (field: SortField) => void;
  children: React.ReactNode;
}) {
  const isActive = field === currentField;

  return (
    <button
      onClick={() => onClick(field)}
      className="flex items-center gap-1 hover:text-foreground"
    >
      {children}
      {isActive &&
        (currentOrder === 'asc' ? (
          <ChevronUp className="h-3 w-3" />
        ) : (
          <ChevronDown className="h-3 w-3" />
        ))}
    </button>
  );
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export function ZapAlertsTable({
  alerts,
  isLoading = false,
  className,
}: ZapAlertsTableProps) {
  // State
  const [searchQuery, setSearchQuery] = useState('');
  const [riskFilter, setRiskFilter] = useState<string>('all');
  const [sortField, setSortField] = useState<SortField>('risk');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');

  // Handle sort
  const handleSort = (field: SortField) => {
    if (field === sortField) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('desc');
    }
  };

  // Filter and sort alerts
  const filteredAlerts = useMemo(() => {
    let result = [...alerts];

    // Filter by search
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (alert) =>
          alert.name.toLowerCase().includes(query) ||
          alert.url.toLowerCase().includes(query) ||
          alert.description.toLowerCase().includes(query)
      );
    }

    // Filter by risk
    if (riskFilter !== 'all') {
      result = result.filter((alert) => alert.risk === riskFilter);
    }

    // Sort
    result.sort((a, b) => {
      let comparison = 0;

      switch (sortField) {
        case 'risk':
          comparison = RISK_ORDER[a.risk] - RISK_ORDER[b.risk];
          break;
        case 'confidence':
          comparison = CONFIDENCE_ORDER[a.confidence] - CONFIDENCE_ORDER[b.confidence];
          break;
        case 'name':
          comparison = a.name.localeCompare(b.name);
          break;
        case 'url':
          comparison = a.url.localeCompare(b.url);
          break;
      }

      return sortOrder === 'asc' ? comparison : -comparison;
    });

    return result;
  }, [alerts, searchQuery, riskFilter, sortField, sortOrder]);

  // Summary
  const summary = useMemo(() => {
    return {
      total: alerts.length,
      high: alerts.filter((a) => a.risk === 'high').length,
      medium: alerts.filter((a) => a.risk === 'medium').length,
      low: alerts.filter((a) => a.risk === 'low').length,
      info: alerts.filter((a) => a.risk === 'informational').length,
    };
  }, [alerts]);

  return (
    <div className={cn('space-y-4', className)}>
      {/* Summary */}
      <div className="flex items-center gap-4 flex-wrap">
        <span className="text-sm font-medium">
          {summary.total} alertas encontradas:
        </span>
        <div className="flex gap-2">
          <Badge variant="destructive">{summary.high} Alta</Badge>
          <Badge className="bg-orange-500">{summary.medium} Media</Badge>
          <Badge className="bg-yellow-500 text-black">{summary.low} Baja</Badge>
          <Badge variant="secondary">{summary.info} Info</Badge>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-4 flex-wrap">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Buscar alertas..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
        <Select value={riskFilter} onValueChange={setRiskFilter}>
          <SelectTrigger className="w-[150px]">
            <Filter className="h-4 w-4 mr-2" />
            <SelectValue placeholder="Riesgo" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos</SelectItem>
            <SelectItem value="high">Alta</SelectItem>
            <SelectItem value="medium">Media</SelectItem>
            <SelectItem value="low">Baja</SelectItem>
            <SelectItem value="informational">Info</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[100px]">
                <SortButton
                  field="risk"
                  currentField={sortField}
                  currentOrder={sortOrder}
                  onClick={handleSort}
                >
                  Riesgo
                </SortButton>
              </TableHead>
              <TableHead className="w-[100px]">
                <SortButton
                  field="confidence"
                  currentField={sortField}
                  currentOrder={sortOrder}
                  onClick={handleSort}
                >
                  Confianza
                </SortButton>
              </TableHead>
              <TableHead>
                <SortButton
                  field="name"
                  currentField={sortField}
                  currentOrder={sortOrder}
                  onClick={handleSort}
                >
                  Alerta
                </SortButton>
              </TableHead>
              <TableHead className="max-w-[300px]">
                <SortButton
                  field="url"
                  currentField={sortField}
                  currentOrder={sortOrder}
                  onClick={handleSort}
                >
                  URL
                </SortButton>
              </TableHead>
              <TableHead className="w-[120px]">Acciones</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center py-8">
                  Cargando alertas...
                </TableCell>
              </TableRow>
            ) : filteredAlerts.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center py-8 text-muted-foreground">
                  No se encontraron alertas
                </TableCell>
              </TableRow>
            ) : (
              filteredAlerts.map((alert) => (
                <TableRow key={alert.id}>
                  <TableCell>
                    <RiskBadge risk={alert.risk} />
                  </TableCell>
                  <TableCell>
                    <ConfidenceBadge confidence={alert.confidence} />
                  </TableCell>
                  <TableCell>
                    <div>
                      <div className="font-medium">{alert.name}</div>
                      <div className="text-xs text-muted-foreground line-clamp-1">
                        {alert.description}
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className="max-w-[300px]">
                    <div className="flex items-center gap-1">
                      <Badge variant="outline" className="text-xs">
                        {alert.method}
                      </Badge>
                      <span className="truncate text-sm" title={alert.url}>
                        {alert.url}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <AlertDetailDialog alert={alert} />
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

export default ZapAlertsTable;
