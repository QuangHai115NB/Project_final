# src/services/suggestion_engine.py
"""
Suggestion Engine — dùng Gemini API để sinh ra suggested_fix
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
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")


def _call_gemini(prompt: str, max_tokens: int = 500) -> str:
    """
    Gọi Gemini API, trả về text response.
    Trả về "" nếu lỗi hoặc không có key.
    """
    if not GEMINI_API_KEY:
        return ""

    try:
        import urllib.request
        import urllib.parse

        payload = json.dumps({
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": 0.3,
                "topP": 0.8,
            },
        }).encode("utf-8")

        model = urllib.parse.quote(GEMINI_MODEL, safe="")
        api_key = urllib.parse.quote(GEMINI_API_KEY, safe="")
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={api_key}"
        )

        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "content-type": "application/json",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            candidates = data.get("candidates", [])
            if not candidates:
                return ""
            parts = candidates[0].get("content", {}).get("parts", [])
            return "".join(part.get("text", "") for part in parts).strip()

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

    if not GEMINI_API_KEY:
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

    result = _call_gemini(prompt, max_tokens=150)

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

    if not GEMINI_API_KEY:
        return fallback

    jd_snippet = jd_context[:200] if jd_context else ""

    prompt = f"""You are an IT career coach. A candidate's CV is missing "{skill_name}" which is required in the job description.

Job context: {jd_snippet}

Write ONE specific, realistic example of how the candidate could mention "{skill_name}" in their CV's {section} section.

Format: Start with the section name, then give a concrete bullet example.
Output format: "Add to {section}: '[example bullet]'"

