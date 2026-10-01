import re
from typing import List, Tuple


class Summarizer:
    """
    Summarizes news articles into 2-4 concise sentences and key bullet points.
    """

    @staticmethod
    def extract_summary_and_bullets(text: str, max_sentences: int = 3) -> Tuple[str, List[str]]:
        # Split into sentences
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 10]

        if not sentences:
            return text[:150], []

        summary_sentences = sentences[:max_sentences]
        summary = " ".join(summary_sentences)

        # Extract remaining sentences as bullet points if informative
        bullets = []
        for s in sentences[max_sentences:max_sentences + 3]:
            cleaned_bullet = re.sub(r"^[•\-\*]\s*", "", s).strip()
            if cleaned_bullet and len(cleaned_bullet) < 120:
                bullets.append(cleaned_bullet)

        return summary, bullets
