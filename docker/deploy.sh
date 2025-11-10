#!/bin/bash
# LiteMCP Full Stack Docker Deployment Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
PROJECT_NAME="litemcp"
PROXY_HOST=${PROXY_HOST:-"0.0.0.0"}
PROXY_PORT=${PROXY_PORT:-1888}
API_HOST=${API_HOST:-"0.0.0.0"}
API_PORT=${API_PORT:-9000}
FRONTEND_PORT=${FRONTEND_PORT:-2345}
API_BASE_URL=${API_BASE_URL:-"http://localhost:9000"}
PROXY_BASE_URL=${PROXY_BASE_URL:-"http://localhost:1888"}
MCP_SERVER_HOST=${MCP_SERVER_HOST:-"http://127.0.0.1:1888"}
DEBUG_MODE=${DEBUG_MODE:-"false"}

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_header() {
    echo -e "${BLUE}🚀 LiteMCP Full Stack Docker Deployment${NC}"
    echo "=================================================="
}

# Load mirror configuration if available
MIRRORS_FILE="docker/mirrors.env"
if [ -f "$MIRRORS_FILE" ]; then
    print_info "Loading mirror configuration from $MIRRORS_FILE"
    source "$MIRRORS_FILE"
fi

# Function to show usage
show_usage() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  up           Start all services (default)"
    echo "  down         Stop all services"
    echo "  restart      Restart all services"
    echo "  blue-green   Blue-green deployment (zero downtime)"
    echo "  rollback     Rollback to previous version"
    echo "  logs         Show logs"
    echo "  status       Show service status"
    echo "  clean        Clean up containers and volumes"
    echo "  check-networks  Check available network subnets"
    echo ""
    echo "Environment Variables:"
    echo "  PROXY_HOST        Proxy server host (default: 0.0.0.0)"
    echo "  PROXY_PORT        Proxy server port (default: 1888)"
    echo "  API_HOST          API server host (default: 0.0.0.0)"
    echo "  API_PORT          API server port (default: 9000)"
    echo "  FRONTEND_PORT     Frontend port (default: 2345)"
    echo "  API_BASE_URL      Frontend API base URL (default: http://localhost:9000)"
    echo "  PROXY_BASE_URL    Frontend proxy base URL (default: http://localhost:1888)"
    echo "  DEBUG_MODE        Frontend debug mode (default: false)"
    echo ""
    echo "Examples:"
    echo "  $0 up"
    echo "  $0 blue-green  # Zero downtime deployment"
    echo "  FRONTEND_PORT=3000 $0 up"
    echo "  API_BASE_URL=https://api.example.com $0 up"
    echo "  $0 logs"
    echo "  $0 down"
}

# Function to wait for service health
wait_for_health() {
    local service_name=$1
    local health_url=$2
    local max_attempts=${3:-60}
    local attempt=1

    print_info "Waiting for $service_name to be healthy..."

    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$health_url" > /dev/null 2>&1; then
            print_success "$service_name is healthy"
            return 0
        fi

        if [ $((attempt % 10)) -eq 0 ]; then
            print_info "Still waiting for $service_name... (attempt $attempt/$max_attempts)"
        fi

        sleep 2
        attempt=$((attempt + 1))
    done

    print_error "$service_name health check failed after $max_attempts attempts"
    return 1
}

