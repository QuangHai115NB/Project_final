# src/services/suggestion_engine.py
"""
Suggestion Engine — dùng Anthropic API để sinh ra suggested_fix
thực tế, cụ thể cho từng lỗi phát hiện được.

Không dùng cho toàn bộ CV (tốn token) mà chỉ dùng cho:
1. Rewrite weak bullets → format: Action + Tech + Scope + Result
2. Gợi ý thêm kỹ năng còn thiếu vào đúng section
3. Rewrite Summary cho phù hợp JD

Thiết kế: mỗi function nhận input tối thiểu, trả ra
suggested_fix dạng string — dễ nhúng vào error object.
"""

from __future__ import annotations

import os
import json
import re
from typing import Dict, List, Optional

# API key lấy từ env — không hardcode
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-20250514"


def _call_claude(prompt: str, max_tokens: int = 500) -> str:
    """
    Gọi Anthropic API, trả về text response.
    Trả về "" nếu lỗi hoặc không có key.
    """
    if not ANTHROPIC_API_KEY:
        return ""

    try:
        import urllib.request

        payload = json.dumps({
            "model": CLAUDE_MODEL,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content_blocks = data.get("content", [])
            return "".join(
                block.get("text", "") for block in content_blocks
                if block.get("type") == "text"
            ).strip()

    except Exception:
        return ""


def rewrite_weak_bullet(
        bullet: str,
        missing_skills: List[str],
        jd_context: str = "",
) -> str:
    """
    Viết lại 1 bullet point yếu thành dạng chuyên nghiệp IT.

    Input:
        bullet = "Responsible for backend development"
        missing_skills = ["Spring Boot", "REST API", "MySQL"]
        jd_context = "Build scalable microservices for e-commerce..."

    Output:
        "Developed RESTful APIs using Spring Boot and MySQL to support
         e-commerce order processing, handling 10K+ daily transactions."

    Nếu không có API key → trả về template-based fallback.
    """
    if not bullet or len(bullet.split()) < 3:
        return ""

    skills_hint = ", ".join(missing_skills[:4]) if missing_skills else ""

    # Template fallback (không cần API)
    fallback = _template_rewrite_bullet(bullet, missing_skills)

    if not ANTHROPIC_API_KEY:
        return fallback

    jd_snippet = jd_context[:300] if jd_context else ""
    skills_instruction = (
        f"Try to naturally incorporate some of these technologies if relevant: {skills_hint}."
        if skills_hint else ""
    )

    prompt = f"""You are an IT career coach helping a software engineer improve their CV.

Rewrite the following weak CV bullet point into a strong, professional IT bullet.

Rules:
- Format: [Strong Action Verb] + [What you built/did] + [Technology used] + [Scale/Scope] + [Measurable result if possible]
- Be specific and concrete
- Keep it to 1-2 lines max
- Do NOT invent false metrics — use "[X%]" or "[number]" as placeholders if unsure
- {skills_instruction}

Job context (what the company needs):
{jd_snippet}

Original weak bullet:
"{bullet}"

Rewritten bullet (output ONLY the bullet, no explanation):"""

    result = _call_claude(prompt, max_tokens=150)

    # Nếu API trả về rỗng hoặc lỗi → dùng fallback
    if not result or len(result.split()) < 5:
        return fallback

    # Strip dấu ngoặc kép nếu có
    result = result.strip('"\'')
    return result


def suggest_missing_skill_addition(
        skill_name: str,
        section: str,
        jd_context: str = "",
) -> str:
    """
    Gợi ý cách thêm skill còn thiếu vào CV một cách tự nhiên.

    Input:
        skill_name = "Docker"
        section = "Experience"
        jd_context = "Deploy services using Docker and Kubernetes..."

    Output:
        "Add to Experience: 'Containerized the application using Docker,
         reducing environment setup time by 60%.'"
    """
    fallback = _template_skill_addition(skill_name, section)

    if not ANTHROPIC_API_KEY:
        return fallback

    jd_snippet = jd_context[:200] if jd_context else ""

    prompt = f"""You are an IT career coach. A candidate's CV is missing "{skill_name}" which is required in the job description.

Job context: {jd_snippet}

Write ONE specific, realistic example of how the candidate could mention "{skill_name}" in their CV's {section} section.

Format: Start with the section name, then give a concrete bullet example.
Output format: "Add to {section}: '[example bullet]'"

Output ONLY the suggestion, no explanation:"""

    result = _call_claude(prompt, max_tokens=120)

    if not result:
        return fallback

    return result.strip()


def rewrite_summary_for_jd(
        current_summary: str,
        jd_title: str,
        matched_skills: List[str],
        missing_required: List[str],
) -> str:
    """
    Viết lại Summary/Objective cho phù hợp JD hơn.

    Input:
        current_summary = "Hardworking developer with 2 years experience"
        jd_title = "Backend Engineer"
        matched_skills = ["Python", "Django", "PostgreSQL"]
        missing_required = ["Docker", "AWS"]

    Output:
        "Backend Engineer with 2+ years of experience building scalable
         APIs using Python and Django. Proficient in PostgreSQL..."
    """
    fallback = _template_summary_rewrite(jd_title, matched_skills)

    if not ANTHROPIC_API_KEY:
        return fallback

    skills_str = ", ".join(matched_skills[:6])
    missing_str = ", ".join(missing_required[:3])

    prompt = f"""You are an IT career coach. Rewrite this CV summary to better match a {jd_title} role.

Current summary:
"{current_summary[:400]}"

Candidate's confirmed skills: {skills_str}
Skills gap (mention only if you have real experience): {missing_str}

Rules:
- 2-3 sentences max
- Start with role title + years of experience
- Mention 3-4 key technologies naturally
- Professional IT tone, no buzzwords like "hardworking" or "team player"
- Do NOT invent experience

Output ONLY the rewritten summary:"""

    result = _call_claude(prompt, max_tokens=200)

    if not result or len(result.split()) < 10:
        return fallback

    return result.strip()


def generate_bulk_suggestions(
        errors: List[Dict],
        cv_sections: Dict[str, str],
        jd_text: str,
        max_api_calls: int = 3,
) -> List[Dict]:
    """
    Main function — nhận list errors từ matching engine,
    thêm `suggested_fix` và `optional_rewrite` vào mỗi error.

    Giới hạn API calls để tránh tốn token.
    Ưu tiên lỗi severity=high trước.

    Input: errors từ jd_matcher + rule_checker
    Output: cùng list nhưng mỗi item có thêm:
        - "suggested_fix": str  (luôn có — fallback nếu không có API)
        - "optional_rewrite": str  (có nếu dùng được API)

    Test case:
        errors = [
            {"code": "missing_required_skills", "severity": "high",
             "details": ["Docker", "AWS"], ...},
            {"code": "weak_bullets", "severity": "medium",
             "details": ["Responsible for backend development"], ...},
        ]
        → trả về cùng list với suggested_fix được điền
    """
    enriched = []
    api_calls_used = 0

    # Sort: high severity trước
    sorted_errors = sorted(
        errors,
        key=lambda e: {"high": 0, "medium": 1, "low": 2}.get(e.get("severity", "low"), 3)
    )

    for error in sorted_errors:
        error_copy = dict(error)
        code = error.get("code", "")
        details = error.get("details", [])
        section = error.get("section", "")

        # --- Rule-based fallback luôn có ---
        suggested_fix = _get_rule_based_fix(code, details, section)
        optional_rewrite = ""

        # --- API-powered fix cho các lỗi quan trọng ---
        if api_calls_used < max_api_calls:

            if code == "weak_bullets" and details:
                bullet = details[0] if isinstance(details[0], str) else str(details[0])
                rewritten = rewrite_weak_bullet(
                    bullet=bullet,
                    missing_skills=_extract_missing_from_errors(sorted_errors),
                    jd_context=jd_text[:300],
                )
                if rewritten:
                    optional_rewrite = rewritten
                    api_calls_used += 1

            elif code == "missing_required_skills" and details:
                skill = details[0]
                suggestion = suggest_missing_skill_addition(
                    skill_name=skill,
                    section="Experience",
                    jd_context=jd_text[:200],
                )
                if suggestion:
                    optional_rewrite = suggestion
                    api_calls_used += 1

            elif code == "weak_summary" and cv_sections.get("Summary"):
                missing = _extract_missing_from_errors(sorted_errors)
                matched = _extract_matched_from_errors(sorted_errors)
                rewritten_summary = rewrite_summary_for_jd(
                    current_summary=cv_sections["Summary"],
                    jd_title=_guess_jd_title(jd_text),
                    matched_skills=matched,
                    missing_required=missing,
                )
                if rewritten_summary:
                    optional_rewrite = rewritten_summary
                    api_calls_used += 1

        error_copy["suggested_fix"] = suggested_fix
        if optional_rewrite:
            error_copy["optional_rewrite"] = optional_rewrite

        enriched.append(error_copy)

    return enriched


# ─── Template-based fallbacks (không cần API) ────────────────────────

def _template_rewrite_bullet(bullet: str, missing_skills: List[str]) -> str:
    skills_str = "/".join(missing_skills[:2]) if missing_skills else "[technology]"
    first_words = " ".join(bullet.split()[:4])
    return (
        f"Rewrite this bullet using the format: "
        f"'[Action Verb] [what you built] using {skills_str} to [purpose], "
        f"resulting in [measurable outcome].'\n"
        f"Example: 'Developed RESTful APIs using {skills_str} to support "
        f"[system], reducing [metric] by [X%].'"
    )


def _template_skill_addition(skill_name: str, section: str) -> str:
    templates = {
        "docker": f"Add to {section}: 'Containerized services using Docker, enabling consistent deployments across dev/staging/prod environments.'",
        "aws": f"Add to {section}: 'Deployed application on AWS (EC2/S3/RDS), implementing auto-scaling to handle peak traffic.'",
        "kubernetes": f"Add to {section}: 'Orchestrated microservices deployment using Kubernetes, managing [N] pods across [N] nodes.'",
        "git": f"Add to {section}: 'Managed source code with Git, following GitFlow branching strategy in a team of [N] developers.'",
        "ci/cd": f"Add to {section}: 'Set up CI/CD pipeline using [Jenkins/GitHub Actions], automating build/test/deploy cycles.'",
    }
    skill_lower = skill_name.lower()
    if skill_lower in templates:
        return templates[skill_lower]
    return (
        f"Add to {section}: 'Implemented [feature/task] using {skill_name} to "
        f"[achieve specific goal], improving [metric] by [X%].'"
    )


def _template_summary_rewrite(jd_title: str, matched_skills: List[str]) -> str:
    skills_str = ", ".join(matched_skills[:4]) if matched_skills else "relevant technologies"
    return (
        f"Rewrite your Summary as: '{jd_title} with [X] years of experience "
        f"building [type of systems] using {skills_str}. "
        f"Passionate about [relevant domain] with a track record of [achievement].'"
    )


def _get_rule_based_fix(code: str, details: list, section: str) -> str:
    """Rule-based suggested_fix — luôn trả về text hữu ích."""
    fixes = {
        "missing_required_skills": (
            f"Nếu bạn đã có kinh nghiệm với {', '.join(str(d) for d in details[:3])}, "
            f"hãy thêm vào: (1) mục Skills dưới dạng bullet rõ ràng, "
            f"(2) mục Experience/Projects dưới dạng bullet có context cụ thể."
        ),
        "missing_preferred_skills": (
            f"Các kỹ năng nice-to-have: {', '.join(str(d) for d in details[:3])}. "
            f"Nếu bạn có kinh nghiệm dù nhỏ, hãy thêm vào Projects hoặc một dòng trong Skills."
        ),
        "weak_bullets": (
            "Viết lại bullet theo format: "
            "'[Action Verb] + [Hệ thống/Feature bạn xây] + [Technology] + [Kết quả đo được]'. "
            "Ví dụ: 'Developed student management module using Spring Boot + MySQL, "
            "supporting 500+ concurrent users.'"
        ),
        "missing_metrics": (
            "Thêm số liệu vào ít nhất 2-3 bullets: "
            "số user, số API endpoints, % cải thiện performance, số lượng request/day, "
            "thời gian giảm được, số module xây dựng, team size..."
        ),
        "generic_phrases": (
            f"Xóa cụm từ: {', '.join(str(d) for d in details[:3])}. "
            f"Thay bằng minh chứng cụ thể: technology đã dùng, feature đã xây, kết quả đạt được."
        ),
        "missing_sections": (
            f"Bổ sung section: {', '.join(str(d) for d in details)}. "
            f"Đây là phần thiết yếu để ATS và recruiter đánh giá đúng hồ sơ của bạn."
        ),
        "keyword_gap": (
            f"CV chưa chứa từ khóa: {', '.join(str(d) for d in details[:5])}. "
            f"Tích hợp tự nhiên vào Summary và Experience bullets — không spam từ khóa."
        ),
        "weak_experience_alignment": (
            "Mô tả Experience chưa bám sát JD. Đọc lại JD, xác định 3-5 trách nhiệm chính, "
            "sau đó viết lại bullets để thể hiện bạn đã làm những việc tương tự."
        ),
        "seniority_gap": (
            f"JD yêu cầu level {details[1] if len(details) > 1 else 'khác'} "
            f"nhưng CV đang thể hiện level {details[0] if details else 'không rõ'}. "
            f"Điều chỉnh ngôn ngữ, scope dự án và số năm kinh nghiệm cho phù hợp."
        ),
        "skill_no_evidence": (
            f"Kỹ năng {', '.join(str(d) for d in details[:2])} có trong Skills "
            f"nhưng không xuất hiện trong Experience/Projects. "
            f"Thêm ít nhất 1 bullet chứa kỹ năng này kèm context cụ thể."
        ),
        "contact_info": (
            f"Bổ sung thông tin: {', '.join(str(d) for d in details)}. "
            f"LinkedIn và GitHub đặc biệt quan trọng với CV IT."
        ),
        "cv_length": (
            "Độ dài CV chưa tối ưu. CV IT nên có 400-700 từ (1-2 trang). "
            "Tập trung vào kinh nghiệm 3-5 năm gần nhất và dự án liên quan JD."
        ),
    }
    return fixes.get(code, "Xem xét lại phần này và cải thiện theo gợi ý trong báo cáo.")


def _extract_missing_from_errors(errors: List[Dict]) -> List[str]:
    for e in errors:
        if e.get("code") == "missing_required_skills":
            return [str(d) for d in e.get("details", [])]
    return []


def _extract_matched_from_errors(errors: List[Dict]) -> List[str]:
    """Tìm matched skills từ jd_report nếu có."""
    # Thực tế sẽ được pass từ bên ngoài, đây là fallback
    return []


def _guess_jd_title(jd_text: str) -> str:
    """Đoán job title từ JD text."""
    title_patterns = [
        r"(?:we are looking for|hiring|position:|role:)\s*(?:a\s+)?([A-Z][a-zA-Z\s]+(?:Engineer|Developer|Architect|Lead|Manager))",
        r"^([A-Z][a-zA-Z\s]{5,50}(?:Engineer|Developer|Architect|Lead))",
    ]
    for pattern in title_patterns:
        match = re.search(pattern, jd_text[:500], re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).strip()
    return "Software Engineer"
