# ──────────────────────────────────────────────
# roi_utils.py  —  ROI / 프레임 관련 유틸리티
# ──────────────────────────────────────────────

import cv2
import tempfile
import os
import numpy as np
from typing import Optional, Tuple


def extract_first_frame(video_path: str) -> Optional[np.ndarray]:
    """
    영상 파일에서 첫 번째 프레임을 BGR numpy 배열로 반환한다.
    실패 시 None 반환.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None
    ret, frame = cap.read()
    cap.release()
    if not ret:
        return None
    return frame


def get_video_fps(video_path: str) -> float:
    """영상 FPS 반환. 읽기 실패 또는 0이면 30.0 으로 fallback."""
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    if not fps or fps <= 0:
        fps = 30.0
    return fps


def save_uploaded_video(uploaded_file) -> str:
    """
    Streamlit UploadedFile 을 임시 파일로 저장하고 경로를 반환한다.
    """
    suffix = os.path.splitext(uploaded_file.name)[-1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.read())
        return tmp.name


def convert_canvas_rect_to_original(
    obj: dict,
    canvas_width: int,
    canvas_height: int,
    orig_width: int,
    orig_height: int,
) -> Optional[Tuple[int, int, int, int]]:
    """
    streamlit-drawable-canvas 에서 반환된 rect 객체를
    원본 영상 좌표계로 변환한다.

    Parameters
    ----------
    obj          : canvas JSON 오브젝트 (type == 'rect')
    canvas_*     : canvas 표시 크기
    orig_*       : 원본 영상 크기

    Returns
    -------
    (x1, y1, x2, y2) in original image coordinates, or None if invalid.
    """
    try:
        # canvas 좌표 (left, top, width, height)
        left   = obj.get("left",   0)
        top    = obj.get("top",    0)
        width  = obj.get("width",  0)
        height = obj.get("height", 0)

        # scaleX / scaleY 가 있으면 반영
        scale_x = obj.get("scaleX", 1.0)
        scale_y = obj.get("scaleY", 1.0)
        width  *= scale_x
        height *= scale_y

        if width < 5 or height < 5:
            return None  # 너무 작은 rect 는 무시

        # canvas → 원본 비율
        rx = orig_width  / canvas_width
        ry = orig_height / canvas_height

        x1 = int(left          * rx)
        y1 = int(top           * ry)
        x2 = int((left + width)  * rx)
        y2 = int((top + height)  * ry)

        # 범위 클리핑
        x1 = max(0, min(x1, orig_width  - 1))
        y1 = max(0, min(y1, orig_height - 1))
        x2 = max(0, min(x2, orig_width  - 1))
        y2 = max(0, min(y2, orig_height - 1))

        if x2 <= x1 or y2 <= y1:
            return None

        return (x1, y1, x2, y2)
    except Exception:
        return None


def get_box_center(xyxy) -> Tuple[int, int]:
    """bbox (x1,y1,x2,y2) 의 중심점 반환."""
    x1, y1, x2, y2 = xyxy
    return int((x1 + x2) / 2), int((y1 + y2) / 2)


def is_center_inside_roi(
    cx: int, cy: int, roi: Tuple[int, int, int, int]
) -> bool:
    """중심점이 ROI 내부에 있으면 True."""
    rx1, ry1, rx2, ry2 = roi
    return rx1 < cx < rx2 and ry1 < cy < ry2