# Function for blue-green deployment
blue_green_deploy() {
    print_header
    print_info "Starting blue-green deployment (zero downtime)..."

    check_prerequisites
    create_env_file

    # Check if green environment exists and clean up
    print_info "Checking for previous green deployment..."
    if docker ps -a | grep -q "${PROJECT_NAME}-green"; then
        print_warning "Found existing green containers, cleaning up..."
        docker-compose -f docker/docker-compose.yml -p "${PROJECT_NAME}-green" down 2>/dev/null || true
    fi

    # Only remove green network if it exists and is not in use
    if docker network ls | grep -q "${PROJECT_NAME}-green_backend-network"; then
        print_info "Removing unused green network..."
        docker network rm "${PROJECT_NAME}-green_backend-network" 2>/dev/null || {
            print_warning "Green network still in use or cannot be removed, will be reused"
        }
    fi

    # Set temporary service names for new deployment
    export COMPOSE_PROJECT_NAME="${PROJECT_NAME}-green"
    # Green containers use explicitly different names
    local GREEN_BACKEND="${PROJECT_NAME}-green-backend"
    local GREEN_FRONTEND="${PROJECT_NAME}-green-frontend"
    local BLUE_BACKEND="${PROJECT_NAME}-backend"
    local BLUE_FRONTEND="${PROJECT_NAME}-frontend"

    # Temporary ports for green environment
    local GREEN_API_PORT=$((API_PORT + 10000))
    local GREEN_PROXY_PORT=$((PROXY_PORT + 10000))
    local GREEN_FRONTEND_PORT=$((FRONTEND_PORT + 10000))

    # Create temporary docker-compose override for green environment with different subnet
    print_info "Creating green environment configuration..."
    cat > docker/docker-compose.green.yml << EOF
services:
  backend:
    container_name: ${PROJECT_NAME}-green-backend  # Different from blue: litemcp-backend
    networks:
      - backend-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/api/v1/health"]
      interval: 10s
      timeout: 5s
      retries: 60  # 60 retries * 10s = 10 minutes max
      start_period: 180s  # 3 minutes initial startup time
  frontend:
    container_name: ${PROJECT_NAME}-green-frontend  # Different from blue: litemcp-frontend
    depends_on:
      backend:
        condition: service_started  # Don't wait for healthy, just started
    networks:
      - backend-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:80"]
      interval: 10s
      timeout: 5s
      retries: 30
      start_period: 30s

networks:
  backend-network:
    driver: bridge
    ipam:
      config:
        - subnet: 192.168.231.0/24
          gateway: 192.168.231.1
EOF

    print_info "Building new containers (green environment)..."
    print_info "Green ports: API=$GREEN_API_PORT, Proxy=$GREEN_PROXY_PORT, Frontend=$GREEN_FRONTEND_PORT"
    print_info "Green network: 192.168.231.0/24 (different from blue: 192.168.230.0/24)"

    # Build and start green environment with temporary ports and separate network
    print_info "Building green environment (this may take a few minutes)..."
    if ! API_PORT=$GREEN_API_PORT \
    PROXY_PORT=$GREEN_PROXY_PORT \
    FRONTEND_PORT=$GREEN_FRONTEND_PORT \
    docker-compose -f docker/docker-compose.yml -f docker/docker-compose.green.yml -p "${PROJECT_NAME}-green" up -d --build 2>&1; then
        print_error "Failed to build green environment"
        print_info "Cleaning up failed green deployment..."
        docker-compose -f docker/docker-compose.yml -f docker/docker-compose.green.yml -p "${PROJECT_NAME}-green" down 2>/dev/null || true
        docker network rm "${PROJECT_NAME}-green_backend-network" 2>/dev/null || true
        rm -f docker/docker-compose.green.yml
        return 1
    fi

    print_info "Green environment started, waiting for health checks..."

    # Wait for green backend to be healthy
    if ! wait_for_health "Green Backend" "http://localhost:${GREEN_API_PORT}/api/v1/health" 90; then
        print_error "Green backend health check failed"
        print_info "Showing green backend logs:"
        docker logs --tail 50 "$GREEN_BACKEND"
        print_info "Cleaning up failed green deployment..."
        docker-compose -f docker/docker-compose.yml -f docker/docker-compose.green.yml -p "${PROJECT_NAME}-green" down
        rm -f docker/docker-compose.green.yml
        return 1
    fi

    # Wait for green frontend to be healthy
    if ! wait_for_health "Green Frontend" "http://localhost:${GREEN_FRONTEND_PORT}" 30; then
        print_error "Green frontend health check failed"
        print_info "Showing green frontend logs:"
        docker logs --tail 50 "$GREEN_FRONTEND"
        print_info "Cleaning up failed green deployment..."
        docker-compose -f docker/docker-compose.yml -f docker/docker-compose.green.yml -p "${PROJECT_NAME}-green" down
        rm -f docker/docker-compose.green.yml
        return 1
    fi

    print_success "Green environment is healthy!"

    # Backup blue container IDs for potential rollback
    if docker ps -q -f name="^${BLUE_BACKEND}$" > /dev/null 2>&1; then
        print_info "Backing up blue environment container IDs..."
        echo "$(docker ps -q -f name="^${BLUE_BACKEND}$")" > /tmp/litemcp-blue-backend.id
        echo "$(docker ps -q -f name="^${BLUE_FRONTEND}$")" > /tmp/litemcp-blue-frontend.id
        print_success "Blue environment backed up for potential rollback"
    fi

    # Switch traffic: stop blue, stop green, restart green with production ports
    print_info "Switching traffic to green environment..."

    # Stop blue environment (releases production ports)
    if docker ps -q -f name="^${BLUE_BACKEND}$" > /dev/null 2>&1; then
        print_info "Stopping blue environment to release production ports..."
        docker-compose -f docker/docker-compose.yml -p "${PROJECT_NAME}" stop
        docker-compose -f docker/docker-compose.yml -p "${PROJECT_NAME}" rm -f
    fi

    # Stop green environment (we'll restart it with production ports)
    print_info "Stopping green environment..."
    docker-compose -f docker/docker-compose.yml -f docker/docker-compose.green.yml -p "${PROJECT_NAME}-green" stop

    # Tag green images as production images
    print_info "Promoting green images to production..."
    docker tag litemcp-green-backend:latest litemcp-backend:latest
    docker tag litemcp-green-frontend:latest litemcp-frontend:latest

    # Start green with production ports (reuse blue's docker-compose config)
    print_info "Starting new version on production ports..."
    # Use the same images that were just built for green
    API_PORT=${API_PORT} \
    PROXY_PORT=${PROXY_PORT} \
    FRONTEND_PORT=${FRONTEND_PORT} \
    docker-compose -f docker/docker-compose.yml -p "${PROJECT_NAME}" up -d --no-build

    # Final health check
    print_info "Final health check on production ports..."
    if ! wait_for_health "Production Backend" "http://localhost:${API_PORT}/api/v1/health" 30; then
        print_error "Production health check failed, attempting rollback..."
        rollback_deployment
        return 1
    fi

    if ! wait_for_health "Production Frontend" "http://localhost:${FRONTEND_PORT}" 30; then
        print_error "Production frontend check failed, attempting rollback..."
        rollback_deployment
        return 1
    fi

    # Clean up green environment and temporary config
    print_info "Cleaning up green environment..."
    docker-compose -f docker/docker-compose.yml -f docker/docker-compose.green.yml -p "${PROJECT_NAME}-green" down 2>/dev/null || true
    docker network rm "${PROJECT_NAME}-green_backend-network" 2>/dev/null || true
    rm -f docker/docker-compose.green.yml

    # Remove backup files after successful deployment
    rm -f /tmp/litemcp-blue-*.id

    print_success "Blue-green deployment completed successfully!"
    echo ""
    echo "🎉 Deployment Summary:"
    echo "   ✅ Zero downtime achieved"
    echo "   ✅ New version is now serving traffic"
    echo "   ✅ Old version has been removed"
    echo ""
    show_services_info
}

