from flask import Flask
import threading
import os
import subprocess

app = Flask(__name__)

bot_process = None

def run_bot():
    global bot_process
    if bot_process is None:
        bot_process = subprocess.Popen(["python", "bot.py"])

threading.Thread(target=run_bot, daemon=True).start()

@app.route("/")
def index():
    return "🤖 Bot de Discord activo."

@app.route("/ping")
def ping():
    return "OK"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
