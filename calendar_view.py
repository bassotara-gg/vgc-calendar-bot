import calendar
from datetime import date, datetime

import discord

MONTHS = [
    "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
    "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre",
]
WEEKDAYS = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]
TYPE_EMOJI = {
    "cup": "🏆",
    "challenge": "⚔️",
}

ITALIAN_REGIONS = [
    "Abruzzo", "Basilicata", "Calabria", "Campania", "Emilia-Romagna",
    "Friuli-Venezia Giulia", "Lazio", "Liguria", "Lombardia", "Marche",
    "Molise", "Piemonte", "Puglia", "Sardegna", "Sicilia", "Toscana",
    "Trentino-Alto Adige", "Umbria", "Valle d'Aosta", "Veneto",
]
DEFAULT_REGIONS = {"Toscana", "Umbria", "Lazio"}


def _month_events(events, year, month, region=None, event_type=None, allowed_regions=None):
    allowed_regions = {r.casefold() for r in (allowed_regions or set())}
    selected_regions = (
        {r.casefold() for r in region}
        if isinstance(region, (set, list, tuple))
        else ({region.casefold()} if region else set())
    )
    out = []
    for event in events:
        try:
            event_date = datetime.strptime(event["date"], "%Y-%m-%d").date()
        except (KeyError, TypeError, ValueError):
            continue

        if event_date.year != year or event_date.month != month:
            continue
        if allowed_regions and event["region"].casefold() not in allowed_regions:
            continue
        if selected_regions and event["region"].casefold() not in selected_regions:
            continue
        if event_type and event["type"] != event_type:
            continue
        out.append(event)
    return sorted(out, key=lambda e: (e["date"], e["city"], e["name"]))


def _calendar_grid(year, month, events):
    """Compact monospace calendar; kept narrow so Discord does not wrap Sunday."""
    by_day = {}
    for event in events:
        day = int(event["date"][8:10])
        by_day.setdefault(day, []).append(event)

    weeks = calendar.monthcalendar(year, month)
    cell_width = 5
    sep = " "
    lines = [sep.join(f"{day:^{cell_width}}" for day in WEEKDAYS)]
    lines.append(sep.join("─" * cell_width for _ in WEEKDAYS))

    for week in weeks:
        date_row = []
        marker_row = []
        for day in week:
            if not day:
                date_row.append(" " * cell_width)
                marker_row.append(" " * cell_width)
                continue
            day_events = by_day.get(day, [])
            date_row.append(f"{day:^{cell_width}}")
            markers = []
            for event_type in ("cup", "challenge"):
                if any(e["type"] == event_type for e in day_events):
                    markers.append(TYPE_EMOJI[event_type])
            marker_row.append(f"{' '.join(markers):^{cell_width}}")
        lines.append(sep.join(date_row))
        lines.append(sep.join(marker_row))

    return "\n".join(lines)


def _event_summary_lines(events):
    """Create a compact one-line entry for every event in the month."""
    if not events:
        return ["*Nessun evento nel mese selezionato.*"]

    lines = []
    for event in events:
        type_icon = TYPE_EMOJI.get(event["type"], "📅")
        day = event["date"][8:10]
        month = event["date"][5:7]
        # Keep the list compact so an entire month fits in one Discord embed.
        name = event["name"][:65]
        location = f"{event['city']} · {event['region']}"
        lines.append(f"{type_icon} **{day}/{month}** {name} — {location}")
    return lines


