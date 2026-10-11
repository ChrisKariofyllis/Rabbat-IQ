"""A small bilingual grocery glossary for keyword mode and search queries.

The offer index is mostly German. English words are translated before the
search, and a few false friends are not sent through as-is: Marktguru stems
"beer" into Beeren (berries).

Semantic matching, when an AI key is configured, covers everything else.
"""

from app.textutil import normalize

# First entry is the term used in a combined query. Later entries are OR'd
# for a single-word interest.
QUERY_TERMS: dict[str, list[str]] = {
    "yogurt": ["Joghurt"],
    "yoghurt": ["Joghurt"],
    "joghurt": ["Joghurt"],
    "greek": ["griechisch"],
    "griechisch": ["griechisch"],
    "beer": ["Bier", "Pils"],
    "bier": ["Bier", "Pils"],
    "pils": ["Pils", "Bier"],
    "milk": ["Milch"],
    "milch": ["Milch"],
    "cheese": ["Käse"],
    "kase": ["Käse"],
    "bread": ["Brot"],
    "brot": ["Brot"],
    "coffee": ["Kaffee"],
    "kaffee": ["Kaffee"],
    "water": ["Wasser"],
    "wasser": ["Wasser"],
    "chicken": ["Hähnchen"],
    "tools": ["Werkzeug"],
    "tool": ["Werkzeug"],
    "werkzeug": ["Werkzeug"],
    "toolbox": ["Werkzeugkasten", "Werkzeug"],
    "werkzeugkasten": ["Werkzeugkasten", "Werkzeug"],
    "parkside": ["Parkside"],
}

# Sent alone, these match the wrong products on the German index.
FALSE_FRIENDS = {"beer"}

MODIFIERS = {"greek", "griechisch"}

GENERIC = {
    "yogurt",
    "yoghurt",
    "joghurt",
    "beer",
    "bier",
    "pils",
    "milk",
    "milch",
    "cheese",
    "kase",
    "bread",
    "brot",
    "coffee",
    "kaffee",
    "water",
    "wasser",
    "chicken",
    "tools",
    "tool",
    "werkzeug",
    "butter",
}


def queries_for_interest(interest: str) -> list[str]:
    """Up to two queries that should recall this interest from a German index."""

    raw = " ".join((interest or "").split())
    tokens = normalize(raw).split()
    if not tokens:
        return []
    parts: list[str] = []
    distinctive: list[str] = []
    for token in tokens:
        options = QUERY_TERMS.get(token, [token])
        parts.append(options[0])
        if token not in GENERIC and token not in MODIFIERS:
            distinctive.append(options[0])
    queries: list[str] = []
    if len(tokens) == 1:
        options = QUERY_TERMS.get(tokens[0], [parts[0]])
        if len(options) > 1:
            queries.append(" OR ".join(dict.fromkeys(options[:3])))
        else:
            queries.append(options[0])
    else:
        queries.append(" ".join(parts))
        if distinctive and " ".join(distinctive) not in queries:
            queries.append(" ".join(distinctive))
    if raw and normalize(raw) not in FALSE_FRIENDS and not all(token in QUERY_TERMS for token in tokens):
        queries.append(raw)
    unique: list[str] = []
    for query in queries:
        if query and query not in unique:
            unique.append(query)
    return unique[:2]


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