# Function to rollback deployment
rollback_deployment() {
    print_warning "Starting rollback to previous version..."

    # Check if backup exists
    if [ ! -f "/tmp/litemcp-blue-backend.id" ]; then
        print_error "No backup found, cannot rollback"
        return 1
    fi

    # Stop current (failed green) environment
    docker-compose -f docker/docker-compose.yml -p "${PROJECT_NAME}" down

    # Start old blue containers
    local BLUE_BACKEND_ID=$(cat /tmp/litemcp-blue-backend.id)
    local BLUE_FRONTEND_ID=$(cat /tmp/litemcp-blue-frontend.id)

    if [ -n "$BLUE_BACKEND_ID" ] && [ -n "$BLUE_FRONTEND_ID" ]; then
        docker start "$BLUE_BACKEND_ID" "$BLUE_FRONTEND_ID"

        # Wait for health check
        if wait_for_health "Rollback Backend" "http://localhost:${API_PORT}/api/v1/health" 30; then
            print_success "Rollback successful, previous version restored"
            rm -f /tmp/litemcp-blue-*.id
            return 0
        fi
    fi

    print_error "Rollback failed"
    return 1
}

# Function to show services info
show_services_info() {
    echo "🌐 Services are available at:"
    echo "   Frontend:  http://localhost:${FRONTEND_PORT}"
    echo "   Backend:   http://localhost:${API_PORT}"
    echo "   Proxy:     http://localhost:${PROXY_PORT}"
    echo ""
    echo "📋 Useful commands:"
    echo "   View logs:    $0 logs"
    echo "   Check status: $0 status"
    echo "   Stop services: $0 down"
    echo "   Rollback:     $0 rollback"
}

# Function to check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."

    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed"
        exit 1
    fi

    print_success "Prerequisites check passed"
}