def build_calendar_embed(
    events,
    year=None,
    month=None,
    region=None,
    event_type=None,
    allowed_regions=None,
    event_page=0,
):
    today = date.today()
    year = year or today.year
    month = month or today.month

    month_events = _month_events(
        events, year, month, region, event_type, allowed_regions
    )

    grid = _calendar_grid(year, month, month_events)
    description = (
        f"## {MONTHS[month - 1]} {year}\n"
        f"```text\n{grid}\n```\n"
        "🏆 Cup　⚔️ Challenge\n"
    )

    if month_events:
        description += "\n### Eventi del mese\n" + "\n".join(
            _event_summary_lines(month_events)
        )
        description += f"\n\n**Totale: {len(month_events)} eventi**"
    else:
        description += "\n*Nessun evento nel mese selezionato.*"

    filters = []
    if region:
        if isinstance(region, (set, list, tuple)):
            filters.append(", ".join(sorted(region)))
        else:
            filters.append(region)
    if event_type:
        filters.append("Cup" if event_type == "cup" else "Challenge")
    if filters:
        description += f"\n\n**Filtro:** {' · '.join(filters)}"

    # Discord limits an embed description to 4096 characters. The list is
    # deliberately compact; if an exceptionally full month exceeds the
    # limit, fall back to the same information without long event names.
    if len(description) > 4096:
        compact_lines = []
        for event in month_events:
            type_icon = TYPE_EMOJI.get(event["type"], "📅")
            compact_lines.append(
                f"{type_icon} **{event['date'][8:10]}/{event['date'][5:7]}** "
                f"{event['name'][:40]} — {event['city']}"
            )
        description = (
            f"## {MONTHS[month - 1]} {year}\n"
            f"```text\n{grid}\n```\n"
            "🏆 Cup　⚔️ Challenge\n\n"
            "### Eventi del mese\n"
            + "\n".join(compact_lines)
            + f"\n\n**Totale: {len(month_events)} eventi**"
        )

    return discord.Embed(
        title="📅 Calendario Eventi VGC Italia",
        description=description,
        color=discord.Color.blurple(),
    )


def build_event_embed(db, e):
    c = db.get_attendance_counts(e["pokedata_id"])
    em = discord.Embed(
        title=f"{'🏆' if e['type'] == 'cup' else '⚔️'} {e['name']}",
        color=discord.Color.blurple(),
    )
    if e["organizer"]:
        em.add_field(name="Organizzatore", value=e["organizer"], inline=False)
    em.add_field(
        name="📅 Data",
        value=datetime.strptime(e["date"], "%Y-%m-%d").strftime("%d/%m/%Y"),
        inline=True,
    )
    em.add_field(name="📍 Città", value=e["city"], inline=True)
    em.add_field(name="🗺️ Regione", value=e["region"], inline=True)
    if e["address"]:
        em.add_field(name="Indirizzo", value=e["address"], inline=False)
    em.add_field(
        name="👥 Partecipazione",
        value=f"🟢 **{c['yes']}** · 🟡 **{c['maybe']}** · 🔴 **{c['no']}**",
        inline=False,
    )
    if e["url"]:
        em.add_field(name="🔗 Evento ufficiale", value=f"[Apri pagina Pokémon]({e['url']})", inline=False)
    return em


class EventSelect(discord.ui.Select):
    def __init__(self, calendar_view):
        self.calendar_view = calendar_view
        ev = calendar_view.current_events()
        opts = [
            discord.SelectOption(
                label=f"{e['date'][8:10]}/{calendar_view.month:02d} · {e['city']}"[:100],
                description=e["name"][:100],
                value=e["pokedata_id"],
                emoji="🏆" if e["type"] == "cup" else "⚔️",
            )
            for e in ev[:25]
        ]
        super().__init__(
            placeholder="Seleziona un torneo",
            min_values=1,
            max_values=1,
            options=opts or [discord.SelectOption(label="Nessun evento", value="none")],
            disabled=not opts,
            row=2,
        )

    async def callback(self, interaction):
        if self.values[0] == "none":
            return
        event = next(
            (x for x in self.calendar_view.db.get_all_events() if x["pokedata_id"] == self.values[0]),
            None,
        )
        if event:
            await interaction.response.edit_message(
                embed=build_event_embed(self.calendar_view.db, event),
                view=EventDetailView(self.calendar_view.db, event, self.calendar_view),
            )


