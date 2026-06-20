# Streamlit session_state 초기화 및 리셋
# event_logic 순환 import 방지: LoiteringStateManager 는 함수 내부에서만 import

import streamlit as st


def _new_mgr():
    """LoiteringStateManager 지연 생성 (순환 import 방지)"""
    from event_logic import LoiteringStateManager
    return LoiteringStateManager()


def init_session_state() -> None:
    defaults = {
        "page":                    "CCTV 모니터링",
        "roi":                     None,
        "first_frame":             None,
        "analysis_started":        False,
        "current_video_id":        None,
        "video_path":              None,
        "analysis_done":           False,
        "fps_history":             [],
        "tracking_stats_snapshot": None,
        "open_modal_idx":          None,
        "event_frames":            {},
        "event_frame_risks":       {},
        "loitering_mgr":           None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    if st.session_state.loitering_mgr is None:
        st.session_state.loitering_mgr = _new_mgr()


def reset_analysis() -> None:
    st.session_state.roi                     = None
    st.session_state.analysis_started        = False
    st.session_state.analysis_done           = False
    st.session_state.fps_history             = []
    st.session_state.tracking_stats_snapshot = None
    st.session_state.event_frames            = {}
    st.session_state.event_frame_risks       = {}
    st.session_state.loitering_mgr           = _new_mgr()


def full_reset() -> None:
    reset_analysis()
    st.session_state.first_frame      = None
    st.session_state.current_video_id = None
    st.session_state.video_path       = None