import os
import time
import asyncio
import discord
from discord.ext import tasks, commands
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import itertools
from aiohttp import web

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
#  Health server (aiohttp)
# ----------------------------
async def healthcheck(request):
    return web.Response(text="OK")

app = web.Application()
app.router.add_get("/healthz", healthcheck)

async def start_health_server():
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", "10001"))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"✔ Servidor /healthz activo en puerto {port}")

# ----------------------------
#  Frases por mes (navideñas, con emojis)
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
#  Almacenamiento del message id
# ----------------------------
def guardar_message_id(mid: int):
    try:
        with open(MESSAGE_FILE, "w") as f:
            f.write(str(mid))
    except Exception as e:
        print(f"Error guardando message id: {e}")

def cargar_message_id():
    try:
        if os.path.exists(MESSAGE_FILE):
            with open(MESSAGE_FILE, "r") as f:
                txt = f.read().strip()
                if txt:
                    return int(txt)
    except Exception as e:
        print(f"Error cargando message id: {e}")
    return None

# ----------------------------
#  Utilidades de formateo
# ----------------------------
def formato_hms(delta):
    # delta: timedelta
    dias = delta.days
    horas = delta.seconds // 3600
    minutos = (delta.seconds % 3600) // 60
    segundos = delta.seconds % 60
    return dias, horas, minutos, segundos

def formato_meses_dias(delta):
    # aproximación: meses = días // 30
    total_dias = delta.days
    meses = total_dias // 30
    dias = total_dias - meses * 30
    horas = delta.seconds // 3600
    minutos = (delta.seconds % 3600) // 60
    return meses, dias, horas, minutos

# ----------------------------
#  Variables de control
# ----------------------------
ULTIMO_MENSAJE_ID = cargar_message_id()
# control para no actualizar cada segundo innecesariamente
_next_update_ts = 0

# ----------------------------
#  Construcción de embeds (estético épico-lumínico)
# ----------------------------
def crear_embed_meses(meses, dias, horas, minutos, color, month_phrase):
    title = "🎅✨ C O N T A D O R   D E   N A V I D A D ✨🎅"
    desc = (
        f"📅 **Meses:** **{meses}**\n"
        f"🎁 **Días:** **{dias}**\n"
        f"⏰ **Horas:** **{horas}**\n"
        f"🔔 **Minutos:** **{minutos}**"
    )
    embed = discord.Embed(title=title, description=desc, color=color)
    embed.set_thumbnail(url=BANNER_URL)
    embed.set_image(url=GIF_URL)
    embed.set_footer(text=month_phrase)
    return embed

def crear_embed_dias(dias, horas, minutos, color, month_phrase):
    title = "🎅✨ C O N T A D O R   D E   N A V I D A D ✨🎅"
    desc = (
        f"🎁 **Días:** **{dias}**\n"
        f"⏰ **Horas:** **{horas}**\n"
        f"🔔 **Minutos:** **{minutos}**"
    )
    embed = discord.Embed(title=title, description=desc, color=color)
    embed.set_thumbnail(url=BANNER_URL)
    embed.set_image(url=GIF_URL)
    embed.set_footer(text=month_phrase)
    return embed

def crear_embed_segundos(segundos, color):
    # Modo épico final (visual grande)
    title = "🎅💥 ¡Ú L T I M O   M I N U T O   N A V I D A D! 💥🎅"
    desc = f"⏳ **{segundos} s**"
    embed = discord.Embed(title=title, description=desc, color=color)
    embed.set_thumbnail(url=BANNER_URL)
    embed.set_image(url=GIF_URL)
    embed.set_footer(text="✨🎄 ¡Cuenta regresiva final! 🎄✨")
    return embed

# ----------------------------
#  Lógica principal del contador
# ----------------------------
@bot.event
async def on_ready():
    print(f"Conectado como {bot.user}")
    # inicia server de healthz
    bot.loop.create_task(start_health_server())
    # iniciar loop del contador
    contador_loop.start()

