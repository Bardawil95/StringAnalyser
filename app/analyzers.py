import re
from collections import Counter

from app.analyzer_interface import TextAnalyzerInterface


class TextAnalyzer(TextAnalyzerInterface):
    def __init__(self, default_top_n: int = 5):
        self.default_top_n = default_top_n

    def word_count(self, text: str) -> int:
        return len(text.split())

    def character_count(self, text: str) -> int:
        return len(text)

    def character_count_no_spaces(self, text: str) -> int:
        return len(text.replace(" ", ""))

    def sentence_count(self, text: str) -> int:
        sentences = re.split(r"[.!?]+", text)
        return len([s for s in sentences if s.strip()])

    def average_word_length(self, text: str) -> float:
        words = text.split()
        if not words:
            return 0.0
        total_letters = sum(len(w.strip(".,!?;:\"'")) for w in words)
        return round(total_letters / len(words), 2)

    def most_common_words(self, text: str, top_n: int | None = None) -> dict[str, int]:
        n = top_n if top_n is not None else self.default_top_n
        words = re.findall(r"[a-zA-Z']+", text.lower())
        counts = Counter(words)
        return dict(counts.most_common(n))

    def vowel_count(self, text: str) -> int:
        return sum(1 for ch in text.lower() if ch in "aeiou")
