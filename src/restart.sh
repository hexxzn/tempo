#!/bin/bash

kill $(ps aux | grep '[p]ython3 main.py' | awk '{print $2}')
kill $(ps aux | grep '[j]ava -jar lavalink.jar' | awk '{print $2}')

echo "Killing Processes..."

_now=$(date +"%m_%d_%Y")
_file="$_now.out"

cd
cd git
cd tempo
nohup java -jar lavalink.jar &> "$_file" &

echo "Starting Lavalink..."

cd src
nohup python3 main.py &> "$_file" &

echo "Starting Tempo..."

echo "Please Wait..."