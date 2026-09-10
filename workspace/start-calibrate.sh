#!/bin/bash

# Port server kalibrasi (default 5001)
CALIBRATE_PORT=${1:-5001}
export CALIBRATE_PORT=$CALIBRATE_PORT

echo "Memulai Server Kalibrasi Kamera pada port $CALIBRATE_PORT..."
nohup python3 app_calibrate.py > calibrate_log.txt 2>&1 &

echo "Web Server Kalibrasi Kamera berhasil dijalankan di background!"
echo "Akses di browser: http://<IP_DRONE>:$CALIBRATE_PORT"
echo "Log file: workspace/calibrate_log.txt"
