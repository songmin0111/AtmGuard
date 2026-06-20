# ──────────────────────────────────────────────
# draw_utils.py  —  OpenCV 시각화 유틸리티
# ──────────────────────────────────────────────

import cv2
import numpy as np
from typing import Tuple

from config import RISK_COLORS
from event_logic import TrackState


def draw_roi(frame: np.ndarray, roi: Tuple[int, int, int, int]) -> np.ndarray:
    """ROI 영역을 파란색 점선 사각형으로 표시한다."""
    x1, y1, x2, y2 = roi

    # 점선 효과: 짧은 선분을 반복해서 그림
    color = (255, 180, 0)  # BGR: 파란빛 하늘색
    thickness = 2
    dash_len = 12
    gap_len  = 6

    def draw_dashed_line(img, pt1, pt2):
        """두 점 사이를 점선으로 그린다."""
        x_s, y_s = pt1
        x_e, y_e = pt2
        dist = max(abs(x_e - x_s), abs(y_e - y_s), 1)
        segs = int(dist / (dash_len + gap_len))
        for i in range(segs + 1):
            t1 = i * (dash_len + gap_len) / dist
            t2 = min(1.0, t1 + dash_len / dist)
            p1 = (int(x_s + (x_e - x_s) * t1), int(y_s + (y_e - y_s) * t1))
            p2 = (int(x_s + (x_e - x_s) * t2), int(y_s + (y_e - y_s) * t2))
            cv2.line(img, p1, p2, color, thickness)

    draw_dashed_line(frame, (x1, y1), (x2, y1))  # top
    draw_dashed_line(frame, (x2, y1), (x2, y2))  # right
    draw_dashed_line(frame, (x2, y2), (x1, y2))  # bottom
    draw_dashed_line(frame, (x1, y2), (x1, y1))  # left

    # ROI 레이블
    label = "ROI - ATM"
    cv2.putText(
        frame, label,
        (x1 + 6, y1 - 8),
        cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA,
    )
    return frame


def draw_person_box(
    frame: np.ndarray,
    state: TrackState,
) -> np.ndarray:
    """
    사람 bbox 위에 Track ID / 체류시간 / 진입횟수 / 위험도를 표시한다.
    """
    x1, y1, x2, y2 = [int(v) for v in state.bbox]
    color = RISK_COLORS.get(state.risk_level, (128, 128, 128))

    # bbox
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

    # 레이블 텍스트
    dwell_str = f"{state.dwell_seconds:.1f}s"
    label = (
        f"ID #{state.track_id} | "
        f"{dwell_str} | "
        f"entry {state.entry_count} | "
        f"{state.risk_level}"
    )

    # 레이블 배경
    (tw, th), baseline = cv2.getTextSize(
        label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
    )
    label_y = max(y1 - 6, th + 4)
    cv2.rectangle(
        frame,
        (x1, label_y - th - 4),
        (x1 + tw + 4, label_y + baseline),
        color,
        cv2.FILLED,
    )
    cv2.putText(
        frame, label,
        (x1 + 2, label_y - 2),
        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA,
    )

    # Loitering 라벨
    if state.is_loitering:
        loiter_label = "! Loitering"
        cv2.putText(
            frame, loiter_label,
            (x1, y2 + 18),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2, cv2.LINE_AA,
        )

    return frame


def draw_weapon_alert(frame: np.ndarray, weapon_count: int) -> np.ndarray:
    """weapon 감지 시 화면 상단에 붉은 경고 배너를 표시한다."""
    h, w = frame.shape[:2]
    banner_h = 42

    # 반투명 빨간 배너
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, banner_h), (0, 0, 180), cv2.FILLED)
    cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

    text = f"🚨  WEAPON DETECTED  ({weapon_count})"
    cv2.putText(
        frame, text,
        (16, 28),
        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA,
    )
    return frame


def draw_fps(frame: np.ndarray, fps: float) -> np.ndarray:
    """우측 상단에 FPS 를 표시한다."""
    h, w = frame.shape[:2]
    text = f"FPS: {fps:.1f}"
    cv2.putText(
        frame, text,
        (w - 110, 28),
        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1, cv2.LINE_AA,
    )
    return frame