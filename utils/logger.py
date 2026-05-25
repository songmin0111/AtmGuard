# utils/logger.py
"""
사건 로그 저장/로딩 모듈
logs/events.csv 에 이벤트를 추가 저장한다.
컬럼: timestamp, track_id, event_type, risk_level, admin_action
"""

import csv
import os
from datetime import datetime

LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "logs", "events.csv")
FIELDNAMES = ["timestamp", "track_id", "event_type", "risk_level", "admin_action"]


def _ensure_log_file():
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    if not os.path.exists(LOG_PATH):
        with open(LOG_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()


def append_event(track_id: int, event_type: str, risk_level: str,
                 admin_action: str = "pending"):
    """CSV에 이벤트 한 행 추가"""
    _ensure_log_file()
    row = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "track_id": track_id,
        "event_type": event_type,
        "risk_level": risk_level,
        "admin_action": admin_action,
    }
    with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writerow(row)
    return row


def update_admin_action(timestamp: str, track_id: int, action: str):
    """특정 이벤트의 admin_action 컬럼 업데이트"""
    _ensure_log_file()
    rows = load_events()
    for row in rows:
        if row["timestamp"] == timestamp and str(row["track_id"]) == str(track_id):
            row["admin_action"] = action
    with open(LOG_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def load_events() -> list[dict]:
    """CSV 전체 로드 (최신 순)"""
    _ensure_log_file()
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    return list(reversed(rows))
