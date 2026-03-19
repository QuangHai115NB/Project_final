# src/services/rule_checker.py

import re
from typing import Dict, List

from src.data.rules_config import (
    REQUIRED_CV_SECTIONS,
    RECOMMENDED_CV_SECTIONS,
    GENERIC_PHRASES,
    WEAK_BULLET_PATTERNS,
    ACTION_VERBS,
)
from src.services.text_preprocess import clean_text


def _get_section_map(parsed_sections: dict) -> dict:
    if isinstance(parsed_sections, dict) and "sections" in parsed_sections:
        return parsed_sections.get("sections", {})
    return parsed_sections or {}


def check_missing_sections(parsed_sections: dict) -> List[str]:
    sections = _get_section_map(parsed_sections)
    return [sec for sec in REQUIRED_CV_SECTIONS if sec not in sections]


def check_generic_phrases(text: str) -> List[str]:
    lowered = text.lower()
    return [phrase for phrase in GENERIC_PHRASES if phrase in lowered]


def check_cv_length(text: str) -> Dict[str, object]:
    word_count = len(clean_text(text).split())

    if word_count < 180:
        status = "too_short"
    elif word_count > 900:
        status = "too_long"
    else:
        status = "good"

    return {
        "word_count": word_count,
        "status": status
    }


def check_contact_info(text: str) -> Dict[str, bool]:
    lowered = text.lower()

    return {
        "has_email": bool(re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)),
        "has_phone": bool(re.search(r"(\+\d{1,3}\s?)?(\(?\d{2,4}\)?[\s.-]?)?\d{3,4}[\s.-]?\d{3,4}", text)),
        "has_linkedin": ("linkedin.com" in lowered) or ("linkedin" in lowered),
        "has_github": ("github.com" in lowered) or ("github" in lowered),
    }


def analyze_bullet_quality(parsed_sections: dict) -> Dict[str, object]:
    sections = _get_section_map(parsed_sections)

    lines = []
    for section_name in ("Experience", "Projects"):
        content = sections.get(section_name, "")
        for raw_line in content.split("\n"):
            line = raw_line.strip(" \t-•●▪*")
            if len(line.split()) >= 4:
                lines.append((section_name, line))

    total_bullets = len(lines)
    metric_bullets = 0
    action_bullets = 0
    weak_bullets = []

    metric_pattern = re.compile(
        r"(\d+%|\d+\+|[$€£]\d+|\d+\s*(users|clients|ms|s|sec|seconds|minutes|hours|apis|services|projects|records))",
        re.IGNORECASE
    )

    for _, line in lines:
        lowered = line.lower()
        first_word = lowered.split()[0] if lowered.split() else ""

        if metric_pattern.search(lowered):
            metric_bullets += 1

        if first_word in ACTION_VERBS:
            action_bullets += 1

        if any(lowered.startswith(pattern) for pattern in WEAK_BULLET_PATTERNS):
            weak_bullets.append(line)

    return {
        "total_bullets": total_bullets,
        "metric_bullets": metric_bullets,
        "action_verb_bullets": action_bullets,
        "weak_bullets": weak_bullets[:10],
    }


