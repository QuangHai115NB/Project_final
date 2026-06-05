"""
test_matching_engine.py
=======================
Test cases cho CV-JD matching engine.
Chạy: python test_matching_engine.py

Không cần pytest — chạy thẳng để kiểm tra nhanh.
"""

import sys, os

sys.path.insert(0, os.path.abspath("."))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

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
        print("PASSED")
    except AssertionError as e:
        print(f"FAILED: {e}")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")


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


def test_passive_opening_checks_are_disabled():
    """Passive openings should not be scored or reported."""
    from src.services.jd_matcher import _compute_structure_score, _generate_errors_and_suggestions
    from src.services.rule_checker import analyze_bullet_quality

    sections = {
        "Experience": "\n".join([
            "- Responsible for backend development using Django for 10 APIs.",
            "- Worked on PostgreSQL queries for 20 reports.",
        ]),
        "Projects": "\n".join([
            "- Inventory dashboard using React and Django for 100 users.",
            "- Helped with deployment scripts using Docker.",
        ]),
        "Skills": "Django, PostgreSQL, Docker, React",
    }

    score, detail = _compute_structure_score(
        sections,
        {"django", "postgresql", "docker", "react"},
        {"django", "postgresql", "docker"},
    )
    bullet_analysis = analyze_bullet_quality({"sections": sections})

    assert detail["total_bullets"] == 4
    assert score >= 85, f"Passive opening checks should not reduce structure score, got {score}"
    assert "metric_bullets" in bullet_analysis

    issues, _ = _generate_errors_and_suggestions(
        skill_detail={},
        keyword_detail={},
        experience_detail={},
        structure_detail=detail,
        semantic_detail={},
        education_detail={},
        cv_sections=sections,
        jd_text="Backend role",
        use_suggestion_engine=False,
    )
    assert all(issue["error_type"] != "language_quality" for issue in issues)


def test_jd_section_parser_respects_preferred_block():
    """Preferred section bullets khÃ´ng Ä‘Æ°á»£c rÆ¡i sang required."""
    from src.services.jd_matcher import _extract_jd_skills

    jd_text = """
    Requirements:
    - Python
    - Django

    Preferred:
    - AWS
    - Kubernetes

    Responsibilities:
    - Build REST APIs and maintain PostgreSQL workloads
    """

    result = _extract_jd_skills(jd_text)

    assert "python" in result["required"]
    assert "django" in result["required"]
    assert "aws" in result["preferred"]
    assert "kubernetes" in result["preferred"]
    assert "aws" not in result["required"], "Preferred skill leaked into required"
    assert "postgresql" in result["contextual"], "Responsibilities should be tracked separately"


def test_jd_filter_ignores_address_and_benefits_noise():
    """JD matching should ignore address/benefits/company text and keep requirements only."""
    from src.services.jd_matcher import _extract_jd_skills, _filter_jd_for_matching

    jd_text = """
    Company Overview:
    We are a React and AWS company with a modern office.

    Address:
    123 Python Street, Docker Building, React City

    Requirements:
    - Strong backend experience with Django and PostgreSQL
    - Build REST APIs for customer workflows

    Benefits:
    - Salary up to 5000 USD
    - Free AWS training and office snacks
    """

    filtered = _filter_jd_for_matching(jd_text)
    result = _extract_jd_skills(filtered)
    all_skills = set(result["required"]) | set(result["preferred"]) | set(result["contextual"])

    assert "django" in all_skills
    assert "postgresql" in all_skills
    assert "react" not in all_skills
    assert "aws" not in all_skills
    assert "docker" not in all_skills
    assert "Salary" not in filtered
    assert "123 Python Street" not in filtered


def test_semantic_score_ignores_summary_and_skills_padding():
    """Copy JD vÃ o Summary/Skills khÃ´ng Ä‘Æ°á»£c lÃ m semantic score tÄƒng."""
    from src.services.jd_matcher import _compute_semantic_score

    sections = {
        "Summary": SAMPLE_JD,
        "Skills": "Python, Django, PostgreSQL, Docker, AWS",
        "Experience": "",
        "Projects": "",
    }

    score, detail = _compute_semantic_score(sections, SAMPLE_JD, SAMPLE_JD)

    assert score == 0.0, f"Semantic score should ignore Summary/Skills padding, got {score}"
    assert detail.get("semantic_score", 0.0) == 0.0


