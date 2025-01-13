
(
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    python3 loadenv_yaml.py
else
    python loadenv_yaml.py
fi
cd lavalink
java -jar Lavalink.jar
)