# logic/risk.py
"""
위험도(Risk Level) 계산 모듈
- LOW    : ROI 출입 1~2회 또는 체류 < 60초
- MEDIUM : ROI 출입 3~4회 또는 체류 60~120초
- HIGH   : ROI 출입 5회 이상 또는 무기 감지
"""

def calculate_risk(entry_count: int, dwell_seconds: float, weapon_detected: bool) -> str:
    """
    entry_count     : ROI 진입 횟수
    dwell_seconds   : ROI 내 누적 체류 시간(초)
    weapon_detected : 무기 감지 여부
    returns         : 'LOW' | 'MEDIUM' | 'HIGH'
    """
    if weapon_detected or entry_count >= 5:
        return "HIGH"
    if entry_count >= 3 or dwell_seconds >= 60:
        return "MEDIUM"
    return "LOW"


RISK_COLOR = {
    "LOW":    "#22c55e",   # green-500
    "MEDIUM": "#f97316",   # orange-500
    "HIGH":   "#ef4444",   # red-500
}

RISK_BG = {
    "LOW":    "rgba(34,197,94,0.15)",
    "MEDIUM": "rgba(249,115,22,0.15)",
    "HIGH":   "rgba(239,68,68,0.20)",
}
