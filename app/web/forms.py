"""Validate the settings form. Blank secrets keep the saved value."""

import re

PROVIDERS = ("openai", "gemini", "anthropic", "ollama")
MATCH_MODES = ("keyword", "semantic")
COUNTRIES = {"de": "Germany", "at": "Austria"}
CATEGORY_OPTIONS = (
    ("grocery", "Supermarkets and discounters"),
    ("drugstore", "Drugstores"),
    ("hardware", "Hardware stores"),
    ("all", "Every retailer in the feed"),
)


def settings_form_values(settings) -> dict:
    categories = [part.strip() for part in (settings.categories or "").split(",") if part.strip()]
    return {
        "postal_code": settings.postal_code or "",
        "country": settings.country or "de",
        "radius_km": settings.radius_km if settings.radius_km is not None else 5,
        "scan_interval_minutes": settings.scan_interval_minutes or 30,
        "preferred_stores": settings.preferred_stores or "",
        "categories": categories or ["grocery"],
        "match_mode": settings.match_mode or "keyword",
        "min_confidence": settings.min_confidence if settings.min_confidence is not None else 0.55,
        "vision_enabled": bool(settings.vision_enabled),
        "vision_max_pages": settings.vision_max_pages if settings.vision_max_pages is not None else 3,
        "ai_provider": settings.ai_provider or "openai",
        "ai_model": settings.ai_model or "",
        "ai_base_url": settings.ai_base_url or "http://127.0.0.1:11434",
        "telegram_chat_id": settings.telegram_chat_id or "",
        "has_ai_key": bool(settings.ai_api_key),
        "has_telegram_token": bool(settings.telegram_bot_token),
    }


def parse_settings_form(form, current) -> tuple[dict | None, list[str]]:
    errors: list[str] = []
    postal = str(form.get("postal_code") or "").strip()
    country = str(form.get("country") or "de").strip().lower()
    if country not in COUNTRIES:
        errors.append("Choose Germany or Austria.")
        country = "de"
    if country == "de" and postal and not re.fullmatch(r"\d{5}", postal):
        errors.append("German postal codes are 5 digits.")
    if country == "at" and postal and not re.fullmatch(r"\d{4}", postal):
        errors.append("Austrian postal codes are 4 digits.")

    try:
        radius = float(str(form.get("radius_km") or "5").replace(",", "."))
    except ValueError:
        errors.append("Radius must be a number of kilometres.")
        radius = 5
    else:
        if radius < 0.5 or radius > 30:
            errors.append("Radius must be between 0.5 and 30 km.")

    try:
        interval = int(str(form.get("scan_interval_minutes") or "30"))
    except ValueError:
        errors.append("Scan interval must be a whole number of minutes.")
        interval = 30
    else:
        if interval < 15 or interval > 180:
            errors.append("Scan interval must be between 15 and 180 minutes.")

    preferred = str(form.get("preferred_stores") or "").strip()
    if len(preferred) > 300:
        errors.append("Keep the store filter under 300 characters.")

    selected = [item for item in form.getlist("categories") if item in {key for key, _ in CATEGORY_OPTIONS}]
    if not selected:
        errors.append("Choose at least one retailer group.")
    categories = "all" if "all" in selected else ",".join(selected)

    match_mode = str(form.get("match_mode") or "keyword")
    if match_mode not in MATCH_MODES:
        errors.append("Choose keyword or semantic matching.")
        match_mode = "keyword"

    try:
        confidence = float(str(form.get("min_confidence") or "0.55").replace(",", "."))
    except ValueError:
        errors.append("Minimum confidence must be a number between 0.3 and 0.95.")
        confidence = 0.55
    else:
        if confidence < 0.3 or confidence > 0.95:
            errors.append("Minimum confidence must be between 0.3 and 0.95.")

    try:
        vision_pages = int(str(form.get("vision_max_pages") or "3"))
    except ValueError:
        errors.append("Vision page budget must be a whole number.")
        vision_pages = 3
    else:
        if vision_pages < 0 or vision_pages > 8:
            errors.append("Vision page budget must be between 0 and 8 pages per scan.")

    provider = str(form.get("ai_provider") or "openai").strip().lower()
    if provider not in PROVIDERS:
        errors.append("Choose an AI provider.")
        provider = "openai"
    model = str(form.get("ai_model") or "").strip()
    if len(model) > 80:
        errors.append("Model name must be under 80 characters.")
    base_url = str(form.get("ai_base_url") or "").strip() or "http://127.0.0.1:11434"
    if not base_url.startswith(("http://", "https://")):
        errors.append("The model base URL must start with http:// or https://.")

    chat_id = str(form.get("telegram_chat_id") or "").strip()
    if chat_id and not re.fullmatch(r"-?\d+", chat_id):
        errors.append("Telegram chat id should be a number. Send /start to the bot to see it.")

    api_key = str(form.get("ai_api_key") or "").strip()
    if form.get("clear_ai_key"):
        api_key = ""
    elif not api_key:
        api_key = current.ai_api_key or ""

    token = str(form.get("telegram_bot_token") or "").strip()
    if form.get("clear_telegram_token"):
        token = ""
    elif not token:
        token = current.telegram_bot_token or ""

    if errors:
        return None, errors

    data = {
        "postal_code": postal,
        "country": country,
        "radius_km": radius,
        "scan_interval_minutes": interval,
        "preferred_stores": preferred,
        "categories": categories,
        "match_mode": match_mode,
        "min_confidence": confidence,
        "vision_enabled": bool(form.get("vision_enabled")),
        "vision_max_pages": vision_pages,
        "ai_provider": provider,
        "ai_model": model,
        "ai_api_key": api_key,
        "ai_base_url": base_url,
        "telegram_bot_token": token,
        "telegram_chat_id": chat_id,
    }
    if postal != (current.postal_code or ""):
        data["latitude"] = None
        data["longitude"] = None
        data["place_name"] = ""
    return data, []
