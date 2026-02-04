# =============================================================================
# NESTSECURE Frontend - Dockerfile Multi-stage
# =============================================================================
# Next.js 16 + React 19 + Node.js 20
# Optimizado para desarrollo y producción
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Base - Dependencias comunes
# -----------------------------------------------------------------------------
FROM node:20-alpine AS base

# Instalar dependencias del sistema necesarias
RUN apk add --no-cache libc6-compat

WORKDIR /app

# Copiar archivos de configuración de paquetes
COPY package.json package-lock.json* ./

# -----------------------------------------------------------------------------
# Stage 2: Dependencies - Instalar todas las dependencias
# -----------------------------------------------------------------------------
FROM base AS deps

# Instalar dependencias (incluyendo devDependencies)
RUN npm ci --legacy-peer-deps

# -----------------------------------------------------------------------------
# Stage 3: Development - Entorno de desarrollo con hot-reload
# -----------------------------------------------------------------------------
FROM base AS development

WORKDIR /app

# Copiar node_modules desde la etapa de dependencias
COPY --from=deps /app/node_modules ./node_modules

# Copiar el resto del código fuente
COPY . .

# Variables de entorno para desarrollo
ENV NODE_ENV=development
ENV NEXT_TELEMETRY_DISABLED=1
ENV WATCHPACK_POLLING=true
ENV CHOKIDAR_USEPOLLING=true

# Puerto de desarrollo
EXPOSE 3000

# Health check para desarrollo
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/api/health || exit 1

# Comando de desarrollo con hot-reload
CMD ["npm", "run", "dev"]

# -----------------------------------------------------------------------------
# Stage 4: Builder - Compilar para producción
# -----------------------------------------------------------------------------
FROM base AS builder

WORKDIR /app

# Copiar node_modules y código fuente
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Variables de entorno para build
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
# La API URL se configura en runtime, pero necesitamos un placeholder para build
ENV NEXT_PUBLIC_API_URL=http://backend:8000/api/v1
ENV NEXT_PUBLIC_WS_URL=ws://backend:8000/ws

# Compilar la aplicación
RUN npm run build

# -----------------------------------------------------------------------------
# Stage 5: Production - Imagen mínima para producción
# -----------------------------------------------------------------------------
FROM node:20-alpine AS production

WORKDIR /app

# Crear usuario no-root para seguridad
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Instalar dependencias mínimas
RUN apk add --no-cache wget

# Variables de entorno para producción
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Copiar archivos estáticos y build
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# Cambiar a usuario no-root
USER nextjs

# Puerto de producción
EXPOSE 3000

# Health check para producción
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/api/health || exit 1

# Comando de producción
CMD ["node", "server.js"]
