#!/bin/bash

# Scion Multi-Material Printer Web Interface Installation Script

echo "=========================================="
echo "Scion MMU Web Interface Installation"
echo "=========================================="

# Check if we're in the right directory
if [ ! -f "app.py" ]; then
    echo "Error: Please run this script from the web-app directory"
    exit 1
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install -r requirements.txt

# Create systemd service file for auto-start (optional)
read -p "Create systemd service for auto-start? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cat > /tmp/scion-mmu-web.service << EOF
[Unit]
Description=Scion Multi-Material Printer Web Interface
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=$(pwd)
Environment=PATH=/usr/bin:/usr/local/bin
ExecStart=/usr/bin/python3 app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    sudo mv /tmp/scion-mmu-web.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable scion-mmu-web.service

    echo "Systemd service created. Use 'sudo systemctl start scion-mmu-web' to start."
fi

echo ""
echo "Installation complete!"
echo ""
echo "To start the web interface:"
echo "  python3 app.py"
echo ""
echo "Then open your browser to:"
echo "  http://localhost:5000"
echo "  or http://$(hostname -I | awk '{print $1}'):5000"
echo ""
echo "The web interface provides:"
echo "  • Visual recipe builder"
echo "  • Real-time sequence timing control"
echo "  • Step-by-step material change debugging"
echo "  • Manual pump controls with timing adjustment"
echo "  • Live process monitoring"
echo "=========================================="