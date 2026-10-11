"""Small pure helpers for search text, prices, and model output."""

import json
import re
import unicodedata


def normalize(text: str | None) -> str:
    value = (text or "").casefold().replace("ß", "ss")
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def same_chain(left: str | None, right: str | None) -> bool:
    """True when two retailer labels refer to the same banner.

    "Aldi" matches "ALDI SÜD". Short fragments such as "hit" do not match
    unrelated words.
    """

    a = normalize(left)
    b = normalize(right)
    if not a or not b:
        return False
    if a == b:
        return True
    short, long = (a, b) if len(a) <= len(b) else (b, a)
    if len(short) < 4:
        return False
    return long.startswith(short)


def parse_preferred(text: str | None) -> list[str]:
    parts = re.split(r"[,;\n]+", text or "")
    return [part.strip() for part in parts if part.strip()]


def parse_price(value) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = re.sub(r"[^\d,.\-]", "", str(value))
    if not text or text in {"-", ".", ",", "-."}:
        return None
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def extract_json(text: str) -> dict | list:
    """Pull the JSON object or array out of a model reply."""

    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    start_obj = cleaned.find("{")
    start_arr = cleaned.find("[")
    if start_obj < 0 and start_arr < 0:
        raise ValueError("The model reply did not contain JSON.")
    if start_arr >= 0 and (start_obj < 0 or start_arr < start_obj):
        end = cleaned.rfind("]")
        if end < start_arr:
            raise ValueError("The model reply did not contain JSON.")
        return json.loads(cleaned[start_arr : end + 1])
    end = cleaned.rfind("}")
    if end < start_obj:
        raise ValueError("The model reply did not contain JSON.")
    return json.loads(cleaned[start_obj : end + 1])


def clamp_confidence(value) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    if number > 1:
        number = number / 100
    return max(0.0, min(1.0, number))
