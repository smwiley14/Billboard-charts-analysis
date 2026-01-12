#!/bin/bash
# Deployment script for Billboard Charts Dashboard on Digital Ocean
# This script sets up the dashboard as a systemd service

set -e

echo "🚀 Starting Billboard Dashboard Deployment..."

# Configuration
DASHBOARD_DIR="/opt/billboard-dashboard"
SERVICE_NAME="billboard-dashboard"
USER="root"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Please run as root (use sudo)"
    exit 1
fi

# Create directory
echo "📁 Creating dashboard directory..."
mkdir -p $DASHBOARD_DIR

# Copy files (assuming we're in the project root)
echo "📋 Copying dashboard files..."
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

cp $PROJECT_DIR/dashboard.py $DASHBOARD_DIR/
cp $PROJECT_DIR/requirements.txt $DASHBOARD_DIR/

# Check for .env file
if [ ! -f "$DASHBOARD_DIR/.env" ]; then
    echo "⚠️  .env file not found. Creating template..."
    cat > $DASHBOARD_DIR/.env << EOF
# Database connection string
# Format: postgresql+psycopg2://username:password@host:port/database
# Example: postgresql+psycopg2://airflow:password@localhost:5432/music_warehouse
MUSIC_WAREHOUSE_DATABASE_URL=postgresql+psycopg2://user:password@host:5432/music_warehouse
EOF
    echo "✏️  Please edit $DASHBOARD_DIR/.env with your database credentials"
    echo "   Then run this script again to continue deployment"
    exit 1
fi

# Create virtual environment
echo "🐍 Setting up Python virtual environment..."
if [ ! -d "$DASHBOARD_DIR/venv" ]; then
    python3 -m venv $DASHBOARD_DIR/venv
fi

# Install dependencies
echo "📦 Installing Python dependencies..."
$DASHBOARD_DIR/venv/bin/pip install --upgrade pip
$DASHBOARD_DIR/venv/bin/pip install -r $DASHBOARD_DIR/requirements.txt

# Install systemd service
echo "⚙️  Installing systemd service..."
cp $SCRIPT_DIR/dashboard.service /etc/systemd/system/$SERVICE_NAME.service
systemctl daemon-reload
systemctl enable $SERVICE_NAME

# Start service
echo "🔄 Starting dashboard service..."
systemctl restart $SERVICE_NAME

# Check status
sleep 2
if systemctl is-active --quiet $SERVICE_NAME; then
    echo "✅ Dashboard service is running!"
    echo ""
    echo "📊 Dashboard should be available at: http://$(hostname -I | awk '{print $1}'):8501"
    echo ""
    echo "Useful commands:"
    echo "  - View logs: sudo journalctl -u $SERVICE_NAME -f"
    echo "  - Restart: sudo systemctl restart $SERVICE_NAME"
    echo "  - Stop: sudo systemctl stop $SERVICE_NAME"
    echo "  - Status: sudo systemctl status $SERVICE_NAME"
else
    echo "❌ Service failed to start. Check logs with:"
    echo "   sudo journalctl -u $SERVICE_NAME -n 50"
    exit 1
fi

