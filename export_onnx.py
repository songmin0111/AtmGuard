from ultralytics import YOLO

model = YOLO("weights/best.pt")

model.export(
    format="onnx",
    imgsz=640,
    batch=1,
    dynamic=False,
    simplify=True,
    nms=False,
)