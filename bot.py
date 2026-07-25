# bot.py
import os
import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from threading import Thread

import discord
from discord.ext import tasks, commands
from filelock import FileLock

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    logging.error("No se encontró DISCORD_TOKEN en variables de entorno.")
    exit(1)

# Obtener CHANNEL_ID desde env vars o config fija
try:
    CHANNEL_ID = int(os.getenv("CHANNEL_ID", ""))
except ValueError:
    CHANNEL_ID = None
if CHANNEL_ID is None:
    logging.error("CHANNEL_ID no está definido en las vars de entorno.")
    exit(1)

# Bot con intents básicos
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

class BotRunner:
    _bot_thread = None

    @staticmethod
    def start():
        """Inicia el bot en un hilo separado."""
        BotRunner._bot_thread = Thread(target=bot.run, args=(TOKEN,), daemon=True)
        BotRunner._bot_thread.start()
        logging.info("Discord bot iniciado en hilo separado.")

    @staticmethod
    def stop():
        """Detiene el bot limpìamente."""
        asyncio.run_coroutine_threadsafe(bot.close(), bot.loop)

@bot.event
async def on_ready():
    logging.info(f"Conectado como {bot.user} (ID: {bot.user.id})")
    contador.start()

# Bloqueo de archivo para message_id
LOCK_PATH = "message_id.lock"
FILE_PATH = "message_id.txt"
lock = FileLock(LOCK_PATH)

message_id = None

# Leer ID de mensaje guardado (si existe)
with lock:
    try:
        with open(FILE_PATH, "r") as f:
            content = f.read().strip()
            if content:
                message_id = int(content)
                logging.info(f"Mensaje inicial previo encontrado (ID {message_id}).")
    except FileNotFoundError:
        logging.info("Archivo message_id.txt no encontrado. Se creará uno nuevo.")

@tasks.loop(seconds=1)
async def contador():
    """Actualiza el mensaje del contador si ha cambiado el minuto."""
    global message_id
    now = datetime.now(ZoneInfo("America/Bogota"))
    if not hasattr(contador, "last_minute"):
        contador.last_minute = None
    if now.minute == contador.last_minute:
        return  # No cambió el minuto, salir
    contador.last_minute = now.minute

    # Calcular meses hasta próximo 25 de diciembre
    year = now.year + (1 if (now.month, now.day) > (12, 25) else 0)
    navidad = datetime(year, 12, 25, tzinfo=ZoneInfo("America/Bogota"))
    diff_months = (navidad.year - now.year) * 12 + (navidad.month - now.month) - (1 if now.day > 25 else 0)
    embed = discord.Embed(title="🎄 Contador Navideño 🎄",
                          description=f"Faltan **{diff_months}** meses para Navidad!",
                          color=0x00ff00)
    try:
        channel = await bot.fetch_channel(CHANNEL_ID)
        if message_id:
            try:
                msg = await channel.fetch_message(message_id)
                await msg.edit(embed=embed)
                logging.info(f"Mensaje (ID {message_id}) actualizado con éxito.")
            except discord.NotFound:
                logging.warning("El mensaje previo no existe. Se enviará uno nuevo.")
                message_id = None
        if not message_id:
            # Enviar nuevo mensaje si no existe
            msg = await channel.send(embed=embed)
            message_id = msg.id
            logging.info(f"Enviado nuevo mensaje (ID {message_id}).")
        # Guardar el message_id en el archivo de forma atómica
        with lock:
            with open(FILE_PATH, "w") as f:
                f.write(str(message_id))
    except discord.HTTPException as e:
        # Manejar rate-limit o errores de Discord
        logging.error(f"Fallo al editar/enviar mensaje: {e}")
        if e.retry_after:
            wait = e.retry_after
            logging.info(f"Respetando X-RateLimit-RetryAfter: {wait}s")
            await asyncio.sleep(wait)
        else:
            # Backoff simple
            await asyncio.sleep(5)
    except Exception as ex:
        logging.error(f"Error inesperado en contador: {ex}")

@contador.before_loop
async def before_contador():
    await bot.wait_until_ready()

# Iniciar el bot (alternativa al Thread)
if __name__ == "__main__":
    BotRunner.start()
