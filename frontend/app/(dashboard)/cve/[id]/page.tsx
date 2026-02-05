'use client';

import { use } from 'react';
import Link from 'next/link';
import { useCVE, usePrefetchCVE } from '@/hooks/use-cve';
import { CVEDetails, CVSSBadge, SeverityBadge } from '@/components/cve';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  ArrowLeft, 
  ExternalLink, 
  AlertTriangle, 
  Bug,
  Calendar,
  Clock,
  Shield,
  Link as LinkIcon,
  Package,
  FileText,
  RefreshCw,
  Copy,
  Check,
} from 'lucide-react';
import { useState, useCallback } from 'react';

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function CVEDetailPage({ params }: PageProps) {
  const { id } = use(params);
  const cveId = decodeURIComponent(id);
  const [copied, setCopied] = useState(false);
  
  const { cve, isLoading, error, refetch } = useCVE(cveId);

  const handleCopyId = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(cveId);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  }, [cveId]);

  // Loading state
  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Skeleton className="h-10 w-32" />
          <Skeleton className="h-10 w-64" />
        </div>
        <Skeleton className="h-40" />
        <Skeleton className="h-96" />
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" asChild>
          <Link href="/cve" data-testid="back-button">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Volver a Búsqueda CVE
          </Link>
        </Button>
        <Alert variant="destructive" data-testid="error-alert">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>
            Error al cargar CVE: {error.message}
          </AlertDescription>
        </Alert>
        <Button onClick={() => refetch()} variant="outline">
          <RefreshCw className="h-4 w-4 mr-2" />
          Reintentar
        </Button>
      </div>
    );
  }

  // Not found state
  if (!cve) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" asChild>
          <Link href="/cve" data-testid="back-button">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Volver a Búsqueda CVE
          </Link>
        </Button>
        <Alert data-testid="not-found-alert">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>CVE no encontrado</AlertTitle>
          <AlertDescription>
            El CVE &quot;{cveId}&quot; no existe o no está disponible en la base de datos.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Back button */}
      <Button variant="ghost" asChild>
        <Link href="/cve" data-testid="back-button">
          <ArrowLeft className="h-4 w-4 mr-2" />
          Volver a Búsqueda CVE
        </Link>
      </Button>

      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold" data-testid="cve-id">{cve.cve_id}</h1>
            <Button
              variant="ghost"
              size="icon"
              onClick={handleCopyId}
              title="Copiar ID"
            >
              {copied ? (
                <Check className="h-4 w-4 text-green-500" />
              ) : (
                <Copy className="h-4 w-4" />
              )}
            </Button>
          </div>
          
          <div className="flex items-center gap-2 flex-wrap">
            {cve.cvss_v3_severity && (
              <SeverityBadge severity={cve.cvss_v3_severity} />
            )}
            {cve.cvss_v3_score && (
              <CVSSBadge score={cve.cvss_v3_score} />
            )}
            {cve.exploit_available && (
              <Badge variant="destructive" className="gap-1">
                <Bug className="h-3 w-3" />
                Exploit Disponible
              </Badge>
            )}
            {cve.in_cisa_kev && (
              <Badge variant="outline" className="gap-1 border-orange-500 text-orange-500">
                <AlertTriangle className="h-3 w-3" />
                CISA KEV
              </Badge>
            )}
          </div>
        </div>

        {/* External links */}
        <div className="flex items-center gap-2" data-testid="external-links">
          <Button variant="outline" size="sm" asChild>
            <a 
              href={`https://nvd.nist.gov/vuln/detail/${cve.cve_id}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              <ExternalLink className="h-4 w-4 mr-2" />
              NVD
            </a>
          </Button>
          <Button variant="outline" size="sm" asChild>
            <a 
              href={`https://cve.mitre.org/cgi-bin/cvename.cgi?name=${cve.cve_id}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              <ExternalLink className="h-4 w-4 mr-2" />
              MITRE
            </a>
          </Button>
          {cve.in_cisa_kev && (
            <Button variant="outline" size="sm" asChild>
              <a 
                href="https://www.cisa.gov/known-exploited-vulnerabilities-catalog"
                target="_blank"
                rel="noopener noreferrer"
              >
                <ExternalLink className="h-4 w-4 mr-2" />
                CISA KEV
              </a>
            </Button>
          )}
        </div>
      </div>

      {/* Main content with Tabs */}
      <Tabs defaultValue="overview" className="w-full" data-testid="cve-tabs">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview" className="gap-2">
            <FileText className="h-4 w-4" />
            Resumen
          </TabsTrigger>
          <TabsTrigger value="references" className="gap-2">
            <LinkIcon className="h-4 w-4" />
            Referencias
          </TabsTrigger>
          <TabsTrigger value="products" className="gap-2">
            <Package className="h-4 w-4" />
            Productos Afectados
          </TabsTrigger>
          <TabsTrigger value="technical" className="gap-2">
            <Shield className="h-4 w-4" />
            Detalles Técnicos
          </TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-4" data-testid="tab-overview">
          <Card>
            <CardHeader>
              <CardTitle>Descripción</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground leading-relaxed" data-testid="cve-description">
                {cve.description || 'No hay descripción disponible.'}
              </p>
            </CardContent>
          </Card>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* CVSS Details */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Puntuación CVSS v3</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Score Base</span>
                  <span className="text-2xl font-bold" data-testid="cvss-score">
                    {cve.cvss_v3_score?.toFixed(1) || 'N/A'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Severidad</span>
                  {cve.cvss_v3_severity ? (
                    <SeverityBadge severity={cve.cvss_v3_severity} />
                  ) : (
                    <span className="text-muted-foreground">N/A</span>
                  )}
                </div>
                {cve.cvss_v3_vector && (
                  <div className="pt-2 border-t">
                    <span className="text-sm text-muted-foreground">Vector:</span>
                    <code className="ml-2 text-xs bg-muted px-2 py-1 rounded" data-testid="cvss-vector">
                      {cve.cvss_v3_vector}
                    </code>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Timeline */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Timeline</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground flex items-center gap-2">
                    <Calendar className="h-4 w-4" />
                    Publicado
                  </span>
                  <span data-testid="published-date">
                    {cve.published_date 
                      ? new Date(cve.published_date).toLocaleDateString('es-ES', {
                          year: 'numeric',
                          month: 'long',
                          day: 'numeric'
                        })
                      : 'N/A'
                    }
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground flex items-center gap-2">
                    <Clock className="h-4 w-4" />
                    Última Modificación
                  </span>
                  <span data-testid="modified-date">
                    {cve.last_modified_date 
                      ? new Date(cve.last_modified_date).toLocaleDateString('es-ES', {
                          year: 'numeric',
                          month: 'long',
                          day: 'numeric'
                        })
                      : 'N/A'
                    }
                  </span>
                </div>
                {cve.epss_score !== undefined && cve.epss_score !== null && (
                  <div className="flex items-center justify-between pt-2 border-t">
                    <span className="text-muted-foreground">EPSS Score</span>
                    <Badge variant={cve.epss_score > 0.5 ? 'destructive' : 'secondary'}>
                      {(cve.epss_score * 100).toFixed(2)}%
                    </Badge>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* References Tab */}
        <TabsContent value="references" className="space-y-4" data-testid="tab-references">
          <Card>
            <CardHeader>
              <CardTitle>Referencias Externas</CardTitle>
              <CardDescription>
                Enlaces a recursos adicionales sobre esta vulnerabilidad
              </CardDescription>
            </CardHeader>
            <CardContent>
              {cve.references && cve.references.length > 0 ? (
                <div className="space-y-2">
                  {cve.references.map((ref, index) => (
                    <div 
                      key={index}
                      className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50 transition-colors"
                    >
                      <div className="flex items-center gap-3 flex-1 min-w-0">
                        <ExternalLink className="h-4 w-4 text-muted-foreground shrink-0" />
                        <div className="min-w-0 flex-1">
                          <a 
                            href={ref.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm text-primary hover:underline truncate block"
                          >
                            {ref.url}
                          </a>
                          {ref.source && (
                            <span className="text-xs text-muted-foreground">
                              Fuente: {ref.source}
                            </span>
                          )}
                        </div>
                      </div>
                      {ref.tags && ref.tags.length > 0 && (
                        <div className="flex gap-1 shrink-0 ml-2">
                          {ref.tags.slice(0, 2).map((tag, tagIndex) => (
                            <Badge key={tagIndex} variant="outline" className="text-xs">
                              {tag}
                            </Badge>
                          ))}
                          {ref.tags.length > 2 && (
                            <Badge variant="outline" className="text-xs">
                              +{ref.tags.length - 2}
                            </Badge>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-muted-foreground text-center py-8">
                  No hay referencias disponibles para este CVE.
                </p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Affected Products Tab */}
        <TabsContent value="products" className="space-y-4" data-testid="tab-products">
          <Card>
            <CardHeader>
              <CardTitle>Productos Afectados</CardTitle>
              <CardDescription>
                Lista de productos y versiones afectadas por esta vulnerabilidad
              </CardDescription>
            </CardHeader>
            <CardContent>
              {cve.affected_products && cve.affected_products.length > 0 ? (
                <div className="space-y-2">
                  {cve.affected_products.map((product, index) => (
                    <div 
                      key={index}
                      className="flex items-center justify-between p-3 border rounded-lg"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <Package className="h-4 w-4 text-muted-foreground" />
                          <span className="font-medium">{product.product || 'Desconocido'}</span>
                        </div>
                        <div className="text-sm text-muted-foreground">
                          <span>Vendor: {product.vendor || 'N/A'}</span>
                        </div>
                      </div>
                      <div className="text-right">
                        {product.version_start && (
                          <Badge variant="outline" className="text-xs">
                            {product.version_start} - {product.version_end || '*'}
                          </Badge>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-muted-foreground text-center py-8">
                  No hay información de productos afectados disponible.
                </p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Technical Details Tab */}
        <TabsContent value="technical" className="space-y-4" data-testid="tab-technical">
          <Card>
            <CardHeader>
              <CardTitle>Detalles Técnicos</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* CWE */}
              {cve.cwe_ids && cve.cwe_ids.length > 0 && (
                <div>
                  <h4 className="font-medium mb-2">CWE (Common Weakness Enumeration)</h4>
                  <div className="flex gap-2 flex-wrap">
                    {cve.cwe_ids.map((cweId, index) => (
                      <a
                        key={index}
                        href={`https://cwe.mitre.org/data/definitions/${cweId.replace('CWE-', '')}.html`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1"
                      >
                        <Badge variant="secondary" className="hover:bg-secondary/80">
                          {cweId}
                          <ExternalLink className="h-3 w-3 ml-1" />
                        </Badge>
                      </a>
                    ))}
                  </div>
                </div>
              )}

              {/* CVSS Vector Breakdown */}
              {cve.cvss_v3_vector && (
                <div>
                  <h4 className="font-medium mb-2">Vector CVSS v3.1</h4>
                  <div className="bg-muted p-4 rounded-lg">
                    <code className="text-sm break-all">
                      {cve.cvss_v3_vector}
                    </code>
                  </div>
                </div>
              )}

              {/* Additional info */}
              <div className="grid grid-cols-2 gap-4 pt-4 border-t">
                <div>
                  <span className="text-sm text-muted-foreground">Exploit Disponible</span>
                  <p className="font-medium">
                    {cve.exploit_available ? (
                      <span className="text-red-600">Sí</span>
                    ) : (
                      <span className="text-green-600">No conocido</span>
                    )}
                  </p>
                </div>
                <div>
                  <span className="text-sm text-muted-foreground">En CISA KEV</span>
                  <p className="font-medium">
                    {cve.in_cisa_kev ? (
                      <span className="text-orange-600">Sí - Explotación activa</span>
                    ) : (
                      <span className="text-muted-foreground">No</span>
                    )}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
