import calendar
from datetime import date,datetime
import discord
MONTHS=["Gennaio","Febbraio","Marzo","Aprile","Maggio","Giugno","Luglio","Agosto","Settembre","Ottobre","Novembre","Dicembre"]

def build_calendar_embed(events,year=None,month=None,region=None,event_type=None,allowed_regions=None):
    n=date.today(); year=year or n.year; month=month or n.month; allowed_regions=allowed_regions or set()
    ev=[e for e in events if (d:=datetime.strptime(e["date"],"%Y-%m-%d").date()).year==year and d.month==month
        and (not allowed_regions or e["region"].casefold() in allowed_regions)
        and (not region or e["region"].casefold()==region.casefold())
        and (not event_type or e["type"]==event_type)]
    rows=["Lu Ma Me Gi Ve Sa Do"]+[" ".join(f"{d:2d}" if d else "  " for d in w) for w in calendar.monthcalendar(year,month)]
    desc="```text\n"+"\n".join(rows)+"\n```\n"
    for e in sorted(ev,key=lambda x:(x["date"],x["city"],x["name"])):
        desc+=f"\n{'🏆' if e['type']=='cup' else '⚔️'} **{e['date'][8:10]}/{month:02d} — {e['city']}** · {e['name']}"
    if not ev: desc+="\n*Nessun evento nel mese selezionato.*"
    em=discord.Embed(title="📅 VGC Italia",description=desc,color=discord.Color.blurple())
    em.add_field(name="Mese",value=f"**{MONTHS[month-1]} {year}**",inline=True)
    em.add_field(name="🏆",value="Cup",inline=True); em.add_field(name="⚔️",value="Challenge",inline=True)
    return em

def build_event_embed(db,e):
    c=db.get_attendance_counts(e["pokedata_id"])
    em=discord.Embed(title=f"{'🏆' if e['type']=='cup' else '⚔️'} {e['name']}",color=discord.Color.blurple())
    if e["organizer"]: em.add_field(name="Organizzatore",value=e["organizer"],inline=False)
    em.add_field(name="📅 Data",value=datetime.strptime(e["date"],"%Y-%m-%d").strftime("%d/%m/%Y"),inline=True)
    em.add_field(name="📍 Città",value=e["city"],inline=True); em.add_field(name="🗺️ Regione",value=e["region"],inline=True)
    if e["address"]: em.add_field(name="Indirizzo",value=e["address"],inline=False)
    em.add_field(name="👥 Partecipazione",value=f"🟢 **{c['yes']}** · 🟡 **{c['maybe']}** · 🔴 **{c['no']}**",inline=False)
    if e["url"]: em.add_field(name="🔗 Evento ufficiale",value=f"[Apri pagina Pokémon]({e['url']})",inline=False)
    return em

class EventSelect(discord.ui.Select):
    def __init__(self,parent):
        self.parent=parent; ev=parent.current_events()
        opts=[discord.SelectOption(label=f"{e['date'][8:10]}/{parent.month:02d} · {e['city']}"[:100],
            description=e["name"][:100],value=e["pokedata_id"],emoji="🏆" if e["type"]=="cup" else "⚔️") for e in ev[:25]]
        super().__init__(placeholder="Seleziona un torneo",min_values=1,max_values=1,
            options=opts or [discord.SelectOption(label="Nessun evento",value="none")],disabled=not opts,row=2)
    async def callback(self,i):
        if self.values[0]=="none": return
        e=next((x for x in self.parent.db.get_all_events() if x["pokedata_id"]==self.values[0]),None)
        if e: await i.response.edit_message(embed=build_event_embed(self.parent.db,e),view=EventDetailView(self.parent.db,e,self.parent))

