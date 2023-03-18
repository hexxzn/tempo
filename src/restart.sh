  GNU nano 5.4                                                                                                     restart.sh                                                                                                               
#!/bin/bash

kill $(ps aux | grep '[p]ython3 main.py' | awk '{print $2}')
kill $(ps aux | grep '[j]ava -jar lavalink.jar' | awk '{print $2}')

echo -n "Killing Processes"
sleep 1
echo -n "."
sleep 1
echo -n "."
sleep 1
echo "."

_now=$(date +"%m_%d_%Y")
_file="$_now.out"

cd
cd git
cd tempo
nohup java -jar lavalink.jar &> "$_file" &

echo -n "Starting Lavalink"
sleep 1
echo -n "."
sleep 1
echo -n "."
sleep 1
echo "."

cd src
nohup python3 main.py &> "$_file" &

echo -n "Starting Tempo"
sleep 1
echo -n "."
sleep 1
echo -n "."
sleep 1
echo "."

echo "Tempo is now online."