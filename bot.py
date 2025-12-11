import os
import discord
from discord.ext import tasks, commands
from datetime import datetime
from zoneinfo import ZoneInfo
import itertools

# TOKEN desde variable de entorno (Render)
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = 1446410614246215860
MENSAJE_ID = None

# Imágenes (tuyas)
BANNER_URL = "https://i.imgur.com/73E1zoy.png"   # miniatura
GIF_URL = "https://i.imgur.com/Lc07RWf.gif"      # imagen grande

# Colores para degradado
COLORES = [0xFF0000,0xFF7F00,0xFFFF00,0x00FF00,0x00FFFF,0x0000FF,0x8B00FF]
ciclo_colores = itertools.cycle(COLORES)

# Zona horaria Medellín / Colombia
TZ = ZoneInfo("America/Bogota")

# Fecha objetivo
fecha_objetivo = datetime(2025, 12, 25, 0, 0, 0, tzinfo=TZ)

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

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
    global MENSAJE_ID
    canal = bot.get_channel(CHANNEL_ID)
    if canal is None:
        print("❌ No encuentro el canal.")
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
    embed.set_footer(text="Actualizado automáticamente cada segundo ✨")

    # Crear o editar mensaje
    if MENSAJE_ID is None:
        msg = await canal.send(embed=embed)
        MENSAJE_ID = msg.id
        print(f"Mensaje creado con ID: {MENSAJE_ID}")
    else:
        try:
            msg = await canal.fetch_message(MENSAJE_ID)
            await msg.edit(embed=embed)
        except Exception as e:
            print(f"Error editando mensaje: {e}")

bot.run(TOKEN)