def run_rule_checks(text: str, parsed_sections: dict) -> dict:
    sections = _get_section_map(parsed_sections)

    missing_sections = check_missing_sections(parsed_sections)
    generic_phrases = check_generic_phrases(text)
    cv_length = check_cv_length(text)
    contact_info = check_contact_info(text)
    bullet_analysis = analyze_bullet_quality(parsed_sections)

    issues = []
    suggestions = []
    penalty = 0

    if missing_sections:
        penalty += 20 * len(missing_sections)
        issues.append({
            "code": "missing_sections",
            "severity": "high",
            "title": "CV thiếu mục quan trọng",
            "details": missing_sections
        })
        suggestions.append({
            "type": "add_section",
            "target": "structure",
            "message": f"Hãy bổ sung các mục còn thiếu: {', '.join(missing_sections)}."
        })

    missing_recommended = [sec for sec in RECOMMENDED_CV_SECTIONS if sec not in sections]
    if missing_recommended:
        penalty += 5 * len(missing_recommended)
        issues.append({
            "code": "missing_recommended_sections",
            "severity": "medium",
            "title": "CV thiếu mục nên có cho ngành IT",
            "details": missing_recommended
        })
        suggestions.append({
            "type": "add_section",
            "target": "content",
            "message": f"Nên bổ sung thêm mục: {', '.join(missing_recommended)} để CV IT thuyết phục hơn."
        })

    if generic_phrases:
        penalty += min(15, 3 * len(generic_phrases))
        issues.append({
            "code": "generic_phrases",
            "severity": "medium",
            "title": "CV đang dùng nhiều cụm từ chung chung",
            "details": generic_phrases
        })
        suggestions.append({
            "type": "rewrite_phrase",
            "target": "summary",
            "message": "Thay cụm từ chung chung bằng minh chứng cụ thể, ví dụ công nghệ đã dùng, module đã làm, kết quả đã đạt."
        })

    if cv_length["status"] != "good":
        penalty += 10
        issues.append({
            "code": "cv_length",
            "severity": "medium",
            "title": "Độ dài CV chưa hợp lý",
            "details": [f"word_count={cv_length['word_count']}", f"status={cv_length['status']}"]
        })
        if cv_length["status"] == "too_short":
            suggestions.append({
                "type": "expand_content",
                "target": "cv",
                "message": "CV đang quá ngắn. Hãy bổ sung mô tả project, tech stack, kết quả đạt được và vai trò cụ thể."
            })
        else:
            suggestions.append({
                "type": "trim_content",
                "target": "cv",
                "message": "CV đang quá dài. Hãy rút gọn các phần ít liên quan JD, giữ lại phần có công nghệ và thành tích."
            })

    missing_contact_items = [k for k, v in contact_info.items() if not v]
    if missing_contact_items:
        penalty += 3 * len(missing_contact_items)
        issues.append({
            "code": "contact_info",
            "severity": "low",
            "title": "Thiếu một số thông tin liên hệ / hồ sơ",
            "details": missing_contact_items
        })
        suggestions.append({
            "type": "add_contact",
            "target": "header",
            "message": "Nên bổ sung email, số điện thoại, LinkedIn và GitHub để tăng độ chuyên nghiệp."
        })

    if bullet_analysis["total_bullets"] > 0 and bullet_analysis["metric_bullets"] == 0:
        penalty += 10
        issues.append({
            "code": "missing_metrics",
            "severity": "medium",
            "title": "Phần Experience/Projects chưa có số liệu đo lường",
            "details": ["Không tìm thấy bullet có %, số lượng user, số API, thời gian phản hồi, số module..."]
        })
        suggestions.append({
            "type": "add_metrics",
            "target": "experience",
            "message": "Mỗi project/kinh nghiệm nên có ít nhất 1 bullet chứa số liệu: %, số user, số API, số module, thời gian xử lý..."
        })

    if bullet_analysis["total_bullets"] > 0 and bullet_analysis["action_verb_bullets"] < max(1, bullet_analysis["total_bullets"] // 2):
        penalty += 8
        issues.append({
            "code": "weak_bullets",
            "severity": "medium",
            "title": "Nhiều bullet chưa bắt đầu bằng động từ mạnh",
            "details": bullet_analysis["weak_bullets"]
        })
        suggestions.append({
            "type": "rewrite_bullets",
            "target": "experience",
            "message": "Viết bullet theo mẫu: Action Verb + Technology + Scope + Result. Ví dụ: Developed REST APIs using FastAPI for student support system, reducing response time by 30%."
        })

    structure_score = max(0.0, 100.0 - penalty)

    return {
        "structure_score": round(structure_score, 2),
        "missing_sections": missing_sections,
        "generic_phrases": generic_phrases,
        "cv_length": cv_length,
        "contact_info": contact_info,
        "bullet_analysis": bullet_analysis,
        "issues": issues,
        "suggestions": suggestions,
    }