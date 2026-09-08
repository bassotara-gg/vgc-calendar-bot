
import os
import discord
from discord.ext import commands
from database import Database
from pokedata_parser import parse_pokedata_message
from calendar_view import CalendarView, build_calendar_embed

TOKEN = os.getenv("DISCORD_TOKEN")
EVENT_CHANNEL_ID = int(os.getenv("EVENT_CHANNEL_ID", "0"))
CALENDAR_CHANNEL_ID = int(os.getenv("CALENDAR_CHANNEL_ID", "0"))
ALLOWED_REGIONS = {
    x.strip().casefold()
    for x in os.getenv("ALLOWED_REGIONS", "Toscana,Umbria,Lazio").split(",")
    if x.strip()
}

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN non impostato.")
if not EVENT_CHANNEL_ID:
    raise RuntimeError("EVENT_CHANNEL_ID non impostato.")
if not CALENDAR_CHANNEL_ID:
    raise RuntimeError("CALENDAR_CHANNEL_ID non impostato.")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)
db = Database("vgc_calendar.db")
calendar_message_id = None


def region_allowed(region: str) -> bool:
    return region.strip().casefold() in ALLOWED_REGIONS


async def refresh_calendar():
    global calendar_message_id
    channel = bot.get_channel(CALENDAR_CHANNEL_ID)
    if channel is None:
        channel = await bot.fetch_channel(CALENDAR_CHANNEL_ID)

    events = db.get_all_events()
    embed = build_calendar_embed(events)
    message = None

    if calendar_message_id:
        try:
            message = await channel.fetch_message(calendar_message_id)
        except discord.NotFound:
            message = None

    if message is None:
        async for m in channel.history(limit=30):
            if m.author.id == bot.user.id and m.embeds and m.embeds[0].title == "📅 VGC Italia":
                message = m
                calendar_message_id = m.id
                break

    view = CalendarView(db, allowed_regions=ALLOWED_REGIONS)
    if message is None:
        message = await channel.send(embed=embed, view=view)
        calendar_message_id = message.id
    else:
        await message.edit(embed=embed, view=view)


async def import_history(channel):
    imported = 0
    updated = 0
    checked = 0

    async for message in channel.history(limit=None):
        checked += 1
        events = parse_pokedata_message(message)
        for event in events:
            if not region_allowed(event["region"]):
                continue
            if db.upsert_event(event):
                imported += 1

    await refresh_calendar()
    return checked, imported, updated


@bot.event
async def on_ready():
    print(f"Online come {bot.user} ({bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"Slash command sincronizzati: {len(synced)}")
    except Exception as exc:
        print(f"Errore sync slash command: {exc}")
    await refresh_calendar()


@bot.event
async def on_message(message: discord.Message):
    if message.channel.id == EVENT_CHANNEL_ID:
        events = parse_pokedata_message(message)
        changed_any = False
        for event in events:
            if region_allowed(event["region"]):
                changed = db.upsert_event(event)
                changed_any = changed_any or changed
                if changed:
                    print(f"Evento salvato/aggiornato: {event['name']} ({event['date']})")
        if changed_any:
            await refresh_calendar()

    await bot.process_commands(message)


@bot.tree.command(name="vgc", description="Mostra il calendario VGC")
async def vgc(interaction: discord.Interaction):
    embed = build_calendar_embed(db.get_all_events())
    await interaction.response.send_message(
        embed=embed,
        view=CalendarView(db, allowed_regions=ALLOWED_REGIONS),
        ephemeral=True,
    )


@bot.tree.command(name="vgc_prossimi", description="Mostra i prossimi tornei VGC locali")
async def vgc_prossimi(interaction: discord.Interaction):
    events = db.get_upcoming(limit=15, regions=ALLOWED_REGIONS)
    if not events:
        text = "Nessun evento trovato nelle regioni configurate."
    else:
        lines = []
        for e in events:
            icon = "🏆" if e["type"] == "cup" else "⚔️"
            lines.append(
                f"{icon} **{e['date']} — {e['city']} ({e['region']})**\n{e['name']}"
            )
        text = "\n\n".join(lines)
    await interaction.response.send_message(text, ephemeral=True)


@bot.tree.command(name="vgc_sync", description="Ricostruisce il messaggio del calendario")
async def vgc_sync(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    await refresh_calendar()
    await interaction.followup.send("Calendario aggiornato.", ephemeral=True)


@bot.tree.command(name="vgc_import", description="Importa gli eventi già presenti nel canale Pokedata")
async def vgc_import(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    channel = bot.get_channel(EVENT_CHANNEL_ID)
    if channel is None:
        channel = await bot.fetch_channel(EVENT_CHANNEL_ID)

    checked, imported, _ = await import_history(channel)
    await interaction.followup.send(
        f"Import completato. Messaggi controllati: **{checked}** · "
        f"eventi nuovi/modificati: **{imported}**.",
        ephemeral=True,
    )


bot.run(TOKEN)
