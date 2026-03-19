# src/data/rules_config.py

REQUIRED_CV_SECTIONS = ["Summary", "Skills", "Experience", "Education"]
RECOMMENDED_CV_SECTIONS = ["Projects", "Certifications"]

SECTION_HEADERS = {
    "Summary": [
        "summary", "profile", "objective", "professional summary",
        "career objective", "about me", "executive summary"
    ],
    "Skills": [
        "skills", "technical skills", "key skills", "competencies",
        "technologies", "tools", "proficiencies", "technical stack"
    ],
    "Experience": [
        "experience", "work experience", "employment", "professional experience",
        "career history", "work history", "employment history"
    ],
    "Education": [
        "education", "academic background", "academic profile",
        "qualifications", "qualification", "degrees"
    ],
    "Projects": [
        "projects", "personal projects", "academic projects",
        "selected projects", "notable projects", "open source"
    ],
    "Certifications": [
        "certifications", "certificates", "awards", "honors",
        "licenses", "training"
    ],
    "Contact": [
        "contact", "contact info", "contact information", "personal information"
    ],
}

GENERIC_PHRASES = [
    "hard-working",
    "team player",
    "responsible",
    "fast learner",
    "good communication",
    "can work under pressure",
    "willing to learn",
    "high sense of responsibility",
    "self-motivated",
    "detail-oriented"
]

WEAK_BULLET_PATTERNS = [
    "responsible for",
    "worked on",
    "helped with",
    "involved in",
    "participated in",
    "assisted with"
]

ACTION_VERBS = [
    "built", "developed", "implemented", "designed", "created", "optimized",
    "improved", "delivered", "deployed", "integrated", "automated", "migrated",
    "maintained", "refactored", "tested", "led", "analyzed", "engineered",
    "debugged", "reduced", "increased", "accelerated", "launched"
]

METRIC_HINTS = [
    "%", "percent", "ms", "s", "sec", "seconds", "minutes", "hours",
    "users", "clients", "requests", "transactions", "records",
    "services", "apis", "endpoints", "modules", "projects"
]

JD_REQUIRED_MARKERS = [
    "must", "required", "requirements", "you have", "need to",
    "we are looking for", "mandatory", "minimum qualifications"
]

JD_PREFERRED_MARKERS = [
    "preferred", "nice to have", "bonus", "plus", "good to have",
    "preferred qualifications"
]

KEYWORD_BLACKLIST = {
    "experience", "skills", "education", "job", "work", "candidate",
    "team", "company", "role", "position", "requirement", "requirements",
    "responsibilities", "summary", "project", "projects", "knowledge",
    "strong", "good", "ability"
}

SCORE_WEIGHTS = {
    "section": 15,
    "skill": 40,
    "keyword": 20,
    "experience": 15,
    "language": 10,
}

MAX_KEYWORDS = 20
MAX_LANGUAGE_ISSUES = 15