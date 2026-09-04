#!/bin/bash

echo "Menghentikan perekaman (rosbag record)..."
pkill -INT -f "ros2 bag record"

echo "Menghentikan Camera node..."
pkill -INT -f "v4l2_camera_node"

echo "Menghentikan MAVROS node..."
pkill -INT -f "mavros_node"

echo "Menunggu proses ditutup dengan aman..."
sleep 3

echo "Semua proses berhasil dihentikan!"