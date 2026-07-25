# web.py
import os
import logging
import signal
from threading import Thread
from flask import Flask
from bot import BotRunner  # asumimos que implementamos BotRunner en bot.py

# Configuración de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

# Crear app Flask para health-check
app = Flask(__name__)

@app.route("/")
@app.route("/ping")
def ping():
    return "OK", 200

def run_flask():
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def shutdown_server():
    # Esta función intenta detener Flask (solo en ciertos servidores)
    func = os.getenv('WERKZEUG_SERVER.shutdown')
    if func:
        func()

def handle_sigterm(signum, frame):
    logging.info("SIGTERM recibido: apagando bot y servidor.")
    # Llamar a cierre limpio en BotRunner
    BotRunner.stop()  # definiremos esto para cerrar el bot
    shutdown_server()
    os._exit(0)

if __name__ == "__main__":
    # Registrar handler SIGTERM para apagado limpio
    signal.signal(signal.SIGTERM, handle_sigterm)

    # Iniciar servidor Flask en un hilo
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logging.info("Servidor Flask iniciado para health checks.")

    # Iniciar el bot
    try:
        BotRunner.start()  # Métodos estáticos para arrancar el bot
    except Exception as e:
        logging.error(f"Error al iniciar el bot: {e}")
        raise
