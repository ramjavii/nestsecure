'use client';

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ChartSkeleton } from '@/components/shared/loading-skeleton';

interface VulnTrendChartProps {
  data?: Array<{
    date: string;
    critical: number;
    high: number;
    medium: number;
    low: number;
  }>;
  isLoading?: boolean;
}

export function VulnTrendChart({ data, isLoading }: VulnTrendChartProps) {
  if (isLoading) {
    return <ChartSkeleton />;
  }

  // Use provided data or empty array
  const chartData = data || [];

  // Show empty state if no data
  if (chartData.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Vulnerabilidades - Últimos 30 días</CardTitle>
          <CardDescription>
            Tendencia de vulnerabilidades detectadas por severidad
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-[300px] flex items-center justify-center text-muted-foreground">
            <div className="text-center">
              <p>Sin datos de tendencia disponibles</p>
              <p className="text-sm mt-1">Ejecuta escaneos para ver la tendencia</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Vulnerabilidades - Últimos 30 días</CardTitle>
        <CardDescription>
          Tendencia de vulnerabilidades detectadas por severidad
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="colorCritical" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="colorHigh" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f97316" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#f97316" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="colorMedium" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#eab308" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#eab308" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="colorLow" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
              <XAxis
                dataKey="date"
                tickLine={false}
                axisLine={false}
                tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }}
                tickMargin={8}
              />
              <YAxis
                tickLine={false}
                axisLine={false}
                tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }}
                tickMargin={8}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px',
                  boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
                }}
                labelStyle={{ color: 'hsl(var(--foreground))' }}
              />
              <Area
                type="monotone"
                dataKey="critical"
                stroke="#ef4444"
                fillOpacity={1}
                fill="url(#colorCritical)"
                strokeWidth={2}
                name="Crítica"
              />
              <Area
                type="monotone"
                dataKey="high"
                stroke="#f97316"
                fillOpacity={1}
                fill="url(#colorHigh)"
                strokeWidth={2}
                name="Alta"
              />
              <Area
                type="monotone"
                dataKey="medium"
                stroke="#eab308"
                fillOpacity={1}
                fill="url(#colorMedium)"
                strokeWidth={2}
                name="Media"
              />
              <Area
                type="monotone"
                dataKey="low"
                stroke="#3b82f6"
                fillOpacity={1}
                fill="url(#colorLow)"
                strokeWidth={2}
                name="Baja"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
