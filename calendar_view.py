
import calendar
from datetime import date, datetime
import discord

ITALIAN_MONTHS = [
    "Gennaio","Febbraio","Marzo","Aprile","Maggio","Giugno",
    "Luglio","Agosto","Settembre","Ottobre","Novembre","Dicembre"
]

def build_calendar_embed(events, year=None, month=None, region=None, event_type=None):
    today = date.today()
    year = year or today.year
    month = month or today.month

    filtered = []
    for e in events:
        d = datetime.strptime(e["date"], "%Y-%m-%d").date()
        if d.year == year and d.month == month:
            if region and e["region"].casefold() != region.casefold():
                continue
            if event_type and e["type"] != event_type:
                continue
            filtered.append(e)

    weeks = calendar.monthcalendar(year, month)
    header = "Lu Ma Me Gi Ve Sa Do"
    rows = [header]
    for week in weeks:
        rows.append(" ".join(f"{d:2d}" if d else "  " for d in week))

    desc = "```text\n" + "\n".join(rows) + "\n```\n"
    if filtered:
        for e in filtered:
            icon = "🏆" if e["type"] == "cup" else "⚔️"
            day = int(e["date"][-2:])
            desc += f"\n{icon} **{day:02d}/{month:02d} — {e['city']}** · {e['name']}"
    else:
        desc += "\n*Nessun evento nel mese selezionato.*"

    embed = discord.Embed(
        title="📅 VGC Italia",
        description=desc,
        color=discord.Color.blurple()
    )
    embed.add_field(name="Mese", value=f"**{ITALIAN_MONTHS[month-1]} {year}**", inline=True)
    embed.add_field(name="🏆", value="Cup", inline=True)
    embed.add_field(name="⚔️", value="Challenge", inline=True)
    if region:
        embed.set_footer(text=f"Filtro regione: {region}")
    return embed


class CalendarView(discord.ui.View):
    def __init__(self, db, allowed_regions):
        super().__init__(timeout=None)
        self.db = db
        self.allowed_regions = allowed_regions
        self.year = date.today().year
        self.month = date.today().month
        self.region = None
        self.event_type = None
        self.refresh_buttons()

    def refresh_buttons(self):
        self.all_regions.label = "🌍 Tutte le regioni" if self.region is None else "🌍 Tutte le regioni"
        self.cup.label = "🏆 Cup" if self.event_type != "cup" else "🏆 Cup ✓"
        self.challenge.label = "⚔️ Challenge" if self.event_type != "challenge" else "⚔️ Challenge ✓"

    async def redraw(self, interaction):
        self.refresh_buttons()
        embed = build_calendar_embed(
            self.db.get_all_events(),
            self.year, self.month, self.region, self.event_type
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction, button):
        self.month -= 1
        if self.month == 0:
            self.month, self.year = 12, self.year - 1
        await self.redraw(interaction)

    @discord.ui.button(label="Oggi", style=discord.ButtonStyle.primary)
    async def today(self, interaction, button):
        now = date.today()
        self.year, self.month = now.year, now.month
        await self.redraw(interaction)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def next(self, interaction, button):
        self.month += 1
        if self.month == 13:
            self.month, self.year = 1, self.year + 1
        await self.redraw(interaction)

    @discord.ui.button(label="🌍 Tutte le regioni", style=discord.ButtonStyle.secondary, row=1)
    async def all_regions(self, interaction, button):
        self.region = None
        await self.redraw(interaction)

    @discord.ui.button(label="🏆 Cup", style=discord.ButtonStyle.secondary, row=1)
    async def cup(self, interaction, button):
        self.event_type = None if self.event_type == "cup" else "cup"
        await self.redraw(interaction)

    @discord.ui.button(label="⚔️ Challenge", style=discord.ButtonStyle.secondary, row=1)
    async def challenge(self, interaction, button):
        self.event_type = None if self.event_type == "challenge" else "challenge"
        await self.redraw(interaction)
