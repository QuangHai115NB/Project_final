from __future__ import annotations

import io
import os
import re
from datetime import datetime
from html import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


COLOR_PRIMARY = colors.HexColor("#2563EB")
COLOR_SUCCESS = colors.HexColor("#10B981")
COLOR_WARNING = colors.HexColor("#F59E0B")
COLOR_DANGER = colors.HexColor("#EF4444")
COLOR_TEXT = colors.HexColor("#1F2937")
COLOR_MUTED = colors.HexColor("#6B7280")
COLOR_LINE = colors.HexColor("#E5E7EB")
HIGHLIGHT_BG = {
    "red": colors.HexColor("#FEE2E2"),
    "amber": colors.HexColor("#FEF3C7"),
    "blue": colors.HexColor("#DBEAFE"),
    "green": colors.HexColor("#DCFCE7"),
}


def _register_font() -> str:
    candidates = [
        os.getenv("REPORT_PDF_FONT_PATH", ""),
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\calibri.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        if path and os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont("CVReportFont", path))
                return "CVReportFont"
            except Exception:
                continue
    return "Helvetica"


FONT_NAME = _register_font()


def _score_color(score: float):
    if score >= 70:
        return COLOR_SUCCESS
    if score >= 55:
        return COLOR_WARNING
    return COLOR_DANGER


def _normalize_report_text(value) -> str:
    text = str(value or "")
    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2022": "-",
        "\u25cf": "-",
        "\u25aa": "-",
        "\u00a0": " ",
        "\t": " ",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    text = re.sub(r"\.{3,}", "...", text)
    text = re.sub(r"[ \f\r\v]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"([,.;:!?])(?=[^\s\]\)\}])", r"\1 ", text)
    text = re.sub(r"([\(\[\{])\s+", r"\1", text)
    text = re.sub(r"\s+([\)\]\}])", r"\1", text)
    text = re.sub(r"\s*/\s*", " / ", text)
    text = re.sub(r"\s+-\s+", " - ", text)
    text = re.sub(r"\.\s+\.\s+\.", "...", text)
    text = re.sub(r" {2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return _balance_report_punctuation(text.strip())


def _balance_report_punctuation(text: str) -> str:
    pairs = {
        "(": ")",
        "[": "]",
        "{": "}",
    }
    closing_to_opening = {closing: opening for opening, closing in pairs.items()}
    output = []
    stack = []

    for char in text:
        if char in pairs:
            stack.append(char)
            output.append(char)
            continue
        if char in closing_to_opening:
            expected_opening = closing_to_opening[char]
            if stack and stack[-1] == expected_opening:
                stack.pop()
                output.append(char)
            elif expected_opening in stack:
                while stack and stack[-1] != expected_opening:
                    output.append(pairs[stack.pop()])
                if stack:
                    stack.pop()
                    output.append(char)
            else:
                continue
            continue
        output.append(char)

    while stack:
        output.append(pairs[stack.pop()])

    balanced = "".join(output)
    if balanced.count('"') % 2 == 1:
        balanced += '"'
    if balanced.count("'") % 2 == 1 and re.search(r"\s'[^']*$|^'[^']*$", balanced):
        balanced += "'"
    return balanced


def _safe_text(value) -> str:
    return escape(_normalize_report_text(value).replace("\n", "<br/>"))


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title",
            parent=base["Title"],
            fontName=FONT_NAME,
            fontSize=22,
            leading=26,
            textColor=COLOR_PRIMARY,
            alignment=TA_CENTER,
            spaceAfter=8,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=base["Normal"],
            fontName=FONT_NAME,
            fontSize=10,
            leading=14,
            textColor=COLOR_MUTED,
            alignment=TA_CENTER,
            spaceAfter=16,
        ),
        "heading": ParagraphStyle(
            "Heading",
            parent=base["Heading2"],
            fontName=FONT_NAME,
            fontSize=14,
            leading=18,
            textColor=COLOR_TEXT,
            spaceBefore=12,
            spaceAfter=8,
        ),
        "normal": ParagraphStyle(
            "NormalCV",
            parent=base["Normal"],
            fontName=FONT_NAME,
            fontSize=9.5,
            leading=13,
            textColor=COLOR_TEXT,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=base["Normal"],
            fontName=FONT_NAME,
            fontSize=8,
            leading=11,
            textColor=COLOR_MUTED,
        ),
        "issue": ParagraphStyle(
            "Issue",
            parent=base["Normal"],
            fontName=FONT_NAME,
            fontSize=9,
            leading=12,
            textColor=COLOR_TEXT,
        ),
    }


