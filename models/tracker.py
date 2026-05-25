# models/tracker.py
"""
ByteTrack 래퍼.
현재는 ultralytics 내장 tracker를 사용하므로
별도 초기화 없이 detector.run_tracking() 이 호출하는 구조.
나중에 독립 ByteTrack 라이브러리 연동 시 이 파일을 확장한다.
"""


class ByteTrackWrapper:
    """placeholder – ultralytics 내장 bytetrack 사용 중"""

    def __init__(self):
        pass

    def reset(self):
        """추적 상태 초기화 (새 영상 로드 시 호출)"""
        pass
