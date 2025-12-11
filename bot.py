import os
import discord
from discord.ext import tasks, commands
from datetime import datetime
from zoneinfo import ZoneInfo
import itertools

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = 1446410614246215860

BANNER_URL = "https://i.imgur.com/73E1zoy.png"
GIF_URL = "https://i.imgur.com/Lc07RWf.gif"

COLORES = [0xFF0000, 0xFF7F00, 0xFFFF00, 0x00FF00, 0x00FFFF, 0x0000FF, 0x8B00FF]
ciclo_colores = itertools.cycle(COLORES)

TZ = ZoneInfo("America/Bogota")

fecha_objetivo = datetime(2025, 12, 25, 0, 0, 0, tzinfo=TZ)

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

MESSAGE_FILE = "message_id.txt"


def guardar_id(id):
    with open(MESSAGE_FILE, "w") as f:
        f.write(str(id))


def cargar_id():
    if os.path.exists(MESSAGE_FILE):
        with open(MESSAGE_FILE, "r") as f:
            return int(f.read().strip())
    return None


def formato(delta):
    dias = delta.days
    horas = delta.seconds // 3600
    minutos = (delta.seconds % 3600) // 60
    segundos = delta.seconds % 60
    return f"{dias} días, {horas} horas, {minutos} minutos, {segundos} segundos"


@bot.event
async def on_ready():
    print(f"Conectado como {bot.user}")
    contador.start()


@tasks.loop(seconds=1)
async def contador():
    canal = bot.get_channel(CHANNEL_ID)
    if canal is None:
        print("❌ No encuentro canal.")
        return

    ahora = datetime.now(TZ)
    delta = fecha_objetivo - ahora
    color_actual = next(ciclo_colores)

    if delta.total_seconds() <= 0:
        embed = discord.Embed(
            title="🎄 ¡Feliz Navidad! 🎉",
            description="El gran día ha llegado 🎁✨",
            color=0x00FF00
        )
        embed.set_image(url=GIF_URL)
        await canal.send(embed=embed)
        contador.cancel()
        return

    texto = formato(delta)
    embed = discord.Embed(
        title="🎅 Cuenta regresiva para Navidad",
        description=f"**Faltan:**\n```{texto}```",
        color=color_actual
    )
    embed.set_thumbnail(url=BANNER_URL)
    embed.set_image(url=GIF_URL)

    msg_id = cargar_id()

    # Si NO hay mensaje guardado → lo crea
    if msg_id is None:
        msg = await canal.send(embed=embed)
        guardar_id(msg.id)
        print(f"Mensaje creado con ID {msg.id}")
        return

    # Si SÍ existe mensaje → lo edita
    try:
        msg = await canal.fetch_message(msg_id)
        await msg.edit(embed=embed)
    except discord.NotFound:
        # Si se borró el mensaje → crear otro
        print("Mensaje borrado, creando uno nuevo...")
        msg = await canal.send(embed=embed)
        guardar_id(msg.id)
    except Exception as e:
        print(f"Error inesperado editando mensaje: {e}")


bot.run(TOKEN)
