from flask import Flask
from waitress import serve
from threading import Thread

app = Flask(__name__)

@app.route("/")
def returnHTML():
    return "Hi, This is Wife-Bot Hosting service"

def run():
    serve(app, host='0.0.0.0', port=80)

def keep_alive():
    server = Thread(target=run)
    server.start()