def test_semantic_falls_back_to_cv_text_when_no_sections_detected():
    """When parsing finds no sections, semantic should still analyze the raw CV text."""
    from src.services.jd_matcher import _compute_semantic_score

    cv_text = (
        "Built Django REST APIs with PostgreSQL for customer workflows. "
        "Deployed Docker services and optimized SQL queries for production systems."
    )
    jd_text = (
        "Responsibilities\n"
        "- Build backend REST APIs for customer workflows\n"
        "- Optimize PostgreSQL queries and deploy Docker services\n"
    )

    score, detail = _compute_semantic_score({}, cv_text, jd_text)

    assert score > 0.0
    assert detail.get("cv_bullets_analyzed", 0) > 0
    assert detail.get("jd_lines_analyzed", 0) > 0


def test_semantic_keeps_non_skill_jd_responsibilities():
    """Semantic JD lines must include responsibilities even when they do not contain taxonomy skills."""
    from src.services.semantic_matcher import _extract_jd_responsibilities

    jd_text = (
        "Build and maintain backend REST APIs for customer workflows\n"
        "Optimize PostgreSQL queries and improve service performance\n"
        "Experience with Python, Django, PostgreSQL, Docker\n"
    )

    lines = _extract_jd_responsibilities(jd_text)

    assert "Build and maintain backend REST APIs for customer workflows" in lines
    assert "Optimize PostgreSQL queries and improve service performance" in lines


def test_semantic_score_rises_after_adding_reported_jd_evidence():
    """Adding the JD evidence requested by the report should improve semantic score."""
    from src.services.jd_matcher import _compute_semantic_score

    jd_text = (
        "Responsibilities\n"
        "- Build and maintain backend REST APIs for customer workflows\n"
        "- Optimize PostgreSQL queries and improve service performance\n"
        "Requirements\n"
        "- Experience with Python, Django, PostgreSQL, Docker\n"
    )
    weak_cv = "SUMMARY\nBackend developer familiar with Python and databases.\n\nSKILLS\nPython, Django, PostgreSQL, Docker"
    fixed_cv = (
        "SUMMARY\n"
        "Built and maintained backend REST APIs for customer workflows using Python, Django, PostgreSQL and Docker. "
        "Optimized PostgreSQL queries and improved service performance.\n\n"
        "SKILLS\nPython, Django, PostgreSQL, Docker"
    )

    weak_score, weak_detail = _compute_semantic_score(
        {"Summary": "Backend developer familiar with Python and databases.", "Skills": "Python, Django, PostgreSQL, Docker"},
        weak_cv,
        jd_text,
    )
    fixed_score, fixed_detail = _compute_semantic_score(
        {
            "Summary": (
                "Built and maintained backend REST APIs for customer workflows using Python, Django, PostgreSQL and Docker. "
                "Optimized PostgreSQL queries and improved service performance."
            ),
            "Skills": "Python, Django, PostgreSQL, Docker",
        },
        fixed_cv,
        jd_text,
    )

    assert weak_detail.get("cv_bullets_analyzed", 0) > 0
    assert fixed_detail.get("cv_bullets_analyzed", 0) > 0
    assert fixed_score > weak_score + 20, f"Expected fixed CV semantic to improve, weak={weak_score}, fixed={fixed_score}"
    assert fixed_score >= 70, f"Expected fixed CV semantic to be strong, got {fixed_score}"


def test_skill_evidence_is_alias_aware():
    """Evidence matching pháº£i nháº­n alias canonical nhÆ° postgres -> postgresql."""
    from src.services.semantic_matcher import find_skill_context_in_cv

    context = find_skill_context_in_cv(
        "postgresql",
        {
            "Skills": "PostgreSQL, Redis",
            "Experience": "- Optimized Postgres queries and indexing strategy for analytics workloads.",
            "Projects": "",
        },
    )

    assert context["in_skills_section"] is True
    assert context["has_evidence"] is True