def _paragraph(text, style):
    return Paragraph(_safe_text(text), style)


def _add_meta(story, styles, summary: dict, generated_at: str) -> None:
    rows = [
        ["CV", summary.get("cv_title") or "N/A"],
        ["JD", summary.get("jd_title") or "N/A"],
        ["Generated", generated_at],
    ]
    table = Table(
        [[_paragraph(left, styles["normal"]), _paragraph(right, styles["normal"])] for left, right in rows],
        colWidths=[3.2 * cm, 13.5 * cm],
    )
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, COLOR_LINE),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EFF6FF")),
        ("TEXTCOLOR", (0, 0), (0, -1), COLOR_PRIMARY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(table)
    story.append(Spacer(1, 10))


def _add_score(story, styles, summary: dict) -> None:
    final_score = float(summary.get("final_score", 0) or 0)
    score_style = ParagraphStyle(
        "Score",
        parent=styles["title"],
        fontSize=28,
        leading=32,
        textColor=_score_color(final_score),
    )
    label = summary.get("label") or ""
    story.append(_paragraph(f"{final_score:.0f}/100", score_style))
    if label:
        story.append(_paragraph(label, styles["subtitle"]))
    story.append(Spacer(1, 8))


def _add_reading_guide(story, styles) -> None:
    story.append(_paragraph("Cách đọc báo cáo", styles["heading"]))
    rows = [
        ["1", "Xem điểm tổng và bảng điểm để biết nhóm nào đang yếu."],
        ["2", "Xem CV đã đánh dấu để thấy những dòng CV đang được gắn với khuyến nghị."],
        ["3", "Trong mỗi lỗi, đọc theo thứ tự: Thay vì / Đang có -> Bạn nên viết -> Vì sao cần sửa."],
        ["4", "Các câu gợi ý bằng tiếng Anh chỉ là mẫu. Hãy thay placeholder bằng kinh nghiệm thật của bạn."],
    ]
    table = Table(
        [[_paragraph(left, styles["normal"]), _paragraph(right, styles["normal"])] for left, right in rows],
        colWidths=[1.0 * cm, 15.7 * cm],
    )
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, COLOR_LINE),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EFF6FF")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(table)
    story.append(Spacer(1, 8))


def _pdf_explanation_text(explanations: dict, key: str) -> str:
    item = explanations.get(key, {}) if explanations else {}
    reasons = item.get("reasons_vi", []) or item.get("reasons_en", [])
    if not reasons:
        return "-"
    return " ".join(str(reason) for reason in reasons[:2])


def _add_breakdown(story, styles, breakdown: dict, weights: dict, explanations: dict | None = None) -> None:
    rows = [["Nhom danh gia", "Diem", "Trong so", "Vi sao bi tru diem"]]
    for label, key in [
        ("Cau truc CV", "section_score"),
        ("Muc dap ung ky nang", "skill_score"),
        ("Muc khop ngu nghia", "semantic_score"),
        ("Tu khoa ky thuat", "keyword_score"),
        ("Thoi luong kinh nghiem", "experience_score"),
        ("Chat luong bang chung", "jd_structure_score"),
    ]:
        if key not in breakdown and key not in weights:
            continue
        rows.append([
            label,
            f"{float(breakdown.get(key, 0) or 0):.0f}/100",
            f"{float(weights.get(key, 0) or 0):.0f}%" if key in weights else "-",
            _pdf_explanation_text(explanations or {}, key),
        ])

    story.append(_paragraph("Bang diem co trong so", styles["heading"]))
    table = Table(
        [[_paragraph(cell, styles["normal"]) for cell in row] for row in rows],
        colWidths=[4.5 * cm, 2.4 * cm, 2.2 * cm, 7.3 * cm],
    )
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, COLOR_LINE),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(table)

