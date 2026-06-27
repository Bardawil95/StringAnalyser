"""
Integration tests for the HTTP layer.

All tests go through the Flask test client so they exercise routing,
validation, error handling, and the full request/response cycle.
Dependency-injection tests verify that the API correctly delegates to
whatever analyzer is wired in at app-creation time.
"""

from app.analyzers import TextAnalyzer
from app.validation import MAX_INPUT_LENGTH
from app.main import create_app


# ---------------------------------------------------------------------------
# Endpoint: GET /health
# ---------------------------------------------------------------------------


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Endpoint: GET /analyses
# ---------------------------------------------------------------------------


def test_analyses_endpoint_documents_max_length(client):
    response = client.get("/analyses")
    body = response.get_json()
    assert body["max_input_length"] == MAX_INPUT_LENGTH
    assert "word_count" in body["available_analyses"]


def test_analyses_endpoint_lists_all_seven_analyses(client):
    response = client.get("/analyses")
    available = response.get_json()["available_analyses"]
    expected = {
        "word_count",
        "character_count",
        "character_count_no_spaces",
        "sentence_count",
        "average_word_length",
        "most_common_words",
        "vowel_count",
    }
    assert set(available) == expected


# ---------------------------------------------------------------------------
# Endpoint: POST /analyze — happy paths
# ---------------------------------------------------------------------------


def test_analyze_default_runs_all_analyses(client):
    response = client.post("/analyze", json={"text": "Hello world. Hello again!"})
    assert response.status_code == 200
    data = response.get_json()["results"]
    assert data["word_count"] == 4
    assert data["sentence_count"] == 2


def test_analyze_specific_analysis_only(client):
    response = client.post(
        "/analyze?analyses=word_count",
        json={"text": "one two three"},
    )
    assert response.status_code == 200
    assert response.get_json()["results"] == {"word_count": 3}


def test_analyze_multiple_specific_analyses(client):
    response = client.post(
        "/analyze?analyses=word_count,vowel_count",
        json={"text": "hello"},
    )
    assert response.status_code == 200
    results = response.get_json()["results"]
    assert set(results.keys()) == {"word_count", "vowel_count"}


def test_most_common_words(client):
    response = client.post(
        "/analyze?analyses=most_common_words",
        json={"text": "the cat sat on the mat the cat ran"},
    )
    data = response.get_json()["results"]["most_common_words"]
    assert data["the"] == 3
    assert data["cat"] == 2


# ---------------------------------------------------------------------------
# Endpoint: POST /analyze — validation errors
# ---------------------------------------------------------------------------


def test_analyze_missing_json_body_returns_400(client):
    response = client.post("/analyze", content_type="application/json", data="not-json")
    assert response.status_code == 400


def test_analyze_empty_text_rejected(client):
    response = client.post("/analyze", json={"text": ""})
    assert response.status_code == 400


def test_analyze_whitespace_only_text_rejected(client):
    response = client.post("/analyze", json={"text": "   "})
    assert response.status_code == 400


def test_analyze_non_string_text_rejected(client):
    response = client.post("/analyze", json={"text": 42})
    assert response.status_code == 400


def test_analyze_missing_text_field_rejected(client):
    response = client.post("/analyze", json={"other": "value"})
    assert response.status_code == 400


def test_analyze_text_too_long_rejected(client):
    response = client.post("/analyze", json={"text": "a" * (MAX_INPUT_LENGTH + 1)})
    assert response.status_code == 413


def test_analyze_unknown_analysis_returns_400(client):
    response = client.post(
        "/analyze?analyses=not_a_real_analysis",
        json={"text": "hello"},
    )
    assert response.status_code == 400
    assert "unknown" in response.get_json()["detail"]


# ---------------------------------------------------------------------------
# Regression tests for HTTP error handling
# ---------------------------------------------------------------------------


def test_wrong_method_returns_405_not_500(client):
    response = client.get("/analyze")
    assert response.status_code == 405


def test_unknown_route_returns_404_not_500(client):
    response = client.get("/does-not-exist")
    assert response.status_code == 404


def test_oversized_body_rejected_with_413(client):
    # Body > 64 KB triggers Flask's MAX_CONTENT_LENGTH before our field-level check.
    response = client.post("/analyze", json={"text": "x" * 100_000})
    assert response.status_code == 413


# ---------------------------------------------------------------------------
# Dependency injection tests
# ---------------------------------------------------------------------------


def test_injected_mock_analyzer_is_called_with_text(client_with_mock):
    client, mock = client_with_mock
    response = client.post("/analyze?analyses=word_count", json={"text": "hello world"})
    assert response.status_code == 200
    assert response.get_json()["results"]["word_count"] == 99
    mock.word_count.assert_called_once_with("hello world")


def test_all_methods_on_mock_called_when_no_filter(client_with_mock):
    client, mock = client_with_mock
    response = client.post("/analyze", json={"text": "some text"})
    assert response.status_code == 200
    mock.word_count.assert_called_once()
    mock.character_count.assert_called_once()
    mock.vowel_count.assert_called_once()


def test_analyzer_exception_returns_null_for_that_analysis(client_with_mock):
    client, mock = client_with_mock
    mock.word_count.side_effect = RuntimeError("analyzer broke")
    response = client.post("/analyze?analyses=word_count", json={"text": "hello"})
    assert response.status_code == 200
    assert response.get_json()["results"]["word_count"] is None


def test_analyzer_exception_does_not_affect_other_analyses(client_with_mock):
    client, mock = client_with_mock
    mock.word_count.side_effect = RuntimeError("analyzer broke")
    response = client.post(
        "/analyze?analyses=word_count,vowel_count",
        json={"text": "hello"},
    )
    results = response.get_json()["results"]
    assert results["word_count"] is None
    assert results["vowel_count"] == 7  # mock default


def test_custom_analyzer_configuration_is_respected():
    custom_analyzer = TextAnalyzer(default_top_n=2)
    application = create_app(analyzer=custom_analyzer)
    application.config["TESTING"] = True
    with application.test_client() as c:
        response = c.post(
            "/analyze?analyses=most_common_words",
            json={"text": "a b c d e f"},
        )
    data = response.get_json()["results"]["most_common_words"]
    assert len(data) == 2


# ---------------------------------------------------------------------------
# Additional coverage: content-type and empty analyses param
# ---------------------------------------------------------------------------


def test_valid_json_without_content_type_header_returns_400(client):
    # With no Content-Type: application/json header, Flask's get_json(silent=True)
    # returns None even though the body is valid JSON, so validation rejects it.
    response = client.post("/analyze", data='{"text": "hello"}')
    assert response.status_code == 400


def test_empty_analyses_param_runs_all_analyses(client):
    # `?analyses=` (present but empty) is treated the same as omitting it: run all.
    response = client.post("/analyze?analyses=", json={"text": "hello world"})
    assert response.status_code == 200
    results = response.get_json()["results"]
    assert len(results) == 7
