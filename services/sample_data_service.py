import pandas as pd

from services.data_loader import DataLoader


class SampleDataService(DataLoader):
    """Backward-compatible wrapper around DataLoader for existing app services."""

    def load_faq_knowledge_base(self) -> pd.DataFrame:
        faq_items = self.load_faq_items()
        if not faq_items:
            return pd.DataFrame(columns=["question", "intent", "answer", "tags"])
        return pd.DataFrame(
            [
                {
                    "question": item.question,
                    "intent": item.intent,
                    "answer": item.answer,
                    "tags": item.tags,
                }
                for item in faq_items
            ]
        )
