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
    echo "  up      Start all services (default)"
    echo "  down    Stop all services"
    echo "  restart Restart all services"
    echo "  logs    Show logs"
    echo "  status  Show service status"
    echo "  clean   Clean up containers and volumes"
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
    echo "  FRONTEND_PORT=3000 $0 up"
    echo "  API_BASE_URL=https://api.example.com $0 up"
    echo "  $0 logs"
    echo "  $0 down"
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

    # Update docker-compose.yml with environment variables
    export PROXY_HOST API_HOST PROXY_PORT API_PORT FRONTEND_PORT
    export VITE_API_BASE_URL=${API_BASE_URL}
    export VITE_PROXY_BASE_URL=${PROXY_BASE_URL}
    export VITE_DEBUG_MODE=${DEBUG_MODE}

    print_info "Building and starting containers..."
    docker-compose -f docker/docker-compose.yml up -d --build

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
    echo "🌐 Services are available at:"
    echo "   Frontend:  http://localhost:${FRONTEND_PORT}"
    echo "   Backend:   http://localhost:${API_PORT}"
    echo "   Proxy:     http://localhost:${PROXY_PORT}"
    echo ""
    echo "📋 Useful commands:"
    echo "   View logs:    $0 logs"
    echo "   Check status: $0 status"
    echo "   Stop services: $0 down"
    echo "   Check networks: $0 check-networks"
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