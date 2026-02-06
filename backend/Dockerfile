# =============================================================================
# NESTSECURE - Dockerfile Backend
# =============================================================================
# Multi-stage build para optimizar el tamaño de la imagen
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Base con dependencias del sistema
# -----------------------------------------------------------------------------
FROM python:3.11-slim-bookworm AS base

# Evitar preguntas interactivas durante la instalación
ENV DEBIAN_FRONTEND=noninteractive

# Variables de entorno de Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Instalar dependencias del sistema necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Build tools
    build-essential \
    gcc \
    # PostgreSQL client
    libpq-dev \
    postgresql-client \
    # Para WeasyPrint (reportes PDF)
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    # Nmap
    nmap \
    # Utilidades
    curl \
    wget \
    git \
    unzip \
    # Limpieza
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# Instalar Nuclei Scanner
# =============================================================================
# Nuclei - Fast vulnerability scanner based on templates
# https://github.com/projectdiscovery/nuclei
# =============================================================================
ARG NUCLEI_VERSION=3.3.7
ENV NUCLEI_VERSION=${NUCLEI_VERSION}

# Descargar e instalar Nuclei
RUN ARCH=$(dpkg --print-architecture) && \
    if [ "$ARCH" = "amd64" ]; then NUCLEI_ARCH="linux_amd64"; \
    elif [ "$ARCH" = "arm64" ]; then NUCLEI_ARCH="linux_arm64"; \
    else echo "Unsupported architecture: $ARCH" && exit 1; fi && \
    wget -q "https://github.com/projectdiscovery/nuclei/releases/download/v${NUCLEI_VERSION}/nuclei_${NUCLEI_VERSION}_${NUCLEI_ARCH}.zip" -O /tmp/nuclei.zip && \
    unzip -q /tmp/nuclei.zip -d /tmp/nuclei && \
    mv /tmp/nuclei/nuclei /usr/local/bin/nuclei && \
    chmod +x /usr/local/bin/nuclei && \
    rm -rf /tmp/nuclei /tmp/nuclei.zip && \
    nuclei -version

# Crear usuario no-root para seguridad (antes de crear directorios con ownership)
RUN groupadd --gid 1000 nestsecure \
    && useradd --uid 1000 --gid nestsecure --shell /bin/bash --create-home nestsecure

# Crear directorio para templates de Nuclei
RUN mkdir -p /opt/nuclei-templates && \
    chown nestsecure:nestsecure /opt/nuclei-templates

# Variable de entorno para templates
ENV NUCLEI_TEMPLATES_PATH=/opt/nuclei-templates

# Directorio de trabajo
WORKDIR /app

# -----------------------------------------------------------------------------
# Stage 2: Dependencias de desarrollo
# -----------------------------------------------------------------------------
FROM base AS development

# Copiar archivos de requerimientos
COPY requirements.txt requirements-dev.txt ./

# Instalar todas las dependencias (incluyendo dev)
RUN pip install --upgrade pip setuptools wheel \
    && pip install -r requirements-dev.txt

# Copiar el código fuente
COPY --chown=nestsecure:nestsecure . .

# Crear directorios necesarios
RUN mkdir -p /app/logs /app/reports /app/templates \
    && chown -R nestsecure:nestsecure /app

# Cambiar a usuario no-root
USER nestsecure

# Puerto de la aplicación
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Comando por defecto (desarrollo con hot-reload)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# -----------------------------------------------------------------------------
# Stage 3: Build de producción
# -----------------------------------------------------------------------------
FROM base AS builder

# Copiar solo requirements para cache de Docker
COPY requirements.txt ./

# Crear virtual environment e instalar dependencias
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --upgrade pip setuptools wheel \
    && pip install -r requirements.txt

# -----------------------------------------------------------------------------
# Stage 4: Imagen de producción
# -----------------------------------------------------------------------------
FROM python:3.11-slim-bookworm AS production

# Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PATH="/opt/venv/bin:$PATH" \
    # Configuración por defecto de producción
    ENVIRONMENT=production \
    DEBUG=false

# Instalar solo dependencias runtime necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    shared-mime-info \
    nmap \
    curl \
    wget \
    unzip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Instalar Nuclei en producción
ARG NUCLEI_VERSION=3.3.7
RUN ARCH=$(dpkg --print-architecture) && \
    if [ "$ARCH" = "amd64" ]; then NUCLEI_ARCH="linux_amd64"; \
    elif [ "$ARCH" = "arm64" ]; then NUCLEI_ARCH="linux_arm64"; \
    else echo "Unsupported architecture: $ARCH" && exit 1; fi && \
    wget -q "https://github.com/projectdiscovery/nuclei/releases/download/v${NUCLEI_VERSION}/nuclei_${NUCLEI_VERSION}_${NUCLEI_ARCH}.zip" -O /tmp/nuclei.zip && \
    unzip -q /tmp/nuclei.zip -d /tmp/nuclei && \
    mv /tmp/nuclei/nuclei /usr/local/bin/nuclei && \
    chmod +x /usr/local/bin/nuclei && \
    rm -rf /tmp/nuclei /tmp/nuclei.zip

# Crear directorio para templates
RUN mkdir -p /opt/nuclei-templates
ENV NUCLEI_TEMPLATES_PATH=/opt/nuclei-templates

# Crear usuario no-root
RUN groupadd --gid 1000 nestsecure \
    && useradd --uid 1000 --gid nestsecure --shell /bin/bash --create-home nestsecure

# Copiar virtual environment desde builder
COPY --from=builder /opt/venv /opt/venv

# Directorio de trabajo
WORKDIR /app

# Copiar código fuente
COPY --chown=nestsecure:nestsecure . .

# Crear directorios necesarios (incluyendo nuclei templates)
RUN mkdir -p /app/logs /app/reports /app/templates \
    && chown -R nestsecure:nestsecure /app \
    && chown -R nestsecure:nestsecure /opt/nuclei-templates

# Cambiar a usuario no-root
USER nestsecure

# Puerto
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Comando de producción (sin reload, múltiples workers)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
