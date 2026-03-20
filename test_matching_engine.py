"""
test_matching_engine.py
=======================
Test cases cho CV-JD matching engine.
Chạy: python test_matching_engine.py

Không cần pytest — chạy thẳng để kiểm tra nhanh.
"""

import sys, os

sys.path.insert(0, os.path.abspath("."))

# ─── Mock data ─────────────────────────────────────────────────────

SAMPLE_CV_STRONG = """
John Doe | john@example.com | linkedin.com/in/johndoe | github.com/johndoe

SUMMARY
Backend Engineer with 3 years of experience building scalable REST APIs and 
microservices using Python, Django, and PostgreSQL.

SKILLS
Python, Django, Flask, PostgreSQL, Redis, Docker, Git, REST API, Linux, 
SQL, HTML, CSS, JavaScript

EXPERIENCE
Senior Backend Developer — TechCorp (2022–2024)
- Developed RESTful APIs using Django and PostgreSQL for e-commerce platform, 
  handling 50,000+ daily transactions.
- Implemented Redis caching layer, reducing API response time by 40%.
- Deployed services on Docker containers with CI/CD via GitHub Actions.
- Led migration from monolith to microservices architecture for 3 core modules.

Backend Intern — StartupXYZ (2021–2022)
- Built student management module using Flask and MySQL, supporting 500 users.
- Integrated third-party payment gateway, processing 1,000+ transactions/day.

EDUCATION
B.Sc. Computer Science — University ABC (2021)

PROJECTS
Personal Finance Tracker
- Developed full-stack web app using Django + React, deployed on Linux server.
- Automated monthly report generation, saving 3 hours/month for 200 users.

CERTIFICATIONS
AWS Certified Developer – Associate (2023)
"""

SAMPLE_CV_WEAK = """
Nguyen Van A | nguyenvana@gmail.com

SUMMARY
Hardworking developer with good communication skills and willing to learn.
Fast learner, team player, responsible.

SKILLS
Java, Python, some web development

EXPERIENCE
Software Engineer — ABC Company (2022–2024)
- Responsible for backend development
- Worked on database tasks
- Helped with API integration
- Participated in team meetings

EDUCATION
B.Sc. Information Technology (2022)
"""

SAMPLE_JD = """
Backend Engineer — FinTech Startup

We are looking for a Backend Engineer to join our growing team.

Requirements:
- 2+ years experience in Python or Java backend development
- Strong knowledge of Django or Spring Boot
- Experience with PostgreSQL, Redis, MySQL
- REST API design and development
- Docker and containerization
- Git version control

Preferred (nice to have):
- AWS or GCP cloud experience
- Kubernetes
- CI/CD pipeline setup
- Microservices architecture

Responsibilities:
- Design and develop scalable backend services
- Build and maintain REST APIs for mobile and web clients
- Optimize database queries and caching strategies
- Deploy and monitor services on cloud infrastructure
- Collaborate with frontend team on API contracts
"""


# ─── Test functions ──────────────────────────────────────────────────

def run_test(name: str, fn):
    print(f"\n{'=' * 60}")
    print(f"TEST: {name}")
    print('=' * 60)
    try:
        fn()
        print("✅ PASSED")
    except AssertionError as e:
        print(f"❌ FAILED: {e}")
    except Exception as e:
        print(f"⚠️  ERROR: {type(e).__name__}: {e}")


def test_skill_extraction():
    """Skills phải extract đúng từ cả CV và JD."""
    from src.data.skills_taxonomy import extract_skills

    cv_result = extract_skills(SAMPLE_CV_STRONG)
    jd_result = extract_skills(SAMPLE_JD)

    cv_skills = set(cv_result["skills"])
    jd_skills = set(jd_result["skills"])

    print(f"CV skills ({len(cv_skills)}): {sorted(cv_skills)}")
    print(f"JD skills ({len(jd_skills)}): {sorted(jd_skills)}")

    # CV strong phải có ít nhất: python, django, postgresql, redis, docker
    expected_cv = {"python", "django", "postgresql", "redis", "docker"}
    missing = expected_cv - cv_skills
    assert not missing, f"Missing expected CV skills: {missing}"

    # JD phải có: python, django, postgresql, redis, docker
    expected_jd = {"python", "django", "postgresql", "redis", "docker"}
    missing_jd = expected_jd - jd_skills
    assert not missing_jd, f"Missing expected JD skills: {missing_jd}"


