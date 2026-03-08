import re

def clean_text(text: str) -> str:
    if not text:
        return ""

    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove weird repeated spaces/tabs
    text = re.sub(r"[ \t]+", " ", text)

    # Collapse too many blank lines (>=3 -> 2)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()