# src/data/skills_taxonomy.py

from collections import defaultdict
import re
from typing import Dict, List

SKILL_TAXONOMY = {
    "programming_languages": {
        "python": ["python", "python3"],
        "java": ["java", "core java"],
        "javascript": ["javascript", "js"],
        "typescript": ["typescript", "ts"],
        "c#": ["c#", "c sharp", "csharp"],
        "c++": ["c++", "cpp"],
        "go": ["go", "golang"],
        "php": ["php"],
        "ruby": ["ruby"],
        "kotlin": ["kotlin"],
        "dart": ["dart"],
        "swift": ["swift"],
        "sql": ["sql"],
        "html": ["html"],
        "css": ["css"],
    },
    "frameworks_backend": {
        "spring boot": ["spring boot", "springboot"],
        "spring": ["spring framework", "spring"],
        "django": ["django"],
        "flask": ["flask"],
        "fastapi": ["fastapi", "fast api"],
        "node.js": ["node.js", "nodejs", "node js"],
        "express": ["express", "express.js", "expressjs"],
        "laravel": ["laravel"],
        ".net": [".net", "dotnet"],
        "asp.net": ["asp.net", "asp net"],
        "hibernate": ["hibernate"],
        "jpa": ["jpa"],
    },
    "frameworks_frontend": {
        "react": ["react", "react.js", "reactjs"],
        "next.js": ["next.js", "nextjs", "next js"],
        "angular": ["angular"],
        "vue": ["vue", "vue.js", "vuejs"],
    },
    "database": {
        "mysql": ["mysql"],
        "postgresql": ["postgresql", "postgres", "postgre sql"],
        "mongodb": ["mongodb", "mongo db"],
        "redis": ["redis"],
        "sqlite": ["sqlite"],
        "oracle": ["oracle"],
        "sql server": ["sql server", "mssql", "ms sql"],
        "firebase": ["firebase", "firestore"],
        "dynamodb": ["dynamodb"],
    },
    "cloud_devops": {
        "aws": ["aws", "amazon web services"],
        "azure": ["azure"],
        "gcp": ["gcp", "google cloud", "google cloud platform"],
        "docker": ["docker"],
        "kubernetes": ["kubernetes", "k8s"],
        "jenkins": ["jenkins"],
        "git": ["git"],
        "github actions": ["github actions"],
        "gitlab ci": ["gitlab ci", "gitlab-ci"],
        "terraform": ["terraform"],
        "linux": ["linux"],
        "kafka": ["kafka", "apache kafka"],
        "rabbitmq": ["rabbitmq"],
        "ci/cd": ["ci/cd", "cicd", "continuous integration", "continuous delivery"],
    },
    "testing_tools": {
        "pytest": ["pytest"],
        "junit": ["junit"],
        "selenium": ["selenium"],
        "postman": ["postman"],
        "swagger": ["swagger", "openapi"],
        "rest api": ["rest api", "restful api", "restful services"],
        "unit testing": ["unit testing", "unit test"],
        "integration testing": ["integration testing", "integration test"],
    },
    "data_ai": {
        "pandas": ["pandas"],
        "numpy": ["numpy"],
        "scikit-learn": ["scikit-learn", "sklearn"],
        "tensorflow": ["tensorflow"],
        "pytorch": ["pytorch", "torch"],
        "nlp": ["nlp", "natural language processing"],
        "llm": ["llm", "large language model", "large language models"],
        "rag": ["rag", "retrieval augmented generation", "retrieval-augmented generation"],
    },
    "mobile": {
        "android": ["android"],
        "flutter": ["flutter"],
        "react native": ["react native"],
        "ios": ["ios"],
    }
}

ALIAS_ROWS = []
CANONICAL_TO_CATEGORY = {}

for category, skills in SKILL_TAXONOMY.items():
    for canonical, aliases in skills.items():
        CANONICAL_TO_CATEGORY[canonical] = category
        unique_aliases = list(dict.fromkeys([canonical] + aliases))
        for alias in unique_aliases:
            ALIAS_ROWS.append((canonical, category, alias.lower()))

ALIAS_ROWS.sort(key=lambda x: len(x[2]), reverse=True)


def _build_pattern(term: str) -> re.Pattern:
    escaped = re.escape(term)
    return re.compile(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", re.IGNORECASE)


PATTERNS = [
    (canonical, category, alias, _build_pattern(alias))
    for canonical, category, alias in ALIAS_ROWS
]


def normalize_skill_name(skill: str) -> str:
    if not skill:
        return ""
    value = skill.strip().lower()
    for canonical, _, alias in ALIAS_ROWS:
        if value == alias:
            return canonical
    return value


def extract_skills(text: str) -> Dict[str, List[str]]:
    if not text:
        return {"skills": [], "by_category": {}, "evidence": {}}

    lowered = text.lower()
    found = set()
    by_category = defaultdict(list)
    evidence = defaultdict(list)

    for canonical, category, alias, pattern in PATTERNS:
        if pattern.search(lowered):
            if canonical not in found:
                found.add(canonical)
                by_category[category].append(canonical)
            if len(evidence[canonical]) < 3:
                evidence[canonical].append(alias)

    return {
        "skills": sorted(found),
        "by_category": {k: sorted(v) for k, v in by_category.items()},
        "evidence": dict(evidence),
    }