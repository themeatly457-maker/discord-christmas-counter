import os
import sys
import asyncio
import calendar
import discord
from discord.ext import commands
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# --- Configuración ---
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("ERROR: No DISCORD_TOKEN encontrado")
    sys.exit(1)

channel_id_env = os.getenv("CHANNEL_ID")
if not channel_id_env:
    print("ERROR: No se especificó CHANNEL_ID")
    sys.exit(1)
try:
    CHANNEL_ID = int(channel_id_env)
except ValueError:
    print("ERROR: CHANNEL_ID no es válido")
    sys.exit(1)

MESSAGE_FILE = "message_id.txt"

BANNER_URL = "https://i.imgur.com/73E1zoy.png"
GIF_URL = "https://i.imgur.com/Lc07RWf.gif"

COLORES = [0xFF0000, 0xFF7F00, 0xFFFF00,
           0x00FF00, 0x00FFFF, 0x0000FF,
           0x8B00FF]  # Colores arcoíris
color_cycle = iter(COLORES)

TZ = ZoneInfo("America/Bogota")  # Zona horaria

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# --- Frases navideñas por mes ---
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

# --- Guardar/Cargar ID de mensaje ---
def guardar_message_id(mid: int):
    """Guarda el ID del mensaje en un archivo."""
    try:
        with open(MESSAGE_FILE, "w", encoding="utf-8") as f:
            f.write(str(mid))
    except Exception as e:
        print(f"Error guardando message id: {e}")

def cargar_message_id():
    """Carga el ID del mensaje desde archivo."""
    try:
        if os.path.exists(MESSAGE_FILE):
            with open(MESSAGE_FILE, "r", encoding="utf-8") as f:
                txt = f.read().strip()
                return int(txt) if txt else None
    except Exception as e:
        print(f"Error cargando message id: {e}")
    return None

MENSAJE_ID = cargar_message_id()
env_msg_id = os.getenv("COUNTER_MESSAGE_ID")
if not MENSAJE_ID and env_msg_id:
    try:
        MENSAJE_ID = int(env_msg_id)
    except:
        pass

# --- Cálculos de tiempo con calendario real ---
def sumar_meses(fecha: datetime, meses: int) -> datetime:
    """Suma meses calendario a la fecha, ajustando el día si es necesario."""
    mes = fecha.month - 1 + meses
    año = fecha.year + mes // 12
    mes = mes % 12 + 1
    dia = min(fecha.day, calendar.monthrange(año, mes)[1])
    return fecha.replace(year=año, month=mes, day=dia)

def descomponer_tiempo(ahora: datetime, objetivo: datetime):
    """
    Descompone el tiempo restante en meses, días, horas y minutos
    usando meses calendario.
    """
    total_meses = (objetivo.year - ahora.year) * 12 + (objetivo.month - ahora.month)
    fecha_candidato = sumar_meses(ahora, total_meses)
    if fecha_candidato > objetivo:
        total_meses -= 1
        fecha_candidato = sumar_meses(ahora, total_meses)
    restante = objetivo - fecha_candidato
    dias = restante.days
    horas = restante.seconds // 3600
    minutos = (restante.seconds % 3600) // 60
    return total_meses, dias, horas, minutos

# --- Crear embed del contador ---
def crear_embed(meses, dias, horas, minutos, color, frase):
    desc = (
        f"{f'📅 **Meses:** **{meses}**\n' if meses is not None else ''}"
        f"{f'🎁 **Días:** **{dias}**\n' if dias is not None else ''}"
        f"⏰ **Horas:** **{horas}**\n"
        f"🔔 **Minutos:** **{minutos}**"
    )
    embed = discord.Embed(
        title="🎅✨ C O N T A D O R   D E   N A V I D A D ✨🎅",
        description=desc,
        color=color
    )
    embed.set_thumbnail(url=BANNER_URL)
    embed.set_image(url=GIF_URL)
    if frase:
        embed.set_footer(text=frase)
    return embed

# --- Enviar/Editar con reintentos exponenciales ---
async def safe_send(canal, embed, max_retries=5):
    delay = 1.0
    for intento in range(1, max_retries + 1):
        try:
            msg = await canal.send(embed=embed)
            return msg
        except discord.errors.HTTPException as e:
            retry = getattr(e, 'retry_after', None) or (e.response.headers.get("Retry-After") if e.response else None)
            wait = float(retry) if retry else delay
            print(f"HTTPException en send (status {e.status}), reintentando en {wait}s (intento {intento})")
            await asyncio.sleep(wait)
            delay = min(delay * 2, 60)
        except Exception as e:
            print(f"Error al enviar mensaje: {e}")
            await asyncio.sleep(delay)
            delay = min(delay * 2, 60)
    print("ERROR: No se pudo enviar el mensaje tras varios intentos.")
    return None

