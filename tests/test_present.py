from app.web.present import chain_color


def test_named_chains_keep_a_stable_color():
    assert chain_color("EDEKA") == ("var(--chain-edeka)", "edeka")
    assert chain_color("Lidl") == ("var(--chain-lidl)", "lidl")
    assert chain_color("Netto Marken-Discount")[1] == "netto"
    assert chain_color("REWE City")[1] == "rewe"
    assert chain_color("ALDI SÜD") == ("var(--chain-aldi)", "aldi")
    assert chain_color("NORMA")[1] == "norma"
    assert chain_color("Mix Markt")[1] == "mix"
    assert chain_color("GALERIA Kaufhof")[1] == "galeria"


def test_unknown_chains_stay_on_one_fallback():
    first = chain_color("Wochenmarkt am Isartor")
    assert first == chain_color("Wochenmarkt am Isartor")
    assert first[0].startswith("var(--chain-fallback-")
    assert first[1] == ""


def test_short_names_do_not_swallow_other_words():
    assert chain_color("Hit")[1] == "hit"
    assert chain_color("Hitachi")[1] == ""
    assert chain_color("dm")[1] == "dm"
    assert chain_color("Edmunds")[1] == ""
