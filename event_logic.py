# ──────────────────────────────────────────────
# event_logic.py  —  Loitering / Weapon 이벤트 판단 로직
# ──────────────────────────────────────────────

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Tuple, Optional

from config import (
    MED_DWELL_SECONDS,
    HIGH_DWELL_SECONDS,
    MED_ENTRY_COUNT,
    HIGH_ENTRY_COUNT,
    LOW_DWELL_SECONDS,
    EVENT_COOLDOWN_SECONDS,
)


# ── 단일 Track 상태 ────────────────────────────
@dataclass
class TrackState:
    track_id: int
    inside_roi: bool = False
    entry_count: int = 0
    dwell_frames: int = 0
    dwell_seconds: float = 0.0
    risk_level: str = "NORMAL"
    is_loitering: bool = False
    bbox: Tuple = (0, 0, 0, 0)
    cx: int = 0
    cy: int = 0


# ── 이벤트 로그 항목 ───────────────────────────
@dataclass
class EventLog:
    track_id: int
    event_type: str          # "loitering" | "weapon"
    risk_level: str
    dwell_seconds: float
    entry_count: int
    timestamp: str


class LoiteringStateManager:
    """
    트랙 ID 별로 ROI 진입횟수 / 체류시간을 누적 관리하고
    위험도를 산출한다.
    """

    def __init__(self):
        self._states: Dict[int, TrackState] = {}
        self._events: List[EventLog] = []
        # 이벤트 쿨다운: {event_key: last_logged_timestamp}
        self._last_event_time: Dict[str, datetime] = {}

    # ── 외부에서 매 프레임 호출 ─────────────────
    def update(
        self,
        track_id: int,
        bbox: Tuple[float, float, float, float],
        current_inside: bool,
        fps: float,
    ) -> TrackState:
        """
        트랙 상태를 업데이트하고 최신 TrackState 를 반환한다.

        Parameters
        ----------
        track_id       : ByteTrack 이 부여한 정수 ID
        bbox           : (x1, y1, x2, y2) float 좌표
        current_inside : 현재 프레임에서 ROI 내부 여부
        fps            : 영상 FPS (체류시간 계산용)
        """
        if track_id not in self._states:
            self._states[track_id] = TrackState(track_id=track_id)

        s = self._states[track_id]
        s.bbox = bbox
        x1, y1, x2, y2 = bbox
        s.cx = int((x1 + x2) / 2)
        s.cy = int((y1 + y2) / 2)

        # 밖 → 안 전환 시에만 진입횟수 증가
        if not s.inside_roi and current_inside:
            s.entry_count += 1

        # ROI 내부에 있는 동안 체류 프레임 누적
        if current_inside:
            s.dwell_frames += 1

        s.inside_roi = current_inside

        # 체류시간 (초)
        safe_fps = fps if fps > 0 else 30.0
        s.dwell_seconds = s.dwell_frames / safe_fps

        # 위험도 판정
        s.risk_level   = self._calc_risk(s)
        s.is_loitering = s.risk_level in ("MED", "HIGH")

        # 이벤트 로깅 (쿨다운 적용)
        if s.is_loitering:
            self._try_log_event(
                track_id=track_id,
                event_type="loitering",
                risk_level=s.risk_level,
                dwell_seconds=s.dwell_seconds,
                entry_count=s.entry_count,
            )

        return s

    def log_weapon_event(self, weapon_count: int):
        """weapon 감지 시 이벤트를 기록한다."""
        self._try_log_event(
            track_id=-1,
            event_type="weapon",
            risk_level="HIGH",
            dwell_seconds=0.0,
            entry_count=weapon_count,
        )

    def get_all_states(self) -> Dict[int, TrackState]:
        return self._states

    def get_events(self) -> List[EventLog]:
        return self._events

    def reset(self):
        self._states.clear()
        self._events.clear()
        self._last_event_time.clear()

    # ── 내부 헬퍼 ──────────────────────────────
    def _calc_risk(self, s: TrackState) -> str:
        if s.entry_count >= HIGH_ENTRY_COUNT or s.dwell_seconds >= HIGH_DWELL_SECONDS:
            return "HIGH"
        if s.entry_count >= MED_ENTRY_COUNT or s.dwell_seconds >= MED_DWELL_SECONDS:
            return "MED"
        if s.inside_roi and s.dwell_seconds >= LOW_DWELL_SECONDS:
            return "LOW"
        if s.inside_roi:
            return "LOW"
        return "NORMAL"

    def _try_log_event(
        self,
        track_id: int,
        event_type: str,
        risk_level: str,
        dwell_seconds: float,
        entry_count: int,
    ):
        """쿨다운 내 중복 이벤트는 기록하지 않는다."""
        key = f"{event_type}_{track_id}"
        now = datetime.now()

        last = self._last_event_time.get(key)
        if last is not None:
            elapsed = (now - last).total_seconds()
            if elapsed < EVENT_COOLDOWN_SECONDS:
                return  # 쿨다운 중 → 스킵

        self._last_event_time[key] = now
        self._events.append(
            EventLog(
                track_id=track_id,
                event_type=event_type,
                risk_level=risk_level,
                dwell_seconds=dwell_seconds,
                entry_count=entry_count,
                timestamp=now.strftime("%H:%M:%S"),
            )
        )