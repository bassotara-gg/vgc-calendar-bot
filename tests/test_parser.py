from pokedata_parser import parse_pokedata_message

class FakeMessage:
    id = 123456
    content = """[League Cup VG](https://www.pokemon.com/us/pokemon-trainer-club/play-pokemon-tournaments/26-10-004173/)

**cup VGC 11-10-2026** [https://www.pokemon.com/us/pokemon-trainer-club/play-pokemon-tournaments/26-10-004173/](https://www.pokemon.com/us/pokemon-trainer-club/play-pokemon-tournaments/26-10-004173/)

IL COVO DEL NERD ERBA

**Country**

IT

**State**

Lombardia

**Address**

CORSO XXV APRILE, 74, 22036 ERBA CO, ITALY

**Date**

2026-10-11

**City**

Erba
"""

def test_cup():
    e = parse_pokedata_message(FakeMessage())
    assert e["type"] == "cup"
    assert e["date"] == "2026-10-11"
    assert e["city"] == "Erba"
    assert e["region"] == "Lombardia"
    assert e["pokedata_id"] == "26-10-004173"


class FakeChallenge:
    id = 123457
    content = """[League Challenge VG](https://www.pokemon.com/us/pokemon-trainer-club/play-pokemon-tournaments/26-10-004171/)

**Play!OnGame League Challenge 10** [https://www.pokemon.com/us/pokemon-trainer-club/play-pokemon-tournaments/26-10-004171/](https://www.pokemon.com/us/pokemon-trainer-club/play-pokemon-tournaments/26-10-004171/)

ONGAME MONTESILVANO

**Country**

IT

**State**

Abruzzo

**Address**

VIA SAN FRANCESCO, 3, 65015 MONTESILVANO PE, ITALY

**Date**

2026-10-16

**City**

Montesilvano
"""

def test_challenge():
    e = parse_pokedata_message(FakeChallenge())
    assert e["type"] == "challenge"
    assert e["date"] == "2026-10-16"
    assert e["city"] == "Montesilvano"
    assert e["region"] == "Abruzzo"
    assert e["pokedata_id"] == "26-10-004171"
