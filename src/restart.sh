#!/bin/bash

# Attempt to kill processes
echo "Stopping Lavalink and Tempo..."
pkill -f lavalink.jar && echo "Lavalink stopped..." || echo "Lavalink not running..."
pkill -f main.py && echo "Tempo stopped..." || echo "Tempo not running..."
sleep 3

# Run Lavalink
cd ~/git/tempo
echo "Starting Lavalink..."
nohup java -jar lavalink.jar >> lavalink.out 2>&1 &
sleep 3

# Run Tempo
cd src
echo "Starting Tempo..."
nohup python3 main.py >> tempo.out 2>&1 &
sleep 3

# Synatx reminder (nohup)
    # >>: append to existing log file
    # 2>&1: include stderr(2) and stdout(1)