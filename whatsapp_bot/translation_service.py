from functools import lru_cache
from sarvamai import SarvamAI
from config import SARVAM_API_KEY

SUPPORTED_TARGET_LANGUAGES = {"te-IN", "hi-IN"}


@lru_cache(maxsize=1)
def _get_client():
    if not SARVAM_API_KEY:
        raise RuntimeError("SARVAM_API_KEY is not configured")

    return SarvamAI(api_subscription_key=SARVAM_API_KEY)


def _extract_translated_text(response):
    if response is None:
        return None

    if isinstance(response, dict):
        return response.get("translated_text")

    translated = getattr(response, "translated_text", None)
    if translated:
        return translated

    model_dump = getattr(response, "model_dump", None)
    if callable(model_dump):
        data = model_dump()
        if isinstance(data, dict):
            return data.get("translated_text")

    dict_method = getattr(response, "dict", None)
    if callable(dict_method):
        data = dict_method()
        if isinstance(data, dict):
            return data.get("translated_text")

    return None


def translate_text(text: str, target_language_code: str = "te-IN") -> str:
    if not text:
        return text

    if target_language_code not in SUPPORTED_TARGET_LANGUAGES:
        raise ValueError(
            f"Unsupported target language: {target_language_code}. "
            f"Supported: {', '.join(sorted(SUPPORTED_TARGET_LANGUAGES))}"
        )

    response = _get_client().text.translate(
        input=text,
        source_language_code="auto",
        target_language_code=target_language_code
    )

    translated_text = _extract_translated_text(response)
    if not translated_text:
        raise RuntimeError("Sarvam translation failed: missing translated_text")

    return translated_text


def translate_to_telugu(text: str) -> str:
    return translate_text(text, target_language_code="te-IN")


def translate_to_hindi(text: str) -> str:
    return translate_text(text, target_language_code="hi-IN")
