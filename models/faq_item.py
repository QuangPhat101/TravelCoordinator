from dataclasses import dataclass


@dataclass(slots=True)
class FaqItem:
    question: str
    intent: str
    answer: str
    tags: str = ""
