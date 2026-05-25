# utils/roi.py
"""
ROI(관심 구역) 관련 유틸리티
- 중심점이 ROI 내부인지 판단
- ROI 좌표 직렬화/역직렬화 (session_state 저장용)
"""


def is_inside_roi(cx: float, cy: float, roi: tuple) -> bool:
    """
    roi = (x1, y1, x2, y2)
    중심점 (cx, cy)가 ROI 내부이면 True
    """
    if roi is None:
        return False
    x1, y1, x2, y2 = roi
    return x1 < cx < x2 and y1 < cy < y2


def center_of_box(xyxy) -> tuple[float, float]:
    """xyxy → (cx, cy)"""
    x1, y1, x2, y2 = xyxy
    return (x1 + x2) / 2, (y1 + y2) / 2


def roi_to_dict(roi: tuple) -> dict:
    if roi is None:
        return {}
    return {"x1": roi[0], "y1": roi[1], "x2": roi[2], "y2": roi[3]}


def dict_to_roi(d: dict):
    if not d:
        return None
    return (d["x1"], d["y1"], d["x2"], d["y2"])
