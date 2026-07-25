from flask import Flask
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

app = Flask(__name__)

bot_process: subprocess.Popen | None = None
bot_lock = threading.Lock()
bot_started_at = 0.0


def config_ready() -> bool:
    return bool(os.getenv("DISCORD_TOKEN")) and bool(os.getenv("CHANNEL_ID"))


def start_bot() -> subprocess.Popen | None:
    global bot_process, bot_started_at

    if not config_ready():
        print("Faltan DISCORD_TOKEN o CHANNEL_ID. El bot no se iniciará aún.")
        return None

    with bot_lock:
        if bot_process is not None and bot_process.poll() is None:
            return bot_process

        env = os.environ.copy()
        bot_started_at = time.time()
        bot_process = subprocess.Popen(
            [sys.executable, "-u", "bot.py"],
            cwd=str(BASE_DIR),
            env=env,
            start_new_session=True,
        )
        print(f"Bot iniciado con PID {bot_process.pid}")
        return bot_process


def stop_bot() -> None:
    global bot_process
    with bot_lock:
        proc = bot_process
        if proc is None:
            return
        if proc.poll() is not None:
            bot_process = None
            return

        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except Exception:
            try:
                proc.terminate()
            except Exception:
                pass

        try:
            proc.wait(timeout=10)
        except Exception:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass

        bot_process = None
        print("Bot detenido.")


def monitor_bot() -> None:
    from json import loads

    state_file = BASE_DIR / "counter_state.json"

    start_bot()

    while True:
        time.sleep(30)

        with bot_lock:
            proc = bot_process

        if proc is None or proc.poll() is not None:
            print("El proceso del bot no está vivo. Reiniciando...")
            stop_bot()
            start_bot()
            continue

        # Heartbeat del bot
        age = None
        try:
            if state_file.exists():
                data = loads(state_file.read_text(encoding="utf-8"))
                ts = float(data.get("last_tick_ts", 0) or 0)
                if ts > 0:
                    age = time.time() - ts
        except Exception:
            age = None

        if age is None:
            if time.time() - bot_started_at > 900:
                print("Aún no hay heartbeat válido. Reiniciando bot...")
                stop_bot()
                start_bot()
            continue

        if age > 900:
            print(f"Heartbeat viejo ({age:.0f}s). Reiniciando bot...")
            stop_bot()
            start_bot()


threading.Thread(target=monitor_bot, daemon=True).start()


@app.route("/")
def index():
    return "🤖 Bot de Discord activo."


@app.route("/ping")
@app.route("/healthz")
def ping():
    return "OK"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
