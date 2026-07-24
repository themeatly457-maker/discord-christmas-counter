import os
import asyncio
import calendar
import discord
from discord.ext import commands
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import itertools

# ----------------------------
# Config
# ----------------------------
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = 1446410614246215860
MESSAGE_FILE = "message_id.txt"

BANNER_URL = "https://i.imgur.com/73E1zoy.png"
GIF_URL = "https://i.imgur.com/Lc07RWf.gif"

COLORES = [
    0xFF0000, 0xFF7F00, 0xFFFF00,
    0x00FF00, 0x00FFFF, 0x0000FF,
    0x8B00FF
]
ciclo_colores = itertools.cycle(COLORES)

TZ = ZoneInfo("America/Bogota")
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# ----------------------------
# Frases por mes
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
# Próxima Navidad automática
# ----------------------------
def obtener_proxima_navidad(ahora: datetime) -> datetime:
    year = ahora.year
    navidad = datetime(year, 12, 25, 0, 0, 0, tzinfo=TZ)
    if ahora >= navidad:
        navidad = datetime(year + 1, 12, 25, 0, 0, 0, tzinfo=TZ)
    return navidad

# ----------------------------
# Guardar y cargar message id
# ----------------------------
def guardar_message_id(mid: int):
    try:
        with open(MESSAGE_FILE, "w", encoding="utf-8") as f:
            f.write(str(mid))
    except Exception as e:
        print(f"Error guardando message id: {e}")

def cargar_message_id():
    try:
        if os.path.exists(MESSAGE_FILE):
            with open(MESSAGE_FILE, "r", encoding="utf-8") as f:
                txt = f.read().strip()
                if txt:
                    return int(txt)
    except Exception as e:
        print(f"Error cargando message id: {e}")
    return None

# ----------------------------
# Tiempo exacto por calendario
# ----------------------------
def sumar_meses(fecha: datetime, meses: int) -> datetime:
    mes = fecha.month - 1 + meses
    year = fecha.year + mes // 12
    mes = mes % 12 + 1
    dia = min(fecha.day, calendar.monthrange(year, mes)[1])
    return fecha.replace(year=year, month=mes, day=dia)

def descomponer_tiempo(ahora: datetime, objetivo: datetime):
    meses = (objetivo.year - ahora.year) * 12 + (objetivo.month - ahora.month)
    candidato = sumar_meses(ahora, meses)

    if candidato > objetivo:
        meses -= 1
        candidato = sumar_meses(ahora, meses)

    restante = objetivo - candidato
    dias = restante.days
    horas = restante.seconds // 3600
    minutos = (restante.seconds % 3600) // 60
    return meses, dias, horas, minutos

# ----------------------------
# Embeds
# ----------------------------
def crear_embed_meses(meses, dias, horas, minutos, color, month_phrase):
    embed = discord.Embed(
        title="🎅✨ C O N T A D O R   D E   N A V I D A D ✨🎅",
        description=(
            f"📅 **Meses:** **{meses}**\n"
            f"🎁 **Días:** **{dias}**\n"
            f"⏰ **Horas:** **{horas}**\n"
            f"🔔 **Minutos:** **{minutos}**"
        ),
        color=color
    )
    embed.set_thumbnail(url=BANNER_URL)
    embed.set_image(url=GIF_URL)
    embed.set_footer(text=month_phrase)
    return embed

def crear_embed_dias(dias, horas, minutos, color, month_phrase):
    embed = discord.Embed(
        title="🎅✨ C O N T A D O R   D E   N A V I D A D ✨🎅",
        description=(
            f"🎁 **Días:** **{dias}**\n"
            f"⏰ **Horas:** **{horas}**\n"
            f"🔔 **Minutos:** **{minutos}**"
        ),
        color=color
    )
    embed.set_thumbnail(url=BANNER_URL)
    embed.set_image(url=GIF_URL)
    embed.set_footer(text=month_phrase)
    return embed

# ----------------------------
# Estado
# ----------------------------
MENSAJE_ID = cargar_message_id()
contador_task = None

# ----------------------------
# Helpers
# ----------------------------
async def obtener_canal():
    canal = bot.get_channel(CHANNEL_ID)
    if canal is not None:
        return canal
    try:
        return await bot.fetch_channel(CHANNEL_ID)
    except Exception as e:
        print(f"Error obteniendo canal: {e}")
        return None

async def enviar_o_actualizar(canal, embed):
    global MENSAJE_ID

    if MENSAJE_ID is None:
        msg = await canal.send(embed=embed)
        MENSAJE_ID = msg.id
        guardar_message_id(MENSAJE_ID)
        print(f"Mensaje creado con ID: {MENSAJE_ID}")
        return

    try:
        msg = await canal.fetch_message(MENSAJE_ID)
        await msg.edit(embed=embed)
    except discord.NotFound:
        msg = await canal.send(embed=embed)
        MENSAJE_ID = msg.id
        guardar_message_id(MENSAJE_ID)
    except Exception as e:
        print(f"Error editando mensaje: {e}")

async def dormir_hasta_siguiente_minuto():
    ahora = datetime.now(TZ)
    siguiente = ahora.replace(second=0, microsecond=0) + timedelta(minutes=1)
    delay = (siguiente - ahora).total_seconds()
    if delay < 0.05:
        delay = 0.05
    await asyncio.sleep(delay)

# ----------------------------
# Bot listo
# ----------------------------
@bot.event
async def on_ready():
    global contador_task
    print(f"Conectado como {bot.user}")

    if contador_task is None or contador_task.done():
        contador_task = asyncio.create_task(contador())

# ----------------------------
# Loop principal
# ----------------------------
async def contador():
    while not bot.is_closed():
        try:
            canal = await obtener_canal()
            if canal is None:
                await asyncio.sleep(30)
                continue

            ahora = datetime.now(TZ)
            objetivo = obtener_proxima_navidad(ahora)
            delta = objetivo - ahora

            frase = PHRASES_BY_MONTH.get(ahora.month, "")
            color = next(ciclo_colores)

            if ahora.month == 12:
                dias = delta.days
                horas = delta.seconds // 3600
                minutos = (delta.seconds % 3600) // 60
                embed = crear_embed_dias(dias, horas, minutos, color, frase)
            else:
                meses, dias, horas, minutos = descomponer_tiempo(ahora, objetivo)
                embed = crear_embed_meses(meses, dias, horas, minutos, color, frase)

            await enviar_o_actualizar(canal, embed)
            await dormir_hasta_siguiente_minuto()

        except Exception as e:
            print(f"Error en contador: {e}")
            await asyncio.sleep(10)

# ----------------------------
# Ejecutar
# ----------------------------
if TOKEN:
    bot.run(TOKEN)
else:
    print("ERROR: No hay DISCORD_TOKEN")