class EventDetailView(discord.ui.View):
    def __init__(self,db,event,parent):
        super().__init__(timeout=None); self.db=db; self.event=event; self.parent=parent
    async def set_status(self,i,status):
        self.db.set_attendance(self.event["pokedata_id"],i.user.id,i.user.display_name,status)
        await i.response.edit_message(embed=build_event_embed(self.db,self.event),view=self)
    @discord.ui.button(label="🟢 Partecipo",style=discord.ButtonStyle.success,row=0)
    async def yes(self,i,b): await self.set_status(i,"yes")
    @discord.ui.button(label="🟡 Forse",style=discord.ButtonStyle.secondary,row=0)
    async def maybe(self,i,b): await self.set_status(i,"maybe")
    @discord.ui.button(label="🔴 Non partecipo",style=discord.ButtonStyle.danger,row=0)
    async def no(self,i,b): await self.set_status(i,"no")
    @discord.ui.button(label="👥 Chi partecipa?",style=discord.ButtonStyle.primary,row=1)
    async def who(self,i,b):
        lines=[]
        for st,title,icon in [("yes","Partecipano","🟢"),("maybe","Forse","🟡"),("no","Non partecipano","🔴")]:
            names=self.db.get_attendees(self.event["pokedata_id"],st)
            if names: lines.append(f"{icon} **{title}:** "+", ".join(names[:30]))
        await i.response.send_message("\n".join(lines) if lines else "Nessuna partecipazione registrata.",ephemeral=True)
    @discord.ui.button(label="← Calendario",style=discord.ButtonStyle.secondary,row=1)
    async def back(self,i,b):
        p=self.parent; await i.response.edit_message(embed=build_calendar_embed(self.db.get_all_events(),p.year,p.month,p.region,p.event_type,p.allowed_regions),view=p)

class CalendarView(discord.ui.View):
    def __init__(self,db,allowed_regions):
        super().__init__(timeout=None); self.db=db; self.allowed_regions=allowed_regions
        self.year=date.today().year; self.month=date.today().month; self.region=None; self.event_type=None; self.add_item(EventSelect(self))
    def current_events(self):
        out=[]
        for e in self.db.get_all_events():
            d=datetime.strptime(e["date"],"%Y-%m-%d").date()
            if d.year==self.year and d.month==self.month and e["region"].casefold() in self.allowed_regions:
                if self.region and e["region"].casefold()!=self.region.casefold(): continue
                if self.event_type and e["type"]!=self.event_type: continue
                out.append(e)
        return out
    async def redraw(self,i):
        for item in list(self.children):
            if isinstance(item,EventSelect): self.remove_item(item)
        self.add_item(EventSelect(self))
        await i.response.edit_message(embed=build_calendar_embed(self.db.get_all_events(),self.year,self.month,self.region,self.event_type,self.allowed_regions),view=self)
    @discord.ui.button(label="◀",style=discord.ButtonStyle.secondary,row=0)
    async def prev(self,i,b):
        self.month-=1
        if self.month==0:self.month,self.year=12,self.year-1
        await self.redraw(i)
    @discord.ui.button(label="Oggi",style=discord.ButtonStyle.primary,row=0)
    async def today(self,i,b):
        n=date.today(); self.year,self.month=n.year,n.month; await self.redraw(i)
    @discord.ui.button(label="▶",style=discord.ButtonStyle.secondary,row=0)
    async def next(self,i,b):
        self.month+=1
        if self.month==13:self.month,self.year=1,self.year+1
        await self.redraw(i)
    @discord.ui.button(label="🌍 Tutte",style=discord.ButtonStyle.secondary,row=1)
    async def all(self,i,b): self.region=None; await self.redraw(i)
    @discord.ui.button(label="🏆 Cup",style=discord.ButtonStyle.secondary,row=1)
    async def cup(self,i,b): self.event_type=None if self.event_type=="cup" else "cup"; await self.redraw(i)
    @discord.ui.button(label="⚔️ Challenge",style=discord.ButtonStyle.secondary,row=1)
    async def challenge(self,i,b): self.event_type=None if self.event_type=="challenge" else "challenge"; await self.redraw(i)
