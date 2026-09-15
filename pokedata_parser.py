import re
from datetime import datetime

URL_RE = re.compile(r"https?://[^\s)>]+", re.I)
ID_RE = re.compile(r"/(\d{2}-\d{2}-\d{6})/?(?:\?.*)?$", re.I)


def _clean(s):
    return re.sub(r"\s+", " ", s or "").strip()


def _extract_event_id(url):
    if not url:
        return ""
    match = ID_RE.search(url.rstrip(".,)"))
    return match.group(1) if match else ""


def _extract_pokemon_url(text):
    for url in URL_RE.findall(text or ""):
        clean = url.rstrip(".,)")
        lower = clean.lower()
        if "pokemon.com" in lower and "play-pokemon-tournaments" in lower:
            return clean
    return ""


def _event_from_values(*, title, description, fields, message_id):
    """Parse one Pokedata Discord embed into an event dictionary."""
    title = _clean(title)
    description = _clean(description)

    lower_title = title.casefold()
    if "league challenge" in lower_title and "pokemon" in lower_title:
        event_type = "challenge"
    elif "league cup" in lower_title and "pokemon" in lower_title:
        event_type = "cup"
    else:
        # Pokedata's actual embed title contains the Pokémon URL even when
        # the visible title text itself doesn't contain the word Pokémon.
        if "league challenge" in lower_title:
            event_type = "challenge"
        elif "league cup" in lower_title:
            event_type = "cup"
        else:
            return None

    pokemon_url = _extract_pokemon_url(title)
    if not pokemon_url:
        return None

    pokedata_id = _extract_event_id(pokemon_url)
    if not pokedata_id:
        return None

    field_map = {}
    for name, value in fields:
        field_map[_clean(name).casefold()] = _clean(value)

    raw_date = field_map.get("date", "")
    try:
        event_date = datetime.strptime(raw_date, "%Y-%m-%d").date().isoformat()
    except ValueError:
        return None

    city = field_map.get("city", "")
    region = field_map.get("state", "")
    address = field_map.get("address", "")
    if not city or not region:
        return None

    # The Pokedata embed uses description for the organizer.
    organizer = description

    # Remove the URL from the title to obtain the event name.
    name = re.sub(r"\s*https?://\S+", "", title, count=1, flags=re.I).strip()
    name = _clean(name)

    return {
        "pokedata_id": pokedata_id,
        "type": event_type,
        "name": name or f"VGC {'Cup' if event_type == 'cup' else 'Challenge'}",
        "date": event_date,
        "city": city,
        "region": region,
        "address": address,
        "organizer": organizer,
        "url": pokemon_url,
        "source_message_id": str(message_id),
    }


def _parse_embed(embed, message_id):
    fields = []
    for field in getattr(embed, "fields", []) or []:
        fields.append((getattr(field, "name", ""), getattr(field, "value", "")))

    return _event_from_values(
        title=getattr(embed, "title", "") or "",
        description=getattr(embed, "description", "") or "",
        fields=fields,
        message_id=message_id,
    )


def _parse_text_message(message):
    """Fallback parser for the older/text Pokedata format."""
    text = message.content or ""
    if not text:
        return []

    # Split on each Pokémon tournament URL/header. This fallback is kept for
    # compatibility with older messages; current Pokedata events use embeds.
    header_re = re.compile(
        r"(?im)^.*?League\s+(Cup|Challenge)\s+VG.*?pokemon\.com.*?$"
    )
    starts = [m.start() for m in header_re.finditer(text)]
    if not starts:
        return []

    events = []
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(text)
        block = text[start:end]
        lines = [x.strip() for x in block.splitlines() if x.strip()]
        if not lines:
            continue

        header = header_re.search(block)
        event_type = "cup" if header.group(1).casefold() == "cup" else "challenge"
        pokemon_url = _extract_pokemon_url(block)
        pokedata_id = _extract_event_id(pokemon_url)
        if not pokedata_id:
            continue

        def field(label):
            pattern = rf"\*?\*?{re.escape(label)}\*?\*?\s*\n\s*([^\n]+)"
            match = re.search(pattern, block, re.I)
            return _clean(match.group(1)) if match else ""

        raw_date = field("Date")
        try:
            event_date = datetime.strptime(raw_date, "%Y-%m-%d").date().isoformat()
        except ValueError:
            continue

        city = field("City")
        region = field("State")
        address = field("Address")
        if not city or not region:
            continue

        header_line = next((line for line in lines if "League " in line and "VG" in line and "pokemon.com" in line.lower()), "")
        header_index = lines.index(header_line) if header_line else 0
        name = ""
        if header_index + 1 < len(lines):
            candidate = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", lines[header_index + 1])
            candidate = candidate.replace("**", "").strip()
            if candidate and "pokemon.com" not in candidate.lower():
                name = candidate

        country_index = next(
            (i for i, line in enumerate(lines) if line.replace("*", "").strip().casefold() == "country"),
            None,
        )
        organizer = ""
        if country_index is not None:
            candidates = []
            for candidate in lines[header_index + 1:country_index]:
                candidate = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", candidate)
                candidate = candidate.replace("**", "").strip()
                if candidate and "pokemon.com" not in candidate.lower():
                    candidates.append(candidate)
            if len(candidates) >= 2:
                organizer = candidates[-1]

        events.append({
            "pokedata_id": pokedata_id,
            "type": event_type,
            "name": name or f"VGC {'Cup' if event_type == 'cup' else 'Challenge'}",
            "date": event_date,
            "city": city,
            "region": region,
            "address": address,
            "organizer": organizer,
            "url": pokemon_url,
            "source_message_id": str(message.id),
        })

    return events


def parse_pokedata_message(message):
    """Return every Cup/Challenge event contained in a Pokedata Discord message.

    Current Pokedata messages use Discord embeds, so every embed is parsed
    independently. The function also retains support for the older text format.
    """
    events = []

    for embed in getattr(message, "embeds", []) or []:
        event = _parse_embed(embed, message.id)
        if event:
            events.append(event)

    if not events and getattr(message, "content", ""):
        events.extend(_parse_text_message(message))

    unique = {}
    for event in events:
        unique[event["pokedata_id"]] = event
    return list(unique.values())
