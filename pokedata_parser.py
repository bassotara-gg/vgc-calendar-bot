import re
from datetime import datetime

URL_RE = re.compile(r"https?://[^\s)>\]]+", re.I)
ID_RE = re.compile(r"/(\d{2}-\d{2}-\d{6})/?(?:[\s\"'>]|$)", re.I)
EVENT_RE = re.compile(r"\b(?:league\s+(?:cup|challenge)|(?:vg\s+)?league\s+(?:cup|challenge)|(?:league\s+(?:cup|challenge))\s+vg)\b", re.I)


def _clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _strip_markdown(value):
    value = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", value or "")
    return _clean(value.replace("**", "").replace("__", ""))


def _pokemon_url(value):
    for url in URL_RE.findall(str(value or "")):
        url = url.rstrip(".,)")
        if "pokemon.com" in url.lower() and "play-pokemon-tournaments" in url.lower():
            return url
    return ""


def _event_id(url):
    match = re.search(r"/(\d{2}-\d{2}-\d{6})/?(?:$|[?#\s])", url or "", re.I)
    return match.group(1) if match else ""


def _event_type(value):
    text = _clean(value).casefold()
    if not EVENT_RE.search(text):
        return ""
    return "cup" if "cup" in text else "challenge"


def _field_from_text(text, label):
    match = re.search(
        rf"(?im)^\s*\*?\*?{re.escape(label)}\*?\*?\s*$\n\s*([^\n]+)",
        text or "",
    )
    return _clean(match.group(1)) if match else ""


def _parse_date(value):
    value = _clean(value)
    try:
        return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
    except ValueError:
        return ""


def _make_event(message_id, event_type, name, url, city, region, address, organizer, raw_date):
    url = _pokemon_url(url)
    pokedata_id = _event_id(url)
    event_date = _parse_date(raw_date)
    if not event_type or not pokedata_id or not event_date or not city or not region:
        return None
    return {
        "pokedata_id": pokedata_id,
        "type": event_type,
        "name": _strip_markdown(name) or f"VGC {'Cup' if event_type == 'cup' else 'Challenge'}",
        "date": event_date,
        "city": _clean(city),
        "region": _clean(region),
        "address": _clean(address),
        "organizer": _clean(organizer),
        "url": url,
        "source_message_id": str(message_id),
    }


def _parse_embed(embed, message_id):
    title = _clean(getattr(embed, "title", ""))
    description = _clean(getattr(embed, "description", ""))
    embed_url = _clean(getattr(embed, "url", ""))

    # Pokedata normally puts the Pokémon tournament URL in the embed URL or title.
    combined_header = "\n".join(x for x in (title, description, embed_url) if x)
    event_type = _event_type(combined_header)
    pokemon_url = _pokemon_url(embed_url) or _pokemon_url(title) or _pokemon_url(description)
    if not event_type or not pokemon_url:
        return None

    fields = {}
    for field in getattr(embed, "fields", []) or []:
        field_name = _clean(getattr(field, "name", ""))
        field_value = _clean(getattr(field, "value", ""))
        if field_name:
            fields[field_name.casefold()] = field_value

    # Discord embeds expose organizer as description in the Pokedata format.
    # If description also contains the URL, strip the URL and formatting.
    organizer = description
    organizer = URL_RE.sub("", organizer)
    organizer = _strip_markdown(organizer)

    # The event name is the title before the Pokémon URL. Pokedata examples often
    # use either "VG League Challenge ..." or "League Challenge VG ...".
    name = title
    name = URL_RE.sub("", name)
    name = _strip_markdown(name)

    return _make_event(
        message_id,
        event_type,
        name,
        pokemon_url,
        fields.get("city", ""),
        fields.get("state", ""),
        fields.get("address", ""),
        organizer,
        fields.get("date", ""),
    )


def _parse_text_block(block, message_id):
    # Fallback for older/non-embed Pokedata messages.
    pokemon_url = _pokemon_url(block)
    event_type = _event_type(block)
    if not pokemon_url or not event_type:
        return None

    lines = [x.strip() for x in (block or "").splitlines() if x.strip()]
    header_index = next(
        (i for i, line in enumerate(lines) if EVENT_RE.search(_strip_markdown(line))),
        None,
    )
    name = ""
    organizer = ""
    if header_index is not None:
        candidates = []
        for line in lines[header_index + 1 :]:
            clean = _strip_markdown(line)
            if not clean or _pokemon_url(line):
                continue
            if re.fullmatch(r"(?:country|state|address|date|city)", clean, re.I):
                break
            candidates.append(clean)
        if candidates:
            name = candidates[0]
        if len(candidates) >= 2:
            organizer = candidates[-1]

    return _make_event(
        message_id,
        event_type,
        name,
        pokemon_url,
        _field_from_text(block, "City"),
        _field_from_text(block, "State"),
        _field_from_text(block, "Address"),
        organizer,
        _field_from_text(block, "Date"),
    )


def parse_pokedata_message(message):
    """Return every Cup/Challenge event contained in a Pokedata Discord message."""
    events = []

    # Current Pokedata webhook format: one Discord message can contain multiple embeds.
    for embed in getattr(message, "embeds", []) or []:
        event = _parse_embed(embed, message.id)
        if event:
            events.append(event)

    # Fallback for old/plain-text webhook messages.
    text = getattr(message, "content", "") or ""
    if text:
        events_in_text = []
        # Split on event headers when possible; otherwise try the whole message.
        matches = list(re.finditer(r"(?im)^.*?(?:league\s+(?:cup|challenge)|(?:vg\s+)?league\s+(?:cup|challenge)).*$", text))
        if matches:
            for index, match in enumerate(matches):
                start = match.start()
                end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
                event = _parse_text_block(text[start:end], message.id)
                if event:
                    events_in_text.append(event)
        else:
            event = _parse_text_block(text, message.id)
            if event:
                events_in_text.append(event)
        events.extend(events_in_text)

    unique = {}
    for event in events:
        unique[event["pokedata_id"]] = event
    return list(unique.values())
