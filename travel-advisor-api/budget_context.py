"""Signed client-carried budget provenance; no process-local session storage."""
import base64
import hashlib
import hmac
import json
import re
import time
from schemas import BudgetValues


def encode_context(values, response_id, secret, duration_days=None):
    payload = json.dumps({"values": values, "response_id": response_id,
        "duration_days": duration_days, "expires": int(time.time()) + 86400}, sort_keys=True, separators=(",", ":")).encode()
    encoded = base64.urlsafe_b64encode(payload).decode().rstrip("=")
    signature = hmac.new(secret.encode(), encoded.encode(), hashlib.sha256).hexdigest()
    return encoded + "." + signature


def decode_context(token, response_id, secret):
    if not token:
        return {"values": {}, "duration_days": None}
    try:
        encoded, signature = token.split(".")
        expected = hmac.new(secret.encode(), encoded.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError()
        data = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
        if data["response_id"] != response_id or data["expires"] < time.time():
            raise ValueError()
        return {"values": BudgetValues.model_validate(data["values"]).model_dump(exclude_none=True),
            "duration_days": data.get("duration_days")}
    except (ValueError, TypeError, KeyError):
        raise ValueError("Invalid or expired budget context. Please start a new trip.") from None


def extract_budget_values(message):
    """Conservative labelled whole-trip EUR syntax, never model-extracted authority.

    Conflicting repeats are rejected (including copied prompt-injection examples).
    Ambiguous natural-language/daily costs should be entered in the explicit form.
    """
    pattern = r"\b(accommodation|food|transportation|activities|extras|flights)\s*[:=]\s*(?:EUR\s*|€\s*)?(-?\d+(?:\.\d+)?)\b"
    values = {}
    for match in re.finditer(pattern, message, re.IGNORECASE):
        key, raw = match.groups()
        suffix = message[match.end():match.end() + 22]
        if re.match(r"\s*(?:USD|GBP|JPY|dollars|pounds|/\s*(?:day|night)|per\s+(?:day|night))\b", suffix, re.I):
            raise ValueError("Please enter whole-trip amounts in EUR using the budget form.")
        key, value = key.lower(), float(raw)
        BudgetValues.model_validate({key: value})
        if key in values and values[key] != value:
            raise ValueError("Conflicting budget values. Please use the budget form to confirm costs.")
        values[key] = value
    return values
