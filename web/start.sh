#!/bin/bash

# LiteMCP Web Frontend Startup Script (Linux/macOS)

set -e

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored messages
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

# Check Node.js environment
check_nodejs() {
    print_info "Checking Node.js environment..."
    
    if ! command -v node &> /dev/null; then
        print_error "Node.js is not installed! Please install Node.js version 16+"
        echo "Installation methods:"
        echo "  macOS: brew install node"
        echo "  Linux: sudo apt install nodejs npm"
        echo "  Or visit: https://nodejs.org/"
        exit 1
    fi
    
    NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
    if [ "$NODE_VERSION" -lt 16 ]; then
        print_error "Node.js version is too low! Current version: $(node --version), requires version 16+"
        exit 1
    fi
    
    print_success "Node.js environment check passed: $(node --version)"
}

# Check npm
check_npm() {
    if ! command -v npm &> /dev/null; then
        print_error "npm is not installed! Please install npm"
        exit 1
    fi
    print_success "npm version: $(npm --version)"
}

# Install dependencies
install_dependencies() {
    print_info "Checking and installing frontend dependencies..."
    
    if [ ! -d "node_modules" ] || [ ! -f "package-lock.json" ]; then
        print_info "Installing dependencies..."
        npm install
        print_success "Dependencies installed successfully"
    else
        print_info "Dependencies already exist, skipping installation"
    fi
}

# Check backend service
check_backend() {
    print_info "Checking backend service status..."
    
    if curl -s http://localhost:9000/health > /dev/null 2>&1; then
        print_success "Backend service is running normally (http://localhost:9000)"
    else
        print_warning "Backend service is not started, please start the backend service first:"
        echo "  cd .."
        echo "  ./scripts/manage.sh up"
        echo ""
        print_info "Continuing to start frontend service..."
    fi
}

# Start development server
start_dev_server() {
    print_info "Starting frontend development server..."
    print_info "Service address: http://localhost:2345"
    print_info "Press Ctrl+C to stop the service"
    echo ""
    
    npm run dev
}

# Main function
main() {
    echo "🚀 LiteMCP Web Frontend Startup Script"
    echo "================================"
    
    # Check environment
    check_nodejs
    check_npm
    
    # Install dependencies
    install_dependencies
    
    # Check backend
    check_backend
    
    # Start service
    start_dev_server
}

# Run main function
main "$@"