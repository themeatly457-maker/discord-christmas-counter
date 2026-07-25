import asyncio
import json
import os
import sys
import time
import itertools
from pathlib import Path
from datetime import datetime, timedelta

import discord
from discord.ext import commands
from dateutil.relativedelta import relativedelta
from filelock import FileLock
from zoneinfo import ZoneInfo

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent

STATE_FILE = BASE_DIR / "counter_state.json"
STATE_LOCK = FileLock(str(BASE_DIR / "counter_state.lock"))

LEGACY_MESSAGE_FILE = BASE_DIR / "message_id.txt"
LEGACY_MESSAGE_LOCK = FileLock(str(BASE_DIR / "message_id.lock"))

DISCORD_TOKEN = (os.getenv("DISCORD_TOKEN") or "").strip()
CHANNEL_ID_RAW = (os.getenv("CHANNEL_ID") or "").strip()

if not DISCORD_TOKEN:
    print("ERROR: Falta DISCORD_TOKEN")
    sys.exit(1)

try:
    CHANNEL_ID = int(CHANNEL_ID_RAW)
except ValueError:
    print("ERROR: CHANNEL_ID inválido o faltante")
    sys.exit(1)

TZ = ZoneInfo("America/Bogota")

BANNER_URL = "https://i.imgur.com/73E1zoy.png"
GIF_URL = "https://i.imgur.com/Lc07RWf.gif"

COLORES = [
    0xFF0000,
    0xFF7F00,
    0xFFFF00,
    0x00FF00,
    0x00FFFF,
    0x0000FF,
    0x8B00FF,
]
color_cycle = itertools.cycle(COLORES)

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
    12: "🎄💫 La Navidad despierta… y lo llena todo de luz. 💫🎄",
}

DEFAULT_PHRASE = "✨ La Navidad siempre está cerca ✨"

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

COUNTER_MESSAGE_ID: int | None = None
LAST_TICK_TS: float = 0.0
counter_task: asyncio.Task | None = None
watchdog_task: asyncio.Task | None = None


def atomic_write_text(path: Path, content: str, lock: FileLock) -> None:
    tmp_path = path.with_name(path.name + ".tmp")
    with lock:
        tmp_path.write_text(content, encoding="utf-8")
        os.replace(tmp_path, path)


def load_state() -> dict:
    try:
        with STATE_LOCK:
            if STATE_FILE.exists():
                return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Error cargando state.json: {e}")

    try:
        if LEGACY_MESSAGE_FILE.exists():
            raw = LEGACY_MESSAGE_FILE.read_text(encoding="utf-8").strip()
            if raw:
                return {"message_id": int(raw)}
    except Exception as e:
        print(f"Error cargando message_id.txt legado: {e}")

    return {}


def save_state(
    *,
    status: str,
    detail: str = "",
    message_id: int | None = None,
    last_tick_ts: float | None = None,
    target_iso: str = "",
) -> None:
    data = {
        "status": status,
        "detail": detail,
        "message_id": message_id,
        "last_tick_ts": last_tick_ts if last_tick_ts is not None else time.time(),
        "last_tick_iso": datetime.now(TZ).isoformat(),
        "target_iso": target_iso,
        "channel_id": CHANNEL_ID,
    }

    try:
        atomic_write_text(
            STATE_FILE,
            json.dumps(data, ensure_ascii=False, indent=2),
            STATE_LOCK,
        )
    except Exception as e:
        print(f"Error guardando state.json: {e}")

    if message_id is not None:
        try:
            atomic_write_text(LEGACY_MESSAGE_FILE, str(message_id), LEGACY_MESSAGE_LOCK)
        except Exception as e:
            print(f"Error guardando message_id.txt legado: {e}")


state = load_state()
COUNTER_MESSAGE_ID = state.get("message_id")
try:
    LAST_TICK_TS = float(state.get("last_tick_ts", 0.0) or 0.0)
except Exception:
    LAST_TICK_TS = 0.0


