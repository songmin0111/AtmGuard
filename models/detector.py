# models/detector.py
"""
YOLOv8 Detection 모델 로더 및 추론 래퍼.
weights/best.pt 가 없을 경우 yolov8n.pt(사전학습) 로 대체
"""

import os
from pathlib import Path

WEIGHTS_PATH = Path(__file__).parent.parent / "weights" / "best.pt"
FALLBACK_WEIGHTS = "yolov8n.pt"


def load_model():
    """YOLO 모델 로드. ultralytics 미설치 시 None 반환."""
    try:
        from ultralytics import YOLO
        w = str(WEIGHTS_PATH) if WEIGHTS_PATH.exists() else FALLBACK_WEIGHTS
        model = YOLO(w)
        return model
    except ImportError:
        return None


def run_detection(model, frame, conf: float = 0.4):
    """
    단일 프레임 추론.
    returns ultralytics Results 객체, 또는 None(모델 없음).
    """
    if model is None:
        return None
    results = model(frame, conf=conf, verbose=False)
    return results[0] if results else None


def run_tracking(model, frame, conf: float = 0.4):
    """
    ByteTrack 추적 추론.
    returns ultralytics Results 객체, 또는 None.
    """
    if model is None:
        return None
    results = model.track(frame, tracker="bytetrack.yaml",
                           persist=True, conf=conf, verbose=False)
    return results[0] if results else None
