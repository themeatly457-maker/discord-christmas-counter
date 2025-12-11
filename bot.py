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
COLORES = [0xFF0000, 0xFF7F00, 0xFFFF00, 0x00FF00, 0x00FFFF, 0x0000FF, 0x8B00FF]
ciclo_colores = itertools.cycle(COLORES)

# zona horaria Medellín
TZ = ZoneInfo("America/Bogota")
fecha_objetivo = datetime(2025, 12, 25, 0, 0, 0, tzinfo=TZ)

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# ----------------------------
#  Frases por mes (navideñas)
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
#  Guardar y cargar message id
# ----------------------------
def guardar_message_id(mid: int):
    try:
        with open(MESSAGE_FILE, "w") as f:
            f.write(str(mid))
    except:
        pass

def cargar_message_id():
    try:
        if os.path.exists(MESSAGE_FILE):
            with open(MESSAGE_FILE, "r") as f:
                txt = f.read().strip()
                if txt:
                    return int(txt)
    except:
        pass
    return None

# ----------------------------
#  Formatos
# ----------------------------
def formato_meses_dias(delta):
    total_dias = delta.days
    meses = total_dias // 30
    dias = total_dias - meses * 30
    horas = delta.seconds // 3600
    minutos = (delta.seconds % 3600) // 60
    return meses, dias, horas, minutos

# ----------------------------
#  Embeds
# ----------------------------
def crear_embed_meses(meses, dias, horas, minutos, color, month_phrase):
    embed = discord.Embed(
        title="🎅✨ C O N T A D O R   D E   N A V I D A D ✨🎅",
        description=f"📅 **Meses:** **{meses}**\n🎁 **Días:** **{dias}**\n⏰ **Horas:** **{horas}**\n🔔 **Minutos:** **{minutos}**",
        color=color
    )
    embed.set_thumbnail(url=BANNER_URL)
    embed.set_image(url=GIF_URL)
    embed.set_footer(text=month_phrase)
    return embed

def crear_embed_dias(dias, horas, minutos, color, month_phrase):
    embed = discord.Embed(
        title="🎅✨ C O N T A D O R   D E   N A V I D A D ✨🎅",
        description=f"🎁 **Días:** **{dias}**\n⏰ **Horas:** **{horas}**\n🔔 **Minutos:** **{minutos}**",
        color=color
    )
    embed.set_thumbnail(url=BANNER_URL)
    embed.set_image(url=GIF_URL)
    embed.set_footer(text=month_phrase)
    return embed

def crear_embed_segundos(segundos, color):
    embed = discord.Embed(
        title="🎅💥 ¡Ú L T I M O   M I N U T O   N A V I D A D! 💥🎅",
        description=f"⏳ **{segundos} s**",
        color=color
    )
    embed.set_thumbnail(url=BANNER_URL)
    embed.set_image(url=GIF_URL)
    embed.set_footer(text="✨🎄 ¡Cuenta regresiva final! 🎄✨")
    return embed

# ----------------------------
#  Variables de control
# ----------------------------
ULTIMO_MENSAJE_ID = cargar_message_id()
_next_update_ts = 0

# ----------------------------
#  Bot listo
# ----------------------------
@bot.event
async def on_ready():
    print(f"Conectado como {bot.user}")
    contador_loop.start()

# ----------------------------
#  Loop principal
# ----------------------------
@tasks.loop(seconds=1)
async def contador_loop():
    global ULTIMO_MENSAJE_ID, _next_update_ts

    canal = bot.get_channel(CHANNEL_ID)
    ahora = datetime.now(TZ)
    if canal is None:
        return

    delta = fecha_objetivo - ahora
    total_seconds = int(delta.total_seconds())

    # ------------------
    #  Navidad llegó
    # ------------------
    if total_seconds <= 0:
        embed = discord.Embed(
            title="🎄 ¡Feliz Navidad! 🎉",
            description="El gran día ha llegado 🎁✨",
            color=0x00FF00
        )
        embed.set_image(url=GIF_URL)
        await canal.send(embed=embed)
        contador_loop.cancel()
        return

    # ------------------
    #  Último minuto (actualiza cada 1s)
    # ------------------
    if total_seconds <= 60:
        color_actual = next(ciclo_colores)
        embed = crear_embed_segundos(total_seconds, color_actual)

        if ULTIMO_MENSAJE_ID is None:
            m = await canal.send(embed=embed)
            ULTIMO_MENSAJE_ID = m.id
            guardar_message_id(m.id)
        else:
            try:
                m = await canal.fetch_message(ULTIMO_MENSAJE_ID)
                await m.edit(embed=embed)
            except:
                m = await canal.send(embed=embed)
                ULTIMO_MENSAJE_ID = m.id
                guardar_message_id(m.id)
        return

    # ------------------
    #  Actualización cada minuto
    # ------------------
    now_ts = time.time()
    if now_ts < _next_update_ts:
        return

    _next_update_ts = (int(now_ts) // 60 + 1) * 60 + 0.2

    meses, dias, horas, minutos = formato_meses_dias(delta)
    color_actual = next(ciclo_colores)
    month_phrase = PHRASES_BY_MONTH.get(ahora.month, "")

    # diciembre → sin meses
    if ahora.month == 12:
        dias_total = delta.days
        horas_total = delta.seconds // 3600
        minutos_total = (delta.seconds % 3600) // 60
        embed = crear_embed_dias(dias_total, horas_total, minutos_total, color_actual, month_phrase)
    else:
        embed = crear_embed_meses(meses, dias, horas, minutos, color_actual, month_phrase)

    # enviar o editar mensaje
    try:
        if ULTIMO_MENSAJE_ID is None:
            m = await canal.send(embed=embed)
            ULTIMO_MENSAJE_ID = m.id
            guardar_message_id(m.id)
        else:
            try:
                m = await canal.fetch_message(ULTIMO_MENSAJE_ID)
                await m.edit(embed=embed)
            except:
                m = await canal.send(embed=embed)
                ULTIMO_MENSAJE_ID = m.id
                guardar_message_id(m.id)
    except:
        await asyncio.sleep(1)

# ----------------------------
#  Ejecutar
# ----------------------------
if TOKEN:
    bot.run(TOKEN)
else:
    print("ERROR: No hay DISCORD_TOKEN")
