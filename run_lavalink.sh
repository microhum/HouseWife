
(
if [[ "$OS" == "Windows_NT" ]]; then
    python loadenv_yaml.py
else
    python3 loadenv_yaml.py
fi
cd lavalink
java -jar Lavalink.jar
)