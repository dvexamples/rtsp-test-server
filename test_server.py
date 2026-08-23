#!/bin/bash
set -e

# Detect the absolute path of the directory where this script is located
APP_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
echo "Managing RTSP test server suite in $APP_DIR..."

# 1. Stop and remove any existing RTSP services [зупинка та видалення існуючих служб]
echo "Stopping existing RTSP services..."
EXISTING_SERVICES=$(systemctl list-unit-files 'rtspserver*' --no-legend 2>/dev/null | awk '{print $1}') || true

if [ -n "$EXISTING_SERVICES" ]; then
    for s in $EXISTING_SERVICES; do
        systemctl stop "$s" 2>/dev/null || true
        systemctl disable "$s" 2>/dev/null || true
    done
fi

# Clean up old service unit files [файли конфігурації служб]
rm -f /etc/systemd/system/rtspserver*.service
systemctl daemon-reload
systemctl reset-failed 2>/dev/null || true

# 2. Update the Git repository [оновлення репозиторію Git]
echo "Pulling latest changes from Git..."
cd "$APP_DIR"
git pull origin main || git pull

# 3. Ensure all GStreamer dependencies are installed [перевірка залежностей]
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

# 4. Define parameter combinations [комбінації параметрів]
CODECS=("h264" "h265" "mjpeg")
RESOLUTIONS=("720p" "1024p")
PATTERNS=("smpte" "zone-plate" "ball" "snow" "checkers1" "blink")

# Starting port [початковий порт]
PORT=8500

echo "Generating and starting all permutation services..."
for c in "${CODECS[@]}"; do
    for r in "${RESOLUTIONS[@]}"; do
        for p in "${PATTERNS[@]}"; do
            
            SERVICE_NAME="rtspserver-${c}-${r}-${p}"
            
            cat <<EOF > /etc/systemd/system/${SERVICE_NAME}.service
[Unit]
Description=RTSP Test Server: Codec $c | Res $r | Pattern $p | Port $PORT
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$APP_DIR
ExecStart=/usr/bin/python3 $APP_DIR/test_server.py --codec $c --res $r --pattern $p --port $PORT
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
            
            systemctl enable "${SERVICE_NAME}"
            systemctl start "${SERVICE_NAME}"
            echo "Started $SERVICE_NAME on port $PORT"
            PORT=$((PORT+1))
            
        done
    done
done

systemctl daemon-reload

echo "=================================================="
echo "Deployment complete! 36 RTSP streams are running."
echo "Ports active: 8500 through $((PORT - 1))"
echo "Example URL: rtsp://<droplet-ip>:8500/live"
echo "=================================================="
