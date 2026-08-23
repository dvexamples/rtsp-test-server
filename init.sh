#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Detect the absolute path of the directory where this script is located
APP_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)

echo "Setting up environment in $APP_DIR..."

# 1. Update package lists
apt-get update

# 2. Install Python and ALL required GStreamer dependencies [залежності]
apt-get install -y python3 \
                   gstreamer1.0-tools \
                   gstreamer1.0-plugins-base \
                   gstreamer1.0-plugins-good \
                   gstreamer1.0-plugins-bad \
                   gstreamer1.0-plugins-ugly \
                   gstreamer1.0-libav \
                   libgstrtspserver-1.0-dev \
                   python3-gst-1.0

# 3. Create a systemd service file [файл служби systemd]
echo "Configuring systemd service..."
cat <<EOF > /etc/systemd/system/rtspserver.service
[Unit]
Description=RTSP Test Server for QGroundControl
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$APP_DIR
ExecStart=/usr/bin/python3 $APP_DIR/test_server.py --codec h264 --res 720p --pattern smpte
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# 4. Reload the daemon [фоновий процес], enable, and start the service
systemctl daemon-reload
systemctl enable rtspserver
systemctl restart rtspserver

echo "Setup complete! The RTSP server is now running in the background."