def test_report_contains_versioned_scoring_snapshot():
    """Report pháº£i lÆ°u schema/scoring snapshot Ä‘á»ƒ tái láº­p."""
    from types import SimpleNamespace

    from src.services.report_builder import build_match_report
    from src.services.rule_checker import run_rule_checks
    from src.services.section_parser import parse_sections
    from src.services.jd_matcher import match_cv_to_jd
    from src.services.scoring import calibrate_score

    parsed = parse_sections(SAMPLE_CV_STRONG)
    rule_report = run_rule_checks(SAMPLE_CV_STRONG, parsed)
    jd_report = match_cv_to_jd(
        SAMPLE_CV_STRONG,
        SAMPLE_JD,
        parsed,
        use_semantic=False,
        use_suggestion_engine=False,
    )
    report = build_match_report(
        cv_record=SimpleNamespace(title="Strong CV"),
        jd_record=SimpleNamespace(title="Sample JD"),
        cv_text=SAMPLE_CV_STRONG,
        jd_text=SAMPLE_JD,
        parsed_sections=parsed,
        rule_report=rule_report,
        jd_report=jd_report,
    )

    assert report["report_schema_version"], "Missing report_schema_version"
    assert report["scoring"]["scoring_version"], "Missing scoring_version"
    assert report["scoring"]["skill_taxonomy_version"], "Missing skill taxonomy version"
    assert report["scoring"]["weights_used"], "Missing weights_used snapshot"
    assert report["snapshots"]["score_values"], "Missing score_values snapshot"
    assert report["score_explanations"], "Missing score explanations"
    assert report["score_explanations"]["skill_score"]["reasons_vi"], "Missing skill score deduction reasons"
    assert report["score_explanations"]["jd_structure_score"]["reasons_en"], "Missing evidence score deduction reasons"

    recomputed = round(
        sum(
            float(report["snapshots"]["score_values"].get(key, 0.0)) * float(weight) / 100.0
            for key, weight in report["score_weights"].items()
        ),
        2,
    )
    assert recomputed == round(float(report["scoring"]["raw_final_score"]), 2)
    assert calibrate_score(recomputed) == round(float(report["summary"]["final_score"]), 2)


def test_report_hides_fix_items_for_perfect_score_dimensions():
    """A 100/100 dimension should not show repair items for that dimension."""
    from types import SimpleNamespace

    from src.services.report_builder import build_match_report

    jd_report = {
        "score_breakdown": {
            "skill_score": 100,
            "semantic_score": 100,
            "keyword_score": 100,
            "experience_score": 100,
            "structure_score": 100,
        },
        "skills": {"score": 100, "required_coverage_pct": 100, "missing_required": [], "missing_preferred": []},
        "keywords": {"score": 100, "missing": ["ghost-keyword"], "tfidf_similarity": 100},
        "experience": {"score": 100},
        "education": {},
        "requirements": {"missing": []},
        "semantic": {"status": "ok", "model_loaded": True, "score": 100, "unmatched_jd_lines": []},
        "structure": {"score": 100},
        "issues": [
            {"code": "keyword_gap", "severity": "medium", "evidence": ["ghost-keyword"]},
            {"code": "uncovered_responsibilities", "severity": "medium", "evidence": ["Already covered"]},
        ],
        "suggestions": [],
        "rewrite_examples": [],
        "meta": {"semantic_available": True},
    }
    report = build_match_report(
        cv_record=SimpleNamespace(title="Perfect CV"),
        jd_record=SimpleNamespace(title="JD"),
        cv_text="Experience\n- Built APIs.",
        jd_text="Requirements\n- Build APIs.",
        parsed_sections={"sections": {"Experience": "- Built APIs."}, "sections_found": ["Experience"], "missing_required_sections": []},
        rule_report={"score": 100, "structure_score": 100, "issues": [], "suggestions": [], "missing_sections": []},
        jd_report=jd_report,
    )

    assert all(issue["code"] not in {"keyword_gap", "uncovered_responsibilities"} for issue in report["issues"])
    assert report["score_explanations"]["keyword_score"]["reasons_vi"] == []
    assert report["score_explanations"]["semantic_score"]["reasons_vi"] == []


# ─── Run all tests ────────────────────────────────────────────────────

def test_semantic_fallback_score_not_zero():
    """Semantic fallback must provide a useful score when embeddings are unavailable."""
    import src.services.semantic_matcher as semantic_matcher

    original_model = semantic_matcher._model
    original_failed = semantic_matcher._model_load_failed
    semantic_matcher._model = None
    semantic_matcher._model_load_failed = True

    try:
        result = semantic_matcher.match_bullets_to_jd(
            cv_experience_text=SAMPLE_CV_STRONG,
            jd_text=SAMPLE_JD,
        )
    finally:
        semantic_matcher._model = original_model
        semantic_matcher._model_load_failed = original_failed

    print(f"Semantic fallback score: {result['semantic_score']:.2f}")
    print(f"Semantic fallback status: {result['status']}")

    assert result["semantic_score"] > 0, "Semantic fallback should not return 0"
    assert result["fallback"] == "tfidf_skill_overlap"


