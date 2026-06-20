# Loitering / Weapon 이벤트 판단 + Occlusion 대응 Re-ID

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import numpy as np

from config import (
    MED_DWELL_SECONDS,
    HIGH_DWELL_SECONDS,
    MED_ENTRY_COUNT,
    HIGH_ENTRY_COUNT,
    LOW_DWELL_SECONDS,
    EVENT_COOLDOWN_SECONDS,
)


# 단일 Track 상태 
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
    # Re-ID용 히스토리
    color_hist: Optional[np.ndarray] = None   # 마지막 색상 히스토그램
    last_seen_frame: int = 0
    outside_frames: int = 999


# 이벤트 로그 항목 
@dataclass
class EventLog:
    track_id: int
    event_type: str          # "loitering" | "weapon"
    risk_level: str
    dwell_seconds: float
    entry_count: int
    timestamp: str
    response_status: str = "미확인"   # "미확인" | "출동" | "오탐"
    response_note: str = ""


# ID Switch 통계 
@dataclass
class TrackingStats:
    total_tracks: int = 0
    id_switches: int = 0
    reidentified: int = 0    # Re-ID로 복구된 횟수
    frame_count: int = 0


class LoiteringStateManager:
    """
        트랙 ID 별로 ROI 진입횟수 / 체류시간을 누적 관리하고 위험도를 산출한다.
        Occlusion 대응: 색상 히스토그램 기반 Re-ID로 ID switch 완화.
    """

    # Re-ID 임계값: 코사인 유사도 기준 (0~1, 높을수록 유사)
    REID_SIMILARITY_THRESH = 0.9
    # 사라진 후 몇 프레임까지 Re-ID 시도할지
    REID_LOST_FRAME_LIMIT = 30
    ENTRY_RECOUNT_GAP_FRAMES = 15

    def __init__(self):
        self._states: Dict[int, TrackState] = {}
        self._events: List[EventLog] = []
        self._last_event_time: Dict[str, datetime] = {}
        self._stats = TrackingStats()
        self._frame_idx: int = 0
        # 잃어버린(사라진) 트랙 후보: {old_id: TrackState}
        self._lost_tracks: Dict[int, TrackState] = {}
        self._id_alias: Dict[int, int] = {}

    def next_frame(self):
        """영상 프레임이 1장 진행될 때마다 호출"""
        self._frame_idx += 1
        self._stats.frame_count = self._frame_idx
    
    # 매 프레임 호출 
    def update(
        self,
        track_id: int,
        bbox: Tuple[float, float, float, float],
        current_inside: bool,
        fps: float,
        frame: Optional[np.ndarray] = None,
    ) -> TrackState:
        """
            트랙 상태를 업데이트하고 최신 TrackState 를 반환한다.

            Parameters
            ----------
            track_id       : ByteTrack 이 부여한 정수 ID
            bbox           : (x1, y1, x2, y2) float 좌표
            current_inside : 현재 프레임에서 ROI 내부 여부
            fps            : 영상 FPS (체류시간 계산용)
            frame          : 원본 BGR 프레임 (Re-ID 히스토그램 계산용, None이면 스킵)
        """

        # Re-ID: 새 track_id가 lost_tracks의 누군가와 유사한지 확인 
        if track_id not in self._states and self._lost_tracks and frame is not None:
            matched_old_id = self._try_reid(track_id, bbox, frame)
            
            if matched_old_id is not None:
                 # 새 ByteTrack ID를 기존 ID로 매핑
                self._id_alias[track_id] = matched_old_id
                self._lost_tracks.pop(matched_old_id, None)
                track_id = matched_old_id
        
                self._stats.reidentified += 1
                self._stats.id_switches += 1
        # 이미 alias 등록된 ID면 기존 대표 ID로 변환
        track_id = self._id_alias.get(track_id, track_id)
        
        if track_id not in self._states:
            print(f"[NEW STATE CREATED] track_id={track_id}, frame={self._frame_idx}")

            # 혹시 lost_tracks에 같은 ID가 남아 있으면 기존 상태 복구
            if track_id in self._lost_tracks:
                self._states[track_id] = self._lost_tracks.pop(track_id)
            else:
                self._states[track_id] = TrackState(track_id=track_id)
                self._stats.total_tracks += 1

        s = self._states[track_id]
        s.bbox = bbox
        s.last_seen_frame = self._frame_idx
        x1, y1, x2, y2 = bbox
        s.cx = int((x1 + x2) / 2)
        s.cy = int((y1 + y2) / 2)

        # 색상 히스토그램 업데이트 (Re-ID용)
        if frame is not None:
            s.color_hist = self._compute_hist(frame, bbox)

        if current_inside:
            if not s.inside_roi and s.outside_frames >= self.ENTRY_RECOUNT_GAP_FRAMES:
                s.entry_count += 1

            s.dwell_frames += 1
            s.outside_frames = 0
        else:
            s.outside_frames += 1

        s.inside_roi = current_inside

        safe_fps = fps if fps > 0 else 30.0
        s.dwell_seconds = s.dwell_frames / safe_fps

        s.risk_level   = self._calc_risk(s)
        s.is_loitering = s.risk_level in ("LOW", "MED", "HIGH")

        if s.is_loitering:
            self._try_log_event(
                track_id=s.track_id,
                event_type="loitering",
                risk_level=s.risk_level,
                dwell_seconds=s.dwell_seconds,
                entry_count=s.entry_count,
            )

        self._stats.frame_count = self._frame_idx
        return s

    def mark_lost(self, track_id: int):
        """이번 프레임에 감지되지 않은 트랙을 lost 후보로 이동"""
        if track_id in self._states:
            self._lost_tracks[track_id] = self._states[track_id]

    def cleanup_lost(self):
        """오래된 lost 트랙 정리 (REID_LOST_FRAME_LIMIT 초과)"""
        stale = [
        tid for tid, s in self._lost_tracks.items()
        if (self._frame_idx - s.last_seen_frame) > self.REID_LOST_FRAME_LIMIT
        ]
        for tid in stale:
            del self._lost_tracks[tid]

    def log_weapon_event(self, weapon_count: int):
        self._try_log_event(
            track_id=-1,
            event_type="weapon",
            risk_level="HIGH",
            dwell_seconds=0.0,
            entry_count=weapon_count,
        )

    def update_event_response(self, event_idx: int, status: str, note: str = ""):
        if 0 <= event_idx < len(self._events):
            self._events[event_idx].response_status = status
            self._events[event_idx].response_note = note

    def get_all_states(self) -> Dict[int, TrackState]:
        return self._states

    def get_events(self) -> List[EventLog]:
        return self._events

    def get_live_dwell(self, track_id: int) -> float:
        """track_id 의 현재(최신) 체류시간 반환. 트랙이 없으면 -1."""
        s = self._states.get(track_id) or self._lost_tracks.get(track_id)
        return s.dwell_seconds if s else -1.0

    def get_live_risk(self, track_id: int) -> str:
        """track_id 의 현재 위험도 반환. 없으면 빈 문자열."""
        s = self._states.get(track_id) or self._lost_tracks.get(track_id)
        return s.risk_level if s else ""

    def get_stats(self) -> TrackingStats:
        return self._stats

    def reset(self):
        self._states.clear()
        self._events.clear()
        self._last_event_time.clear()
        self._lost_tracks.clear()
        self._id_alias.clear()
        self._stats = TrackingStats()
        self._frame_idx = 0

    # 내부 헬퍼 
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

    def _try_log_event(self, track_id, event_type, risk_level, dwell_seconds, entry_count):
        now = datetime.now()

        RISK_ORDER = {
            "NORMAL": 0,
            "LOW": 1,
            "MED": 2,
            "HIGH": 3,
        }

        # 사람 서성거림 이벤트는 track_id별로 하나만 유지하고 계속 업데이트
        if event_type == "loitering" and track_id >= 0:
            for e in self._events:
                if e.track_id == track_id and e.event_type == "loitering":
                    # 위험도는 더 높은 단계로만 갱신
                    if RISK_ORDER.get(risk_level, 0) >= RISK_ORDER.get(e.risk_level, 0):
                        e.risk_level = risk_level

                    # 체류시간/진입횟수는 더 큰 값 유지
                    e.dwell_seconds = max(e.dwell_seconds, dwell_seconds)
                    e.entry_count = max(e.entry_count, entry_count)

                    return

        # weapon 이벤트는 너무 자주 쌓이지 않도록 cooldown 적용
        key = f"{event_type}_{track_id}"
        last = self._last_event_time.get(key)

        if last is not None and (now - last).total_seconds() < EVENT_COOLDOWN_SECONDS:
            return

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

    def _compute_hist(self, frame: np.ndarray, bbox: Tuple) -> np.ndarray:
        """bbox 영역의 HSV 색상 히스토그램 (32bin H + 32bin S) 반환"""
        try:
            import cv2
            x1, y1, x2, y2 = [int(v) for v in bbox]
            h, w = frame.shape[:2]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            if x2 <= x1 or y2 <= y1:
                return None
            roi = frame[y1:y2, x1:x2]
            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
            h_hist = cv2.calcHist([hsv], [0], None, [32], [0, 180]).flatten()
            s_hist = cv2.calcHist([hsv], [1], None, [32], [0, 256]).flatten()
            hist = np.concatenate([h_hist, s_hist])
            norm = np.linalg.norm(hist)
            return hist / norm if norm > 0 else hist
        except Exception:
            return None

    def _cosine_sim(self, a: np.ndarray, b: np.ndarray) -> float:
        if a is None or b is None:
            return 0.0
        try:
            return float(np.dot(a, b))
        except Exception:
            return 0.0

    def _try_reid(self, new_id: int, bbox: Tuple, frame: np.ndarray) -> Optional[int]:
        """
            새로 등장한 new_id의 색상 히스토그램과 lost_tracks를 비교.
            유사도가 임계값 이상인 가장 가까운 lost ID를 반환.
        """
        new_hist = self._compute_hist(frame, bbox)
        if new_hist is None:
            return None
        
        x1, y1, x2, y2 = bbox
        new_cx = int((x1 + x2) / 2)
        new_cy = int((y1 + y2) / 2)

        best_id = None
        best_sim = self.REID_SIMILARITY_THRESH
        
        MAX_CENTER_DISTANCE = 80  # 너무 멀리 떨어진 객체는 같은 사람으로 보지 않음

        for lost_id, lost_state in self._lost_tracks.items():
            # 너무 오래된 트랙은 스킵
            if (self._frame_idx - lost_state.last_seen_frame) > self.REID_LOST_FRAME_LIMIT:
                continue
            
            dist = ((new_cx - lost_state.cx) ** 2 + (new_cy - lost_state.cy) ** 2) ** 0.5

            if dist > MAX_CENTER_DISTANCE:
                continue
            
            sim = self._cosine_sim(new_hist, lost_state.color_hist)
            if sim > best_sim:
                best_sim = sim
                best_id = lost_id

        return best_id