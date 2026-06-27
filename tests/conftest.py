import pytest
from unittest.mock import Mock

from app.analyzer_interface import TextAnalyzerInterface
from app.main import create_app


@pytest.fixture
def app():
    application = create_app()
    application.config["TESTING"] = True
    return application


@pytest.fixture
def client(app):
    with app.test_client() as c:
        yield c


@pytest.fixture
def mock_analyzer():
    """A Mock that satisfies the TextAnalyzerInterface contract with sensible defaults."""
    mock = Mock(spec=TextAnalyzerInterface)
    mock.word_count.return_value = 99
    mock.character_count.return_value = 100
    mock.character_count_no_spaces.return_value = 90
    mock.sentence_count.return_value = 5
    mock.average_word_length.return_value = 4.5
    mock.most_common_words.return_value = {"test": 3}
    mock.vowel_count.return_value = 7
    return mock


@pytest.fixture
def client_with_mock(mock_analyzer):
    """Flask test client wired to a mock analyzer via dependency injection."""
    application = create_app(analyzer=mock_analyzer)
    application.config["TESTING"] = True
    with application.test_client() as c:
        yield c, mock_analyzer