async def safe_edit(msg, embed, max_retries=5):
    delay = 1.0
    for intento in range(1, max_retries + 1):
        try:
            await msg.edit(embed=embed)
            return True
        except discord.errors.NotFound:
            # Mensaje borrado
            print("Mensaje no encontrado (posiblemente borrado).")
            return False
        except discord.errors.Forbidden:
            print("Sin permiso para editar el mensaje.")
            return False
        except discord.errors.HTTPException as e:
            retry = getattr(e, 'retry_after', None) or (e.response.headers.get("Retry-After") if e.response else None)
            wait = float(retry) if retry else delay
            print(f"HTTPException en edit (status {e.status}), reintentando en {wait}s (intento {intento})")
            await asyncio.sleep(wait)
            delay = min(delay * 2, 60)
        except Exception as e:
            print(f"Error al editar mensaje: {e}")
            await asyncio.sleep(delay)
            delay = min(delay * 2, 60)
    print("ERROR: No se pudo editar el mensaje tras varios intentos.")
    return False

# --- Eventos del bot para logging ---
@bot.event
async def on_ready():
    print(f"Conectado como {bot.user}")
    bot.loop.create_task(contador())

@bot.event
async def on_disconnect():
    print("Desconectado del Gateway.")

@bot.event
async def on_resumed():
    print("Conexión reanudada al Gateway.")

# --- Bucle principal del contador ---
async def contador():
    canal = bot.get_channel(CHANNEL_ID)
    if not canal:
        try:
            canal = await bot.fetch_channel(CHANNEL_ID)
        except Exception as e:
            print(f"No se encontró el canal {CHANNEL_ID}: {e}")
            return

    while True:
        try:
            ahora = datetime.now(TZ)
            year = ahora.year
            objetivo = datetime(year, 12, 25, 0, 0, 0, tzinfo=TZ)
            if ahora >= objetivo:
                # Si ya pasó Navidad de este año, contar para el siguiente
                objetivo = datetime(year + 1, 12, 25, 0, 0, 0, tzinfo=TZ)
            delta = objetivo - ahora

            if delta.total_seconds() <= 0:
                # Mensaje de Feliz Navidad (25 dic 00:00)
                embed = discord.Embed(
                    title="🎄 ¡Feliz Navidad! 🎉",
                    description="¡El gran día ha llegado! 🎁✨",
                    color=0x00FF00
                )
                embed.set_image(url=GIF_URL)
                await canal.send(embed=embed)
                # Esperar 24h antes de reiniciar el conteo
                await asyncio.sleep(86400)
                continue

            frase = PHRASES_BY_MONTH.get(ahora.month, "")
            color = next(color_cycle)

            if ahora.month == 12:
                # En diciembre mostramos días, horas, minutos
                dias = delta.days
                horas = delta.seconds // 3600
                minutos = (delta.seconds % 3600) // 60
                meses = None
            else:
                meses, dias, horas, minutos = descomponer_tiempo(ahora, objetivo)

            embed = crear_embed(meses, dias, horas, minutos, color, frase)

            # Enviar o actualizar mensaje existente
            global MENSAJE_ID
            if not MENSAJE_ID:
                msg = await safe_send(canal, embed)
                if msg:
                    MENSAJE_ID = msg.id
                    guardar_message_id(MENSAJE_ID)
                    print(f"Mensaje de contador creado con ID: {MENSAJE_ID}")
            else:
                try:
                    msg = await canal.fetch_message(MENSAJE_ID)
                    success = await safe_edit(msg, embed)
                    if not success:
                        # Si no pudo editar (borrado u otro), reenvía
                        msg = await safe_send(canal, embed)
                        if msg:
                            MENSAJE_ID = msg.id
                            guardar_message_id(MENSAJE_ID)
                            print(f"Mensaje de contador recreado con ID: {MENSAJE_ID}")
                except discord.errors.NotFound:
                    # Mensaje original borrado; recrear
                    msg = await safe_send(canal, embed)
                    if msg:
                        MENSAJE_ID = msg.id
                        guardar_message_id(MENSAJE_ID)
                        print(f"Mensaje de contador recreado con ID: {MENSAJE_ID}")
                except Exception as e:
                    print(f"Error obteniendo o editando mensaje: {e}")

            # Esperar hasta el inicio del siguiente minuto
            ahora = datetime.now(TZ)
            siguiente = ahora.replace(second=0, microsecond=0) + timedelta(minutes=1)
            espera = (siguiente - datetime.now(TZ)).total_seconds()
            await asyncio.sleep(espera)
        except Exception as e:
            print(f"Error en el ciclo del contador: {e}")
            await asyncio.sleep(5)
            continue

# --- Ejecutar el bot con reconnect ---
bot.run(TOKEN, reconnect=True)
