
REQUIRED_CV_SECTIONS = ["Summary", "Skills", "Experience"]
RECOMMENDED_CV_SECTIONS = ["Projects", "Certifications"]

# Tu dien tu
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

#Tu sao rong, chung chung
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

#Cac cum tu bat dau cau yeu
WEAK_BULLET_PATTERNS = [
    "responsible for",
    "worked on",
    "helped with",
    "involved in",
    "participated in",
    "assisted with"
]

# Dong tu manh
ACTION_VERBS = [
    # --- Danh sách ban đầu (Original) ---
    "built", "developed", "implemented", "designed", "created", "optimized",
    "improved", "delivered", "deployed", "integrated", "automated", "migrated",
    "maintained", "refactored", "tested", "led", "analyzed", "engineered",
    "debugged", "reduced", "increased", "accelerated", "launched",

    # --- Nhóm Kiến trúc & Thiết kế hệ thống (Architecture & Design) ---
    "architected", "structured", "modeled", "conceptualized", "formulated",
    "drafted", "outlined", "mapped", "prototyped", "tailored",

    # --- Nhóm Lập trình & Cấu hình (Coding & Configuration) ---
    "programmed", "coded", "authored", "scripted", "configured", "customized",
    "compiled", "assembled", "installed", "setup",

    # --- Nhóm Tối ưu hóa & Nâng cấp (Optimization & Modernization) ---
    "streamlined", "modernized", "upgraded", "transformed", "scaled", "enhanced",
    "maximized", "minimized", "revamped", "standardized", "redesigned", "reengineered",
    "simplified", "consolidated",

    # --- Nhóm Kiểm thử, Bảo mật & Xử lý sự cố (Testing, Security & Problem Solving) ---
    "resolved", "troubleshot", "audited", "secured", "validated", "verified",
    "investigated", "diagnosed", "monitored", "assessed", "evaluated", "prevented",

    # --- Nhóm Triển khai & Vận hành (Execution & Operation) ---
    "executed", "orchestrated", "provisioned", "released", "published", "incorporated",
    "operated", "administered", "facilitated", "driven", "generated", "produced",

    # --- Nhóm Lãnh đạo & Quản lý (Leadership & Teamwork) ---
    "spearheaded", "mentored", "coordinated", "directed", "managed", "supervised",
    "collaborated", "partnered", "guided", "trained", "empowered", "championed"
]
#Dau hieu do luong
METRIC_HINTS = [
    "%", "percent", "ms", "s", "sec", "seconds", "minutes", "hours",
    "users", "clients", "requests", "transactions", "records",
    "services", "apis", "endpoints", "modules", "projects"
]

#Yeu cau bat buoc
JD_REQUIRED_MARKERS = [
    "must", "required", "requirements", "you have", "need to",
    "we are looking for", "mandatory", "minimum qualifications"
]

#Yeu cau diem cong
JD_PREFERRED_MARKERS = [
    "preferred", "nice to have", "bonus", "plus", "good to have",
    "preferred qualifications"
]

#Danh sach den cac tu
KEYWORD_BLACKLIST = {
    "experience", "skills", "education", "job", "work", "candidate",
    "team", "company", "role", "position", "requirement", "requirements",
    "responsibilities", "summary", "project", "projects", "knowledge",
    "strong", "good", "ability",
    "salary", "compensation", "benefit", "benefits", "bonus", "allowance",
    "insurance", "health insurance", "social insurance", "paid leave",
    "annual leave", "vacation", "remote", "hybrid", "onsite", "office",
    "location", "address", "working hours", "working time", "full time",
    "part time", "interview", "recruitment", "apply", "application"
}

# Sử dụng Biểu thức chính quy (Regex) để bắt và loại bỏ mạnh tay hơn các đoạn văn bản chứa thông tin về lương thưởng,
# loại hình làm việc
KEYWORD_EXCLUDED_PATTERNS = [
    r"\b(salary|compensation|benefits?|bonus|allowance|insurance|paid leave|annual leave|vacation)\b",
    r"\b(remote|hybrid|onsite|office|location|address|working hours|working time|full time|part time)\b",
    r"\b(interview|recruitment|apply|application|probation|contract)\b",
    r"[$€£¥₫]\s*\d+",
    r"\b\d+\s*(usd|vnd|eur|gbp|tr|million|month|year)\b",
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
