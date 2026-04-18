"""
Word Report Generator
---------------------
Tạo file Word (.docx) từ match report JSON để user có thể tải về.

Dùng python-docx — lightweight, không cần COM/Windows-specific.

Template structure:
  1. Header: Logo placeholder + Title
  2. Overview: Score lớn + CV/JD info + date
  3. Score Breakdown: Bar chart text-based (5 layers)
  4. Skills Summary: Matched vs Missing
  5. Issues & Suggestions: Priority sorted
  6. Rewrite Examples: Before/After bullets
  7. Footer: Generated date + app info
"""

from __future__ import annotations

import io
import json
from datetime import datetime

from docx import Document
from docx.shared import (
    Cm,
    Inches,
    Pt,
    RGBColor,
    Emu,
)
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

# ── Color Palette ──────────────────────────────────────────────
COLOR_PRIMARY      = RGBColor(0x25, 0x63, 0xEB)   # Blue #2563EB
COLOR_SUCCESS      = RGBColor(0x10, 0xB9, 0x81)   # Green #10B981
COLOR_WARNING      = RGBColor(0xF5, 0x9E, 0x0B)   # Amber #F59E0B
COLOR_DANGER       = RGBColor(0xEF, 0x44, 0x44)  # Red #EF4444
COLOR_GRAY_DARK    = RGBColor(0x1F, 0x29, 0x37)   # Near black
COLOR_GRAY_MEDIUM  = RGBColor(0x6B, 0x72, 0x80)   # Medium gray
COLOR_GRAY_LIGHT   = RGBColor(0xF3, 0xF4, 0xF6)   # Light gray bg
COLOR_WHITE        = RGBColor(0xFF, 0xFF, 0xFF)   # White


# ── Helper utilities ──────────────────────────────────────────

def _set_cell_bg(cell, hex_color: str):
    """Set table cell background color."""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), hex_color)
    tcPr.append(shd)


def _set_cell_border(cell, **kwargs):
    """Set cell borders."""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = OxmlElement('w:tcBorders')
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        tag = OxmlElement(f'w:{edge}')
        tag.set(qn('w:val'), kwargs.get('val', 'single'))
        tag.set(qn('w:sz'), kwargs.get('sz', '4'))
        tag.set(qn('w:space'), '0')
        tag.set(qn('w:color'), kwargs.get('color', 'auto'))
        tcBorders.append(tag)
    tcPr.append(tcBorders)


def _paragraph_spacing(para, before=0, after=0):
    pPr = para._p.get_or_add_pPr()
    spacing = OxmlElement('w:spacing')
    spacing.set(qn('w:before'), str(before))
    spacing.set(qn('w:after'), str(after))
    pPr.append(spacing)


