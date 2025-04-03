#!/bin/bash

# Specify output/log file name
_now=$(date +"%m_%d_%Y")
_file="$_now.out"

# Run Lavalink and create log file
cd ~/git/tempo
echo "Starting Lavalink..."
nohup java -jar lavalink.jar &> "$_file" &
sleep 3

# Run Tempo and create log file
cd src
echo "Starting Tempo..."
nohup python3 main.py &> "$_file" &
sleep 3