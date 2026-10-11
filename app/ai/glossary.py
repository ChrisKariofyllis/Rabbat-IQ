"""A small bilingual grocery glossary for keyword mode.

Semantic matching, when an AI key is configured, covers everything else.
"""

SYNONYMS: dict[str, list[str]] = {
    "yogurt": ["joghurt", "yoghurt"],
    "yoghurt": ["joghurt", "yogurt"],
    "joghurt": ["yogurt", "yoghurt"],
    "greek": ["griechisch", "griechischer", "griechische"],
    "griechisch": ["greek"],
    "beer": ["bier", "pils", "helles"],
    "bier": ["beer", "pils", "helles"],
    "pils": ["beer", "bier"],
    "milk": ["milch"],
    "milch": ["milk"],
    "cheese": ["kase", "kaese"],
    "kase": ["cheese"],
    "bread": ["brot"],
    "brot": ["bread"],
    "coffee": ["kaffee"],
    "kaffee": ["coffee"],
    "water": ["wasser"],
    "wasser": ["water"],
    "chicken": ["hahnchen", "haehnchen", "huhn"],
    "butter": ["butter"],
    "tools": ["werkzeug"],
    "tool": ["werkzeug"],
    "werkzeug": ["tools", "tool"],
    "toolbox": ["werkzeugkasten"],
    "werkzeugkasten": ["toolbox", "werkzeug"],
}
