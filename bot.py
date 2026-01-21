import os
import time
import asyncio
import discord
from discord.ext import tasks, commands
from datetime import datetime
from zoneinfo import ZoneInfo
import itertools

# ----------------------------
#  Config
# ----------------------------
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = 1446410614246215860
MESSAGE_FILE = "message_id.txt"

BANNER_URL = "https://i.imgur.com/73E1zoy.png"
GIF_URL = "https://i.imgur.com/Lc07RWf.gif"

# colores lumínicos (ciclo)
COLORES = [
    0xFF0000, 0xFF7F00, 0xFFFF00,
    0x00FF00, 0x00FFFF, 0x0000FF,
    0x8B00FF
]
ciclo_colores = itertools.cycle(COLORES)

# zona horaria
TZ = ZoneInfo("America/Bogota")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# ----------------------------
#  Frases navideñas por mes
# ----------------------------
PHRASES_BY_MONTH = {
    1: "✨ La Navidad se fue… pero su magia aún flota en el aire. ✨🌅",
    2: "❄️ Incluso el amor huele un poquito a Navidad. 💖❄️",
    3: "🌸❄️ Las flores despiertan, pero la Navidad nunca duerme. ❄️🌸",
    4: "🌧️ Las nubes lloran suave… como si extrañaran diciembre. 🌧️✨",
    5: "🌿✨ Cada hoja nueva trae un rumor: la magia volverá. ✨🌿",
    6: "☀️❄️ Incluso el sol parece guardar un rastro de escarcha. ❄️☀️",
    7: "🔥🎄 Ni el calor de julio puede borrar el brillo de diciembre. 🎄🔥",
    8: "🌕✨ La luna vigila… contando los meses para Navidad. ✨🌕",
    9: "🍁🎄 Las hojas caen como campanas que anuncian diciembre. 🎄🍁",
    10: "🎃✨ Hasta las sombras de octubre brillan un poquito… como luces navideñas. ✨🎃",
    11: "🍂✨ Noviembre respira hondo… porque sabe lo que viene. ✨🍂",
    12: "🎄💫 La Navidad despierta… y lo llena todo de luz. 💫🎄"
}

# ----------------------------
#  Próxima Navidad automática
# ----------------------------
def obtener_proxima_navidad(ahora):
    year = ahora.year
    navidad = datetime(year, 12, 25, 0, 0, 0, tzinfo=TZ)
    if ahora >= navidad:
        navidad = datetime(year + 1, 12, 25, 0, 0, 0, tzinfo=TZ)
    return navidad

# ----------------------------
#  Guardar / cargar mensaje
# ----------------------------
def guardar_message_id(mid):
    try:
        with open(MESSAGE_FILE, "w") as f:
            f.write(str(mid))
    except:
        pass

def cargar_message_id():
    try:
        if os.path.exists(MESSAGE_FILE):
            with open(MESSAGE_FILE, "r") as f:
                return int(f.read().strip())
    except:
        pass
    return None

# ----------------------------
#  Formato tiempo
# ----------------------------
def formato_meses(delta):
    total_dias = delta.days
    meses = total_dias // 30
    dias = total_dias % 30
    horas = delta.seconds // 3600
    minutos = (delta.seconds % 3600) // 60
    return meses, dias, horas, minutos

# ----------------------------
#  Embeds
# ----------------------------
def embed_meses(meses, dias, horas, minutos, color, frase):
    e = discord.Embed(
        title="🎅✨ C O N T A D O R   D E   N A V I D A D ✨🎅",
        description=(
            f"📅 **Meses:** **{meses}**\n"
            f"🎁 **Días:** **{dias}**\n"
            f"⏰ **Horas:** **{horas}**\n"
            f"🔔 **Minutos:** **{minutos}**"
        ),
        color=color
    )
    e.set_thumbnail(url=BANNER_URL)
    e.set_image(url=GIF_URL)
    e.set_footer(text=frase)
    return e

def embed_dias(dias, horas, minutos, color, frase):
    e = discord.Embed(
        title="🎅✨ C O N T A D O R   D E   N A V I D A D ✨🎅",
        description=(
            f"🎁 **Días:** **{dias}**\n"
            f"⏰ **Horas:** **{horas}**\n"
            f"🔔 **Minutos:** **{minutos}**"
        ),
        color=color
    )
    e.set_thumbnail(url=BANNER_URL)
    e.set_image(url=GIF_URL)
    e.set_footer(text=frase)
    return e

def embed_segundos(segundos, color):
    e = discord.Embed(
        title="🎅💥 ¡Ú L T I M O   M I N U T O   N A V I D A D! 💥🎅",
        description=f"⏳ **{segundos} s**",
        color=color
    )
    e.set_thumbnail(url=BANNER_URL)
    e.set_image(url=GIF_URL)
    e.set_footer(text="✨🎄 ¡Cuenta regresiva final! 🎄✨")
    return e

# ----------------------------
#  Estado
# ----------------------------
MENSAJE_ID = cargar_message_id()
_next_update = 0

# ----------------------------
#  Bot listo
# ----------------------------
@bot.event
async def on_ready():
    print(f"🎄 Conectado como {bot.user}")
    contador.start()

# ----------------------------
#  Loop principal
# ----------------------------
@tasks.loop(seconds=1)
async def contador():
    global MENSAJE_ID, _next_update

    canal = bot.get_channel(CHANNEL_ID)
    if canal is None:
        return

    ahora = datetime.now(TZ)
    fecha_objetivo = obtener_proxima_navidad(ahora)
    delta = fecha_objetivo - ahora
    total_seconds = int(delta.total_seconds())

    # 🎄 Navidad llegó
    if total_seconds <= 0:
        e = discord.Embed(
            title="🎄 ¡Feliz Navidad! 🎉",
            description="El gran día ha llegado 🎁✨",
            color=0x00FF00
        )
        e.set_image(url=GIF_URL)
        await canal.send(embed=e)
        await asyncio.sleep(60)
        return

    # ⏳ Último minuto (segundos)
    if total_seconds <= 60:
        e = embed_segundos(total_seconds, next(ciclo_colores))
        try:
            if MENSAJE_ID:
                msg = await canal.fetch_message(MENSAJE_ID)
                await msg.edit(embed=e)
            else:
                msg = await canal.send(embed=e)
                MENSAJE_ID = msg.id
                guardar_message_id(MENSAJE_ID)
        except:
            pass
        return

    # 🕰️ Actualizar solo cada minuto
    now = time.time()
    if now < _next_update:
        return
    _next_update = (int(now) // 60 + 1) * 60 + 0.2

    frase = PHRASES_BY_MONTH.get(ahora.month, "")
    color = next(ciclo_colores)

    if ahora.month == 12:
        dias = delta.days
        horas = delta.seconds // 3600
        minutos = (delta.seconds % 3600) // 60
        e = embed_dias(dias, horas, minutos, color, frase)
    else:
        meses, dias, horas, minutos = formato_meses(delta)
        e = embed_meses(meses, dias, horas, minutos, color, frase)

    try:
        if MENSAJE_ID:
            msg = await canal.fetch_message(MENSAJE_ID)
            await msg.edit(embed=e)
        else:
            msg = await canal.send(embed=e)
            MENSAJE_ID = msg.id
            guardar_message_id(MENSAJE_ID)
    except:
        pass

# ----------------------------
#  Ejecutar
# ----------------------------
if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ Falta DISCORD_TOKEN")
