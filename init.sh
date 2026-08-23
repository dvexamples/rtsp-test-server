#!/bin/bash

echo "Starting environment setup..."

# 1. Update package lists
apt-get update

# 2. Install Python, Git, and GStreamer dependencies
apt-get install -y git python3 gstreamer1.0-tools gstreamer1.0-plugins-base \
                   gstreamer1.0-plugins-good gstreamer1.0-plugins-bad \
                   libgstrtspserver-1.0-dev python3-gst-1.0

# 3. Define the deployment directory and clone the repository
APP_DIR="/opt/rtsp-test-server"

if [ ! -d "$APP_DIR" ]; then
    echo "Cloning repository..."
    git clone https://github.com/dvexamples/rtsp-test-server.git $APP_DIR
else
    echo "Repository already exists. Pulling latest changes..."
    cd $APP_DIR && git pull
fi

# 4. Create a systemd service file
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

# 5. Reload the daemon [фоновий процес], enable, and start the service
systemctl daemon-reload
systemctl enable rtspserver
systemctl restart rtspserver

echo "Setup complete! The RTSP server is now running on port 8554."
