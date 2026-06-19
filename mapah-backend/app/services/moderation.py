"""
AI-powered submission moderation via Anthropic Claude.

Spec §5.5.11 – single classification call, structured JSON output,
no LangChain/agent orchestration.
"""
import json
import logging
import re

from flask import current_app

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "claude-sonnet-4-5"
_DEFAULT_MAX_TOKENS = 200
_MODERATION_VERSION = "2026-06-18-gibberish-v2"
_DEFAULT_FALLBACK_MODELS = (
    "claude-sonnet-4-5",
    "claude-3-7-sonnet-latest",
    "claude-3-5-haiku-20241022",
)
_SYSTEM_PROMPT = """You moderate user submissions for a kosher place directory.

Return JSON only.

Approve legitimate submissions for real places.
Flag suspicious submissions that look like spam, abuse, scams, unrelated ads, profanity,
nonsense, fake place names, invented addresses, or manipulative keyword stuffing.

For new places, be especially cautious about:
- promotional copy, coupon language, or marketing slogans
- URLs, phone numbers, social handles, or contact-spam in names/reasons/aliases
- random characters, repeated words, gibberish, or clearly fake restaurant names
- unrelated content (crypto, betting, adult content, pharmaceuticals, SEO spam)

If unsure, flag for manual review instead of approving.
"""

# Tags that cannot logically coexist on the same place
_MUTUALLY_EXCLUSIVE = [{"meat", "dairy"}]


def _normalize_text(value: str | None) -> str:
    return " ".join((value or "").strip().lower().split())


def _is_obvious_spam_text(value: str | None) -> bool:
    normalized = _normalize_text(value)
    if not normalized:
        return False

    if normalized in {
        "blah",
        "blah blah",
        "blah blah blah",
        "asdf",
        "qwerty",
        "test test",
        "this is dumb",
    }:
        return True

    if "http://" in normalized or "https://" in normalized or "www." in normalized:
        return True

    words = normalized.split(" ")
    if len(words) >= 3 and len(set(words)) == 1:
        return True

    if re.search(r"(.)\1{6,}", normalized):
        return True

    return False


def _obvious_spam_reason(payload: dict) -> str | None:
    fields_to_check = [payload.get("place_name"), payload.get("reason")]
    fields_to_check.extend(payload.get("aliases", []))

    if payload.get("submission_type") == "hechsher_create":
        hechsher_data = payload.get("hechsher") or {}
        fields_to_check.append(hechsher_data.get("hechsher_display_name"))
        fields_to_check.extend(hechsher_data.get("aliases", []))

    for value in fields_to_check:
        if isinstance(value, str) and _is_obvious_spam_text(value):
            return "Obvious spam/gibberish detected in submission text"

    return None


def _is_model_not_found_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return "not_found_error" in text and "model" in text


def _candidate_models() -> list[str]:
    primary_model = current_app.config.get("ANTHROPIC_MODERATION_MODEL", _DEFAULT_MODEL)
    configured_fallbacks = str(
        current_app.config.get("ANTHROPIC_MODERATION_FALLBACK_MODELS", "")
    )
    fallback_models = [m.strip() for m in configured_fallbacks.split(",") if m.strip()]
    if not fallback_models:
        fallback_models = list(_DEFAULT_FALLBACK_MODELS)

    ordered: list[str] = [primary_model, *fallback_models]
    deduped: list[str] = []
    for model_name in ordered:
        if model_name not in deduped:
            deduped.append(model_name)
    return deduped


def are_tags_inconsistent(existing_tags: list[str], proposed_tags: list[str]) -> bool:
    """Return True if proposed tags conflict with existing tags."""
    combined = set(existing_tags) | set(proposed_tags)
    for exclusive_set in _MUTUALLY_EXCLUSIVE:
        if exclusive_set.issubset(combined):
            return True
    return False


def are_aliases_inconsistent(existing_aliases: list[str], proposed_aliases: list[str]) -> bool:
    """Return True when proposed aliases are suspiciously unrelated to known aliases."""
    existing_norm = {a.strip().lower() for a in existing_aliases if a and a.strip()}
    proposed_norm = {a.strip().lower() for a in proposed_aliases if a and a.strip()}
    if not proposed_norm:
        return True
    if not existing_norm:
        return False
    # If there is zero overlap and no proposal contains the current place name/aliases,
    # treat as inconsistent and require manual review.
    return existing_norm.isdisjoint(proposed_norm)


def _build_anthropic_client(api_key: str):
    import anthropic

    return anthropic.Anthropic(api_key=api_key)


def _extract_message_text(message) -> str:
    text_parts: list[str] = []
    for block in getattr(message, "content", []) or []:
        if isinstance(block, dict):
            if block.get("type") == "text" and block.get("text"):
                text_parts.append(block["text"])
            continue
        if getattr(block, "type", None) == "text" and getattr(block, "text", None):
            text_parts.append(block.text)

    if not text_parts:
        raise ValueError("Anthropic moderation response did not include text content")

    return "\n".join(text_parts).strip()


