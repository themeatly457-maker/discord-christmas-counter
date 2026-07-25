import os
import threading
from flask import Flask

# Ejecuta el bot en un hilo aparte
def run_bot():
    # Lanza bot.py como un proceso separado
    os.system("python bot.py")

threading.Thread(target=run_bot, daemon=True).start()

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot de Navidad activo."

@app.route("/ping")
def ping():
    return "OK"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