def _add_horizontal_rule(doc, color_hex="2563EB", thickness=12):
    """Add a colored horizontal line."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), str(thickness))
    bottom.set(qn('w:space'), '1')
    bottom.set(qn('w:color'), color_hex)
    pBdr.append(bottom)
    pPr.append(pBdr)
    return p


def _score_to_color(score: float) -> RGBColor:
    """Return color based on score range."""
    if score >= 70:
        return COLOR_SUCCESS
    elif score >= 55:
        return COLOR_WARNING
    return COLOR_DANGER


def _format_evidence_item(item) -> str:
    if isinstance(item, dict):
        location = " - ".join(
            part for part in [
                str(item.get("section", "")) if item.get("section") else "",
                f"bullet #{item.get('bullet_index')}" if item.get("bullet_index") else "",
            ]
            if part
        )
        excerpt = item.get("excerpt") or item.get("jd_line") or str(item)
        reason = item.get("reason", "")
        prefix = f"{location}: " if location else ""
        suffix = f" ({reason})" if reason else ""
        return f"{prefix}{excerpt}{suffix}"
    return str(item)


def _score_to_label(score: float) -> str:
    """Return label text based on score."""
    if score >= 85:
        return "Excellent"
    if score >= 70:
        return "Good"
    if score >= 55:
        return "Fair"
    return "Weak"


def _hex_to_rgb(hex_str: str) -> RGBColor:
    """Convert hex string to RGBColor."""
    h = hex_str.lstrip('#')
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


# ── Section builders ──────────────────────────────────────────

def _add_header(doc: Document, cv_title: str, jd_title: str, match_date: str):
    """Page header with app branding."""
    # Title
    title_para = doc.add_paragraph()
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title_para.add_run("CV REVIEWER")
    run.bold = True
    run.font.size = Pt(22)
    run.font.color.rgb = COLOR_PRIMARY
    _paragraph_spacing(title_para, before=200, after=0)

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = subtitle.add_run("📋 Match Report")
    r.font.size = Pt(14)
    r.font.color.rgb = COLOR_GRAY_MEDIUM
    _paragraph_spacing(subtitle, before=0, after=60)

    # Info table
    table = doc.add_table(rows=3, cols=2)
    table.style = 'Table Grid'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    info = [
        ("📄 CV", cv_title or "N/A"),
        ("💼 JD", jd_title or "N/A"),
        ("📅 Date", match_date),
    ]
    for i, (label, value) in enumerate(info):
        label_cell = table.rows[i].cells[0]
        value_cell = table.rows[i].cells[1]

        _set_cell_bg(label_cell, "EFF6FF")
        _set_cell_bg(value_cell, "FFFFFF")

        lp = label_cell.paragraphs[0]
        lr = lp.add_run(label)
        lr.bold = True
        lr.font.size = Pt(10)
        lr.font.color.rgb = COLOR_PRIMARY

        vp = value_cell.paragraphs[0]
        vr = vp.add_run(value)
        vr.font.size = Pt(10)
        vr.font.color.rgb = COLOR_GRAY_DARK

    # Set column widths
    table.columns[0].width = Cm(3.5)
    table.columns[1].width = Cm(11)

    doc.add_paragraph()


def _add_overall_score(doc: Document, final_score: float, label: str):
    """Big score display with color ring."""
    # Score box using table
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = table.rows[0].cells[0]

    # Background color based on score
    if final_score >= 70:
        bg = "DCFCE7"  # green light
        score_color_hex = "10B981"
    elif final_score >= 55:
        bg = "FEF3C7"  # amber light
        score_color_hex = "F59E0B"
    else:
        bg = "FEE2E2"  # red light
        score_color_hex = "EF4444"

    _set_cell_bg(cell, bg)
    cell.width = Cm(10)

    # Score paragraph
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    score_run = p.add_run(f"{final_score:.0f}")
    score_run.bold = True
    score_run.font.size = Pt(48)
    score_run.font.color.rgb = _hex_to_rgb(score_color_hex)

    p.add_run(" / 100")

    label_p = cell.add_paragraph()
    label_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    label_r = label_p.add_run(f"— {label.upper()} —")
    label_r.bold = True
    label_r.font.size = Pt(11)
    label_r.font.color.rgb = _hex_to_rgb(score_color_hex)

    doc.add_paragraph()


def _add_score_breakdown(doc: Document, breakdown: dict):
    """Text-based bar chart for 5 layers."""
    heading = doc.add_heading("📊 Score Breakdown", level=2)
    heading.runs[0].font.color.rgb = COLOR_GRAY_DARK

    scores = [
        ("Skill Coverage",   breakdown.get("skill_score", 0)),
        ("Semantic Match",   breakdown.get("semantic_score", 0)),
        ("Keyword Match",    breakdown.get("keyword_score", 0)),
        ("Experience",       breakdown.get("experience_score", 0)),
        ("Structure",        breakdown.get("jd_structure_score", breakdown.get("structure_score", 0))),
    ]

    table = doc.add_table(rows=len(scores), cols=3)
    table.style = 'Table Grid'
    table.alignment = WD_TABLE_ALIGNMENT.LEFT

    for i, (name, score) in enumerate(scores):
        name_cell = table.rows[i].cells[0]
        bar_cell  = table.rows[i].cells[1]
        score_cell = table.rows[i].cells[2]

        # Name
        name_p = name_cell.paragraphs[0]
        nr = name_p.add_run(name)
        nr.font.size = Pt(10)
        nr.bold = True
        name_cell.width = Cm(4)

        # Bar (text-based)
        bar_p = bar_cell.paragraphs[0]
        filled = int(score / 5)   # each block = 5%
        empty  = 20 - filled
        color  = _score_to_color(score)
        bar_r = bar_p.add_run("█" * filled + "░" * empty)
        bar_r.font.size = Pt(9)
        bar_r.font.color.rgb = color
        bar_cell.width = Cm(8)

        # Score value
        score_p = score_cell.paragraphs[0]
        sr = score_p.add_run(f"{score:.0f}/100")
        sr.font.size = Pt(10)
        sr.bold = True
        sr.font.color.rgb = color
        score_cell.width = Cm(2.5)

    doc.add_paragraph()


def _add_skills_summary(doc: Document, skills_summary: dict):
    """Skills matched vs missing table."""
    heading = doc.add_heading("🎯 Skills Summary", level=2)
    heading.runs[0].font.color.rgb = COLOR_GRAY_DARK

    # Required skills
    matched_req = skills_summary.get("matched_required", [])
    missing_req = skills_summary.get("missing_required", [])
    matched_pref = skills_summary.get("matched_preferred", [])
    missing_pref = skills_summary.get("missing_preferred", [])
    coverage = skills_summary.get("required_coverage_pct", 0)

    # Coverage bar
    cov_p = doc.add_paragraph()
    cov_p.add_run("Required Skills Coverage: ").bold = True
    cov_r = cov_p.add_run(f"{coverage:.0f}%")
    cov_r.bold = True
    cov_r.font.color.rgb = _score_to_color(float(coverage))

    cov_bar = doc.add_paragraph()
    filled = int(float(coverage) / 5)
    bar_color = _score_to_color(float(coverage))
    bar_r = cov_bar.add_run("█" * filled + "░" * (20 - filled))
    bar_r.font.color.rgb = bar_color
    bar_r.font.size = Pt(10)
    _paragraph_spacing(cov_bar, after=80)

    # Tables: Matched vs Missing
    if matched_req or missing_req:
        req_table = doc.add_table(rows=1 + max(len(matched_req), len(missing_req)), cols=2)
        req_table.style = 'Table Grid'

        # Header
        req_table.rows[0].cells[0].paragraphs[0].add_run("✅ Matched Required").bold = True
        req_table.rows[0].cells[1].paragraphs[0].add_run("❌ Missing Required").bold = True
        for cell in req_table.rows[0].cells:
            _set_cell_bg(cell, "DCFCE7")
            cell.paragraphs[0].runs[0].font.color.rgb = COLOR_SUCCESS
            cell.paragraphs[0].runs[0].font.size = Pt(10)

        for i in range(1, max(len(matched_req), len(missing_req)) + 1):
            if i - 1 < len(matched_req):
                req_table.rows[i].cells[0].paragraphs[0].add_run(f"• {matched_req[i-1]}").font.size = Pt(9)
            if i - 1 < len(missing_req):
                req_table.rows[i].cells[1].paragraphs[0].add_run(f"• {missing_req[i-1]}").font.size = Pt(9)
                req_table.rows[i].cells[1].paragraphs[0].runs[0].font.color.rgb = COLOR_DANGER

        req_table.columns[0].width = Cm(6.5)
        req_table.columns[1].width = Cm(7.5)

    if matched_pref or missing_pref:
        doc.add_paragraph()
        pref_table = doc.add_table(rows=1 + max(len(matched_pref), len(missing_pref)), cols=2)
        pref_table.style = 'Table Grid'

        pref_table.rows[0].cells[0].paragraphs[0].add_run("⭐ Matched Preferred").bold = True
        pref_table.rows[0].cells[1].paragraphs[0].add_run("○ Missing Preferred").bold = True
        for cell in pref_table.rows[0].cells:
            _set_cell_bg(cell, "FEF3C7")
            cell.paragraphs[0].runs[0].font.color.rgb = COLOR_WARNING
            cell.paragraphs[0].runs[0].font.size = Pt(10)

        for i in range(1, max(len(matched_pref), len(missing_pref)) + 1):
            if i - 1 < len(matched_pref):
                pref_table.rows[i].cells[0].paragraphs[0].add_run(f"• {matched_pref[i-1]}").font.size = Pt(9)
            if i - 1 < len(missing_pref):
                pref_table.rows[i].cells[1].paragraphs[0].add_run(f"○ {missing_pref[i-1]}").font.size = Pt(9)
                pref_table.rows[i].cells[1].paragraphs[0].runs[0].font.color.rgb = COLOR_WARNING

        pref_table.columns[0].width = Cm(6.5)
        pref_table.columns[1].width = Cm(7.5)

    doc.add_paragraph()


def _add_issues(doc: Document, issues: list):
    """Issues list with severity badges."""
    if not issues:
        return

    heading = doc.add_heading("⚠️ Issues & Suggestions", level=2)
    heading.runs[0].font.color.rgb = COLOR_GRAY_DARK

    severity_colors = {
        "high":   ("FEE2E2", "EF4444", "🔴 HIGH"),
        "medium": ("FEF3C7", "F59E0B", "🟡 MEDIUM"),
        "low":    ("F3F4F6", "6B7280", "🟢 LOW"),
    }

    for issue in issues:
        severity = issue.get("severity", "low")
        bg, color_hex, badge = severity_colors.get(severity, ("F3F4F6", "6B7280", "⚪ LOW"))

        title = issue.get("title", issue.get("code", "Issue"))
        explanation = issue.get("explanation", "")
        suggested_fix = issue.get("suggested_fix", "")
        evidence = issue.get("evidence", [])

        # Issue block (table for background color)
        table = doc.add_table(rows=1, cols=1)
        table.style = 'Table Grid'
        table.alignment = WD_TABLE_ALIGNMENT.LEFT
        cell = table.rows[0].cells[0]
        _set_cell_bg(cell, bg)

        p = cell.paragraphs[0]
        # Badge
        badge_run = p.add_run(f"{badge}  ")
        badge_run.bold = True
        badge_run.font.size = Pt(10)
        badge_run.font.color.rgb = _hex_to_rgb(color_hex)

        # Title
        title_run = p.add_run(title)
        title_run.bold = True
        title_run.font.size = Pt(11)
        title_run.font.color.rgb = COLOR_GRAY_DARK

        # Explanation
        if explanation:
            exp_p = cell.add_paragraph()
            exp_r = exp_p.add_run(explanation)
            exp_r.font.size = Pt(10)
            exp_r.font.color.rgb = COLOR_GRAY_DARK
            _paragraph_spacing(exp_p, before=40, after=0)

        # Evidence
        if evidence:
            ev_p = cell.add_paragraph()
            ev_r = ev_p.add_run("Evidence: " + "; ".join(_format_evidence_item(e) for e in evidence[:3]))
            ev_r.font.size = Pt(9)
            ev_r.italic = True
            ev_r.font.color.rgb = COLOR_GRAY_MEDIUM

        # Suggested fix
        if suggested_fix:
            fix_p = cell.add_paragraph()
            fix_label = fix_p.add_run("💡 Fix: ")
            fix_label.bold = True
            fix_label.font.size = Pt(10)
            fix_label.font.color.rgb = COLOR_PRIMARY
            fix_r = fix_p.add_run(suggested_fix)
            fix_r.font.size = Pt(10)
            fix_r.font.color.rgb = COLOR_GRAY_DARK

        _paragraph_spacing(cell.paragraphs[0], before=60, after=40)
        cell.add_paragraph()  # bottom padding

    doc.add_paragraph()


def _add_rewrite_examples(doc: Document, rewrite_examples: list):
    """Before/After bullet examples."""
    if not rewrite_examples:
        return

    heading = doc.add_heading("✍️ Rewrite Examples", level=2)
    heading.runs[0].font.color.rgb = COLOR_GRAY_DARK

    for i, example in enumerate(rewrite_examples[:3], 1):
        target = example.get("target_section", "Section")
        label = example.get("label", "Example")
        template = example.get("template", "")

        # Example card
        table = doc.add_table(rows=1, cols=1)
        table.style = 'Table Grid'
        cell = table.rows[0].cells[0]
        _set_cell_bg(cell, "EFF6FF")

        p = cell.paragraphs[0]
        r1 = p.add_run(f"{i}. [{target}] {label}")
        r1.bold = True
        r1.font.size = Pt(10)
        r1.font.color.rgb = COLOR_PRIMARY

        if template:
            tp = cell.add_paragraph()
            tr = tp.add_run(f"   Template: {template}")
            tr.font.size = Pt(9)
            tr.italic = True
            tr.font.color.rgb = COLOR_GRAY_MEDIUM

        cell.add_paragraph()

    doc.add_paragraph()


def _add_footer(doc: Document):
    """Report footer."""
    _add_horizontal_rule(doc, color_hex="E5E7EB", thickness=6)

    footer_p = doc.add_paragraph()
    footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    now = datetime.now().strftime("%B %d, %Y %H:%M")
    r1 = footer_p.add_run(f"Generated by CV Reviewer • {now}")
    r1.font.size = Pt(8)
    r1.font.color.rgb = COLOR_GRAY_MEDIUM

    footer_p2 = doc.add_paragraph()
    footer_p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r2 = footer_p2.add_run("This report is for reference only. Please verify information before use.")
    r2.font.size = Pt(8)
    r2.italic = True
    r2.font.color.rgb = COLOR_GRAY_MEDIUM


# ── Main entry point ───────────────────────────────────────────

def generate_match_report_docx(
    match_record,       # MatchHistory ORM object
    report_json: dict,  # Full report dict from build_match_report
) -> bytes:
    """
    Generate a Word document from a match record + report JSON.

    Args:
        match_record: MatchHistory ORM object (has cv, jd, score, created_at)
        report_json:  Full report dict returned by build_match_report()

    Returns:
        bytes — raw .docx file content (for send_file / storage)
    """
    doc = Document()

    # Page setup: A4
    section = doc.sections[0]
    section.page_height = Cm(29.7)
    section.page_width  = Cm(21)
    section.left_margin   = Cm(2)
    section.right_margin  = Cm(2)
    section.top_margin    = Cm(2)
    section.bottom_margin = Cm(2)

    # Default font
    doc.styles['Normal'].font.name = 'Calibri'
    doc.styles['Normal'].font.size = Pt(11)

    # ── Extract data from report_json ──────────────────────────────
    summary = report_json.get("summary", {})
    breakdown = report_json.get("score_breakdown", {})
    skills_summary = report_json.get("skills_summary", {})
    issues = report_json.get("issues", [])
    suggestions = report_json.get("suggestions", [])
    rewrite_examples = report_json.get("rewrite_examples", [])
    cv_checks = report_json.get("cv_checks", {})
    semantic_analysis = report_json.get("semantic_analysis", {})

    final_score = float(summary.get("final_score", 0))
    score_label = summary.get("label", _score_to_label(final_score))
    cv_title = summary.get("cv_title", "")
    jd_title = summary.get("jd_title", "")
    match_date = (
        match_record.created_at.strftime("%B %d, %Y at %H:%M")
        if match_record.created_at else datetime.now().strftime("%B %d, %Y")
    )
    total_issues = summary.get("total_issues", len(issues))

    # ── Build sections ────────────────────────────────────────────
    _add_header(doc, cv_title, jd_title, match_date)
    _add_overall_score(doc, final_score, score_label)
    _add_score_breakdown(doc, breakdown)
    _add_skills_summary(doc, skills_summary)
    _add_issues(doc, issues)
    _add_rewrite_examples(doc, rewrite_examples)

    # ── Section: CV Checks summary (optional) ─────────────────────
    if cv_checks:
        section_analysis = report_json.get("section_analysis", {})
        if section_analysis:
            cv_heading = doc.add_heading("📄 CV Structure Analysis", level=2)
            cv_heading.runs[0].font.color.rgb = COLOR_GRAY_DARK

            sections_found = section_analysis.get("sections_found", [])
            missing_req = section_analysis.get("missing_required_sections", [])

            sp = doc.add_paragraph()
            sp.add_run("Sections found: ").bold = True
            sp.add_run(", ".join(sections_found) if sections_found else "None").font.color.rgb = COLOR_SUCCESS

            if missing_req:
                mp = doc.add_paragraph()
                mp.add_run("Missing required: ").bold = True
                mr = mp.add_run(", ".join(missing_req))
                mr.font.color.rgb = COLOR_DANGER

            doc.add_paragraph()

    # ── Section: Semantic top matches ──────────────────────────────
    top_matches = semantic_analysis.get("top_matches", [])
    if top_matches:
        sem_heading = doc.add_heading("🔗 Top Semantic Matches", level=2)
        sem_heading.runs[0].font.color.rgb = COLOR_GRAY_DARK

        for m in top_matches[:3]:
            cv_bullet = m.get("cv_bullet", "")[:120]
            jd_match  = m.get("best_jd_match", "")[:120]
            score     = m.get("score", 0)

            table = doc.add_table(rows=1, cols=1)
            table.style = 'Table Grid'
            cell = table.rows[0].cells[0]
            _set_cell_bg(cell, "F0FDF4")

            p = cell.paragraphs[0]
            r1 = p.add_run(f"CV: {cv_bullet}")
            r1.font.size = Pt(9)
            r1.font.color.rgb = COLOR_GRAY_DARK

            p2 = cell.add_paragraph()
            r2 = p2.add_run(f"JD: {jd_match}")
            r2.font.size = Pt(9)
            r2.italic = True
            r2.font.color.rgb = COLOR_GRAY_MEDIUM

            p3 = cell.add_paragraph()
            r3 = p3.add_run(f"Similarity: {score:.0f}%")
            r3.bold = True
            r3.font.size = Pt(9)
            r3.font.color.rgb = COLOR_SUCCESS

        doc.add_paragraph()

    _add_footer(doc)

    # ── Serialize to bytes ─────────────────────────────────────────
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.read()