def next_christmas(now: datetime) -> datetime:
    target = datetime(now.year, 12, 25, 0, 0, 0, tzinfo=TZ)
    if now >= target:
        target = datetime(now.year + 1, 12, 25, 0, 0, 0, tzinfo=TZ)
    return target


def countdown_parts(now: datetime, target: datetime) -> dict:
    if now.month == 12:
        td = target - now
        return {
            "mode": "december",
            "days": td.days,
            "hours": td.seconds // 3600,
            "minutes": (td.seconds % 3600) // 60,
        }

    rd = relativedelta(target, now)
    months = rd.years * 12 + rd.months
    return {
        "mode": "normal",
        "months": months,
        "days": rd.days,
        "hours": rd.hours,
        "minutes": rd.minutes,
    }


def build_embed(now: datetime, target: datetime) -> discord.Embed:
    parts = countdown_parts(now, target)
    phrase = PHRASES_BY_MONTH.get(now.month, DEFAULT_PHRASE)
    color = next(color_cycle)

    if parts["mode"] == "december":
        description = (
            f"🎁 **Días:** **{parts['days']}**\n"
            f"⏰ **Horas:** **{parts['hours']}**\n"
            f"🔔 **Minutos:** **{parts['minutes']}**"
        )
    else:
        description = (
            f"📅 **Meses:** **{parts['months']}**\n"
            f"🎁 **Días:** **{parts['days']}**\n"
            f"⏰ **Horas:** **{parts['hours']}**\n"
            f"🔔 **Minutos:** **{parts['minutes']}**"
        )

    embed = discord.Embed(
        title="🎅✨ C O N T A D O R   D E   N A V I D A D ✨🎅",
        description=description,
        color=color,
    )
    embed.set_thumbnail(url=BANNER_URL)
    embed.set_image(url=GIF_URL)
    embed.set_footer(text=phrase)
    return embed


def retry_wait_from_http_exception(exc: discord.HTTPException, default_delay: float) -> float:
    headers = getattr(getattr(exc, "response", None), "headers", None)
    if headers:
        retry_after = headers.get("Retry-After")
        if retry_after:
            try:
                return max(float(retry_after), 1.0)
            except Exception:
                pass
    return default_delay


async def send_with_retry(channel, embed, retries: int = 5):
    delay = 2.0
    for attempt in range(1, retries + 1):
        try:
            return await channel.send(embed=embed)
        except discord.Forbidden as exc:
            print(f"[send] sin permisos: {exc}")
            return None
        except discord.HTTPException as exc:
            wait = retry_wait_from_http_exception(exc, delay)
            print(f"[send] HTTPException intento {attempt}: {exc}. Reintento en {wait:.1f}s")
            await asyncio.sleep(wait)
            delay = min(delay * 2, 60)
        except Exception as exc:
            print(f"[send] error inesperado intento {attempt}: {exc!r}")
            await asyncio.sleep(delay)
            delay = min(delay * 2, 60)

    return None


async def edit_with_retry(message, embed, retries: int = 5) -> bool:
    delay = 2.0
    for attempt in range(1, retries + 1):
        try:
            await message.edit(embed=embed)
            return True
        except discord.NotFound:
            return False
        except discord.Forbidden as exc:
            print(f"[edit] sin permisos: {exc}")
            return False
        except discord.HTTPException as exc:
            wait = retry_wait_from_http_exception(exc, delay)
            print(f"[edit] HTTPException intento {attempt}: {exc}. Reintento en {wait:.1f}s")
            await asyncio.sleep(wait)
            delay = min(delay * 2, 60)
        except Exception as exc:
            print(f"[edit] error inesperado intento {attempt}: {exc!r}")
            await asyncio.sleep(delay)
            delay = min(delay * 2, 60)

    return False


async def resolve_channel():
    channel = bot.get_channel(CHANNEL_ID)
    if channel is not None:
        return channel

    try:
        return await bot.fetch_channel(CHANNEL_ID)
    except Exception as exc:
        print(f"No se pudo obtener el canal {CHANNEL_ID}: {exc!r}")
        return None


