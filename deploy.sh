#!/bin/bash
# deploy.sh - Automated deployment script for AI Disk Health Monitor

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="https://github.com/ll918/ai_disks_health.git"
INSTALL_DIR="/opt/ai-disk-health"
PYTHON_VERSION="3.8"
OLLAMA_MODEL="gemma3:1b"

# Logging function
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

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        warning "Running as root. This is recommended for system-wide installation."
    else
        warning "Not running as root. Some features may require sudo privileges."
    fi
}

# Check system requirements
check_requirements() {
    log "Checking system requirements..."

    # Check Ubuntu/Debian
    if ! command -v apt-get &> /dev/null; then
        error "This script requires Ubuntu/Debian with apt package manager"
        exit 1
    fi

    # Check Python version
    if ! command -v python3 &> /dev/null; then
        error "Python 3 is required but not installed"
        exit 1
    fi

    PYTHON_VER=$(python3 --version 2>&1 | cut -d' ' -f2)
    log "Found Python version: $PYTHON_VER"

    success "System requirements check completed"
}

# Install system dependencies
install_system_deps() {
    log "Installing system dependencies..."

    sudo apt update
    sudo apt install -y \
        python3 \
        python3-pip \
        smartmontools \
        git \
        curl \
        wget \
        jq

    success "System dependencies installed"
}

# Install Ollama
install_ollama() {
    log "Installing Ollama..."

    if command -v ollama &> /dev/null; then
        success "Ollama already installed"
        return 0
    fi

    curl -fsSL https://ollama.com/install.sh | sh

    # Add current user to ollama group
    sudo usermod -a -G ollama $USER

    success "Ollama installed"
}

# Download and setup application
setup_application() {
    log "Setting up AI Disk Health Monitor..."

    # Create installation directory
    sudo mkdir -p $INSTALL_DIR
    sudo chown $(whoami):$(whoami) $INSTALL_DIR

    # Clone repository
    if [ -d "$INSTALL_DIR/.git" ]; then
        log "Repository already exists, pulling latest changes..."
        cd $INSTALL_DIR
        git pull
    else
        log "Cloning repository..."
        git clone $REPO_URL $INSTALL_DIR
        cd $INSTALL_DIR
    fi

    # Install Python dependencies
    log "Installing Python dependencies..."
    pip3 install -r requirements.txt

    success "Application setup completed"
}

# Download AI model
download_model() {
    log "Downloading AI model: $OLLAMA_MODEL..."

    if ollama list | grep -q $OLLAMA_MODEL; then
        success "Model $OLLAMA_MODEL already downloaded"
    else
        ollama pull $OLLAMA_MODEL
        success "Model $OLLAMA_MODEL downloaded"
    fi
}

# Create systemd service
create_service() {
    log "Creating systemd service..."

    SERVICE_FILE="/etc/systemd/system/ai-disk-health.service"

    sudo tee $SERVICE_FILE > /dev/null <<EOF
[Unit]
Description=AI Disk Health Monitor
After=network.target ollama.service
Requires=ollama.service

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/python3 $INSTALL_DIR/main.py --save
Restart=always
RestartSec=300
Environment=PYTHONPATH=$INSTALL_DIR

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable ai-disk-health

    success "Systemd service created and enabled"
}

# Create convenience scripts
create_scripts() {
    log "Creating convenience scripts..."

    # Main script
    sudo tee /usr/local/bin/ai-disk-health > /dev/null <<'EOF'
#!/bin/bash
cd $INSTALL_DIR
exec python3 main.py "$@"
EOF

    sudo chmod +x /usr/local/bin/ai-disk-health

    # Update script
    sudo tee /usr/local/bin/ai-disk-health-update > /dev/null <<'EOF'
#!/bin/bash
cd $INSTALL_DIR
git pull
pip3 install -r requirements.txt --upgrade
ollama pull gemma3:1b
systemctl restart ai-disk-health
echo "AI Disk Health Monitor updated successfully"
EOF

    sudo chmod +x /usr/local/bin/ai-disk-health-update

    success "Convenience scripts created"
}

# Test installation
test_installation() {
    log "Testing installation..."

    cd $INSTALL_DIR

    # Check dependencies
    if python3 main.py --check-deps; then
        success "Dependency check passed"
    else
        warning "Some dependencies may be missing, but installation can continue"
    fi

    # Test basic functionality
    log "Running basic functionality test..."
    if timeout 30 python3 main.py --json > /dev/null 2>&1; then
        success "Basic functionality test passed"
    else
        warning "Basic test had issues, but installation may still work"
    fi
}

# Display summary
show_summary() {
    echo ""
    echo "========================================"
    echo "🎉 AI Disk Health Monitor Deployment Complete!"
    echo "========================================"
    echo ""
    echo "Installation Directory: $INSTALL_DIR"
    echo "Service Name: ai-disk-health"
    echo "AI Model: $OLLAMA_MODEL"
    echo ""
    echo "Available Commands:"
    echo "  ai-disk-health              - Run analysis manually"
    echo "  ai-disk-health --verbose    - Run with detailed output"
    echo "  ai-disk-health --save       - Save report to file"
    echo "  ai-disk-health --json       - Output in JSON format"
    echo "  ai-disk-health-update       - Update application"
    echo ""
    echo "Service Management:"
    echo "  systemctl start ai-disk-health    - Start service"
    echo "  systemctl stop ai-disk-health     - Stop service"
    echo "  systemctl status ai-disk-health   - Check status"
    echo "  journalctl -u ai-disk-health -f   - View logs"
    echo ""
    echo "Next Steps:"
    echo "1. Run 'ai-disk-health' to perform initial analysis"
    echo "2. Check logs with 'journalctl -u ai-disk-health -f'"
    echo "3. Configure monitoring schedule if needed"
    echo ""
    echo "For more information, see: $INSTALL_DIR/README.md"
    echo "========================================"
}

# Main execution
main() {
    echo "🚀 AI Disk Health Monitor - Automated Deployment"
    echo "================================================"
    echo ""

    check_root
    check_requirements
    install_system_deps
    install_ollama
    setup_application
    download_model
    create_service
    create_scripts
    test_installation
    show_summary
}

# Run main function
main "$@"