def _extract_json_object(raw_text: str) -> dict:
    try:
        result = json.loads(raw_text)
    except json.JSONDecodeError:
        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        result = json.loads(raw_text[start : end + 1])

    if not isinstance(result, dict):
        raise ValueError("Moderation response must be a JSON object")
    return result


def _normalize_moderation_result(result: dict) -> dict:
    normalized_result = str(result.get("result", "")).strip().lower()
    if normalized_result not in {"approved", "flagged"}:
        raise ValueError("Unexpected moderation result value")

    normalized = {"result": normalized_result}
    if normalized_result == "flagged":
        reason = str(result.get("reason") or "Suspicious submission").strip()
        normalized["reason"] = reason[:500]
    return normalized


def _build_moderation_payload(payload: dict, existing_tags: list[str] | None = None) -> str:
    moderation_payload = {
        "submission_type": payload.get("submission_type"),
        "place_id": payload.get("place_id"),
        "place_name": payload.get("place_name"),
        "street_address": payload.get("street_address"),
        "latitude": payload.get("latitude"),
        "longitude": payload.get("longitude"),
        "hechsher_ids": payload.get("hechsher_ids", []),
        "tags": payload.get("tags", []),
        "aliases": payload.get("aliases", []),
        "reason": payload.get("reason", ""),
        "source": payload.get("source", "manual"),
        "hechsher": payload.get("hechsher"),
        "original": payload.get("original"),
        "existing_tags": existing_tags or [],
    }
    return json.dumps(moderation_payload, ensure_ascii=False, sort_keys=True)


def classify_submission(payload: dict, existing_tags: list[str] | None = None) -> dict:
    """
    Call Anthropic Claude to classify a submission.

    Returns:
        {"result": "approved"} | {"result": "flagged", "reason": str}

    Falls back to {"result": "approved"} only in testing mode (or when explicitly
    configured) if the API key is not configured.
    """
    obvious_spam = _obvious_spam_reason(payload)
    if obvious_spam:
        return {
            "result": "flagged",
            "reason": obvious_spam,
            "source": "heuristic",
            "moderation_version": _MODERATION_VERSION,
        }

    api_key = current_app.config.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        if current_app.testing or current_app.config.get("ANTHROPIC_AUTO_APPROVE_WITHOUT_KEY", False):
            logger.warning(
                "ANTHROPIC_API_KEY not set in testing/auto-approve mode – moderation is bypassed."
            )
            return {
                "result": "approved",
                "source": "bypass_no_key",
                "moderation_version": _MODERATION_VERSION,
            }
        logger.error("ANTHROPIC_API_KEY not set – defaulting to flagged for safety.")
        return {
            "result": "flagged",
            "reason": "Moderation service not configured",
            "source": "config_missing",
            "moderation_version": _MODERATION_VERSION,
        }

    # Deterministic pre-check: tag inconsistency
    if (
        existing_tags is not None
        and payload.get("submission_type") == "tag_update"
        and are_tags_inconsistent(existing_tags, payload.get("tags", []))
    ):
        return {
            "result": "flagged",
            "reason": "Proposed tags are inconsistent with existing tags",
            "source": "heuristic",
            "moderation_version": _MODERATION_VERSION,
        }

    client = _build_anthropic_client(api_key=api_key)
    for model_name in _candidate_models():
        try:
            message = client.messages.create(
                model=model_name,
                max_tokens=int(
                    current_app.config.get("ANTHROPIC_MODERATION_MAX_TOKENS", _DEFAULT_MAX_TOKENS)
                ),
                temperature=0,
                system=_SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "Moderate the following submission.\n"
                                    "Return strict JSON only in this shape: "
                                    '{"result":"approved"} or '
                                    '{"result":"flagged","reason":"brief reason"}.\n\n'
                                    f"Submission:\n{_build_moderation_payload(payload, existing_tags=existing_tags)}"
                                ),
                            }
                        ],
                    }
                ],
            )
            raw_text = _extract_message_text(message)
            result = _extract_json_object(raw_text)
            normalized_result = _normalize_moderation_result(result)
            normalized_result["source"] = "anthropic"
            normalized_result["moderation_version"] = _MODERATION_VERSION
            normalized_result["model"] = model_name
            return normalized_result
        except Exception as exc:
            if _is_model_not_found_error(exc):
                logger.warning(
                    "Moderation model not found (%s), trying next fallback model", model_name
                )
                continue
            logger.error(
                "Moderation call failed for submission_type=%s using model=%s: %s – defaulting to flagged",
                payload.get("submission_type"),
                model_name,
                exc,
            )
            return {
                "result": "flagged",
                "reason": "Moderation service error",
                "source": "service_error",
                "moderation_version": _MODERATION_VERSION,
            }

    logger.error("All configured moderation models are unavailable")
    return {
        "result": "flagged",
        "reason": "Moderation model unavailable",
        "source": "model_unavailable",
        "moderation_version": _MODERATION_VERSION,
    }

