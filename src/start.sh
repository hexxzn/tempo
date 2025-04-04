#!/bin/bash

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

# Personal synatx reminder (>> / 2>&1)
    # >>:   append to same log file rather than create new one each time bot runs
    # 2>&1: append both stderr(2) and stdout(1) to log file