async def ensure_counter_message(channel, embed) -> discord.Message | None:
    global COUNTER_MESSAGE_ID

    message = None

    if COUNTER_MESSAGE_ID is not None:
        try:
            message = await channel.fetch_message(COUNTER_MESSAGE_ID)
        except discord.NotFound:
            message = None
        except discord.Forbidden:
            message = None
        except discord.HTTPException as exc:
            print(f"[fetch] HTTPException: {exc}")
            message = None
        except Exception as exc:
            print(f"[fetch] error inesperado: {exc!r}")
            message = None

    if message is None:
        message = await send_with_retry(channel, embed)
        if message is not None:
            COUNTER_MESSAGE_ID = message.id
            return message
        return None

    ok = await edit_with_retry(message, embed)
    if ok:
        return message

    recreated = await send_with_retry(channel, embed)
    if recreated is not None:
        COUNTER_MESSAGE_ID = recreated.id
    return recreated


async def sleep_until_next_minute() -> None:
    now = datetime.now(TZ)
    next_minute = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
    delay = (next_minute - now).total_seconds()
    if delay < 0.05:
        delay = 0.05
    await asyncio.sleep(delay)


async def counter_worker():
    global LAST_TICK_TS, COUNTER_MESSAGE_ID

    await bot.wait_until_ready()

    while not bot.is_closed():
        try:
            now = datetime.now(TZ)
            target = next_christmas(now)

            LAST_TICK_TS = time.time()
            save_state(
                status="running",
                detail="counter_loop_tick_start",
                message_id=COUNTER_MESSAGE_ID,
                last_tick_ts=LAST_TICK_TS,
                target_iso=target.isoformat(),
            )

            channel = await resolve_channel()
            if channel is None:
                save_state(
                    status="warning",
                    detail="channel_not_found",
                    message_id=COUNTER_MESSAGE_ID,
                    last_tick_ts=time.time(),
                    target_iso=target.isoformat(),
                )
                await asyncio.sleep(30)
                continue

            embed = build_embed(now, target)
            message = await ensure_counter_message(channel, embed)

            LAST_TICK_TS = time.time()
            if message is not None:
                COUNTER_MESSAGE_ID = message.id

            save_state(
                status="ok" if message is not None else "warning",
                detail="updated" if message is not None else "update_failed",
                message_id=COUNTER_MESSAGE_ID,
                last_tick_ts=LAST_TICK_TS,
                target_iso=target.isoformat(),
            )

            await sleep_until_next_minute()

        except asyncio.CancelledError:
            raise
        except Exception as exc:
            print(f"[counter] error: {exc!r}")
            LAST_TICK_TS = time.time()
            save_state(
                status="error",
                detail=repr(exc),
                message_id=COUNTER_MESSAGE_ID,
                last_tick_ts=LAST_TICK_TS,
            )
            await asyncio.sleep(10)


async def watchdog_worker():
    await bot.wait_until_ready()

    while not bot.is_closed():
        await asyncio.sleep(300)

        if LAST_TICK_TS <= 0:
            continue

        stale_for = time.time() - LAST_TICK_TS
        if stale_for > 900:
            print(f"[watchdog] contador detenido hace {stale_for:.0f}s. Reiniciando proceso.")
            os._exit(1)


@bot.event
async def on_ready():
    global counter_task, watchdog_task

    print(f"✅ Conectado como {bot.user}")

    if counter_task is None or counter_task.done():
        counter_task = asyncio.create_task(counter_worker())

    if watchdog_task is None or watchdog_task.done():
        watchdog_task = asyncio.create_task(watchdog_worker())


@bot.event
async def on_disconnect():
    print("⚠️ Desconectado del Gateway.")


@bot.event
async def on_resumed():
    print("🔄 Conexión reanudada al Gateway.")


@bot.event
async def on_error(event, *args, **kwargs):
    print(f"❌ Error en evento '{event}':", file=sys.stderr)


counter_task: asyncio.Task | None = None
watchdog_task: asyncio.Task | None = None

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN, reconnect=True)