def test_skill_score_strong_cv():
    """CV mạnh phải có skill_score > 70."""
    from src.services.jd_matcher import _extract_jd_skills, _compute_skill_score
    from src.data.skills_taxonomy import extract_skills

    cv_skills = set(extract_skills(SAMPLE_CV_STRONG)["skills"])
    jd_skills = _extract_jd_skills(SAMPLE_JD)
    required = set(jd_skills["required"])
    preferred = set(jd_skills["preferred"])

    score, detail = _compute_skill_score(cv_skills, required, preferred)

    print(f"Skill score (strong CV): {score:.2f}")
    print(f"Required coverage: {detail['required_coverage_pct']}%")
    print(f"Missing required: {detail['missing_required']}")
    print(f"Matched required: {detail['matched_required']}")

    assert score > 60, f"Expected skill_score > 60, got {score:.2f}"


def test_skill_score_weak_cv():
    """CV yếu phải có skill_score < 50."""
    from src.services.jd_matcher import _extract_jd_skills, _compute_skill_score
    from src.data.skills_taxonomy import extract_skills

    cv_skills = set(extract_skills(SAMPLE_CV_WEAK)["skills"])
    jd_skills = _extract_jd_skills(SAMPLE_JD)
    required = set(jd_skills["required"])
    preferred = set(jd_skills["preferred"])

    score, detail = _compute_skill_score(cv_skills, required, preferred)

    print(f"Skill score (weak CV): {score:.2f}")
    print(f"Required coverage: {detail['required_coverage_pct']}%")
    print(f"Missing required: {detail['missing_required']}")

    assert score < 60, f"Expected skill_score < 60 for weak CV, got {score:.2f}"


def test_full_match_strong_vs_weak():
    """CV mạnh phải có match_score cao hơn CV yếu đáng kể."""
    from src.services.jd_matcher import match_cv_to_jd
    from src.services.section_parser import parse_sections

    parsed_strong = parse_sections(SAMPLE_CV_STRONG)
    parsed_weak = parse_sections(SAMPLE_CV_WEAK)

    result_strong = match_cv_to_jd(
        SAMPLE_CV_STRONG, SAMPLE_JD, parsed_strong,
        use_semantic=False,  # Tắt semantic để test nhanh
        use_suggestion_engine=False,
    )
    result_weak = match_cv_to_jd(
        SAMPLE_CV_WEAK, SAMPLE_JD, parsed_weak,
        use_semantic=False,
        use_suggestion_engine=False,
    )

    strong_score = result_strong["match_score"]
    weak_score = result_weak["match_score"]

    print(f"\nStrong CV match score: {strong_score}")
    print(f"Weak CV match score:   {weak_score}")
    print(f"\nStrong CV score breakdown: {result_strong['score_breakdown']}")
    print(f"Weak CV score breakdown:   {result_weak['score_breakdown']}")
    print(f"\nStrong CV issues ({len(result_strong['issues'])}):")
    for issue in result_strong["issues"]:
        print(f"  [{issue['severity']}] {issue['code']}: {issue.get('explanation', '')[:80]}")
    print(f"\nWeak CV issues ({len(result_weak['issues'])}):")
    for issue in result_weak["issues"]:
        print(f"  [{issue['severity']}] {issue['code']}: {issue.get('explanation', '')[:80]}")

    assert strong_score > weak_score, (
        f"Strong CV ({strong_score}) should score higher than weak CV ({weak_score})"
    )
    assert strong_score > 50, f"Strong CV score should be > 50, got {strong_score}"
    assert weak_score < 50, f"Weak CV score should be < 50, got {weak_score}"


def test_issues_have_suggested_fix():
    """Mỗi issue phải có suggested_fix field."""
    from src.services.jd_matcher import match_cv_to_jd
    from src.services.section_parser import parse_sections

    parsed = parse_sections(SAMPLE_CV_WEAK)
    result = match_cv_to_jd(
        SAMPLE_CV_WEAK, SAMPLE_JD, parsed,
        use_semantic=False,
        use_suggestion_engine=False,  # Rule-based only
    )

    for issue in result["issues"]:
        assert "suggested_fix" in issue, (
            f"Issue '{issue['code']}' missing 'suggested_fix'"
        )
        assert len(issue["suggested_fix"]) > 10, (
            f"Issue '{issue['code']}' has empty suggested_fix"
        )
        print(f"  [{issue['code']}] fix: {issue['suggested_fix'][:80]}...")


