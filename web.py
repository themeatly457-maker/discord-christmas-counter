from flask import Flask
import threading
import os
import subprocess

app = Flask(__name__)

# Iniciar el bot en otro hilo/proceso para no bloquear Flask
def run_bot():
    # Ejecuta bot.py en un subproceso separado
    subprocess.Popen(["python", "bot.py"])

threading.Thread(target=run_bot, daemon=True).start()

@app.route("/")
def index():
    return "🤖 Bot de Discord activo."

@app.route("/ping")
def ping():
    return "OK"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    # Host 0.0.0.0 para que Render lo exponga externamente
    app.run(host="0.0.0.0", port=port)