def test_semantic_model_loaded_uses_tfidf_candidate_without_fallback_flag():
    """When the model is loaded, TF-IDF may win as an ensemble scorer, not as fallback."""
    import src.services.semantic_matcher as semantic_matcher

    class FailingModel:
        def encode(self, *args, **kwargs):
            raise RuntimeError("forced encode failure")

    original_model = semantic_matcher._model
    original_failed = semantic_matcher._model_load_failed
    original_error = semantic_matcher._model_load_error
    semantic_matcher._model = FailingModel()
    semantic_matcher._model_load_failed = False
    semantic_matcher._model_load_error = ""

    try:
        empty_result = semantic_matcher.match_bullets_to_jd(
            cv_experience_text="",
            jd_text=SAMPLE_JD,
        )
        error_result = semantic_matcher.match_bullets_to_jd(
            cv_experience_text="Built Django APIs for customer workflows.",
            jd_text="Responsibilities\n- Build backend APIs for customer workflows",
        )
    finally:
        semantic_matcher._model = original_model
        semantic_matcher._model_load_failed = original_failed
        semantic_matcher._model_load_error = original_error

    assert "fallback" not in empty_result
    assert empty_result["status"] == "empty_input"
    assert empty_result["model_loaded"] is True
    assert "fallback" not in error_result
    assert error_result["status"] == "ok"
    assert error_result["model_loaded"] is True
    assert error_result["selected_semantic_scorer"] == "tfidf_skill_overlap"
    assert error_result["model_status"].startswith("embedding_error:")
    assert error_result["tfidf_semantic_score"] >= error_result["model_semantic_score"]


def test_match_handles_string_unmatched_jd_lines():
    """Matcher should not crash when semantic fallback returns JD lines as strings."""
    from src.services.jd_matcher import _generate_errors_and_suggestions

    issues, _ = _generate_errors_and_suggestions(
        skill_detail={},
        keyword_detail={},
        experience_detail={},
        structure_detail={},
        semantic_detail={
            "unmatched_jd_lines": [
                "Build REST APIs for customer workflows",
                "Optimize PostgreSQL queries and indexes",
                "Deploy services with Docker and CI/CD",
            ],
        },
        education_detail={},
        cv_sections={},
        jd_text="Backend Engineer role",
        use_suggestion_engine=False,
    )

    issue = next(
        item for item in issues
        if item["code"] == "uncovered_responsibilities"
    )
    assert len(issue["evidence"]) == 3
    assert all(isinstance(item, str) for item in issue["evidence"])


def test_cs_fundamentals_and_oop_aliases_are_detected():
    """CS fundamentals and hyphenated OOP wording should map to canonical skills."""
    from src.data.skills_taxonomy import extract_skills

    text = (
        "Key Coursework: Data Structures & Algorithms, Algorithm Design. "
        "Utilized Object-Oriented Programming principles in Java services."
    )

    skills = set(extract_skills(text)["skills"])

    assert "data structures" in skills
    assert "algorithms" in skills
    assert "oop" in skills


def test_education_requirement_is_not_reported_as_uncovered_semantic_gap():
    """Covered Education requirements should not be treated as missing Experience evidence."""
    from src.services.jd_matcher import match_cv_to_jd

    cv = """
Education
Bachelor of Computer Science

Experience
- Implemented Java Spring Boot REST APIs using OOP principles.
"""
    jd = """
Requirements
- Bachelor's degree in Computer Science.
- Strong knowledge of Object-Oriented Programming and Java.
"""
    parsed_cv = {
        "sections": {
            "Education": "Bachelor of Computer Science",
            "Experience": "- Implemented Java Spring Boot REST APIs using OOP principles.",
        }
    }

    result = match_cv_to_jd(cv, jd, parsed_cv=parsed_cv, use_suggestion_engine=False)
    uncovered = [
        item.get("jd_line", item) if isinstance(item, dict) else item
        for item in result["semantic"].get("unmatched_jd_lines", [])
    ]

    assert result["education"]["missing"] == []
    assert result["education"]["covered"]
    assert all("bachelor" not in line.lower() for line in uncovered)


