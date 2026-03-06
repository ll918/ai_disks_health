# Deployment Guide

This guide explains how to deploy the AI Disk Health Monitor to various server environments.

## Prerequisites

- Ubuntu/Linux server
- Python 3.8+
- SSH access to the server
- Ollama installed on the server (for AI analysis)

## Deployment Methods

### Method 1: Manual Deployment

1. **Connect to your server:**
   ```bash
   ssh username@your-server-ip
   ```

2. **Install system dependencies:**
   ```bash
   sudo apt update
   sudo apt install -y python3 python3-pip smartmontools
   ```

3. **Install Ollama:**
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   sudo usermod -a -G ollama $USER
   ```

4. **Download the application:**
   ```bash
   git clone https://github.com/ll918/ai_disks_health.git
   cd ai_disks_health
   ```

5. **Install Python dependencies:**
   ```bash
   pip3 install -r requirements.txt
   ```

6. **Download the AI model:**
   ```bash
   ollama pull gemma3:1b
   ```

7. **Test the application:**
   ```bash
   python3 main.py --check-deps
   ```

### Method 2: Automated Deployment Script

Create a deployment script for automated setup:

```bash
#!/bin/bash
# deploy.sh

set -e

echo "🚀 Starting AI Disk Health Monitor deployment..."

# Update system
sudo apt update && sudo apt upgrade -y

# Install system dependencies
sudo apt install -y python3 python3-pip smartmontools git

# Install Ollama
echo "📦 Installing Ollama..."
curl -fsSL https://ollama.com/install.sh | sh
sudo usermod -a -G ollama $USER

# Clone repository
echo "📥 Cloning repository..."
git clone https://github.com/ll918/ai_disks_health.git
cd ai_disks_health

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
pip3 install -r requirements.txt

# Download AI model
echo "🤖 Downloading AI model..."
ollama pull gemma3:1b

echo "✅ Deployment completed!"
echo "Run: cd ai_disks_health && python3 main.py"
```

Usage:
```bash
chmod +x deploy.sh
./deploy.sh
```

### Method 3: Docker Deployment

1. **Create Dockerfile:**
   ```dockerfile
   FROM ubuntu:22.04

   # Install system dependencies
   RUN apt-get update && apt-get install -y \
       python3 \
       python3-pip \
       smartmontools \
       git \
       curl \
       && rm -rf /var/lib/apt/lists/*

   # Install Ollama
   RUN curl -fsSL https://ollama.com/install.sh | sh

   # Set working directory
   WORKDIR /app

   # Copy application files
   COPY . .

   # Install Python dependencies
   RUN pip3 install -r requirements.txt

   # Download AI model
   RUN ollama pull gemma3:1b

   # Set entry point
   CMD ["python3", "main.py"]
   ```

2. **Build and run:**
   ```bash
   docker build -t ai-disk-health .
   docker run -it --privileged ai-disk-health
   ```

## Configuration

### Environment Variables

Set these environment variables for customization:

```bash
export AI_MODEL="gemma3:1b"           # AI model to use
export LOG_LEVEL="INFO"               # Logging level
export REPORT_DIR="/var/reports"      # Directory for saved reports
```

### Systemd Service

Create a systemd service for automatic monitoring:

1. **Create service file:**
   ```bash
   sudo nano /etc/systemd/system/ai-disk-health.service
   ```

2. **Add service configuration:**
   ```ini
   [Unit]
   Description=AI Disk Health Monitor
   After=network.target

   [Service]
   Type=simple
   User=root
   WorkingDirectory=/path/to/ai_disks_health
   ExecStart=/usr/bin/python3 main.py --save
   Restart=always
   RestartSec=300

   [Install]
   WantedBy=multi-user.target
   ```

3. **Enable and start service:**
   ```bash
   sudo systemctl enable ai-disk-health
   sudo systemctl start ai-disk-health
   ```

## Monitoring and Maintenance

### Regular Updates

Update the application regularly:

```bash
cd /path/to/ai_disks_health
git pull
pip3 install -r requirements.txt --upgrade
ollama pull gemma3:1b
```

### Log Monitoring

Monitor application logs:

```bash
# View service logs
sudo journalctl -u ai-disk-health -f

# View recent logs
sudo journalctl -u ai-disk-health --since "1 hour ago"
```

### Disk Space Management

Clean up old reports:

```bash
# Remove reports older than 30 days
find /var/reports -name "*.txt" -mtime +30 -delete
```

## Troubleshooting

### Common Issues

1. **Ollama not accessible:**
   ```bash
   # Check if Ollama is running
   sudo systemctl status ollama

   # Restart Ollama
   sudo systemctl restart ollama
   ```

2. **Permission denied for disk access:**
   ```bash
   # Run with sudo
   sudo python3 main.py
   ```

3. **smartctl not found:**
   ```bash
   # Install smartmontools
   sudo apt install smartmontools
   ```

### Health Checks

Verify deployment:

```bash
# Check dependencies
python3 main.py --check-deps

# Run test analysis
python3 main.py --verbose

# Check service status
sudo systemctl status ai-disk-health
```

## Security Considerations

- Run the application with minimal required privileges
- Secure SSH access with key-based authentication
- Regularly update system and application dependencies
- Monitor logs for suspicious activity
- Consider running in a container for isolation

## Performance Optimization

- Use SSD storage for better I/O performance
- Allocate sufficient RAM for AI model loading
- Schedule analysis during off-peak hours
- Monitor system resources during operation

## Support

For deployment issues or questions:
1. Check the troubleshooting section above
2. Review system logs
3. Verify all dependencies are installed
4. Ensure proper permissions are set
