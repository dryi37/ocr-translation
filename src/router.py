from pathlib import Path
import fitz  


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


def detect_pdf_type(
    pdf_path: str,
    sample_pages: int = 5,
    min_text_chars: int = 30,
    text_ratio_text_pdf: float = 0.8,
    text_ratio_scan_pdf: float = 0.2,
) -> str:
    doc = fitz.open(pdf_path)
    total_pages = len(doc)

    if total_pages == 0:
        raise ValueError("PDF không có trang nào.")

    pages_to_check = min(sample_pages, total_pages)
    text_pages = 0

    for page_idx in range(pages_to_check):
        page = doc[page_idx]
        text = page.get_text("text").strip()

        if len(text) >= min_text_chars:
            text_pages += 1

    ratio = text_pages / pages_to_check

    if ratio >= text_ratio_text_pdf:
        return "pdf_text"
    elif ratio <= text_ratio_scan_pdf:
        return "pdf_scan"
    else:
        return "pdf_mixed"


def detect_input_type(file_path: str) -> str:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {file_path}")

    ext = path.suffix.lower()

    if ext in IMAGE_EXTS:
        return "image"

    if ext == ".pdf":
        return detect_pdf_type(str(path))

    raise ValueError(f"Định dạng file chưa hỗ trợ: {ext}")