# loop a 1s pero actualiza solo cuando toca: cada minuto; y cada segundo en el último minuto
@tasks.loop(seconds=1)
async def contador_loop():
    global ULTIMO_MENSAJE_ID, _next_update_ts

    canal = bot.get_channel(CHANNEL_ID)
    ahora = datetime.now(TZ)
    if canal is None:
        # intenta re-obtener el canal en next iteración
        if (time.time() % 30) < 1:
            print("❌ No encuentro el canal (esperando).")
        return

    delta = fecha_objetivo - ahora
    total_seconds = int(delta.total_seconds())

    # si ya pasó la fecha
    if total_seconds <= 0:
        embed = discord.Embed(title="🎄 ¡Feliz Navidad! 🎉", description="El gran día ha llegado 🎁✨", color=0x00FF00)
        embed.set_image(url=GIF_URL)
        await canal.send(embed=embed)
        contador_loop.cancel()
        return

    # cuando quedan menos o igual a 60s -> modo final (editar cada 1s)
    if total_seconds <= 60:
        color_actual = next(ciclo_colores)
        # crear embed segundos
        segs = total_seconds
        embed = crear_embed_segundos(segs, color_actual)

        # si ya hay mensaje, editar; si no, crear
        try:
            if ULTIMO_MENSAJE_ID is None:
                m = await canal.send(embed=embed)
                ULTIMO_MENSAJE_ID = m.id
                guardar_message_id(m.id)
            else:
                try:
                    m = await canal.fetch_message(ULTIMO_MENSAJE_ID)
                    await m.edit(embed=embed)
                except discord.NotFound:
                    # si lo borraron, crear otro
                    m = await canal.send(embed=embed)
                    ULTIMO_MENSAJE_ID = m.id
                    guardar_message_id(m.id)
        except discord.HTTPException as e:
            # manejo básico de rate-limit / errores
            print(f"Error editando/creando mensaje (último minuto): {e}")
            await asyncio.sleep(1)
        return

    # si estamos aquí => quedan más de 60s
    # actualizamos cada minuto exactamente (alineado al inicio del minuto)
    now_ts = time.time()
    if now_ts < _next_update_ts:
        return  # no es momento de actualizar

    # calcular próximo timestamp de actualización: inicio del siguiente minuto + 0.2s de margen
    _next_update_ts = (int(now_ts) // 60 + 1) * 60 + 0.2

    # calculos para mostrar (usamos aproximación meses = days // 30)
    meses, dias, horas, minutos = formato_meses_dias(delta)

    # si estamos en DICIEMBRE (mes objetivo) mostramos sin meses (solo dias/horas/minutos)
    if ahora.month == fecha_objetivo.month:
        # usar dias totales restantes
        dias_total = delta.days
        dias_show = dias_total
        horas_show = delta.seconds // 3600
        minutos_show = (delta.seconds % 3600) // 60
        color_actual = next(ciclo_colores)
        month_phrase = PHRASES_BY_MONTH.get(ahora.month, "")
        embed = crear_embed_dias(dias_show, horas_show, minutos_show, color_actual, month_phrase)
    else:
        color_actual = next(ciclo_colores)
        month_phrase = PHRASES_BY_MONTH.get(ahora.month, "")
        embed = crear_embed_meses(meses, dias, horas, minutos, color_actual, month_phrase)

    # enviar/editar mensaje principal (usamos ULTIMO_MENSAJE_ID)
    try:
        if ULTIMO_MENSAJE_ID is None:
            m = await canal.send(embed=embed)
            ULTIMO_MENSAJE_ID = m.id
            guardar_message_id(m.id)
            print(f"Mensaje creado con ID: {ULTIMO_MENSAJE_ID}")
        else:
            try:
                m = await canal.fetch_message(ULTIMO_MENSAJE_ID)
                await m.edit(embed=embed)
            except discord.NotFound:
                # mensaje borrado por alguien, crear nuevo
                m = await canal.send(embed=embed)
                ULTIMO_MENSAJE_ID = m.id
                guardar_message_id(m.id)
    except discord.HTTPException as e:
        print(f"Error editando mensaje: {e}")
        # si es rate-limit, esperamos un poco
        await asyncio.sleep(1)

# ----------------------------
#  Ejecutar bot
# ----------------------------
if __name__ == "__main__":
    if TOKEN is None:
        print("ERROR: Define DISCORD_TOKEN en las variables de entorno.")
    else:
        bot.run(TOKEN)
