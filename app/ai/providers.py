"""Bring-your-own-key chat clients for OpenAI, Gemini, Anthropic, and Ollama.

Each client asks for JSON text. Vision calls attach one JPEG.
"""

import base64
import logging

import httpx

log = logging.getLogger(__name__)

DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "gemini": "gemini-2.5-flash",
    "anthropic": "claude-haiku-4-5",
    "ollama": "llava",
}

OFFICIAL_BASES = {
    "openai": "https://api.openai.com/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta",
    "anthropic": "https://api.anthropic.com",
}


class AIError(Exception):
    """The model call failed. The message is safe to show in the UI."""


def resolve_model(provider: str, model: str) -> str:
    cleaned = (model or "").strip()
    return cleaned or DEFAULT_MODELS.get(provider, "")


def resolve_base(provider: str, base_url: str) -> str:
    custom = (base_url or "").strip().rstrip("/")
    if provider == "ollama":
        return custom or "http://127.0.0.1:11434"
    if custom and not custom.startswith("http://127.0.0.1:11434"):
        return custom
    return OFFICIAL_BASES.get(provider, "")


def ai_configured(provider: str, api_key: str, base_url: str) -> bool:
    if provider == "ollama":
        return bool(resolve_base(provider, base_url))
    return bool((api_key or "").strip())


async def complete(
    *,
    provider: str,
    model: str,
    api_key: str,
    base_url: str,
    system: str,
    user_text: str,
    images: list[bytes] | None = None,
) -> str:
    provider = (provider or "openai").strip().lower()
    chosen = resolve_model(provider, model)
    images = images or []
    if provider == "openai":
        return await _openai(chosen, api_key, resolve_base(provider, base_url), system, user_text, images)
    if provider == "gemini":
        return await _gemini(chosen, api_key, resolve_base(provider, base_url), system, user_text, images)
    if provider == "anthropic":
        return await _anthropic(chosen, api_key, resolve_base(provider, base_url), system, user_text, images)
    if provider == "ollama":
        return await _ollama(chosen, resolve_base(provider, base_url), system, user_text, images)
    raise AIError(f"Unknown AI provider “{provider}”.")


async def _post(url: str, *, headers: dict, payload: dict, secret: str = "") -> dict:
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(url, headers=headers, json=payload)
    except httpx.HTTPError as exc:
        raise AIError("Could not reach the AI provider.") from exc
    if response.status_code >= 400:
        detail = _safe_detail(response, secret)
        raise AIError(f"The AI provider returned HTTP {response.status_code}. {detail}".strip())
    try:
        return response.json()
    except ValueError as exc:
        raise AIError("The AI provider returned an unreadable response.") from exc


def _safe_detail(response: httpx.Response, secret: str) -> str:
    text = ""
    try:
        payload = response.json()
        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, dict):
                text = str(error.get("message") or "")
            elif isinstance(error, str):
                text = error
            else:
                text = str(payload.get("message") or "")
    except ValueError:
        text = response.text[:180]
    if secret:
        text = text.replace(secret, "[key]")
    return text[:240]


def _jpeg_b64(image: bytes) -> str:
    return base64.standard_b64encode(image).decode("ascii")


async def _openai(model, api_key, base, system, user_text, images) -> str:
    if not api_key:
        raise AIError("Add an OpenAI API key in settings.")
    content: str | list = user_text
    if images:
        content = [{"type": "text", "text": user_text}]
        for image in images[:1]:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(image)}"},
                }
            )
    payload = {
        "model": model,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": content},
        ],
    }
    data = await _post(
        f"{base}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        payload=payload,
        secret=api_key,
    )
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise AIError("OpenAI returned a response without text.") from exc


async def _gemini(model, api_key, base, system, user_text, images) -> str:
    if not api_key:
        raise AIError("Add a Gemini API key in settings.")
    parts: list[dict] = [{"text": system + "\n\n" + user_text}]
    for image in images[:1]:
        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": _jpeg_b64(image)}})
    payload = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
    }
    url = f"{base}/models/{model}:generateContent?key={api_key}"
    data = await _post(url, headers={"Content-Type": "application/json"}, payload=payload, secret=api_key)
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        raise AIError("Gemini returned a response without text.") from exc


async def _anthropic(model, api_key, base, system, user_text, images) -> str:
    if not api_key:
        raise AIError("Add an Anthropic API key in settings.")
    content: list[dict] = []
    for image in images[:1]:
        content.append(
            {
                "type": "image",
                "source": {"type": "base64", "media_type": "image/jpeg", "data": _jpeg_b64(image)},
            }
        )
    content.append({"type": "text", "text": user_text})
    payload = {
        "model": model,
        "max_tokens": 4096,
        "temperature": 0.1,
        "system": system,
        "messages": [{"role": "user", "content": content}],
    }
    data = await _post(
        f"{base}/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        payload=payload,
        secret=api_key,
    )
    try:
        blocks = data["content"]
        texts = [block.get("text", "") for block in blocks if isinstance(block, dict)]
        return "\n".join(texts)
    except (KeyError, TypeError) as exc:
        raise AIError("Anthropic returned a response without text.") from exc


async def _ollama(model, base, system, user_text, images) -> str:
    message: dict = {"role": "user", "content": user_text}
    if images:
        message["images"] = [_jpeg_b64(image) for image in images[:1]]
    payload = {
        "model": model,
        "stream": False,
        "format": "json",
        "messages": [
            {"role": "system", "content": system},
            message,
        ],
    }
    data = await _post(f"{base}/api/chat", headers={"Content-Type": "application/json"}, payload=payload)
    try:
        return data["message"]["content"]
    except (KeyError, TypeError) as exc:
        raise AIError("Ollama returned a response without text.") from exc
