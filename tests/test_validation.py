"""
Unit tests for validation helper functions.

Both helpers call jsonify() on the error path, so tests that exercise
error cases run inside a Flask application context. Success-path tests
that never reach jsonify work without one.
"""

import pytest
from app.validation import (
    validate_text_input,
    parse_requested_analyses,
    MAX_INPUT_LENGTH,
)
from app.main import create_app


@pytest.fixture
def flask_app():
    application = create_app()
    application.config["TESTING"] = True
    return application


# ---------------------------------------------------------------------------
# validate_text_input
# ---------------------------------------------------------------------------


class TestValidateTextInput:
    def test_valid_text_returns_text_and_no_error(self, flask_app):
        with flask_app.app_context():
            text, error = validate_text_input({"text": "hello world"})
        assert text == "hello world"
        assert error is None

    def test_none_body_returns_400(self, flask_app):
        with flask_app.app_context():
            text, error = validate_text_input(None)
        assert text is None
        _, status_code = error
        assert status_code == 400

    def test_none_body_error_mentions_json(self, flask_app):
        with flask_app.app_context():
            _, error = validate_text_input(None)
        response, _ = error
        assert "JSON" in response.get_json()["detail"]

    def test_missing_text_field_returns_400(self, flask_app):
        with flask_app.app_context():
            text, error = validate_text_input({"other": "value"})
        assert text is None
        _, status_code = error
        assert status_code == 400

    def test_missing_text_field_error_mentions_text(self, flask_app):
        with flask_app.app_context():
            _, error = validate_text_input({"other": "value"})
        response, _ = error
        assert "text" in response.get_json()["detail"]

    @pytest.mark.parametrize(
        "bad_value",
        [
            pytest.param(42, id="integer"),
            pytest.param(["hello"], id="list"),
            pytest.param(True, id="bool"),
            pytest.param("", id="empty_string"),
            pytest.param("   ", id="whitespace_only"),
        ],
    )
    def test_invalid_text_values_return_400(self, flask_app, bad_value):
        # One parametrized test replaces five near-identical cases; the id=
        # labels keep failures self-explaining in the pytest output.
        with flask_app.app_context():
            text, error = validate_text_input({"text": bad_value})
        assert text is None
        _, status_code = error
        assert status_code == 400

    def test_text_at_max_length_is_accepted(self, flask_app):
        with flask_app.app_context():
            text, error = validate_text_input({"text": "a" * MAX_INPUT_LENGTH})
        assert text is not None
        assert error is None

    def test_text_one_over_max_length_returns_413(self, flask_app):
        with flask_app.app_context():
            text, error = validate_text_input({"text": "a" * (MAX_INPUT_LENGTH + 1)})
        assert text is None
        _, status_code = error
        assert status_code == 413

    def test_valid_text_preserved_exactly(self, flask_app):
        # validate_text_input must not strip or transform the text value
        original = "  leading and trailing spaces  "
        with flask_app.app_context():
            text, error = validate_text_input({"text": original})
        assert text == original
        assert error is None


# ---------------------------------------------------------------------------
# parse_requested_analyses
# ---------------------------------------------------------------------------

AVAILABLE = frozenset({"word_count", "character_count", "vowel_count"})


class TestParseRequestedAnalyses:
    def test_none_param_returns_all_available(self, flask_app):
        with flask_app.app_context():
            result, error = parse_requested_analyses(None, AVAILABLE)
        assert error is None
        assert set(result) == AVAILABLE

    def test_empty_string_returns_all_available(self, flask_app):
        with flask_app.app_context():
            result, error = parse_requested_analyses("", AVAILABLE)
        assert error is None
        assert set(result) == AVAILABLE

    def test_single_valid_analysis(self, flask_app):
        with flask_app.app_context():
            result, error = parse_requested_analyses("word_count", AVAILABLE)
        assert error is None
        assert result == ["word_count"]

    def test_multiple_valid_analyses(self, flask_app):
        with flask_app.app_context():
            result, error = parse_requested_analyses(
                "word_count,vowel_count", AVAILABLE
            )
        assert error is None
        assert set(result) == {"word_count", "vowel_count"}

    def test_spaces_around_commas_are_stripped(self, flask_app):
        with flask_app.app_context():
            result, error = parse_requested_analyses(
                "word_count , vowel_count", AVAILABLE
            )
        assert error is None
        assert set(result) == {"word_count", "vowel_count"}

    def test_unknown_analysis_returns_400(self, flask_app):
        with flask_app.app_context():
            result, error = parse_requested_analyses("not_real", AVAILABLE)
        assert result is None
        _, status_code = error
        assert status_code == 400

    def test_mixed_valid_and_unknown_returns_400(self, flask_app):
        with flask_app.app_context():
            result, error = parse_requested_analyses("word_count,not_real", AVAILABLE)
        assert result is None
        _, status_code = error
        assert status_code == 400

    def test_unknown_names_listed_in_error_detail(self, flask_app):
        with flask_app.app_context():
            _, error = parse_requested_analyses("not_real,also_fake", AVAILABLE)
        response, _ = error
        detail = response.get_json()["detail"]
        assert "not_real" in detail["unknown"]
        assert "also_fake" in detail["unknown"]

    def test_available_analyses_listed_in_error_detail(self, flask_app):
        with flask_app.app_context():
            _, error = parse_requested_analyses("not_real", AVAILABLE)
        response, _ = error
        detail = response.get_json()["detail"]
        assert set(detail["available"]) == AVAILABLE
