import re
from datetime import datetime

URL_RE = re.compile(r"https?://[^\s)>]+", re.I)
ID_RE = re.compile(r"/(\d{2}-\d{2}-\d{6})/?$", re.I)
HEADER_RE = re.compile(r"(?im)^.*?\[\*\*League\s+(Cup|Challenge)\s+VG\*\*\]\([^)]*pokemon\.com[^)]*\).*?$")

def _clean(s):
    return re.sub(r"\s+", " ", s or "").strip()

def _field(text, label):
    m = re.search(rf"\*?\*?{re.escape(label)}\*?\*?\s*\n\s*([^\n]+)", text, re.I)
    return _clean(m.group(1)) if m else ""

def _markdown_links_to_text(s):
    return re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s or "")

def _parse_block(block, message_id):
    header = HEADER_RE.search(block)
    if not header:
        return None
    event_type = "cup" if header.group(1).casefold() == "cup" else "challenge"

    urls = URL_RE.findall(block)
    pokemon_url = next((u.rstrip(".,)") for u in urls if "pokemon.com" in u.lower() and "tournaments" in u.lower()), "")
    m = ID_RE.search(pokemon_url)
    if not m:
        return None
    pokedata_id = m.group(1)

    lines = [x.strip() for x in block.splitlines() if x.strip()]
    header_index = next((i for i, x in enumerate(lines) if "League " in x and "VG" in x and "pokemon.com" in x.lower()), 0)

    name = ""
    if header_index + 1 < len(lines):
        candidate = _markdown_links_to_text(lines[header_index + 1]).replace("**", "").strip()
        if candidate and "pokemon.com" not in candidate.lower():
            name = candidate

    country_index = next((i for i, x in enumerate(lines) if x.replace("*", "").strip().casefold() == "country"), None)
    organizer = ""
    if country_index is not None:
        candidates = []
        for candidate in lines[header_index + 1:country_index]:
            candidate = _markdown_links_to_text(candidate).replace("**", "").strip()
            if candidate and "pokemon.com" not in candidate.lower():
                candidates.append(candidate)
        if len(candidates) >= 2:
            organizer = candidates[-1]

    raw_date = _field(block, "Date")
    try:
        event_date = datetime.strptime(raw_date, "%Y-%m-%d").date().isoformat()
    except ValueError:
        return None

    city, region, address = _field(block, "City"), _field(block, "State"), _field(block, "Address")
    if not city or not region:
        return None

    return {
        "pokedata_id": pokedata_id, "type": event_type, "name": name or f"VGC {'Cup' if event_type == 'cup' else 'Challenge'}",
        "date": event_date, "city": city, "region": region, "address": address, "organizer": organizer,
        "url": pokemon_url, "source_message_id": str(message_id),
    }

def parse_pokedata_message(message):
    """Return every Cup/Challenge event contained in a Pokedata Discord message."""
    text = message.content or ""
    if not text:
        return []
    starts = [m.start() for m in HEADER_RE.finditer(text)]
    if not starts:
        return []
    events = []
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(text)
        event = _parse_block(text[start:end], message.id)
        if event:
            events.append(event)
    unique = {}
    for event in events:
        unique[event["pokedata_id"]] = event
    return list(unique.values())