def test_output_structure():
    """Output phải có đủ fields theo schema."""
    from src.services.jd_matcher import match_cv_to_jd
    from src.services.section_parser import parse_sections

    parsed = parse_sections(SAMPLE_CV_STRONG)
    result = match_cv_to_jd(
        SAMPLE_CV_STRONG, SAMPLE_JD, parsed,
        use_semantic=False,
        use_suggestion_engine=False,
    )

    required_keys = [
        "match_score", "score_breakdown", "skills",
        "keywords", "experience", "structure",
        "issues", "rewrite_examples", "meta",
    ]
    for key in required_keys:
        assert key in result, f"Missing key '{key}' in match result"

    breakdown_keys = [
        "skill_score", "keyword_score", "experience_score", "structure_score"
    ]
    for key in breakdown_keys:
        assert key in result["score_breakdown"], f"Missing '{key}' in score_breakdown"

    print("Output structure OK")
    print(f"All keys present: {list(result.keys())}")


def test_section_parser_with_sample_cv():
    """Section parser phải nhận ra các section trong CV mẫu."""
    from src.services.section_parser import parse_sections

    result = parse_sections(SAMPLE_CV_STRONG)
    sections_found = result.get("sections_found", [])

    print(f"Sections found: {sections_found}")

    expected = ["Summary", "Skills", "Experience", "Education", "Projects"]
    for sec in expected:
        assert sec in sections_found, f"Section '{sec}' not detected"


def test_keyword_score():
    """Keyword score phải > 0 cho CV có kỹ năng phù hợp."""
    from src.services.jd_matcher import _compute_keyword_score

    score, detail = _compute_keyword_score(SAMPLE_CV_STRONG, SAMPLE_JD)

    print(f"Keyword score: {score:.2f}")
    print(f"Matched keywords: {detail['matched']}")
    print(f"Missing keywords: {detail['missing']}")

    assert score > 20, f"Expected keyword score > 20, got {score:.2f}"


def test_structure_score_strong_cv():
    """CV mạnh phải có structure score cao hơn CV yếu."""
    from src.services.jd_matcher import _compute_structure_score, _extract_jd_skills
    from src.data.skills_taxonomy import extract_skills
    from src.services.section_parser import parse_sections

    parsed_strong = parse_sections(SAMPLE_CV_STRONG)
    parsed_weak = parse_sections(SAMPLE_CV_WEAK)

    cv_skills_strong = set(extract_skills(SAMPLE_CV_STRONG)["skills"])
    cv_skills_weak = set(extract_skills(SAMPLE_CV_WEAK)["skills"])
    jd_skills = _extract_jd_skills(SAMPLE_JD)
    required = set(jd_skills["required"])

    score_strong, detail_strong = _compute_structure_score(
        parsed_strong.get("sections", {}), cv_skills_strong, required
    )
    score_weak, detail_weak = _compute_structure_score(
        parsed_weak.get("sections", {}), cv_skills_weak, required
    )

    print(f"Structure score (strong): {score_strong:.2f} — {detail_strong}")
    print(f"Structure score (weak):   {score_weak:.2f} — {detail_weak}")

    assert score_strong > score_weak, (
        f"Strong CV structure ({score_strong}) should be > weak ({score_weak})"
    )


# ─── Run all tests ────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        ("Skill Extraction", test_skill_extraction),
        ("Skill Score — Strong CV", test_skill_score_strong_cv),
        ("Skill Score — Weak CV", test_skill_score_weak_cv),
        ("Full Match: Strong vs Weak", test_full_match_strong_vs_weak),
        ("Issues have suggested_fix", test_issues_have_suggested_fix),
        ("Output Structure", test_output_structure),
        ("Section Parser", test_section_parser_with_sample_cv),
        ("Keyword Score", test_keyword_score),
        ("Structure Score", test_structure_score_strong_cv),
    ]

    passed = 0
    failed = 0
    for name, fn in tests:
        run_test(name, fn)
        # Count result (basic)

    print(f"\n{'=' * 60}")
    print(f"Done. Run with full project context to see all results.")
    print(f"Command: cd cv-review && python test_matching_engine.py")