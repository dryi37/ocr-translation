from __future__ import annotations

from typing import Any
from paddleocr import PaddleOCR, LayoutDetection

from utils import normalize_bbox, has_intersection, sort_lines_reading_order, merge_hyphenated_lines


# Model loaders
def build_ocr_engine() -> PaddleOCR:
    return PaddleOCR(
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=True,
    )


def build_layout_engine(model_name: str = "PP-DocLayout_plus-L") -> LayoutDetection:
    return LayoutDetection(model_name=model_name)


# Label mapping
def map_block_type(label: str) -> int:
    """
    0 = text
    1 = figure/image
    2 = table
    3 = chart
    """
    label = str(label).lower()

    label2type = {
        "text": 0,
        "title": 0,
        "paragraph_title": 0,
        "header": 0,
        "footer": 0,
        "caption": 0,
        "reference": 0,
        "equation": 0,
        "formula": 0,
        "list": 0,
        "figure_caption": 0,

        "figure": 1,
        "image": 1,
        "picture": 1,

        "table": 2,

        "chart": 3,
    }

    return int(label2type.get(label, 0))


# OCR / Layout
def run_ocr(
    image_path: str,
    ocr_engine: PaddleOCR,
    page_no: int = 1,
) -> list[dict[str, Any]]:
    ocr_result = ocr_engine.predict(image_path)
    ocr_lines = []

    for _, page in enumerate(ocr_result, start=1):
        boxes = page.get("rec_boxes", [])
        texts = page.get("rec_texts", [])
        scores = page.get("rec_scores", [])

        for i, (box, text, score) in enumerate(zip(boxes, texts, scores), start=1):
            bbox = normalize_bbox(box)
            clean_text = str(text).strip()

            if not clean_text:
                continue

            ocr_lines.append({
                "line_id": f"p{page_no}_l{i}",
                "page": page_no,
                "bbox": bbox,
                "text": clean_text,
                "score": float(score),
            })

    return ocr_lines


def run_layout(
    image_path: str,
    layout_engine: LayoutDetection,
) -> list[dict[str, Any]]:
    layout_result = list(
        layout_engine.predict(
            image_path,
            batch_size=1,
            layout_nms=True,
        )
    )

    if not layout_result:
        return []

    layout_page = layout_result[0]
    layout_data = layout_page.get("res", layout_page)
    return layout_data.get("boxes", [])


def filter_text_res(
    text_res: list[dict[str, Any]],
    region_bbox: list[int],
) -> list[dict[str, Any]]:
    """
    Giữ các line OCR có bbox giao với bbox của layout block.
    """
    res = []
    for line in text_res:
        text_bbox = line["bbox"]
        if has_intersection(region_bbox, text_bbox):
            res.append(line)
    return res


# Main parser
def parse_image(
    image_path: str,
    ocr_engine: PaddleOCR | None = None,
    layout_engine: LayoutDetection | None = None,
    page_no: int = 1,
) -> list[dict[str, Any]]:
    if ocr_engine is None:
        ocr_engine = build_ocr_engine()

    if layout_engine is None:
        layout_engine = build_layout_engine()

    # OCR toàn trang
    text_res = run_ocr(
        image_path=image_path,
        ocr_engine=ocr_engine,
        page_no=page_no,
    )

    # Layout toàn trang
    layout_boxes = run_layout(
        image_path=image_path,
        layout_engine=layout_engine,
    )

    # sort layout theo thứ tự đọc cơ bản
    layout_boxes = sorted(
        layout_boxes,
        key=lambda b: (b["coordinate"][1], b["coordinate"][0]),
    )

    outputs: list[dict[str, Any]] = []
    text_counter = 1
    figure_counter = 1

    # Với mỗi block layout, filter line theo intersection
    for block in layout_boxes:
        bbox = normalize_bbox(block["coordinate"])
        label = str(block.get("label", "text")).lower()
        block_type = map_block_type(label)

        if block_type == 0:
            region_lines = filter_text_res(text_res, bbox)
            region_lines = sort_lines_reading_order(region_lines)

            texts = [ln["text"] for ln in region_lines]
            merged_text = merge_hyphenated_lines(texts)

            if merged_text:
                outputs.append({
                    "page": page_no,
                    "block_id": f"blk{text_counter}",
                    "bbox": bbox,
                    "text": merged_text,
                    "block_type": 0,
                    "source": "ocr"
                })
                text_counter += 1

        else:
            outputs.append({
                "page": page_no,
                "block_id": f"fig{figure_counter}",
                "bbox": bbox,
                "text": "",
                "block_type": int(block_type),
                "source": "ocr"
            })
            figure_counter += 1

    return outputs