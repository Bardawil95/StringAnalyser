"""
String Analysis API - Flask application factory.

create_app() builds and returns the app. An analyzer can be injected
(e.g. a mock in tests); otherwise a default TextAnalyzer is created.
"""

import os
import logging
from typing import Optional
from collections.abc import Callable

from flask import Flask, Response, request, jsonify
from flask.typing import ResponseReturnValue
from werkzeug.exceptions import HTTPException

from app.analyzer_interface import TextAnalyzerInterface
from app.analyzers import TextAnalyzer
from app.validation import (
    validate_text_input,
    parse_requested_analyses,
    MAX_INPUT_LENGTH,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app(analyzer: Optional[TextAnalyzerInterface] = None) -> Flask:
    app = Flask(__name__)

    # Reject oversized bodies at the framework level, before Flask buffers
    # and parses them into memory (resource-exhaustion control).
    app.config["MAX_CONTENT_LENGTH"] = 64 * 1024

    if analyzer is None:
        analyzer = TextAnalyzer(default_top_n=5)

    analyzers: dict[str, Callable[..., object]] = {
        "word_count": analyzer.word_count,
        "character_count": analyzer.character_count,
        "character_count_no_spaces": analyzer.character_count_no_spaces,
        "sentence_count": analyzer.sentence_count,
        "average_word_length": analyzer.average_word_length,
        "most_common_words": analyzer.most_common_words,
        "vowel_count": analyzer.vowel_count,
    }

    @app.route("/analyze", methods=["POST"])
    def analyze_text() -> ResponseReturnValue:
        body = request.get_json(silent=True)
        text, error = validate_text_input(body)
        if error is not None:
            return error

        requested, error = parse_requested_analyses(
            request.args.get("analyses"), analyzers.keys()
        )
        if error is not None:
            return error

        # Both helpers guarantee a non-None value when error is None, but the
        # (value, error) tuple pattern doesn't let the type checker correlate
        # the two, so we assert the invariant explicitly.
        assert requested is not None

        results: dict[str, object] = {}
        for name in requested:
            try:
                results[name] = analyzers[name](text)
            except Exception:
                # One analyzer failing must not take down the whole request.
                logger.exception("Analysis '%s' failed", name)
                results[name] = None

        return jsonify({"results": results})

    @app.route("/analyses", methods=["GET"])
    def list_available_analyses() -> Response:
        return jsonify(
            {
                "available_analyses": list(analyzers.keys()),
                "max_input_length": MAX_INPUT_LENGTH,
            }
        )

    @app.route("/health", methods=["GET"])
    def health_check() -> Response:
        return jsonify({"status": "ok"})

    @app.errorhandler(HTTPException)
    def handle_http_exception(exc: HTTPException):
        # Preserve Flask's own 404/405/413 etc. as JSON instead of letting the
        # catch-all below mask them as 500.
        return jsonify({"error": exc.name, "detail": exc.description}), exc.code or 500

    @app.errorhandler(Exception)
    def handle_unexpected_error(exc: Exception):
        logger.exception("Unhandled exception")
        return jsonify({"error": "Internal server error."}), 500

    return app


if __name__ == "__main__":
    # Local dev only; the container serves the app via gunicorn. debug is OFF
    # unless FLASK_DEBUG=1, so the Werkzeug debugger can never ship on.
    debug = os.environ.get("FLASK_DEBUG") == "1"
    create_app().run(host="0.0.0.0", port=8000, debug=debug)
