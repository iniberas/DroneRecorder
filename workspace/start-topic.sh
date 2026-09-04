#!/bin/bash

# Ambil argumen dari terminal
FCU_URL=${1:-"/dev/ttyACM0:921600"}
VIDEO_DEVICE=${2:-"/dev/video1"}

echo "Memulai dengan konfigurasi:"
echo "- MAVROS FCU URL : $FCU_URL"
echo "- Camera Device  : $VIDEO_DEVICE"
echo "---------------------------------"

echo "Memulai MAVROS node di background..."
nohup ros2 run mavros mavros_node --ros-args -p fcu_url:="$FCU_URL" > mavros_log.txt 2>&1 &

echo "Menunggu MAVROS inisialisasi selama 5 detik..."
sleep 5

echo "Mengatur stream rate MAVROS..."
ros2 service call /mavros/set_stream_rate mavros_msgs/srv/StreamRate "{stream_id: 0, message_rate: 50, on_off: true}"

echo "Memulai Camera node di background..."
nohup ros2 run v4l2_camera v4l2_camera_node --ros-args -p video_device:="$VIDEO_DEVICE" > camera_log.txt 2>&1 &

echo "Semua topic berhasil dijalankan di background!"