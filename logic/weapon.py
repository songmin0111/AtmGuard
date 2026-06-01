# logic/weapon.py
"""
무기(Weapon) 감지 모듈
- YOLO 탐지 결과에서 hammer / pliers 클래스 추출
- 감지 시 즉시 HIGH 위험도 반환
"""

WEAPON_CLASSES = {"hammer", "pliers", "weapon"}


def detect_weapons(boxes, class_names: dict) -> list[dict]:
    
    detections = []
    if boxes is None:
        return detections

    for box in boxes:
        cls_id = int(box.cls[0].item())
        cls_name = class_names.get(cls_id, "unknown").lower()
        if cls_name in WEAPON_CLASSES:
            # HIGH 위험 이벤트 생성
            track_id = int(box.id[0].item()) if box.id is not None else -1
            conf = float(box.conf[0].item())
            xyxy = box.xyxy[0].tolist()
            detections.append({
                "track_id": track_id,
                "cls_name": cls_name,
                "conf": conf,
                "xyxy": xyxy,
            })

    return detections
