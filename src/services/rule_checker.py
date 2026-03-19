import re

def check_missing_sections(sections: dict) -> list:
    """
    Kiểm tra các section thiếu trong CV.
    Trả về danh sách các section thiếu.
    """
    required_sections = ["Summary", "Skills", "Experience", "Education"]
    missing = [sec for sec in required_sections if sec not in sections]
    return missing

def check_generic_phrases(text: str) -> list:
    """
    Kiểm tra xem CV có sử dụng các cụm từ chung chung như "hard-working", "team player".
    Trả về danh sách các cụm từ chung chung nếu có.
    """
    generic_phrases = ["hard-working", "team player", "responsible", "fast learner", "good communication"]
    found_phrases = [phrase for phrase in generic_phrases if phrase in text.lower()]
    return found_phrases

def check_cv_length(text: str) -> str:
    """
    Kiểm tra độ dài CV.
    Nếu CV quá ngắn (dưới 250 từ) hoặc quá dài (trên 1000 từ) sẽ cảnh báo.
    """
    word_count = len(text.split())
    if word_count < 250:
        return "Too short"
    elif word_count > 1000:
        return "Too long"
    return "Normal"
def run_rule_checks(text: str, parsed_sections: dict) -> dict:
    """
    Hàm này chạy tất cả các kiểm tra cho CV: thiếu mục, cụm từ chung chung, độ dài CV
    Trả về báo cáo lỗi cho CV
    """
    missing_sections = check_missing_sections(parsed_sections)
    generic_phrases = check_generic_phrases(text)
    cv_length = check_cv_length(text)

    return {
        "missing_sections": missing_sections,
        "generic_phrases": generic_phrases,
        "cv_length": cv_length
    }