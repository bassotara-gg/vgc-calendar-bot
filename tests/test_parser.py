from types import SimpleNamespace

from pokedata_parser import parse_pokedata_message


def embed(title, description, fields, url=""):
    return SimpleNamespace(
        title=title,
        description=description,
        url=url,
        fields=[SimpleNamespace(name=k, value=v) for k, v in fields.items()],
    )


def message(*embeds, content=""):
    return SimpleNamespace(id=123456, content=content, embeds=list(embeds))


def test_cup_embed():
    e = parse_pokedata_message(message(embed(
        "League Cup VG",
        "IL COVO DEL NERD ERBA",
        {
            "Country": "IT",
            "State": "Lombardia",
            "Address": "CORSO XXV APRILE, 74, 22036 ERBA CO, ITALY",
            "Date": "2026-10-11",
            "City": "Erba",
        },
        "https://www.pokemon.com/us/pokemon-trainer-club/play-pokemon-tournaments/26-10-004173/",
    )))
    assert len(e) == 1
    assert e[0]["type"] == "cup"
    assert e[0]["date"] == "2026-10-11"
    assert e[0]["city"] == "Erba"
    assert e[0]["region"] == "Lombardia"
    assert e[0]["pokedata_id"] == "26-10-004173"


def test_challenge_embed_url_in_title():
    e = parse_pokedata_message(message(embed(
        "VG League Challenge Ottobre\nhttps://www.pokemon.com/us/pokemon-trainer-club/play-pokemon-tournaments/25-10-004290/",
        "MAGIC HISTORY",
        {
            "Country": "IT",
            "State": "Umbria",
            "Address": "52 VIA CADUTI DEL LAVORO, PERUGIA, UMBRIA 06124, IT",
            "Date": "2025-10-12",
            "City": "Perugia",
        },
    )))
    assert len(e) == 1
    assert e[0]["type"] == "challenge"
    assert e[0]["pokedata_id"] == "25-10-004290"
    assert e[0]["organizer"] == "MAGIC HISTORY"


def test_multiple_embeds_in_one_message():
    embeds = [
        embed(
            "League Challenge VG Ottobre LA TANA",
            "LA TANA",
            {"State": "Umbria", "Address": "Via X", "Date": "2026-10-24", "City": "Terni"},
            "https://www.pokemon.com/us/pokemon-trainer-club/play-pokemon-tournaments/26-10-005540/",
        ),
        embed(
            "League CUP VG Novembre LA TANA",
            "LA TANA",
            {"State": "Umbria", "Address": "Via X", "Date": "2026-11-15", "City": "Terni"},
            "https://www.pokemon.com/us/pokemon-trainer-club/play-pokemon-tournaments/26-11-004323/",
        ),
    ]
    e = parse_pokedata_message(message(*embeds))
    assert len(e) == 2
    assert {x["pokedata_id"] for x in e} == {"26-10-005540", "26-11-004323"}


def test_legacy_text_fallback():
    content = """[League Cup VG](https://www.pokemon.com/us/pokemon-trainer-club/play-pokemon-tournaments/26-10-004173/)\n\nIL COVO DEL NERD ERBA\n\n**Country**\n\nIT\n\n**State**\n\nLombardia\n\n**Address**\n\nCORSO XXV APRILE\n\n**Date**\n\n2026-10-11\n\n**City**\n\nErba\n"""
    e = parse_pokedata_message(SimpleNamespace(id=99, content=content, embeds=[]))
    assert len(e) == 1
    assert e[0]["pokedata_id"] == "26-10-004173"
