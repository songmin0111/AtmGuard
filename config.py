# config.py  —  ATM Guard 전역 설정


# 모델 경로
MODEL_PATH = "weights/best.pt"

# 업로드 허용 확장자
ALLOWED_VIDEO_EXTENSIONS = [".mp4", ".avi", ".mov"]

# 추론 기본 confidence
DEFAULT_CONF_THRESHOLD = 0.4

# Canvas 표시 너비 (픽셀)
CANVAS_WIDTH = 720

# Loitering 위험도 기준 
LOW_DWELL_SECONDS  = 2    # ROI 진입 후 위험도 LOW 전환 기준
MED_DWELL_SECONDS  = 4    # MED 체류시간 기준 (초)
HIGH_DWELL_SECONDS = 6    # HIGH 체류시간 기준 (초)

MED_ENTRY_COUNT  = 3      # MED 진입횟수 기준
HIGH_ENTRY_COUNT = 5      # HIGH 진입횟수 기준

# Weapon 클래스 이름 
# best.pt 에서 사용하는 실제 클래스명으로 맞춰야 함
# 단일 클래스 "weapon" 사용
WEAPON_CLASS_NAMES = {"weapon"}

# 위험도 색상 (BGR for OpenCV) 
RISK_COLORS = {
    "NORMAL": (128, 128, 128),   # gray
    "LOW":    (0,   200,   0),   # green
    "MED":    (0,   140, 255),   # orange
    "HIGH":   (0,     0, 220),   # red
}

# 위험도 색상 (HEX for Streamlit UI) 
RISK_COLORS_HEX = {
    "NORMAL": "#808080",
    "LOW":    "#00c800",
    "MED":    "#ff8c00",
    "HIGH":   "#dc0000",
}

# Loitering 이벤트 쿨다운 (중복 로깅 방지) 
EVENT_COOLDOWN_SECONDS = 30

# UI 레이아웃
PAGE_TITLE  = "ATM Guard"
PAGE_ICON   = "🛡️"
SIDEBAR_TITLE = "ATM Guard 설정"