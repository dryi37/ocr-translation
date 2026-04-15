from typing import Any

# Geometry helpers
def normalize_bbox(box: Any) -> list[int]:
    if box is None:
        return [0, 0, 0, 0]

    vals = list(map(float, box))
    if len(vals) < 4:
        return [0, 0, 0, 0]

    x1, y1, x2, y2 = vals[:4]
    x1, x2 = min(x1, x2), max(x1, x2)
    y1, y2 = min(y1, y2), max(y1, y2)

    return [x1, y1, x2, y2]


def has_intersection(box1: list[int], box2: list[int]) -> bool:
    if box1[0] >= box2[2] or box2[0] >= box1[2]:
        return False
    if box1[1] >= box2[3] or box2[1] >= box1[3]:
        return False
    return True

# Text helpers
def sort_lines_reading_order(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(lines, key=lambda x: (x["bbox"][1], x["bbox"][0]))


def merge_hyphenated_lines(texts: list[str]) -> str:
    merged = []

    for t in texts:
        t = t.strip()
        if not t:
            continue

        if merged and merged[-1].endswith("-"):
            merged[-1] = merged[-1][:-1] + t
        else:
            merged.append(t)

    return " ".join(merged).strip()