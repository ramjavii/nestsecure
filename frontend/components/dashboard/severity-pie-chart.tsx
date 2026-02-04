'use client';

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ChartSkeleton } from '@/components/shared/loading-skeleton';

interface SeverityPieChartProps {
  data?: {
    critical: number;
    high: number;
    medium: number;
    low: number;
    info: number;
  };
  isLoading?: boolean;
}

const SEVERITY_COLORS = {
  critical: '#ef4444',
  high: '#f97316',
  medium: '#eab308',
  low: '#3b82f6',
  info: '#6b7280',
};

const SEVERITY_LABELS = {
  critical: 'Crítica',
  high: 'Alta',
  medium: 'Media',
  low: 'Baja',
  info: 'Info',
};

export function SeverityPieChart({ data, isLoading }: SeverityPieChartProps) {
  if (isLoading) {
    return <ChartSkeleton />;
  }

  // Use provided data or zeros
  const stats = data || {
    critical: 0,
    high: 0,
    medium: 0,
    low: 0,
    info: 0,
  };

  const chartData = Object.entries(stats).map(([key, value]) => ({
    name: SEVERITY_LABELS[key as keyof typeof SEVERITY_LABELS],
    value,
    color: SEVERITY_COLORS[key as keyof typeof SEVERITY_COLORS],
  }));

  const total = chartData.reduce((sum, item) => sum + item.value, 0);

  // Show empty state if no vulnerabilities
  if (total === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Distribución por Severidad</CardTitle>
          <CardDescription>
            Total: 0 vulnerabilidades
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-[300px] flex items-center justify-center text-muted-foreground">
            <div className="text-center">
              <p>Sin vulnerabilidades detectadas</p>
              <p className="text-sm mt-1">Ejecuta escaneos para detectar vulnerabilidades</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Distribución por Severidad</CardTitle>
        <CardDescription>
          Total: {total} vulnerabilidades
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={100}
                paddingAngle={2}
                dataKey="value"
              >
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px',
                  boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
                }}
                formatter={(value: number, name: string) => [
                  `${value} (${((value / total) * 100).toFixed(1)}%)`,
                  name,
                ]}
              />
              <Legend
                verticalAlign="bottom"
                height={36}
                formatter={(value) => (
                  <span className="text-sm text-muted-foreground">{value}</span>
                )}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
