'use client';

/**
 * Página de configuración de Scanners (Nuclei + ZAP)
 * 
 * Muestra el estado de los escáneres de vulnerabilidades
 * y permite configurar perfiles por defecto.
 */

import { useState } from 'react';
import {
  RefreshCw,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Loader2,
  Terminal,
  Globe,
  FileText,
  Settings,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { PageHeader } from '@/components/shared/page-header';
import { useNucleiHealth, useNucleiProfiles } from '@/hooks/use-nuclei';
import { useZapVersion, useZapProfiles } from '@/hooks/use-zap';

// ===========================================================================
// STATUS COMPONENT
// ===========================================================================

interface StatusIndicatorProps {
  status: 'online' | 'offline' | 'warning' | 'loading';
  label: string;
}

function StatusIndicator({ status, label }: StatusIndicatorProps) {
  const config = {
    online: {
      icon: CheckCircle2,
      className: 'text-green-500',
      bg: 'bg-green-500/10',
    },
    offline: {
      icon: XCircle,
      className: 'text-red-500',
      bg: 'bg-red-500/10',
    },
    warning: {
      icon: AlertTriangle,
      className: 'text-yellow-500',
      bg: 'bg-yellow-500/10',
    },
    loading: {
      icon: Loader2,
      className: 'text-muted-foreground animate-spin',
      bg: 'bg-muted/50',
    },
  };

  const { icon: Icon, className, bg } = config[status];

  return (
    <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full ${bg}`}>
      <Icon className={`h-4 w-4 ${className}`} />
      <span className="text-sm font-medium">{label}</span>
    </div>
  );
}

// ===========================================================================
// NUCLEI CARD
// ===========================================================================

function NucleiStatusCard() {
  const { data: health, isLoading, error, refetch } = useNucleiHealth();
  const { data: profiles } = useNucleiProfiles();
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await refetch();
    setIsRefreshing(false);
  };

  const getStatus = () => {
    if (isLoading) return 'loading';
    if (error || !health?.nuclei_installed) return 'offline';
    if (!health.templates_count) return 'warning';
    return 'online';
  };

  const getStatusLabel = () => {
    if (isLoading) return 'Verificando...';
    if (error) return 'Error de conexión';
    if (!health?.nuclei_installed) return 'No instalado';
    if (!health.templates_count) return 'Sin templates';
    return 'Operativo';
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-purple-500/10">
            <Terminal className="h-5 w-5 text-purple-500" />
          </div>
          <div>
            <CardTitle className="text-lg">Nuclei Scanner</CardTitle>
            <CardDescription>Escáner de vulnerabilidades basado en templates</CardDescription>
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleRefresh}
          disabled={isRefreshing}
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
          Actualizar
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">Estado</span>
          <StatusIndicator status={getStatus()} label={getStatusLabel()} />
        </div>

        {health && (
          <>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Versión</span>
              <Badge variant="secondary" className="font-mono">
                {health.nuclei_version || 'N/A'}
              </Badge>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Templates</span>
              <span className="text-sm font-medium">
                {health.templates_count?.toLocaleString() || 0} templates
              </span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Última actualización</span>
              <span className="text-sm">
                {health.last_updated
                  ? new Date(health.last_updated).toLocaleDateString('es-ES')
                  : 'Nunca'}
              </span>
            </div>
          </>
        )}

        {profiles && profiles.profiles && (
          <div className="pt-4 border-t">
            <h4 className="text-sm font-medium mb-3">Perfiles Disponibles</h4>
            <div className="flex flex-wrap gap-2">
              {profiles.profiles.map((profile) => (
                <Badge key={profile.name} variant="outline">
                  {profile.name}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ===========================================================================
// ZAP CARD
// ===========================================================================

function ZapStatusCard() {
  const { data: version, isLoading, error, refetch } = useZapVersion();
  const { data: profiles } = useZapProfiles();
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await refetch();
    setIsRefreshing(false);
  };

  const getStatus = () => {
    if (isLoading) return 'loading';
    if (error || !version?.available) return 'offline';
    return 'online';
  };

  const getStatusLabel = () => {
    if (isLoading) return 'Verificando...';
    if (error) return 'Error de conexión';
    if (!version?.available) return 'No disponible';
    return 'Operativo';
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-orange-500/10">
            <Globe className="h-5 w-5 text-orange-500" />
          </div>
          <div>
            <CardTitle className="text-lg">OWASP ZAP</CardTitle>
            <CardDescription>Escáner de seguridad para aplicaciones web</CardDescription>
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleRefresh}
          disabled={isRefreshing}
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
          Actualizar
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">Estado</span>
          <StatusIndicator status={getStatus()} label={getStatusLabel()} />
        </div>

        {version && (
          <>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Versión</span>
              <Badge variant="secondary" className="font-mono">
                {version.version || 'N/A'}
              </Badge>
            </div>
          </>
        )}

        {profiles && profiles.profiles && (
          <div className="pt-4 border-t">
            <h4 className="text-sm font-medium mb-3">Perfiles Disponibles</h4>
            <div className="flex flex-wrap gap-2">
              {profiles.profiles.map((profile) => (
                <Badge key={profile.name} variant="outline">
                  {profile.name}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ===========================================================================
// MAIN PAGE
// ===========================================================================

export default function ScannersSettingsPage() {
  const [defaultNucleiProfile, setDefaultNucleiProfile] = useState('quick');
  const [defaultZapProfile, setDefaultZapProfile] = useState('baseline');

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Configuración de Scanners"
        description="Estado y configuración de escáneres de vulnerabilidades"
      />

      <Tabs defaultValue="status" className="w-full">
        <TabsList className="bg-secondary border border-border">
          <TabsTrigger value="status" className="gap-2">
            <Settings className="h-4 w-4" />
            Estado
          </TabsTrigger>
          <TabsTrigger value="config" className="gap-2">
            <FileText className="h-4 w-4" />
            Configuración
          </TabsTrigger>
        </TabsList>

        <TabsContent value="status" className="mt-6">
          <div className="grid gap-6 md:grid-cols-2">
            <NucleiStatusCard />
            <ZapStatusCard />
          </div>
        </TabsContent>

        <TabsContent value="config" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle>Perfiles por Defecto</CardTitle>
              <CardDescription>
                Configura los perfiles de escaneo que se usarán por defecto
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <label className="text-sm font-medium">Perfil Nuclei por defecto</label>
                <Select value={defaultNucleiProfile} onValueChange={setDefaultNucleiProfile}>
                  <SelectTrigger className="w-64">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="quick">Quick (Solo críticos)</SelectItem>
                    <SelectItem value="web">Web (Vulnerabilidades web)</SelectItem>
                    <SelectItem value="cve">CVE (Búsqueda de CVEs)</SelectItem>
                    <SelectItem value="full">Full (Escaneo completo)</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  Se usará cuando se inicie un escaneo Nuclei sin especificar perfil
                </p>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Perfil ZAP por defecto</label>
                <Select value={defaultZapProfile} onValueChange={setDefaultZapProfile}>
                  <SelectTrigger className="w-64">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="baseline">Baseline (Rápido)</SelectItem>
                    <SelectItem value="full">Full (Completo)</SelectItem>
                    <SelectItem value="api">API (OpenAPI/GraphQL)</SelectItem>
                    <SelectItem value="spa">SPA (Single Page Apps)</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  Se usará cuando se inicie un escaneo ZAP sin especificar perfil
                </p>
              </div>

              <div className="pt-4">
                <Button disabled>
                  Guardar Preferencias
                </Button>
                <p className="text-xs text-muted-foreground mt-2">
                  * La persistencia de preferencias requiere endpoint de backend (próximamente)
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
