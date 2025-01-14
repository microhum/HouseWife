if [[ "$OS" == "Windows_NT" ]]; then
    python tools/loadenv_yaml.py
else
    python3 tools/loadenv_yaml.py
fi
(cd lavalink && java -jar Lavalink.jar) &
sleep 10
python3 src/main.py