def _add_skills_summary(story, styles, skills_summary: dict) -> None:
    if not skills_summary:
        return

    matched = skills_summary.get("matched_required", []) or []
    missing = skills_summary.get("missing_required", []) or []
    columns = []
    if matched:
        columns.append(("Kỹ năng bắt buộc đã có", matched, colors.white))
    if missing:
        columns.append(("Kỹ năng bắt buộc còn thiếu", missing, colors.HexColor("#FEE2E2")))
    if not columns:
        return

    story.append(_paragraph("Tổng quan kỹ năng", styles["heading"]))

    rows = [[column[0] for column in columns]]
    max_rows = max(len(column[1]) for column in columns)
    for index in range(max_rows):
        rows.append([
            column[1][index] if index < len(column[1]) else ""
            for column in columns
        ])

    col_width = 16.4 * cm / len(columns)

    table = Table(
        [[_paragraph(cell, styles["normal"]) for cell in row] for row in rows],
        colWidths=[col_width for _ in columns],
    )
    table_style = [
        ("GRID", (0, 0), (-1, -1), 0.5, COLOR_LINE),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    for index, (_, _, background) in enumerate(columns):
        if background != colors.white:
            table_style.append(("BACKGROUND", (index, 1), (index, -1), background))
    table.setStyle(TableStyle(table_style))
    story.append(table)


def _annotation_lookup(structured_cv: dict) -> dict:
    return {
        annotation["id"]: annotation
        for annotation in structured_cv.get("annotations", []) or []
        if annotation.get("id")
    }


def _add_structured_cv(story, styles, structured_cv: dict) -> None:
    if not structured_cv:
        return

    story.append(PageBreak())
    story.append(_paragraph("CV đã đánh dấu", styles["heading"]))
    story.append(_paragraph(
        "Các dòng được tô màu là những phần CV có liên quan trực tiếp đến khuyến nghị.",
        styles["small"],
    ))
    story.append(Spacer(1, 8))

    annotations_by_id = _annotation_lookup(structured_cv)
    for section in structured_cv.get("sections", []) or []:
        story.append(_paragraph(section.get("name", "CV"), styles["heading"]))
        for item in section.get("items", []) or []:
            item_annotations = [
                annotations_by_id[item_id]
                for item_id in item.get("annotations", []) or []
                if item_id in annotations_by_id
            ]
            tone = item_annotations[0].get("tone") if item_annotations else ""
            bg = HIGHLIGHT_BG.get(tone, colors.white)
            marker = "- " if item.get("type") == "bullet" else ""
            text = marker + item.get("text", "")
            note = ""
            if item_annotations:
                labels = ", ".join(a.get("issue_code", "issue") for a in item_annotations[:3])
                note = f"<br/><font color='#6B7280'>Liên quan: {escape(labels)}</font>"

            table = Table(
                [[Paragraph(_safe_text(text) + note, styles["normal"])]],
                colWidths=[16.4 * cm],
            )
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), bg),
                ("BOX", (0, 0), (-1, -1), 0.4, COLOR_LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(table)
            story.append(Spacer(1, 3))


def _add_issues(story, styles, issues: list[dict]) -> None:
    if not issues:
        return

    story.append(PageBreak())
    story.append(_paragraph("Vấn đề và khuyến nghị", styles["heading"]))
    for issue in issues:
        severity = issue.get("severity", "low")
        bg = {
            "high": colors.HexColor("#FEE2E2"),
            "medium": colors.HexColor("#FEF3C7"),
            "low": colors.HexColor("#F3F4F6"),
        }.get(severity, colors.HexColor("#F3F4F6"))
        title = issue.get("title") or issue.get("code", "Issue")
        explanation = issue.get("explanation_en") or issue.get("explanation") or ""
        suggestion = issue.get("suggested_fix_en") or issue.get("suggested_fix") or ""
        rewrite = issue.get("optional_rewrite") or ""
        rewrite_meaning = issue.get("optional_rewrite_meaning_en") or issue.get("optional_rewrite_meaning_vi") or ""
        evidence = issue.get("evidence") or issue.get("details") or []
        content = [
            _paragraph(f"{severity.upper()} - {title}", styles["issue"]),
        ]
        if evidence:
            evidence_text = "; ".join(
                str(item.get("excerpt") or item.get("jd_line") or item)
                if isinstance(item, dict) else str(item)
                for item in evidence[:4]
            )
            content.append(Paragraph(
                f"<b>Thay vì / Đang có:</b> {_safe_text(evidence_text)}",
                styles["small"],
            ))
        if rewrite:
            content.append(Paragraph(
                f"<b>Bạn nên viết:</b> {_safe_text(rewrite)}",
                styles["issue"],
            ))
        elif suggestion:
            content.append(Paragraph(
                f"<b>Bạn nên sửa theo hướng:</b> {_safe_text(suggestion)}",
                styles["issue"],
            ))
        if explanation:
            content.append(Paragraph(
                f"<b>Vì sao cần sửa:</b> {_safe_text(explanation)}",
                styles["small"],
            ))
        if suggestion and rewrite:
            content.append(Paragraph(
                f"<b>Ghi chú:</b> {_safe_text(suggestion)}",
                styles["small"],
            ))
        if rewrite_meaning:
            content.append(Paragraph(
                f"<b>Cách dùng câu gợi ý:</b> {_safe_text(rewrite_meaning)}",
                styles["small"],
            ))

        table = Table([[content]], colWidths=[16.4 * cm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), bg),
            ("BOX", (0, 0), (-1, -1), 0.4, COLOR_LINE),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(KeepTogether(table))
        story.append(Spacer(1, 6))


def _add_rewrite_examples(story, styles, examples: list[dict]) -> None:
    if not examples:
        return

    story.append(PageBreak())
    story.append(_paragraph("Mẫu viết lại", styles["heading"]))
    story.append(_paragraph(
        "Dùng các mẫu này để viết lại CV. Chỉ giữ những chi tiết đúng với kinh nghiệm thật của bạn.",
        styles["small"],
    ))
    story.append(Spacer(1, 6))
    for example in examples[:5]:
        target = example.get("target_section") or "CV"
        label = example.get("label") or "Rewrite example"
        template = example.get("template") or ""
        meaning = example.get("meaning_en") or example.get("meaning_vi") or ""
        content = [
            _paragraph(f"{target} - {label}", styles["issue"]),
            _paragraph(template, styles["normal"]),
        ]
        if meaning:
            content.append(_paragraph(f"Vì sao mẫu này hiệu quả: {meaning}", styles["small"]))
        table = Table([[content]], colWidths=[16.4 * cm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EFF6FF")),
            ("BOX", (0, 0), (-1, -1), 0.4, COLOR_LINE),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(KeepTogether(table))
        story.append(Spacer(1, 6))


def generate_match_report_pdf(match_record, report_json: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        title="CV Reviewer Report",
    )
    styles = _styles()
    story = []

    summary = report_json.get("summary", {})
    generated_at = (
        match_record.created_at.strftime("%B %d, %Y %H:%M")
        if getattr(match_record, "created_at", None)
        else datetime.now().strftime("%B %d, %Y %H:%M")
    )

    story.append(_paragraph("Báo cáo CV Reviewer", styles["title"]))
    story.append(_paragraph("Tóm tắt đánh giá mức độ phù hợp CV với JD", styles["subtitle"]))
    _add_meta(story, styles, summary, generated_at)
    _add_reading_guide(story, styles)
    _add_score(story, styles, summary)
    _add_breakdown(
        story,
        styles,
        report_json.get("score_breakdown", {}),
        report_json.get("score_weights", {}),
        report_json.get("score_explanations", {}),
    )
    _add_skills_summary(story, styles, report_json.get("skills_summary", {}))
    _add_structured_cv(story, styles, report_json.get("structured_cv", {}))
    _add_issues(story, styles, report_json.get("issues", []))
    _add_rewrite_examples(story, styles, report_json.get("rewrite_examples", []))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()
