# logic/loitering.py
"""
서성거림(Loitering) 감지 모듈
- ROI 출입 횟수 카운팅
- 체류 시간 누적
- 이상행동 트리거 여부 판단
"""

from logic.risk import calculate_risk


class LoiteringTracker:
    """Track ID별 ROI 출입 횟수 및 체류 시간을 관리한다."""

    def __init__(self, entry_threshold: int = 5):
        self.entry_threshold = entry_threshold
        # { track_id: {"inside": bool, "entry_count": int,
        #              "dwell_frames": int, "alerted": bool} }
        self._state: dict = {}

    def update(self, track_id: int, is_inside_roi: bool, fps: float = 25.0):
        """
        프레임마다 호출.
        returns: dict with keys entry_count, dwell_seconds, risk, is_loitering
        """
        if track_id not in self._state:
            self._state[track_id] = {
                "inside": False,
                "entry_count": 0,
                "dwell_frames": 0,
                "alerted": False,
            }

        s = self._state[track_id]

        # 진입 감지 (outside → inside)
        if not s["inside"] and is_inside_roi:
            s["entry_count"] += 1

        # 체류 시간 누적
        if is_inside_roi:
            s["dwell_frames"] += 1

        s["inside"] = is_inside_roi

        dwell_sec = s["dwell_frames"] / max(fps, 1)
        risk = calculate_risk(s["entry_count"], dwell_sec, weapon_detected=False)
        is_loitering = s["entry_count"] >= self.entry_threshold or dwell_sec >= 120

        return {
            "entry_count": s["entry_count"],
            "dwell_seconds": dwell_sec,
            "risk": risk,
            "is_loitering": is_loitering,
        }

    def reset(self, track_id: int):
        self._state.pop(track_id, None)

    def reset_all(self):
        self._state.clear()

    def get_all(self) -> dict:
        return self._state
