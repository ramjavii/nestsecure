#!/bin/bash
# =============================================================================
# NESTSECURE - Script de Inicio de Docker Development
# =============================================================================
# Este script inicia todos los servicios de desarrollo en Docker
# Uso: ./scripts/docker-dev.sh [comando]
# Comandos: start, stop, restart, logs, build, clean
# =============================================================================

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Directorio base del proyecto
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# Archivo de docker-compose
COMPOSE_FILE="docker-compose.dev.yml"

# Función para mostrar ayuda
show_help() {
    echo -e "${BLUE}NESTSECURE Docker Development${NC}"
    echo ""
    echo "Uso: $0 [comando]"
    echo ""
    echo "Comandos:"
    echo "  start       Iniciar todos los servicios"
    echo "  stop        Detener todos los servicios"
    echo "  restart     Reiniciar todos los servicios"
    echo "  logs        Ver logs de todos los servicios"
    echo "  logs-f      Ver logs en tiempo real (follow)"
    echo "  build       Reconstruir imágenes"
    echo "  clean       Limpiar volúmenes y contenedores"
    echo "  status      Ver estado de los servicios"
    echo "  shell-be    Abrir shell en el backend"
    echo "  shell-fe    Abrir shell en el frontend"
    echo "  db          Conectar a PostgreSQL"
    echo "  redis       Conectar a Redis CLI"
    echo ""
}

# Función para verificar Docker
check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Error: Docker no está instalado${NC}"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        echo -e "${RED}Error: Docker daemon no está corriendo${NC}"
        exit 1
    fi
}

# Función para mostrar el estado de los servicios
show_status() {
    echo -e "${BLUE}Estado de los servicios:${NC}"
    docker compose -f "$COMPOSE_FILE" ps
}

# Función para iniciar servicios
start_services() {
    echo -e "${GREEN}Iniciando servicios NESTSECURE...${NC}"
    docker compose -f "$COMPOSE_FILE" up -d
    
    echo ""
    echo -e "${GREEN}Servicios iniciados correctamente${NC}"
    echo ""
    echo -e "${YELLOW}URLs de acceso:${NC}"
    echo -e "  Frontend:  ${BLUE}http://localhost:3000${NC}"
    echo -e "  Backend:   ${BLUE}http://localhost:8000${NC}"
    echo -e "  API Docs:  ${BLUE}http://localhost:8000/docs${NC}"
    echo ""
    echo -e "${YELLOW}Credenciales de demo:${NC}"
    echo -e "  Email:     ${BLUE}admin@nestsecure.com${NC}"
    echo -e "  Password:  ${BLUE}Admin123!${NC}"
    echo ""
    show_status
}

# Función para detener servicios
stop_services() {
    echo -e "${YELLOW}Deteniendo servicios NESTSECURE...${NC}"
    docker compose -f "$COMPOSE_FILE" down
    echo -e "${GREEN}Servicios detenidos${NC}"
}

# Función para reiniciar servicios
restart_services() {
    stop_services
    sleep 2
    start_services
}

# Función para ver logs
show_logs() {
    docker compose -f "$COMPOSE_FILE" logs "$@"
}

# Función para reconstruir imágenes
build_images() {
    echo -e "${BLUE}Reconstruyendo imágenes...${NC}"
    docker compose -f "$COMPOSE_FILE" build --no-cache
    echo -e "${GREEN}Imágenes reconstruidas${NC}"
}

# Función para limpiar todo
clean_all() {
    echo -e "${RED}¡ADVERTENCIA! Esto eliminará todos los contenedores, volúmenes e imágenes de NESTSECURE${NC}"
    read -p "¿Estás seguro? (y/N): " confirm
    
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Deteniendo y eliminando contenedores...${NC}"
        docker compose -f "$COMPOSE_FILE" down -v --remove-orphans
        
        echo -e "${YELLOW}Eliminando imágenes de NESTSECURE...${NC}"
        docker images | grep "nestsecure" | awk '{print $3}' | xargs -r docker rmi -f
        
        echo -e "${GREEN}Limpieza completada${NC}"
    else
        echo -e "${BLUE}Operación cancelada${NC}"
    fi
}

# Función para abrir shell en backend
shell_backend() {
    docker compose -f "$COMPOSE_FILE" exec backend /bin/bash
}

# Función para abrir shell en frontend
shell_frontend() {
    docker compose -f "$COMPOSE_FILE" exec frontend /bin/sh
}

# Función para conectar a PostgreSQL
connect_db() {
    docker compose -f "$COMPOSE_FILE" exec postgres psql -U nestsecure -d nestsecure_db
}

# Función para conectar a Redis
connect_redis() {
    docker compose -f "$COMPOSE_FILE" exec redis redis-cli
}

# Verificar Docker
check_docker

# Procesar comando
case "${1:-start}" in
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    logs)
        shift
        show_logs "$@"
        ;;
    logs-f)
        shift
        show_logs -f "$@"
        ;;
    build)
        build_images
        ;;
    clean)
        clean_all
        ;;
    status)
        show_status
        ;;
    shell-be)
        shell_backend
        ;;
    shell-fe)
        shell_frontend
        ;;
    db)
        connect_db
        ;;
    redis)
        connect_redis
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}Comando desconocido: $1${NC}"
        show_help
        exit 1
        ;;
esac
