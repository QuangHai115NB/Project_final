# src/services/text_preprocess.py

import re
from typing import List


def clean_text(text: str) -> str:
    if not text:
        return ""

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_for_matching(text: str) -> str:
    text = clean_text(text).lower()

    replacements = {
        "node js": "node.js",
        "nodejs": "node.js",
        "react js": "react",
        "reactjs": "react",
        "next js": "next.js",
        "nextjs": "next.js",
        "c sharp": "c#",
        "csharp": "c#",
        "postgre sql": "postgresql",
        "mongo db": "mongodb",
        "restful api": "rest api",
        "restful services": "rest api",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = text.replace("•", "\n- ").replace("●", "\n- ").replace("▪", "\n- ")
    text = re.sub(r"[^\w\s\+\#\.\-/]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def split_lines(text: str) -> List[str]:
    cleaned = clean_text(text)
    lines = []
    for line in cleaned.split("\n"):
        value = line.strip(" \t-•●▪*")
        if value:
            lines.append(value)
    return lines