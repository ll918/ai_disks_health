#!/bin/bash
# Docker entrypoint script for AI Disk Health Monitor

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

# Start Ollama service
start_ollama() {
    log "Starting Ollama service..."
    sudo service ollama start

    # Wait for Ollama to be ready
    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
            success "Ollama service is ready"
            return 0
        fi

        log "Waiting for Ollama to start... (attempt $attempt/$max_attempts)"
        sleep 2
        attempt=$((attempt + 1))
    done

    error "Ollama failed to start within timeout"
    return 1
}

# Run the application
run_application() {
    log "Starting AI Disk Health Monitor..."

    # Activate virtual environment
    source venv/bin/activate

    # Run the application with provided arguments
    exec python3 main.py "$@"
}

# Handle graceful shutdown
shutdown_handler() {
    log "Received shutdown signal, stopping services..."
    sudo service ollama stop
    exit 0
}

# Set up signal handlers
trap shutdown_handler SIGTERM SIGINT

# Main execution
main() {
    echo "🚀 AI Disk Health Monitor - Docker Container"
    echo "================================================"

    # Start Ollama
    start_ollama

    # Run application
    run_application "$@"
}

# Run main function
main "$@"
