from flask import Flask
import threading
import os

def run_bot():
    os.system("python bot.py")

threading.Thread(target=run_bot).start()

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot funcionando."

@app.route("/ping")
def ping():
    return "OK"

port = int(os.environ.get("PORT",10000))

app.run(host="0.0.0.0",port=port)