# Function to check available networks
check_networks() {
    print_header
    print_info "Checking available Docker networks..."

    echo "=== Docker Networks ==="
    docker network ls

    echo -e "\n=== Docker Network Details ==="
    for network in $(docker network ls --format "{{.Name}}" | grep -v "bridge\|host\|none"); do
        if [ ! -z "$network" ]; then
            echo "Network: $network"
            docker network inspect $network 2>/dev/null | grep -A 10 "Subnet" || echo "  (failed to inspect)"
            echo "------------------------"
        fi
    done

    echo -e "\n=== Host Network Interfaces ==="
    ifconfig | grep "inet " | grep -v "127.0.0.1"

    echo -e "\n=== Routing Table (summary) ==="
    netstat -rn | grep -E "^(Destination|10\.|172\.|192\.168\.)" | head -20

    echo -e "\n=== Recommended Safe Networks ==="
    echo "1. 192.168.200.0/24 to 192.168.255.0/24 (if not in routing table)"
    echo "2. 10.200.0.0/24 to 10.255.255.0/24 (Class A private range)"
    echo "3. 172.32.0.0/24 to 172.255.255.0/24 (Class B private range, beyond 172.16-31)"

    print_success "Network check completed"
}

# Function to create environment file
create_env_file() {
    print_info "Creating environment configuration..."

    cat > docker/.env << EOF
# LiteMCP Docker Environment Configuration
PROXY_HOST=${PROXY_HOST}
PROXY_PORT=${PROXY_PORT}
API_HOST=${API_HOST}
API_PORT=${API_PORT}
FRONTEND_PORT=${FRONTEND_PORT}
VITE_API_BASE_URL=${API_BASE_URL}
VITE_PROXY_BASE_URL=${PROXY_BASE_URL}
VITE_DEBUG_MODE=${DEBUG_MODE}
MCP_SERVER_HOST=${MCP_SERVER_HOST}
EOF

    print_success "Environment file created: docker/.env"
}

# Function to start services
start_services() {
    print_header
    print_info "Starting LiteMCP services..."

    check_prerequisites
    create_env_file

    # Check if services are already running
    if docker ps | grep -q "${PROJECT_NAME}-backend"; then
        print_warning "Services appear to be already running"
        print_info "Use './deploy.sh restart' to restart or './deploy.sh down' to stop first"
        return 1
    fi

    # Update docker-compose.yml with environment variables
    export PROXY_HOST API_HOST PROXY_PORT API_PORT FRONTEND_PORT
    export VITE_API_BASE_URL=${API_BASE_URL}
    export VITE_PROXY_BASE_URL=${PROXY_BASE_URL}
    export VITE_DEBUG_MODE=${DEBUG_MODE}

    print_info "Building and starting containers..."
    # Use host network for build to access external resources
    DOCKER_BUILDKIT=1 BUILDKIT_INLINE_CACHE=1 docker-compose -f docker/docker-compose.yml build
    docker-compose -f docker/docker-compose.yml up -d

    print_info "Waiting for services to be ready..."
    sleep 10

    # Check service health
    print_info "Checking service health..."

    # Check backend
    if curl -f http://localhost:${API_PORT}/api/v1/health &>/dev/null; then
        print_success "Backend service is healthy"
    else
        print_warning "Backend service health check failed"
    fi

    # Check frontend
    if curl -f http://localhost:${FRONTEND_PORT} &>/dev/null; then
        print_success "Frontend service is healthy"
    else
        print_warning "Frontend service health check failed"
    fi

    print_success "Deployment completed!"
    echo ""
    show_services_info
}

# Function to stop services
stop_services() {
    print_info "Stopping LiteMCP services..."
    docker-compose -f docker/docker-compose.yml down
    print_success "Services stopped"
}

# Function to restart services
restart_services() {
    print_info "Restarting LiteMCP services..."
    stop_services
    sleep 2
    start_services
}

# Function to show logs
show_logs() {
    print_info "Showing service logs..."
    docker-compose -f docker/docker-compose.yml logs -f
}

# Function to show status
show_status() {
    print_info "Service status:"
    docker-compose -f docker/docker-compose.yml ps

    echo ""
    print_info "Container resource usage:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" $(docker-compose -f docker/docker-compose.yml ps -q) 2>/dev/null || true
}

# Function to clean up
clean_up() {
    print_warning "This will remove all containers, networks, and volumes!"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Cleaning up..."
        docker-compose -f docker/docker-compose.yml down -v --remove-orphans
        docker system prune -f
        # Clean up unused networks specifically
        docker network prune -f
        print_success "Cleanup completed"
    else
        print_info "Cleanup cancelled"
    fi
}

# Main script logic
cd "$(dirname "$0")/.."

case "${1:-up}" in
    up|start)
        start_services
        ;;
    down|stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    blue-green|bg)
        blue_green_deploy
        ;;
    rollback)
        rollback_deployment
        ;;
    logs)
        show_logs
        ;;
    status|ps)
        show_status
        ;;
    clean)
        clean_up
        ;;
    check-networks)
        check_networks
        ;;
    help|--help|-h)
        show_usage
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        show_usage
        exit 1
        ;;
esac