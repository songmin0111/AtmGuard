# utils/draw.py
"""
영상 프레임 위에 바운딩 박스, 트래킹 ID, 위험도, ROI 등을 그린다.
OpenCV(BGR) 기반.
"""

import cv2
import numpy as np
from logic.risk import RISK_COLOR

# BGR 변환 헬퍼
def _hex_to_bgr(hex_color: str):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (b, g, r)


RISK_BGR = {k: _hex_to_bgr(v) for k, v in RISK_COLOR.items()}

NORMAL_BGR = (100, 200, 100)
FONT = cv2.FONT_HERSHEY_SIMPLEX


def draw_roi(frame: np.ndarray, roi: tuple, label: str = "ROI : ATM 구역") -> np.ndarray:
    """파란 점선 박스 + 라벨"""
    if roi is None:
        return frame
    x1, y1, x2, y2 = [int(v) for v in roi]
    # 점선 효과: 작은 사각형들로 근사
    color = (255, 180, 0)
    gap = 12
    for x in range(x1, x2, gap * 2):
        cv2.line(frame, (x, y1), (min(x + gap, x2), y1), color, 2)
        cv2.line(frame, (x, y2), (min(x + gap, x2), y2), color, 2)
    for y in range(y1, y2, gap * 2):
        cv2.line(frame, (x1, y), (x1, min(y + gap, y2)), color, 2)
        cv2.line(frame, (x2, y), (x2, min(y + gap, y2)), color, 2)
    cv2.putText(frame, label, (x1 + 6, y1 - 8),
                FONT, 0.55, color, 1, cv2.LINE_AA)
    return frame


def draw_person_box(frame: np.ndarray, xyxy, track_id: int,
                    status: str, risk: str) -> np.ndarray:
    """
    status: 'Normal' | 'Loitering' | 'Weapon'
    risk  : 'LOW' | 'MEDIUM' | 'HIGH'
    """
    x1, y1, x2, y2 = [int(v) for v in xyxy]
    color = RISK_BGR.get(risk, NORMAL_BGR)

    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

    label = f"ID #{track_id:02d}  {status}  {risk}"
    (tw, th), _ = cv2.getTextSize(label, FONT, 0.5, 1)
    cv2.rectangle(frame, (x1, y1 - th - 8), (x1 + tw + 6, y1), color, -1)
    cv2.putText(frame, label, (x1 + 3, y1 - 4),
                FONT, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
    return frame


def draw_weapon_box(frame: np.ndarray, xyxy, track_id: int,
                    cls_name: str, conf: float) -> np.ndarray:
    x1, y1, x2, y2 = [int(v) for v in xyxy]
    color = RISK_BGR["HIGH"]
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
    label = f"⚠ WEAPON  {cls_name}  {conf:.0%}"
    (tw, th), _ = cv2.getTextSize(label, FONT, 0.55, 1)
    cv2.rectangle(frame, (x1, y1 - th - 10), (x1 + tw + 8, y1), color, -1)
    cv2.putText(frame, label, (x1 + 4, y1 - 5),
                FONT, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
    return frame


def draw_fps(frame: np.ndarray, fps: float) -> np.ndarray:
    cv2.putText(frame, f"FPS: {fps:.1f}", (10, 28),
                FONT, 0.7, (200, 220, 255), 2, cv2.LINE_AA)
    return frame