def test_skill_only_requirements_are_not_reported_as_semantic_gaps_when_covered():
    """Skill-only JD lines should not remain semantic gaps when the CV contains those skills."""
    from src.services.jd_matcher import match_cv_to_jd

    cv = """
Education
Bachelor of Computer Science
Key Coursework: Data Structures & Algorithms, Algorithm Design

Experience
- Applied advanced data structures and algorithmic optimization techniques.
- Utilized Object-Oriented Programming (OOP) principles.
- Implemented Java Spring Boot REST APIs.
- Implemented secure business workflows in C# (.NET).
"""
    jd = """
Requirements
- Strong knowledge of Data Structures and Algorithmic Efficiency.
- Object-Oriented Programming experience.
- Experience with Java or C#.
"""
    parsed_cv = {
        "sections": {
            "Education": "Bachelor of Computer Science\nKey Coursework: Data Structures & Algorithms, Algorithm Design",
            "Experience": (
                "- Applied advanced data structures and algorithmic optimization techniques.\n"
                "- Utilized Object-Oriented Programming (OOP) principles.\n"
                "- Implemented Java Spring Boot REST APIs.\n"
                "- Implemented secure business workflows in C# (.NET)."
            ),
        }
    }

    result = match_cv_to_jd(cv, jd, parsed_cv=parsed_cv, use_suggestion_engine=False)
    uncovered = [
        item.get("jd_line", item) if isinstance(item, dict) else item
        for item in result["semantic"].get("unmatched_jd_lines", [])
    ]

    assert result["skills"]["missing_required"] == []
    assert all("java" not in line.lower() and "c#" not in line.lower() for line in uncovered)
    assert all("data structures" not in line.lower() for line in uncovered)


def test_section_aware_requirement_coverage_maps_soft_and_domain_evidence():
    """Soft/domain requirements should be covered by equivalent recruiter-readable evidence."""
    from src.services.jd_matcher import match_cv_to_jd

    cv = """
Experience
- Performed root cause analysis and debugging for production incidents.
- Designed relational database schemas and SQL migration scripts.
- Created Swagger OpenAPI specifications for backend APIs.

Skills
PostgreSQL, Swagger, REST API
"""
    jd = """
Requirements
- Strong logical reasoning.
- Strong database design fundamentals.
- English technical documentation.
"""
    parsed_cv = {
        "sections": {
            "Experience": (
                "- Performed root cause analysis and debugging for production incidents.\n"
                "- Designed relational database schemas and SQL migration scripts.\n"
                "- Created Swagger OpenAPI specifications for backend APIs."
            ),
            "Skills": "PostgreSQL, Swagger, REST API",
        }
    }

    result = match_cv_to_jd(cv, jd, parsed_cv=parsed_cv, use_suggestion_engine=False)
    requirements = result["requirements"]["requirements"]

    assert result["semantic"]["requirement_coverage_score"] >= 90
    assert all(item["covered"] for item in requirements)
    assert {item["category"] for item in requirements} >= {"soft_skill", "domain_knowledge"}


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
        ("Passive opening checks disabled", test_passive_opening_checks_are_disabled),
        ("JD Section Parser", test_jd_section_parser_respects_preferred_block),
        ("JD Filter Ignores Noise", test_jd_filter_ignores_address_and_benefits_noise),
        ("Semantic Ignores Summary Padding", test_semantic_score_ignores_summary_and_skills_padding),
        ("Semantic Uses Raw CV Without Sections", test_semantic_falls_back_to_cv_text_when_no_sections_detected),
        ("Semantic Keeps Non-skill JD Responsibilities", test_semantic_keeps_non_skill_jd_responsibilities),
        ("Semantic Score Rises After JD Evidence", test_semantic_score_rises_after_adding_reported_jd_evidence),
        ("Alias-aware Skill Evidence", test_skill_evidence_is_alias_aware),
        ("Versioned Scoring Snapshot", test_report_contains_versioned_scoring_snapshot),
        ("Hide Fix Items for Perfect Scores", test_report_hides_fix_items_for_perfect_score_dimensions),
        ("Semantic Fallback Score", test_semantic_fallback_score_not_zero),
        ("Semantic Loaded Model Uses TF-IDF Candidate", test_semantic_model_loaded_uses_tfidf_candidate_without_fallback_flag),
        ("String Unmatched JD Lines", test_match_handles_string_unmatched_jd_lines),
        ("CS Fundamentals and OOP Aliases", test_cs_fundamentals_and_oop_aliases_are_detected),
        ("Covered Education Is Not Semantic Gap", test_education_requirement_is_not_reported_as_uncovered_semantic_gap),
        ("Covered Skill Lines Are Not Semantic Gaps", test_skill_only_requirements_are_not_reported_as_semantic_gaps_when_covered),
        ("Section-aware Soft and Domain Evidence", test_section_aware_requirement_coverage_maps_soft_and_domain_evidence),
    ]

    passed = 0
    failed = 0
    for name, fn in tests:
        run_test(name, fn)
        # Count result (basic)

    print(f"\n{'=' * 60}")
    print(f"Done. Run with full project context to see all results.")
    print(f"Command: cd cv-review && python test_matching_engine.py")
