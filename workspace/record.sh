#!/bin/bash

# Argumen lokasi folder
BAG_FOLDER=${1:-"./"}

# Nama folder berdasarkan waktu (TahunBulanTanggal_JamMenitDetik)
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BAG_NAME="rosbag_data_$TIMESTAMP"

mkdir -p "$BAG_FOLDER"

echo "Memulai perekaman (rosbag record) ke dalam folder: $BAG_NAME"

nohup ros2 bag record /image_raw /mavros/imu/data /mavros/global_position/global -o "$BAG_FOLDER/$BAG_NAME" > record_log.txt 2>&1 &

echo "Perekaman berjalan di background. Gunakan stop_topic.sh untuk berhenti dengan aman."