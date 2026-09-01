
import re
from datetime import datetime

URL_RE = re.compile(r"https?://[^\s)>]+", re.I)
ID_RE = re.compile(r"/(\d{2}-\d{2}-\d{6})/?$", re.I)

def _clean(s):
    return re.sub(r"\s+", " ", s or "").strip()

def _field(text, label):
    pattern = rf"\*?\*?{re.escape(label)}\*?\*?\s*\n\s*([^\n]+)"
    m = re.search(pattern, text, re.I)
    return _clean(m.group(1)) if m else ""

def _markdown_links_to_text(s):
    return re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s or "")

def parse_pokedata_message(message):
    text = message.content or ""
    if not text:
        return None

    low = text.casefold()
    if "league cup vg" in low:
        event_type = "cup"
    elif "league challenge vg" in low:
        event_type = "challenge"
    else:
        return None

    urls = URL_RE.findall(text)
    pokemon_url = next(
        (u.rstrip(".,)") for u in urls
         if "pokemon.com" in u.lower() and "tournaments" in u.lower()),
        None
    )

    pokedata_id = None
    if pokemon_url:
        m = ID_RE.search(pokemon_url)
        if m:
            pokedata_id = m.group(1)

    if not pokedata_id:
        pokedata_id = f"discord-{message.id}"

    lines = [x.strip() for x in text.splitlines() if x.strip()]

    name = ""
    for i, line in enumerate(lines):
        plain = _markdown_links_to_text(line).replace("**", "").strip()
        if "pokemon.com" in line.lower() and i + 1 < len(lines):
            candidate = _markdown_links_to_text(lines[i + 1]).replace("**", "").strip()
            if candidate and "pokemon.com" not in candidate.lower():
                name = candidate
                break

    country_index = next(
        (i for i, x in enumerate(lines)
         if x.replace("*", "").strip().casefold() == "country"),
        None
    )
    organizer = ""
    if country_index is not None:
        candidates = []
        for candidate in lines[:country_index]:
            candidate = _markdown_links_to_text(candidate).replace("**", "").strip()
            if candidate and "pokemon.com" not in candidate.lower():
                candidates.append(candidate)
        # The organizer is normally the last non-link line before Country.
        if candidates:
            organizer = candidates[-1]

    if not name:
        name = _field(text, "Name") or (
            f"VGC {'Cup' if event_type == 'cup' else 'Challenge'}"
        )

    raw_date = _field(text, "Date")
    try:
        event_date = datetime.strptime(raw_date, "%Y-%m-%d").date().isoformat()
    except ValueError:
        return None

    city = _field(text, "City")
    region = _field(text, "State")
    address = _field(text, "Address")

    if not city or not region:
        return None

    return {
        "pokedata_id": pokedata_id,
        "type": event_type,
        "name": name,
        "date": event_date,
        "city": city,
        "region": region,
        "address": address,
        "organizer": organizer,
        "url": pokemon_url or "",
        "source_message_id": str(message.id),
    }