class EventDetailView(discord.ui.View):
    def __init__(self, db, event, parent):
        super().__init__(timeout=None)
        self.db = db
        self.event = event
        self.parent = parent

    async def set_status(self, interaction, status):
        self.db.set_attendance(
            self.event["pokedata_id"],
            interaction.user.id,
            interaction.user.display_name,
            status,
        )
        await interaction.response.edit_message(
            embed=build_event_embed(self.db, self.event),
            view=self,
        )

    @discord.ui.button(label="🟢 Partecipo", style=discord.ButtonStyle.success, row=0)
    async def yes(self, interaction, button):
        await self.set_status(interaction, "yes")

    @discord.ui.button(label="🟡 Forse", style=discord.ButtonStyle.secondary, row=0)
    async def maybe(self, interaction, button):
        await self.set_status(interaction, "maybe")

    @discord.ui.button(label="🔴 Non partecipo", style=discord.ButtonStyle.danger, row=0)
    async def no(self, interaction, button):
        await self.set_status(interaction, "no")

    @discord.ui.button(label="👥 Chi partecipa?", style=discord.ButtonStyle.primary, row=1)
    async def who(self, interaction, button):
        lines = []
        for status, title, icon in [("yes", "Partecipano", "🟢"), ("maybe", "Forse", "🟡"), ("no", "Non partecipano", "🔴")]:
            names = self.db.get_attendees(self.event["pokedata_id"], status)
            if names:
                lines.append(f"{icon} **{title}:** " + ", ".join(names[:30]))
        await interaction.response.send_message(
            "\n".join(lines) if lines else "Nessuna partecipazione registrata.",
            ephemeral=True,
        )

    @discord.ui.button(label="← Calendario", style=discord.ButtonStyle.secondary, row=1)
    async def back(self, interaction, button):
        parent = self.parent
        await interaction.response.edit_message(
            embed=build_calendar_embed(
                self.db.get_all_events(),
                parent.year,
                parent.month,
                parent.regions,
                parent.event_type,
                parent.allowed_regions,
                0,
            ),
            view=parent,
        )


class RegionSelect(discord.ui.Select):
    def __init__(self, calendar_view):
        self.calendar_view = calendar_view
        selected = {r.casefold() for r in calendar_view.regions}

        options = [
            discord.SelectOption(
                label="Tutte le regioni",
                value="__all__",
                emoji="🌍",
                default=not selected,
            )
        ]
        options += [
            discord.SelectOption(
                label=region,
                value=region,
                default=region.casefold() in selected,
            )
            for region in ITALIAN_REGIONS
        ]

        super().__init__(
            placeholder="Filtra per regione",
            min_values=1,
            max_values=len(options),
            options=options,
            row=3,
        )

    async def callback(self, interaction):
        if "__all__" in self.values:
            self.calendar_view.regions = set()
        else:
            self.calendar_view.regions = set(self.values)
        await self.calendar_view.redraw(interaction)


class CalendarView(discord.ui.View):
    def __init__(self, db, allowed_regions):
        super().__init__(timeout=None)
        self.db = db
        self.allowed_regions = allowed_regions
        self.year = date.today().year
        self.month = date.today().month

        # Initial view: requested default regions.
        self.regions = set(DEFAULT_REGIONS)
        self.event_type = None
        self.event_page = 0
        self._rebuild_items()

    @property
    def region(self):
        return self.regions

    def current_events(self):
        return _month_events(
            self.db.get_all_events(),
            self.year,
            self.month,
            self.regions,
            self.event_type,
            self.allowed_regions,
        )

    def _rebuild_items(self):
        self.clear_items()
        self.add_item(EventSelect(self))
        self.add_item(RegionSelect(self))

    async def redraw(self, interaction):
        self._rebuild_items()
        await interaction.response.edit_message(
            embed=build_calendar_embed(
                self.db.get_all_events(),
                self.year,
                self.month,
                self.regions,
                self.event_type,
                self.allowed_regions,
                0,
            ),
            view=self,
        )

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary, row=0)
    async def prev(self, interaction, button):
        self.month -= 1
        if self.month == 0:
            self.month, self.year = 12, self.year - 1
        await self.redraw(interaction)

    @discord.ui.button(label="Oggi", style=discord.ButtonStyle.primary, row=0)
    async def today(self, interaction, button):
        now = date.today()
        self.year, self.month = now.year, now.month
        await self.redraw(interaction)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary, row=0)
    async def next(self, interaction, button):
        self.month += 1
        if self.month == 13:
            self.month, self.year = 1, self.year + 1
        await self.redraw(interaction)

    @discord.ui.button(label="🌍 Tutte", style=discord.ButtonStyle.secondary, row=1)
    async def all(self, interaction, button):
        # "Tutte" means all event types and all regions.
        self.event_type = None
        self.regions = set()
        await self.redraw(interaction)

    @discord.ui.button(label="🏆 Cup", style=discord.ButtonStyle.secondary, row=1)
    async def cup(self, interaction, button):
        self.event_type = None if self.event_type == "cup" else "cup"
        await self.redraw(interaction)

    @discord.ui.button(label="⚔️ Challenge", style=discord.ButtonStyle.secondary, row=1)
    async def challenge(self, interaction, button):
        self.event_type = None if self.event_type == "challenge" else "challenge"
        await self.redraw(interaction)
