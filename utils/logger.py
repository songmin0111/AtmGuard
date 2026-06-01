# utils/logger.py
"""
사건 로그 저장/로딩 모듈
logs/events.csv 에 이벤트를 추가 저장한다.
컬럼: timestamp, track_id, event_type, risk_level, admin_action
"""

import csv
import os
from datetime import datetime


LOG_DIR="logs"

LOG_PATH=os.path.join(
    LOG_DIR,
    "events.csv"
)


FIELDS=[
    "time",
    "track_id",
    "event",
    "risk",
    "admin_action"
]


def init_log():

    os.makedirs(

        LOG_DIR,

        exist_ok=True

    )

    if os.path.exists(

        LOG_PATH

    ):

        return

    with open(

        LOG_PATH,
        "w",
        newline="",
        encoding="utf8"

    ) as f:

        writer=csv.writer(f)
        writer.writerow(FIELDS)


def append_event(
    tid,
    event,
    risk,
    admin_action=""
):

    init_log()

    with open(
        LOG_PATH,
        "a",
        newline="",
        encoding="utf8"
    ) as f:

        writer=csv.writer(f)

        writer.writerow([
            datetime.now(),
            tid,
            event,
            risk,
            admin_action
        ])