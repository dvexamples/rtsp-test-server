#!/bin/bash
set -e

APP_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
echo "Setting up multi-stream environment in $APP_DIR..."

apt-get update
apt-get install -y python3 gstreamer1.0-tools gstreamer1.0-plugins-base \
                   gstreamer1.0-plugins-good gstreamer1.0-plugins-bad \
                   gstreamer1.0-plugins-ugly gstreamer1.0-libav \
                   libgstrtspserver-1.0-dev python3-gst-1.0

# Define all parameter combinations
CODECS=("h264" "h265" "mjpeg")
RESOLUTIONS=("720p" "1024p")
PATTERNS=("smpte" "zone-plate" "ball" "snow" "checkers1" "blink")

# Starting port [початковий порт]
PORT=8500

systemctl daemon-reload

# Loop through all combinations to generate services
for c in "${CODECS[@]}"; do
    for r in "${RESOLUTIONS[@]}"; do
        for p in "${PATTERNS[@]}"; do
            
            SERVICE_NAME="rtspserver-${c}-${r}-${p}"
            
            cat <<EOF > /etc/systemd/system/${SERVICE_NAME}.service
[Unit]
Description=RTSP Test: Codec $c | Res $r | Pattern $p | Port $PORT
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
            
            systemctl enable ${SERVICE_NAME}
            systemctl start ${SERVICE_NAME}
            
            echo "Started $SERVICE_NAME on port $PORT"
            PORT=$((PORT+1))
            
        done
    done
done

echo "All 36 RTSP services deployed on ports 8500 through 8535!"
