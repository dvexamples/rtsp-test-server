#!/bin/bash
set -e

# Detect the absolute path of the directory where this script is located
APP_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
echo "Setting up single dynamic RTSP service in $APP_DIR..."

# 1. Stop and remove all old multi-port RTSP services
echo "Cleaning up old RTSP services..."
OLD_SERVICES=$(systemctl list-unit-files 'rtspserver*' --no-legend 2>/dev/null | awk '{print $1}') || true

if [ -n "$OLD_SERVICES" ]; then
    for s in $OLD_SERVICES; do
        systemctl stop "$s" 2>/dev/null || true
        systemctl disable "$s" 2>/dev/null || true
    done
fi

rm -f /etc/systemd/system/rtspserver*.service
systemctl daemon-reload
systemctl reset-failed 2>/dev/null || true

# 2. Update the Git repository
echo "Pulling latest changes from Git..."
cd "$APP_DIR"
git reset --hard HEAD
git pull origin main || git pull

# 3. Ensure all GStreamer dependencies are installed
echo "Verifying package dependencies..."
apt-get update
apt-get install -y python3 \
                   gstreamer1.0-tools \
                   gstreamer1.0-plugins-base \
                   gstreamer1.0-plugins-good \
                   gstreamer1.0-plugins-bad \
                   gstreamer1.0-plugins-ugly \
                   gstreamer1.0-libav \
                   libgstrtspserver-1.0-dev \
                   python3-gst-1.0

# 4. Create a single systemd service file for the dynamic server
echo "Configuring single dynamic RTSP service..."
cat <<EOF > /etc/systemd/system/rtspserver.service
[Unit]
Description=Dynamic Multi-Stream RTSP Server for QGroundControl
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$APP_DIR
ExecStart=/usr/bin/python3 $APP_DIR/test_server.py --port 8554
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# 5. Enable and start the single service
systemctl daemon-reload
systemctl enable rtspserver
systemctl start rtspserver

echo "=================================================="
echo "Setup complete! Single dynamic RTSP server is active."
echo "Port: 8554"
echo "Syntax: rtsp://<droplet-ip>:8554/<codec>/<resolution>/<pattern>"
echo "Example: rtsp://<droplet-ip>:8554/h264/720p/ball"
echo "=================================================="
