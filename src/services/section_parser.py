import re

SECTION_HEADERS = {
    "Summary": ["summary", "profile", "objective","professional summary", "career objective", "about me", "background", "executive summary"],
    "Skills": ["skills", "technical skills", "key skills", "competencies","technologies", "tools", "proficiencies", "areas of expertise", "hard skills", "soft skills", "technical stack"],
    "Experience": ["experience", "work experience", "employment", "projects","work history", "professional experience", "professional background", "career history", "employment history"],
    "Education": ["education", "academic", "qualification","academic background", "academic profile", "educational history", "degrees"],
    "Projects": ["projects", "personal projects", "open source", "academic projects", "selected projects", "notable projects", "github projects", "coursework projects"],
    "Certifications": ["certifications", "certificates","awards", "honors", "licenses", "professional certifications", "training"],
}


def parse_sections(text: str) -> dict:
    """
    Tách các section trong CV dựa trên các từ khóa đã định nghĩa.
    Trả về một dictionary với tên các section là key và nội dung là value.
    """
    sections = {}
    current_section = None
    section_text = []

    # Chuẩn hóa text
    text = text.lower().replace("\n", " ").strip()

    # Lặp qua các section header đã định nghĩa
    for section, headers in SECTION_HEADERS.items():
        for header in headers:
            if header in text:
                current_section = section
                section_text = []
                break

        if current_section:
            # Tìm tất cả nội dung trong section này
            start_index = text.find(current_section.lower()) + len(current_section)
            end_index = text.find(SECTION_HEADERS.get(current_section, [None])[1]) if len(SECTION_HEADERS.get(current_section)) > 1 else -1
            sections[current_section] = text[start_index:end_index].strip()
            break

    return sections