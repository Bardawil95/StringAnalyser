"""
Unit tests for TextAnalyzer.

These tests call the analyzer methods directly — no HTTP layer, no Flask.
Each public method gets its own class so failures are easy to locate.
"""

import pytest
from app.analyzers import TextAnalyzer


@pytest.fixture
def analyzer():
    return TextAnalyzer(default_top_n=5)


# ---------------------------------------------------------------------------
# word_count
# ---------------------------------------------------------------------------


class TestWordCount:
    def test_two_words(self, analyzer):
        assert analyzer.word_count("hello world") == 2

    def test_single_word(self, analyzer):
        assert analyzer.word_count("hello") == 1

    def test_empty_string(self, analyzer):
        assert analyzer.word_count("") == 0

    def test_multiple_spaces_collapsed(self, analyzer):
        # str.split() without an argument treats any run of whitespace as one delimiter
        assert analyzer.word_count("  hello   world  ") == 2

    def test_sentence_with_punctuation(self, analyzer):
        assert analyzer.word_count("Hello, world!") == 2


# ---------------------------------------------------------------------------
# character_count
# ---------------------------------------------------------------------------


class TestCharacterCount:
    def test_simple_word(self, analyzer):
        assert analyzer.character_count("hello") == 5

    def test_includes_spaces(self, analyzer):
        assert analyzer.character_count("hello world") == 11

    def test_empty_string(self, analyzer):
        assert analyzer.character_count("") == 0

    def test_only_spaces(self, analyzer):
        assert analyzer.character_count("   ") == 3

    def test_includes_punctuation(self, analyzer):
        assert analyzer.character_count("Hi!") == 3


# ---------------------------------------------------------------------------
# character_count_no_spaces
# ---------------------------------------------------------------------------


class TestCharacterCountNoSpaces:
    def test_removes_spaces(self, analyzer):
        assert analyzer.character_count_no_spaces("hello world") == 10

    def test_no_spaces_unchanged(self, analyzer):
        assert analyzer.character_count_no_spaces("hello") == 5

    def test_empty_string(self, analyzer):
        assert analyzer.character_count_no_spaces("") == 0

    def test_all_spaces_returns_zero(self, analyzer):
        assert analyzer.character_count_no_spaces("   ") == 0

    def test_multiple_spaces_between_words(self, analyzer):
        assert analyzer.character_count_no_spaces("a  b  c") == 3


# ---------------------------------------------------------------------------
# sentence_count
# ---------------------------------------------------------------------------


class TestSentenceCount:
    def test_single_sentence_no_punctuation(self, analyzer):
        assert analyzer.sentence_count("Hello world") == 1

    def test_period_terminated(self, analyzer):
        assert analyzer.sentence_count("Hello. World. Again.") == 3

    def test_exclamation_marks(self, analyzer):
        assert analyzer.sentence_count("Hello! World!") == 2

    def test_question_marks(self, analyzer):
        assert analyzer.sentence_count("How are you? I am fine.") == 2

    def test_mixed_punctuation(self, analyzer):
        assert analyzer.sentence_count("Hello! How are you? I am fine.") == 3

    def test_consecutive_punctuation_counts_as_one_break(self, analyzer):
        # "..." is treated as a single separator by the [.!?]+ pattern
        assert analyzer.sentence_count("Wait... what?") == 2

    def test_empty_string(self, analyzer):
        assert analyzer.sentence_count("") == 0

    def test_only_punctuation(self, analyzer):
        # "..." splits into ["", ""], all empty after strip → 0 sentences
        assert analyzer.sentence_count("...") == 0


# ---------------------------------------------------------------------------
# average_word_length
# ---------------------------------------------------------------------------


class TestAverageWordLength:
    def test_empty_string(self, analyzer):
        assert analyzer.average_word_length("") == 0.0

    def test_single_word(self, analyzer):
        assert analyzer.average_word_length("hello") == 5.0

    def test_two_equal_length_words(self, analyzer):
        assert analyzer.average_word_length("hi yo") == 2.0

    def test_strips_trailing_punctuation(self, analyzer):
        # "Hello!" → strip → "Hello" (5 chars)
        assert analyzer.average_word_length("Hello!") == 5.0

    def test_strips_surrounding_quotes(self, analyzer):
        # '"word"' → strip → "word" (4 chars)
        assert analyzer.average_word_length('"word"') == 4.0

    def test_result_rounded_to_two_decimal_places(self, analyzer):
        # "a"(1) + "bb"(2) + "cccc"(4) = 7 / 3 = 2.333... must round to 2.33
        assert analyzer.average_word_length("a bb cccc") == 2.33

    def test_mixed_word_lengths(self, analyzer):
        # "a"(1) + "bb"(2) + "ccc"(3) = 6 / 3 = 2.0
        assert analyzer.average_word_length("a bb ccc") == 2.0


# ---------------------------------------------------------------------------
# most_common_words
# ---------------------------------------------------------------------------


class TestMostCommonWords:
    def test_returns_top_n_words_by_default(self, analyzer):
        # 6 unique words; default top_n=5 so only 5 returned
        result = analyzer.most_common_words("a b c d e f")
        assert len(result) == 5

    def test_custom_top_n(self, analyzer):
        result = analyzer.most_common_words("a b c d e f", top_n=3)
        assert len(result) == 3

    def test_case_insensitive(self, analyzer):
        result = analyzer.most_common_words("Hello hello HELLO")
        assert result["hello"] == 3

    def test_correct_frequency_counts(self, analyzer):
        result = analyzer.most_common_words("the cat sat on the mat the cat ran")
        assert result["the"] == 3
        assert result["cat"] == 2

    def test_fewer_words_than_top_n(self, analyzer):
        result = analyzer.most_common_words("one two", top_n=10)
        assert len(result) == 2

    def test_numbers_excluded_from_results(self, analyzer):
        result = analyzer.most_common_words("hello 123 hello")
        assert "123" not in result
        assert result["hello"] == 2

    def test_contractions_treated_as_single_word(self, analyzer):
        result = analyzer.most_common_words("don't stop don't")
        assert result["don't"] == 2

    def test_custom_default_top_n_on_instance(self):
        custom = TextAnalyzer(default_top_n=2)
        result = custom.most_common_words("a b c d e f")
        assert len(result) == 2

    def test_explicit_top_n_overrides_instance_default(self):
        custom = TextAnalyzer(default_top_n=2)
        result = custom.most_common_words("a b c d e f", top_n=4)
        assert len(result) == 4


# ---------------------------------------------------------------------------
# vowel_count
# ---------------------------------------------------------------------------


class TestVowelCount:
    def test_simple_word(self, analyzer):
        # h-e-l-l-o → e, o = 2
        assert analyzer.vowel_count("hello") == 2

    def test_empty_string(self, analyzer):
        assert analyzer.vowel_count("") == 0

    def test_no_vowels(self, analyzer):
        assert analyzer.vowel_count("crwth") == 0

    def test_all_five_vowels(self, analyzer):
        assert analyzer.vowel_count("aeiou") == 5

    def test_case_insensitive(self, analyzer):
        assert analyzer.vowel_count("AEIOU") == 5

    def test_y_is_not_counted_as_vowel(self, analyzer):
        assert analyzer.vowel_count("gym") == 0

    def test_mixed_sentence(self, analyzer):
        # H-e-l-l-o(e,o) W-o-r-l-d(o) → 3
        assert analyzer.vowel_count("Hello World") == 3

    def test_repeated_vowels(self, analyzer):
        assert analyzer.vowel_count("aaa") == 3
