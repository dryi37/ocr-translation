import fitz
import statistics

def normalize_text(text: str) -> str:
    if text is None:
        return ""
    return " ".join(str(text).split())

def extract_lines_from_block(block, page_no):
    lines_out = []

    for line in block.get("lines", []):
        bbox = line.get("bbox", None)
        if bbox is None:
            continue

        text = "".join(span.get("text", "") for span in line.get("spans", [])).strip()
        text = normalize_text(text)
        if not text:
            continue

        lines_out.append({
            "page": page_no,
            "bbox": [float(v) for v in bbox],
            "text": text,
        })

    return lines_out

def split_block_by_indent(lines, indent_thresh=8):
    if not lines:
        return []

    lines = sorted(lines, key=lambda x: (x["bbox"][1], x["bbox"][0]))
    body_left = statistics.median_low([l["bbox"][0] for l in lines])

    paragraphs = []
    current = [lines[0]]

    for i in range(1, len(lines)):
        prev = current[-1]
        cur = lines[i]

        prev_x0, prev_y0, prev_x1, prev_y1 = prev["bbox"]
        cur_x0, cur_y0, cur_x1, cur_y1 = cur["bbox"]

        indent = cur_x0 - body_left

        if indent > indent_thresh and prev_y1 != cur_y1:
            paragraphs.append(current)
            current = [cur]
        else:
            current.append(cur)

    paragraphs.append(current)

    blocks_out = []
    for para in paragraphs:
        y0 = min(l["bbox"][1] for l in para)
        y1 = max(l["bbox"][3] for l in para)
        x1 = max(l["bbox"][2] for l in para)
        text = " ".join(l["text"] for l in para)

        blocks_out.append({
            "bbox": [float(body_left), float(y0), float(x1), float(y1)],
            "text": text,
            "num_lines": len(para),
            "lines": para,
        })

    return blocks_out

def parse_pdf(
    pdf_path,
    indent_thresh=8,
    min_lines_to_split=4
):
    doc = fitz.open(pdf_path)
    results = []

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        page_no = page_idx + 1
        data = page.get_text("dict")

        text_counter = 0
        figure_counter = 0

        for block in data.get("blocks", []):
            block_type = block.get("type", None)
            bbox = block.get("bbox", None)

            if bbox is None:
                continue

            bbox = [float(v) for v in bbox]

            # Text block
            if block_type == 0:
                lines = extract_lines_from_block(block, page_no)
                if not lines:
                    continue

                text_counter += 1
                raw_text = " ".join(line["text"] for line in lines)

                # Chỉ split nếu block có từ 4 dòng trở lên
                if len(lines) < min_lines_to_split:
                    results.append({
                        "page": page_no,
                        "block_id": f"blk{text_counter}",
                        "bbox": bbox,
                        "text": raw_text,
                        "block_type": 0,
                        "source": "pdf"
                    })
                    continue

                split_blocks = split_block_by_indent(
                    lines,
                    indent_thresh=indent_thresh
                )

                # Nếu split xong vẫn chỉ ra 1 block thì giữ như block thường
                if len(split_blocks) == 1:
                    sb = split_blocks[0]
                    results.append({
                        "page": page_no,
                        "block_id": f"blk{text_counter}",
                        "bbox": sb["bbox"],
                        "text": sb["text"],
                        "block_type": 0,
                        "source": "pdf"
                    })
                else:
                    for j, sb in enumerate(split_blocks, start=1):
                        results.append({
                            "page": page_no,
                            "block_id": f"blk{text_counter}_split{j}",
                            "bbox": sb["bbox"],
                            "text": sb["text"],
                            "block_type": 0,
                            "source": "pdf"
                        })

            # Non-text block
            else:
                figure_counter += 1
                results.append({
                    "page": page_no,
                    "block_id": f"fig{figure_counter}",
                    "bbox": bbox,
                    "text": "",
                    "block_type": int(block_type),
                    "source": "pdf"
                })

    doc.close()

    return results

