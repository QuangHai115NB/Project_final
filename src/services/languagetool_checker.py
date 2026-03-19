# src/services/languagetool_checker.py

from typing import Dict, Any

try:
    import language_tool_python
except Exception:
    language_tool_python = None


def check_english_language(text: str, max_chars: int = 7000, max_issues: int = 15) -> Dict[str, Any]:
    if not text or not text.strip():
        return {
            "status": "empty",
            "score": 0.0,
            "issue_count": 0,
            "issues": [],
            "warning": "Empty CV text"
        }

    if language_tool_python is None:
        return {
            "status": "unavailable",
            "score": 100.0,
            "issue_count": 0,
            "issues": [],
            "warning": "language_tool_python is not installed"
        }

    sample = text[:max_chars]

    try:
        tool = language_tool_python.LanguageTool("en-US")
        matches = tool.check(sample)

        issues = []
        for match in matches:
            issue_type = getattr(match, "ruleIssueType", "")
            if issue_type not in {"misspelling", "grammar", "typographical"}:
                continue

            issues.append({
                "message": match.message,
                "issue_type": issue_type,
                "context": match.context,
                "offset": match.offset,
                "error_length": match.errorLength,
                "replacements": list(match.replacements[:5]),
            })

            if len(issues) >= max_issues:
                break

        score = max(0.0, 100.0 - len(issues) * 3.5)

        return {
            "status": "ok",
            "score": round(score, 2),
            "issue_count": len(issues),
            "issues": issues,
        }

    except Exception as exc:
        return {
            "status": "error",
            "score": 100.0,
            "issue_count": 0,
            "issues": [],
            "warning": str(exc),
        }