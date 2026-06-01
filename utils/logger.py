# utils/logger.py
"""
사건 로그 저장/로딩 모듈
logs/events.csv 에 이벤트를 추가 저장한다.
컬럼: timestamp, track_id, event_type, risk_level, admin_action
"""

import csv
import os
import pandas as pd
from datetime import datetime


LOG_DIR="logs"

LOG_PATH=os.path.join(LOG_DIR, "events.csv")


FIELDS=["time", "track_id", "event", "risk", "admin_action"]


def init_log():
    os.makedirs(LOG_DIR, exist_ok=True)
    if not os.path.exists(LOG_PATH):
        with open(LOG_PATH, "w", newline="", encoding="utf8") as f:
            csv.writer(f).writerow(FIELDS)

# 이상행동 발생 시 즉시 행 추가
def append_event(tid, event, risk, admin_action=""):
    init_log()
    with open(LOG_PATH, "a", newline="", encoding="utf8") as f:
        csv.writer(f).writerow([datetime.now(), tid, event, risk, admin_action])

def update_admin_action(tid, event, action):
    """
    출동/오탐 버튼 클릭 시 호출.
    admin_action이 비어있는 가장 최근 행(tid+event 일치)을 찾아 업데이트.
    """
    init_log()
    try:
        df = pd.read_csv(LOG_PATH)
    except Exception:
        return

    # admin_action이 비어있는 행 중 tid + event가 일치하는 마지막 행
    mask = (
        (df["track_id"] == tid)
        & (df["event"]    == event)
        & (df["admin_action"].isna() | (df["admin_action"] == ""))
    )

    if mask.any():
        last_idx = df[mask].index[-1]
        df.loc[last_idx, "admin_action"] = action
        df.to_csv(LOG_PATH, index=False, encoding="utf8")