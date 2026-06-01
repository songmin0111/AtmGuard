# models/detector.py
"""
YOLOv8 Detection 모델 로더 및 추론 래퍼.
weights/best.pt 가 없을 경우 yolov8n.pt(사전학습) 로 대체
"""

"""
YOLO Loader
"""

from ultralytics import YOLO
from pathlib import Path
import ultralytics


WEIGHT=Path("weights/best.pt")
FALLBACK="yolov8n.pt"

BYTETRACK_YAML = str(
    Path(ultralytics.__file__).parent / "cfg" / "trackers" / "bytetrack.yaml"
)


def load_model():

    try:

        if WEIGHT.exists():

            try:
                model = YOLO(str(WEIGHT))

                print("best.pt 로드 성공")
                print(model.names)

                return model

            except Exception as e:

                print(e)
                print("best.pt 깨짐")

        print("❌ fallback yolov8n 사용")

        model = YOLO(FALLBACK)

        print(model.names)

        return model

    except Exception as e:

        print(e)

        return None


def run_detection(model, frame, conf):

    if model is None:

        return None

    out=model(frame, conf=conf, verbose=False)

    return out[0]


# 영상에서 사람을 추적할 때 ByteTrack
def run_tracking(model, frame, conf):

    if model is None:

        return None

    out=model.track(frame, conf=conf, tracker=BYTETRACK_YAML, persist=True, verbose=False)
    # BYTETRACK 절대경로로 지정
    return out[0]