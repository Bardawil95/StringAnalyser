"""
The contract every text analyzer implementation must satisfy.

Kept in its own file, separate from the implementation, so the
interface can be depended on independently - main.py or any future
code only needs to know about TextAnalyzerInterface, not about how
the methods are actually implemented.
"""

from abc import ABC, abstractmethod


class TextAnalyzerInterface(ABC):
    @abstractmethod
    def word_count(self, text: str) -> int: ...

    @abstractmethod
    def character_count(self, text: str) -> int: ...

    @abstractmethod
    def character_count_no_spaces(self, text: str) -> int: ...

    @abstractmethod
    def sentence_count(self, text: str) -> int: ...

    @abstractmethod
    def average_word_length(self, text: str) -> float: ...

    @abstractmethod
    def most_common_words(self, text: str, top_n: int | None = None) -> dict[str, int]:
        # top_n defaults to None so the implementation can fall back to its
        # own configured default (set in TextAnalyzer.__init__). The contract
        # and the implementation now agree on this default.
        ...

    @abstractmethod
    def vowel_count(self, text: str) -> int: ...
