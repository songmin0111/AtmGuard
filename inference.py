# ──────────────────────────────────────────────
# inference.py  —  YOLO 모델 로드 + ByteTrack 추론
# ──────────────────────────────────────────────

import os
import streamlit as st
from ultralytics import YOLO
from config import MODEL_PATH

# 커스텀 ByteTrack yaml 경로 (없으면 기본값 fallback)
_CUSTOM_TRACKER = os.path.join(os.path.dirname(__file__), "bytetrack_custom.yaml")
_TRACKER_CFG = _CUSTOM_TRACKER if os.path.exists(_CUSTOM_TRACKER) else "bytetrack.yaml"


@st.cache_resource
def load_model():
    """
    YOLOv8 모델을 로드한다.
    @st.cache_resource 로 캐싱 → 슬라이더를 움직여도 재로드되지 않음.
    """
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            f"모델 파일을 찾을 수 없습니다: {MODEL_PATH}\n"
            "weights/ 폴더에 best.pt 를 넣어주세요."
        )
    model = YOLO(MODEL_PATH)
    return model


def run_tracking(model, frame, conf_threshold: float):
    """
    단일 프레임에 대해 ByteTrack tracking 을 수행하고 결과를 반환한다.

    Returns
    -------
    results : ultralytics Results 객체 리스트 (프레임 1개이므로 results[0] 사용)
    class_names : dict  {class_id: class_name}
    """
    results = model.track(
        frame,
        conf=conf_threshold,
        persist=True,
        tracker=_TRACKER_CFG,
        verbose=False,
    )
    # class_names 은 모델에서 직접 가져옴
    class_names = model.names  # {0: 'person', 1: 'weapon', ...}
    return results, class_names