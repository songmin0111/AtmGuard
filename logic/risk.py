# logic/risk.py
"""
위험도(Risk Level) 계산 모듈

판단 기준
- LOW: ROI 출입 1~2회 또는 체류 < 80초

- MEDIUM: ROI 출입 3~4회 또는 체류 80~119초

- HIGH: ROI 출입 5회 이상 또는 무기 감지 또는 체류 시간 120초 이상
"""

def calculate_risk(
    entry_count: int,
    dwell_seconds: float,
    weapon_detected: bool
) -> str:

    # HIGH
    if (
        weapon_detected
        or entry_count >= 5
        or dwell_seconds >= 120
    ):
        return "HIGH"

    # MEDIUM
    if (
        entry_count >= 3
        or dwell_seconds >= 80
    ):
        return "MEDIUM"

    # LOW
    return "LOW"


RISK_COLOR = {

    "LOW": "#22C55E",
    "MEDIUM": "#F59E0B",
    "HIGH": "#EF4444"

}


RISK_BG = {

    "LOW": "rgba(34,197,94,0.15)",
    "MEDIUM": "rgba(245,158,11,0.15)",
    "HIGH": "rgba(239,68,68,0.20)"

}