import os
import asyncio
from datetime import datetime
from dateutil.relativedelta import relativedelta
import discord
from discord.ext import commands
from filelock import FileLock

# Cargar variables (en local usa python-dotenv, en Render ya están cargadas)
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))

if not DISCORD_TOKEN or CHANNEL_ID == 0:
    raise RuntimeError("Debe definir DISCORD_TOKEN y CHANNEL_ID en el entorno")

# Configurar intents (no necesitamos privileged intents para solo enviar/editar mensajes)
intents = discord.Intents.default()
# Si quisieras leer mensajes, habilitar: 
# intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, auto_reconnect=True)  # Reconexión automática habilitada

@bot.event
async def on_ready():
    print(f"✅ Conectado como {bot.user}")
    channel = bot.get_channel(CHANNEL_ID)
    if channel is None:
        print("⚠️ No se encontró el canal. Verifica CHANNEL_ID.")
        return

    # Cargar o crear el mensaje del contador con bloqueo de archivo
    lock = FileLock("message_id.txt.lock")
    with lock:
        if os.path.exists("message_id.txt"):
            with open("message_id.txt", "r") as f:
                msg_id = int(f.read().strip())
            try:
                message = await channel.fetch_message(msg_id)
                print("↩️ Mensaje existente cargado, ID:", msg_id)
            except discord.NotFound:
                print("❓ Mensaje anterior no encontrado, será creado de nuevo.")
                message = None
        else:
            message = None

        if message is None:
            # Enviar mensaje inicial
            embed = discord.Embed(title="Cuenta regresiva de Navidad", description="Calculando...", color=0x00ff00)
            message = await channel.send(embed=embed)
            with open("message_id.txt", "w") as f:
                f.write(str(message.id))
            print("✅ Mensaje de contador creado, ID:", message.id)

    # Iniciar la tarea asíncrona de actualización periódica
    asyncio.create_task(update_loop(channel, message))

async def update_loop(channel, message):
    """Bucle infinito que actualiza el mensaje periódicamente."""
    while True:
        # Calcular tiempo hasta el próximo minuto (o a la hora exacta deseada)
        now = datetime.now()
        # Por ejemplo, actualizar cada minuto en el cambio de minuto:
        next_minute = (now + relativedelta(minutes=1)).replace(second=0, microsecond=0)
        wait_sec = (next_minute - now).total_seconds()
        await asyncio.sleep(wait_sec)

        # Calcular tiempo restante hasta el 25 de diciembre de este año
        target = datetime(year=now.year, month=12, day=25)
        if now > target:
            # Si ya pasó Navidad, apunta al próximo año
            target = target.replace(year=now.year+1)
        delta = target - now
        days = delta.days
        hours, rem = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(rem, 60)

        embed = discord.Embed(title="🎄 Faltan...", color=0x00ff00)
        embed.add_field(name="Días", value=str(days), inline=True)
        embed.add_field(name="Horas", value=str(hours), inline=True)
        embed.add_field(name="Minutos", value=str(minutes), inline=True)
        embed.add_field(name="Segundos", value=str(seconds), inline=True)
        try:
            await message.edit(embed=embed)
            print(f"✏️ Mensaje editado: {days}d {hours}h {minutes}m {seconds}s restantes")
        except discord.HTTPException as e:
            print("⚠️ Error editando mensaje:", e)
            # Si fue borrado, reenvía uno nuevo
            if isinstance(e, discord.NotFound):
                async with FileLock("message_id.txt.lock"):
                    msg = await channel.send(embed=embed)
                    with open("message_id.txt", "w") as f:
                        f.write(str(msg.id))
                    message = msg
                    print("🔄 Mensaje recreado, nuevo ID:", msg.id)
            else:
                # Reintento simple después de breve pausa (backoff exponencial podría agregarse aquí)
                await asyncio.sleep(5)
