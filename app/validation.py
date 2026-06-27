"""
Input validation helpers.

Each helper returns a (value, error) tuple: on success the parsed value
and None; on failure None and a ready-to-return (response, status) pair.
The route layer just checks `if error: return error`.
"""

from typing import Any, Optional
from collections.abc import Collection

from flask import Response, jsonify

MAX_INPUT_LENGTH = 10_000

# A Flask JSON response paired with its HTTP status code.
ErrorResponse = tuple[Response, int]


def validate_text_input(body: Any) -> tuple[Optional[str], Optional[ErrorResponse]]:
    if body is None:
        return None, (jsonify({"detail": "Request body must be valid JSON."}), 400)

    if "text" not in body:
        return None, (
            jsonify({"detail": "Request body must include a 'text' field."}),
            400,
        )

    text = body["text"]

    if not isinstance(text, str):
        return None, (jsonify({"detail": "'text' must be a string."}), 400)

    if len(text.strip()) == 0:
        return None, (jsonify({"detail": "'text' must not be empty."}), 400)

    if len(text) > MAX_INPUT_LENGTH:
        return None, (
            jsonify(
                {
                    "detail": f"'text' exceeds the maximum allowed length of {MAX_INPUT_LENGTH} characters."
                }
            ),
            413,
        )

    return text, None


def parse_requested_analyses(
    analyses_param: Optional[str], available_names: Collection[str]
) -> tuple[Optional[list[str]], Optional[ErrorResponse]]:
    if not analyses_param:
        return list(available_names), None

    requested = [name.strip() for name in analyses_param.split(",") if name.strip()]
    unknown = [name for name in requested if name not in available_names]

    if unknown:
        return None, (
            jsonify(
                {
                    "detail": {
                        "error": "Unknown analysis type(s) requested.",
                        "unknown": unknown,
                        "available": list(available_names),
                    }
                }
            ),
            400,
        )
    return requested, None
