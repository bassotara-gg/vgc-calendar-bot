from types import SimpleNamespace

from pokedata_parser import parse_pokedata_message


def make_embed(title, description, **fields):
    return SimpleNamespace(
        title=title,
        description=description,
        url=None,
        fields=[SimpleNamespace(name=name, value=value) for name, value in fields.items()],
    )


def test_embed_cup():
    message = SimpleNamespace(
        id=1435435444081791058,
        content="",
        embeds=[make_embed(
            "league Cup VCG Infinity\nhttps://www.pokemon.com/us/pokemon-trainer-club/play-pokemon-tournaments/25-12-003934/",
            "MAGIC LAIR",
            Country="IT",
            State="Piedmont",
            Address="14/F CORSO PRINCIPE ODDONE, TORINO, PIEMONTE 10122, IT",
            Date="2025-12-07",
            City="Turin",
        )],
    )

    events = parse_pokedata_message(message)
    assert len(events) == 1
    event = events[0]
    assert event["type"] == "cup"
    assert event["name"] == "league Cup VCG Infinity"
    assert event["organizer"] == "MAGIC LAIR"
    assert event["date"] == "2025-12-07"
    assert event["city"] == "Turin"
    assert event["region"] == "Piedmont"
    assert event["pokedata_id"] == "25-12-003934"


def test_embed_challenge():
    message = SimpleNamespace(
        id=1422275428139139233,
        content="",
        embeds=[make_embed(
            "VG League Challenge Ottobre\nhttps://www.pokemon.com/us/pokemon-trainer-club/play-pokemon-tournaments/25-10-004290/",
            "MAGIC HISTORY",
            Country="IT",
            State="Umbria",
            Address="52 VIA CADUTI DEL LAVORO, PERUGIA, UMBRIA 06124, IT",
            Date="2025-10-12",
            City="Perugia",
        )],
    )

    events = parse_pokedata_message(message)
    assert len(events) == 1
    event = events[0]
    assert event["type"] == "challenge"
    assert event["organizer"] == "MAGIC HISTORY"
    assert event["pokedata_id"] == "25-10-004290"


def test_multiple_embeds_in_one_message():
    message = SimpleNamespace(
        id=999,
        content="",
        embeds=[
            make_embed(
                "League Challenge VG Ottobre LA TANA\nhttps://www.pokemon.com/us/pokemon-trainer-club/play-pokemon-tournaments/26-10-005540/",
                "LA TANA",
                Country="IT", State="Umbria", Address="Via Test 1", Date="2026-10-24", City="Terni",
            ),
            make_embed(
                "VGC League Challenge\nhttps://www.pokemon.com/us/pokemon-trainer-club/play-pokemon-tournaments/26-09-014680/",
                "COLLECTOR PLAZA",
                Country="IT", State="Piemonte", Address="Via Test 2", Date="2026-09-19", City="Torino",
            ),
            make_embed(
                "League Challenge VG Settembre LA TANA\nhttps://www.pokemon.com/us/pokemon-trainer-club/play-pokemon-tournaments/26-09-014739/",
                "LA TANA",
                Country="IT", State="Umbria", Address="Via Test 3", Date="2026-09-26", City="Terni",
            ),
            make_embed(
                "League Challenge VG Novembre LA TANA\nhttps://www.pokemon.com/us/pokemon-trainer-club/play-pokemon-tournaments/26-11-004326/",
                "LA TANA",
                Country="IT", State="Umbria", Address="Via Test 4", Date="2026-11-15", City="Terni",
            ),
            make_embed(
                "League CUP VG Novembre LA TANA\nhttps://www.pokemon.com/us/pokemon-trainer-club/play-pokemon-tournaments/26-11-004323/",
                "LA TANA",
                Country="IT", State="Umbria", Address="Via Test 5", Date="2026-11-15", City="Terni",
            ),
        ],
    )

    events = parse_pokedata_message(message)
    assert len(events) == 5
    assert {event["pokedata_id"] for event in events} == {
        "26-10-005540",
        "26-09-014680",
        "26-09-014739",
        "26-11-004326",
        "26-11-004323",
    }
    assert sum(event["region"] == "Umbria" for event in events) == 4


def test_old_text_format_still_works():
    message = SimpleNamespace(
        id=123456,
        content="""[League Cup VG](https://www.pokemon.com/us/pokemon-trainer-club/play-pokemon-tournaments/26-10-004173/)\n\n**cup VGC 11-10-2026** [https://www.pokemon.com/us/pokemon-trainer-club/play-pokemon-tournaments/26-10-004173/](https://www.pokemon.com/us/pokemon-trainer-club/play-pokemon-tournaments/26-10-004173/)\n\nIL COVO DEL NERD ERBA\n\n**Country**\n\nIT\n\n**State**\n\nLombardia\n\n**Address**\n\nCORSO XXV APRILE, 74, 22036 ERBA CO, ITALY\n\n**Date**\n\n2026-10-11\n\n**City**\n\nErba\n""",
        embeds=[],
    )

    events = parse_pokedata_message(message)
    assert len(events) == 1
    assert events[0]["type"] == "cup"
    assert events[0]["pokedata_id"] == "26-10-004173"
