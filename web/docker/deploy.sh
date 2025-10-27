#!/bin/bash

# LiteMCP Frontend Deployment Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Default values
COMMAND=""
ENVIRONMENT="production"
API_BASE_URL=""
PROXY_BASE_URL=""
BUILD_ONLY=false

# Show help function
show_help() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  up       Start frontend service (default)"
    echo "  down     Stop frontend service"
    echo "  restart  Restart frontend service"
    echo "  logs     Show frontend service logs"
    echo "  status   Show frontend service status"
    echo "  build    Build frontend application"
    echo ""
    echo "Options:"
    echo "  -e, --environment    Environment (development|staging|production) [default: production]"
    echo "  -a, --api-url        API base URL"
    echo "  -p, --proxy-url      Proxy base URL"
    echo "  -b, --build-only     Only build, don't deploy"
    echo "  -h, --help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 up --environment production --api-url https://api.example.com"
    echo "  $0 build --build-only"
    echo "  $0 down"
    echo "  $0 logs"
}

# Parse command line arguments
if [[ $# -gt 0 ]] && [[ ! "$1" =~ ^- ]]; then
    COMMAND="$1"
    shift
fi

while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -a|--api-url)
            API_BASE_URL="$2"
            shift 2
            ;;
        -p|--proxy-url)
            PROXY_BASE_URL="$2"
            shift 2
            ;;
        -b|--build-only)
            BUILD_ONLY=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Set default command if none provided
if [[ -z "$COMMAND" ]]; then
    if [[ "$BUILD_ONLY" == "true" ]]; then
        COMMAND="build"
    else
        COMMAND="up"
    fi
fi

print_info "Starting LiteMCP Frontend deployment..."
print_info "Environment: $ENVIRONMENT"

# Check if Docker is installed for build commands
if [[ "$COMMAND" == "build" || "$COMMAND" == "up" ]]; then
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
fi

# Set environment variables
if [ ! -z "$API_BASE_URL" ]; then
    export VITE_API_BASE_URL="$API_BASE_URL"
    print_info "API Base URL: $API_BASE_URL"
fi

if [ ! -z "$PROXY_BASE_URL" ]; then
    export VITE_PROXY_BASE_URL="$PROXY_BASE_URL"
    print_info "Proxy Base URL: $PROXY_BASE_URL"
fi

# Set environment-specific variables
case $ENVIRONMENT in
    development)
        export VITE_DEBUG_MODE=true
        export VITE_LOG_LEVEL=debug
        ;;
    staging)
        export VITE_DEBUG_MODE=true
        export VITE_LOG_LEVEL=info
        ;;
    production)
        export VITE_DEBUG_MODE=false
        export VITE_LOG_LEVEL=error
        ;;
    *)
        print_error "Invalid environment: $ENVIRONMENT"
        exit 1
        ;;
esac

# Function to build the application
build_application() {
    print_info "Building application using Docker (Node.js 18)..."
    print_info "Environment: $ENVIRONMENT"

    # Create build arguments for Docker
    BUILD_ARGS=""
    if [ ! -z "$VITE_API_BASE_URL" ]; then
        BUILD_ARGS="$BUILD_ARGS --build-arg VITE_API_BASE_URL=$VITE_API_BASE_URL"
    fi
    if [ ! -z "$VITE_PROXY_BASE_URL" ]; then
        BUILD_ARGS="$BUILD_ARGS --build-arg VITE_PROXY_BASE_URL=$VITE_PROXY_BASE_URL"
    fi
    if [ ! -z "$VITE_DEBUG_MODE" ]; then
        BUILD_ARGS="$BUILD_ARGS --build-arg VITE_DEBUG_MODE=$VITE_DEBUG_MODE"
    fi

    # Build Docker image with proper Node.js version (target builder stage)
    docker build -f Dockerfile --target builder -t litemcp-frontend-builder $BUILD_ARGS ..

    # Extract built files from Docker image
    print_info "Extracting built files from Docker container..."
    # Clean up any existing temp container
    docker rm temp-frontend 2>/dev/null || true
    docker create --name temp-frontend litemcp-frontend-builder
    docker cp temp-frontend:/app/dist ./dist
    docker rm temp-frontend

    print_success "Build completed successfully using Docker (Node.js 18)!"
}

# Handle commands
case "$COMMAND" in
    "build")
        build_application
        if [ "$BUILD_ONLY" = true ]; then
            print_info "Build-only mode. Deployment files are in ./dist/"
        else
            print_info "Build files are ready in ./dist/"
        fi
        exit 0
        ;;
    "up")
        print_info "Building and starting frontend service..."
        if command -v docker-compose &> /dev/null; then
            # Create environment file for docker-compose
            cat > .env << EOF
VITE_API_BASE_URL=${VITE_API_BASE_URL}
VITE_PROXY_BASE_URL=${VITE_PROXY_BASE_URL}
VITE_DEBUG_MODE=${VITE_DEBUG_MODE}
EOF
            # Build and start the service
            print_info "Building Docker image and starting container..."
            docker-compose up -d --build
            
            # Check if service started successfully
            if [ $? -eq 0 ]; then
                print_success "Frontend service started successfully!"
                print_info "Service is available at: http://localhost:2345"
            else
                print_error "Failed to start frontend service"
                exit 1
            fi
        else
            print_error "docker-compose not found. Please install Docker Compose."
            exit 1
        fi
        ;;
    "down")
        print_info "Stopping frontend service..."
        if command -v docker-compose &> /dev/null; then
            docker-compose down
            print_success "Frontend service stopped successfully!"
        else
            print_error "docker-compose not found."
            exit 1
        fi
        ;;
    "restart")
        print_info "Restarting frontend service..."
        if command -v docker-compose &> /dev/null; then
            docker-compose restart
            print_success "Frontend service restarted successfully!"
        else
            print_error "docker-compose not found."
            exit 1
        fi
        ;;
    "logs")
        print_info "Showing frontend service logs..."
        if command -v docker-compose &> /dev/null; then
            docker-compose logs -f
        else
            print_error "docker-compose not found."
            exit 1
        fi
        ;;
    "status")
        print_info "Frontend service status:"
        if command -v docker-compose &> /dev/null; then
            docker-compose ps
        else
            print_error "docker-compose not found."
            exit 1
        fi
        ;;
    *)
        print_error "Unknown command: $COMMAND"
        show_help
        exit 1
        ;;
esac
