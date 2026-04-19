
REQUIRED_CV_SECTIONS = ["Summary", "Skills", "Experience"]
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
    "strong", "good", "ability",
    "salary", "compensation", "benefit", "benefits", "bonus", "allowance",
    "insurance", "health insurance", "social insurance", "paid leave",
    "annual leave", "vacation", "remote", "hybrid", "onsite", "office",
    "location", "address", "working hours", "working time", "full time",
    "part time", "interview", "recruitment", "apply", "application",
    "lương", "thu nhập", "phúc lợi", "thưởng", "bảo hiểm", "nghỉ phép",
    "địa điểm", "văn phòng", "thời gian làm việc", "ứng tuyển", "phỏng vấn"
}

KEYWORD_EXCLUDED_PATTERNS = [
    r"\b(salary|compensation|benefits?|bonus|allowance|insurance|paid leave|annual leave|vacation)\b",
    r"\b(remote|hybrid|onsite|office|location|address|working hours|working time|full time|part time)\b",
    r"\b(interview|recruitment|apply|application|probation|contract)\b",
    r"\b(lương|thu nhập|phúc lợi|thưởng|bảo hiểm|nghỉ phép|địa điểm|văn phòng|thời gian làm việc|ứng tuyển|phỏng vấn)\b",
    r"[$€£¥₫]\s*\d+",
    r"\b\d+\s*(usd|vnd|eur|gbp|triệu|tr|million|month|year|tháng|năm)\b",
]

SCORE_WEIGHTS = {
    "section": 15,
    "skill": 40,
    "keyword": 20,
    "experience": 15,
}

# Final report weights. These are applied directly to score_breakdown in
# report_builder, so final_score can be recomputed from the returned JSON.
REPORT_SCORE_WEIGHTS = {
    "section_score": 10,
    "skill_score": 30,
    "semantic_score": 15,
    "keyword_score": 15,
    "experience_score": 15,
    "jd_structure_score": 15,
}

# ── Score labels & UI thresholds ──────────────────────────────
# Dùng CHUNG cho backend (label) và frontend (màu thanh).
# ≥ 70: Good → green   |  55-69: Fair → amber  |  < 55: Weak → red
SCORE_LABELS = [
    (85, "Excellent"),
    (70, "Good"),
    (55, "Fair"),
    (0,  "Weak"),
]

SCORE_COLOR_THRESHOLDS = {
    "green":  70,   # ≥70 → green
    "amber":  55,   # 55-69 → amber
    "red":    0,    # <55 → red
}

MAX_KEYWORDS = 20
MAX_LANGUAGE_ISSUES = 15
