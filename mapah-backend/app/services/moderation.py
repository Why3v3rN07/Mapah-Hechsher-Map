"""
AI-powered submission moderation via Anthropic Claude.

Spec §5.5.11 – single classification call, structured JSON output,
no LangChain/agent orchestration.
"""
import json
import logging

from flask import current_app

logger = logging.getLogger(__name__)

# Tags that cannot logically coexist on the same place
_MUTUALLY_EXCLUSIVE = [{"meat", "dairy"}]


def are_tags_inconsistent(existing_tags: list[str], proposed_tags: list[str]) -> bool:
    """Return True if proposed tags conflict with existing tags."""
    combined = set(existing_tags) | set(proposed_tags)
    for exclusive_set in _MUTUALLY_EXCLUSIVE:
        if exclusive_set.issubset(combined):
            return True
    return False


def classify_submission(payload: dict, existing_tags: list[str] | None = None) -> dict:
    """
    Call Anthropic Claude to classify a submission.

    Returns:
        {"result": "approved"} | {"result": "flagged", "reason": str}

    Falls back to {"result": "approved"} if the API key is not configured
    (so dev/test environments work without a key).
    """
    api_key = current_app.config.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set – skipping AI moderation, auto-approving.")
        return {"result": "approved"}

    # Deterministic pre-check: tag inconsistency
    if (
        existing_tags is not None
        and payload.get("submission_type") == "tag_update"
        and are_tags_inconsistent(existing_tags, payload.get("tags", []))
    ):
        return {"result": "flagged", "reason": "Proposed tags are inconsistent with existing tags"}

    try:
        import anthropic  # lazy import so the package is optional in dev

        client = anthropic.Anthropic(api_key=api_key)
        prompt = (
            "You are a moderation assistant for a kosher restaurant directory.\n"
            "Classify this submission as legitimate or spam/inappropriate.\n\n"
            f"Submission type: {payload.get('submission_type')}\n"
            f"Data: {json.dumps(payload, ensure_ascii=False)}\n"
        )
        if existing_tags:
            prompt += f"Existing place tags: {existing_tags}\n"
        prompt += (
            "\nRules:\n"
            "- Flag if: fake/offensive place name, invalid address, obvious spam.\n"
            "- Flag if: tag_update proposes tags inconsistent with existing tags.\n"
            "- Approve if: looks like a legitimate kosher establishment.\n\n"
            'Respond with valid JSON only: {"result":"approved"} '
            'or {"result":"flagged","reason":"brief reason"}'
        )

        message = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=128,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        result = json.loads(raw)
        if result.get("result") not in ("approved", "flagged"):
            raise ValueError("Unexpected result value")
        return result

    except Exception as exc:
        logger.error("Moderation call failed: %s – defaulting to flagged", exc)
        return {"result": "flagged", "reason": "Moderation service error"}