Output ONLY the suggestion, no explanation:"""

    result = _call_gemini(prompt, max_tokens=120)

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

    if not GEMINI_API_KEY:
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

    result = _call_gemini(prompt, max_tokens=200)

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

        # --- Rule-based fallback always exists ---
        localized = _get_rule_based_fix(code, details, section)
        suggested_fix = localized["meaning_vi"]
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
        error_copy["suggested_fix_en"] = localized["fix_en"]
        error_copy["fix_meaning_vi"] = localized["meaning_vi"]
        error_copy["fix_meaning_en"] = localized["meaning_en"]
        if optional_rewrite:
            error_copy["optional_rewrite"] = optional_rewrite
            error_copy["optional_rewrite_meaning_vi"] = _explain_rewrite_vi(optional_rewrite)
            error_copy["optional_rewrite_meaning_en"] = _explain_rewrite_en(optional_rewrite)

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


def _explain_rewrite_vi(rewrite: str) -> str:
    return (
        "Đây là câu tiếng Anh có thể đưa vào CV sau khi bạn xác nhận đúng với kinh nghiệm thật. "
        "Câu này nhấn mạnh hành động, công nghệ đã dùng, phạm vi công việc và kết quả đo được."
    )


def _explain_rewrite_en(rewrite: str) -> str:
    return (
        "Use this English wording only if it matches your real experience. "
        "It emphasizes action, technology, work scope, and measurable impact."
    )


def _get_rule_based_fix(code: str, details: list, section: str) -> Dict[str, str]:
    """Return English CV wording plus localized meaning for the user."""
    joined = ", ".join(str(d) for d in details[:5])
    fixes = {
        "missing_required_skills": {
            "fix_en": f"Add verified experience with {joined} to Skills and at least one Experience or Projects bullet.",
            "meaning_vi": f"Nếu bạn thật sự có kinh nghiệm với {joined}, hãy đưa vào mục Skills và thêm ít nhất một dòng mô tả trong Experience/Projects để chứng minh.",
            "meaning_en": f"If you genuinely have experience with {joined}, add it to Skills and support it with at least one Experience/Projects bullet.",
        },
        "missing_preferred_skills": {
            "fix_en": f"Mention nice-to-have skills such as {joined} in Projects or Skills only if you have used them.",
            "meaning_vi": f"Các kỹ năng này không bắt buộc nhưng giúp tăng độ phù hợp. Chỉ thêm nếu bạn đã từng dùng.",
            "meaning_en": "These skills are not mandatory, but they improve fit. Add them only if you have real usage.",
        },
        "weak_bullets": {
            "fix_en": "Rewrite weak bullets as: [Action Verb] + [what you built] + [technology] + [scope/result].",
            "meaning_vi": "Hãy viết dòng mô tả theo hướng chủ động: bạn đã xây gì, dùng công nghệ nào, phạm vi ra sao và tạo kết quả gì.",
            "meaning_en": "Use active ownership: what you built, which technology you used, the scope, and the result.",
        },
        "missing_metrics": {
            "fix_en": "Add measurable outcomes to 2-3 bullets, such as users, APIs, response time, throughput, modules, or percentage improvements.",
            "meaning_vi": "CV cần có số liệu để recruiter thấy tác động thật: số user, số API, % cải thiện, thời gian phản hồi, số module.",
            "meaning_en": "Add numbers so recruiters can see impact: users, APIs, percentage gains, response time, or modules delivered.",
        },
        "generic_phrases": {
            "fix_en": f"Replace generic phrases ({joined}) with concrete evidence: technology, feature, scope, and result.",
            "meaning_vi": "Các cụm từ chung chung không chứng minh năng lực. Hãy thay bằng công nghệ, feature và kết quả cụ thể.",
            "meaning_en": "Generic phrases do not prove ability. Replace them with technology, feature scope, and outcomes.",
        },
        "missing_sections": {
            "fix_en": f"Add missing CV sections: {joined}.",
            "meaning_vi": "Các section này giúp ATS và recruiter đọc đúng cấu trúc hồ sơ.",
            "meaning_en": "These sections help ATS and recruiters understand your profile structure.",
        },
        "keyword_gap": {
            "fix_en": f"Naturally include relevant JD keywords such as {joined} in Summary and Experience bullets.",
            "meaning_vi": "Hãy tích hợp keyword quan trọng từ JD vào ngữ cảnh thật, không nhồi từ khóa rời rạc.",
            "meaning_en": "Integrate important JD keywords in real context instead of keyword stuffing.",
        },
        "weak_experience_alignment": {
            "fix_en": "Rewrite Experience bullets to mirror the JD responsibilities you have actually performed.",
            "meaning_vi": "Đọc lại JD, chọn 3-5 trách nhiệm chính. Mỗi dòng mô tả nên nêu rõ việc bạn đã làm, công nghệ liên quan, phạm vi phụ trách và kết quả đạt được.",
            "meaning_en": "Review the JD, pick 3-5 key responsibilities, and show similar work you have actually done.",
        },
        "seniority_gap": {
            "fix_en": "Adjust the Summary and Experience scope so the CV communicates the right seniority level.",
            "meaning_vi": "Ngôn ngữ, phạm vi dự án và mức độ ownership cần khớp level mà JD yêu cầu.",
            "meaning_en": "The wording, project scope, and ownership level should match the seniority required by the JD.",
        },
        "skill_no_evidence": {
            "fix_en": f"Add evidence for {joined} in Experience or Projects, not only in the Skills list.",
            "meaning_vi": "Kỹ năng chỉ xuất hiện trong Skills chưa đủ thuyết phục. Cần có dòng mô tả chứng minh bạn đã dùng kỹ năng đó.",
            "meaning_en": "A skill listed only in Skills is weak evidence. Add a bullet showing how you used it.",
        },
        "contact_info": {
            "fix_en": f"Add missing contact/profile information: {joined}.",
            "meaning_vi": "Thông tin liên hệ và hồ sơ như LinkedIn/GitHub giúp CV IT chuyên nghiệp và đáng tin hơn.",
            "meaning_en": "Contact and profile links such as LinkedIn/GitHub make an IT CV more credible.",
        },
        "cv_length": {
            "fix_en": "Keep the CV focused, usually 400-700 words for an early/mid-career IT profile.",
            "meaning_vi": "CV nên đủ chi tiết nhưng không lan man; ưu tiên kinh nghiệm và dự án liên quan trực tiếp tới JD.",
            "meaning_en": "Keep the CV detailed but focused on experience and projects relevant to the JD.",
        },
    }
    return fixes.get(code, {
        "fix_en": "Review this section and improve it based on the report evidence.",
        "meaning_vi": "Hãy xem lại phần này và chỉnh theo dẫn chứng trong báo cáo.",
        "meaning_en": "Review this section and revise it using the evidence in the report.",
    })


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
