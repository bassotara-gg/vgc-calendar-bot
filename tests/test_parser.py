from types import SimpleNamespace

from pokedata_parser import parse_pokedata_message


def field(name, value):
    return SimpleNamespace(name=name, value=value)


def embed(title="", description="", url="", fields=None, author_name="", author_url=""):
    return SimpleNamespace(
        title=title,
        description=description,
        url=url,
        fields=fields or [],
        author=SimpleNamespace(name=author_name, url=author_url),
    )


def message(content="", embeds=None, message_id=1):
    return SimpleNamespace(id=message_id, content=content, embeds=embeds or [])


def common_fields(city="Firenze", region="Toscana", date="2026-10-11"):
    return [
        field("Country", "IT"),
        field("State", region),
        field("Address", "168 VIA FRANCESCO BARACCA, FIRENZE, TOSCANA 50145, IT"),
        field("Date", date),
        field("City", city),
    ]


def test_standard_embed_with_type_in_title():
    e = embed(
        title="League Cup VG\nhttps://www.pokemon.com/us/pokemon-trainer-club/play-pokemon-tournaments/26-10-007775/",
        description="GAME FIRENZE",
        fields=common_fields(),
    )
    events = parse_pokedata_message(message(embeds=[e]))
    assert len(events) == 1
    assert events[0]["pokedata_id"] == "26-10-007775"
    assert events[0]["type"] == "cup"
    assert events[0]["city"] == "Firenze"
    assert events[0]["region"] == "Toscana"


def test_pokedata_variant_type_in_author_and_event_name_in_title():
    e = embed(
        title="Vgc CUP Ottobre - Game Firenze",
        description="GAME FIRENZE",
        url="https://www.pokemon.com/us/pokemon-trainer-club/play-pokemon-tournaments/26-10-007775/",
        author_name="League Cup VG",
        fields=common_fields(),
    )
    events = parse_pokedata_message(message(embeds=[e], message_id=2))
    assert len(events) == 1
    assert events[0]["pokedata_id"] == "26-10-007775"
    assert events[0]["type"] == "cup"
    assert events[0]["name"] == "Vgc CUP Ottobre - Game Firenze"


def test_two_embeds_same_message():
    cup = embed(
        title="League Cup VG",
        description="Vgc CUP Ottobre - Game Firenze",
        url="https://www.pokemon.com/us/pokemon-trainer-club/play-pokemon-tournaments/26-10-007775/",
        fields=common_fields(),
    )
    challenge = embed(
        title="League Challenge VG",
        description="Vgc Challenge Ottobre- Side Event - Game Firenze",
        url="https://www.pokemon.com/us/pokemon-trainer-club/play-pokemon-tournaments/26-10-007776/",
        fields=common_fields(),
    )
    events = parse_pokedata_message(message(embeds=[cup, challenge], message_id=3))
    assert {e["pokedata_id"] for e in events} == {"26-10-007775", "26-10-007776"}
    assert {e["type"] for e in events} == {"cup", "challenge"}


def test_plain_text_fallback():
    text = """[**League Challenge VG**](https://www.pokemon.com/us/pokemon-trainer-club/play-pokemon-tournaments/26-10-007776/)\n\n**Vgc Challenge Ottobre- Side Event - Game Firenze** [**https://www.pokemon.com/us/pokemon-trainer-club/play-pokemon-tournaments/26-10-007776/**](https://www.pokemon.com/us/pokemon-trainer-club/play-pokemon-tournaments/26-10-007776/)\n\nGAME FIRENZE\n\n**Country**\n\nIT\n\n**State**\n\nToscana\n\n**Address**\n\n168 VIA FRANCESCO BARACCA, FIRENZE, TOSCANA 50145, IT\n\n**Date**\n\n2026-10-11\n\n**City**\n\nFirenze"""
    events = parse_pokedata_message(message(content=text, message_id=4))
    assert len(events) == 1
    assert events[0]["pokedata_id"] == "26-10-007776"
    assert events[0]["type"] == "challenge"
