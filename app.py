# ATM GUARD 메인 Streamlit 앱
import time
import tempfile
import os
from datetime import datetime

import cv2
import numpy as np
import streamlit as st

# 내부 모듈 
from ui.sidebar import render_sidebar
from ui.alert_panel import render_alert_panel, render_risk_gauges
from ui.stats import render_event_log, render_hourly_chart
from logic.loitering import LoiteringTracker
from logic.weapon import detect_weapons
from logic.risk import calculate_risk, RISK_COLOR
from utils.roi import is_inside_roi, center_of_box
from utils.draw import draw_roi, draw_person_box, draw_weapon_box, draw_fps
from utils.logger import append_event

# 페이지 설정 
st.set_page_config(
    page_title="ATM GUARD",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# 글로벌 CSS 
st.markdown(
    """
    <style>
    /* 라이트 테마 전체 배경 */
    [data-testid="stAppViewContainer"] {
        background: #f0f4f8;
        color: #1e293b;
    }
    [data-testid="stSidebar"] {
        background: #ffffff !important;
        border-right: 1px solid #e2e8f0;
    }
    /* 사이드바 내부 텍스트 */
    [data-testid="stSidebar"] * { color: #1e293b !important; }

    /* 헤더 숨기기 */
    [data-testid="stHeader"] {
    background: transparent !important;
    height: 0 !important;
    min-height: 0 !important;
    }
    
    /* 사이드바 열기/닫기 버튼 — 항상 표시 */
    [data-testid="stSidebarCollapsedControl"],
    button[kind="header"],
    [data-testid="collapsedControl"] {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        position: fixed !important;
        top: 10px !important;
        left: 10px !important;
        z-index: 999 !important;
        background: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 8px !important;
        box-shadow: 0 1px 4px rgba(0,0,0,.1) !important;
}

    /* 메인 콘텐츠 영역 */
    [data-testid="stMainBlockContainer"] {
        background: #f0f4f8;
    }

    /* 버튼 스타일 */
    div.stButton > button {
        background: #ffffff;
        color: #374151;
        border: 1.5px solid #d1d5db;
        border-radius: 8px;
        font-size: 13px;
        font-weight: 600;
        padding: 6px 12px;
        transition: all .18s;
    }
    div.stButton > button:hover {
        background: #eff6ff;
        color: #1d4ed8;
        border-color: #3b82f6;
    }

    /* 데이터프레임 */
    [data-testid="stDataFrame"] {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
    }

    /* 섹션 구분선 */
    hr { border-color: #e2e8f0 !important; }

    /* 슬라이더 */
    [data-baseweb="slider"] { padding: 0 4px; }

    /* 라디오 */
    [data-testid="stRadio"] label { font-size: 13px; color: #374151; }

    /* input */
    [data-testid="stNumberInput"] input,
    [data-testid="stTextInput"] input {
        background: #f8fafc !important;
        color: #1e293b !important;
        border: 1.5px solid #d1d5db !important;
        border-radius: 6px !important;
    }

    /* 상단 타이틀 바 */
    .atm-topbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 12px 20px;
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        margin-bottom: 14px;
        box-shadow: 0 1px 4px rgba(0,0,0,.06);
    }
    .atm-brand {
        font-size: 18px;
        font-weight: 800;
        letter-spacing: .06em;
        color: #1d4ed8;
    }
    .atm-cam {
        font-size: 12px;
        color: #6b7280;
        letter-spacing: .1em;
        text-transform: uppercase;
        background: #f1f5f9;
        padding: 4px 10px;
        border-radius: 6px;
    }

    /* 영상 컨테이너 */
    .video-container {
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        overflow: hidden;
        background: #e8edf2;
        box-shadow: 0 1px 4px rgba(0,0,0,.06);
    }

    /* 패널 박스 */
    .panel-box {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 14px 16px;
        box-shadow: 0 1px 4px rgba(0,0,0,.06);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# 세션 상태 초기화 
if "active_alerts" not in st.session_state:
    st.session_state["active_alerts"] = []
if "loitering_tracker" not in st.session_state:
    st.session_state["loitering_tracker"] = LoiteringTracker()
if "track_states" not in st.session_state:
    st.session_state["track_states"] = {}
if "model" not in st.session_state:
    st.session_state["model"] = None  # 모델은 lazy load


# 헬퍼: 더미 프레임 생성 (모델 없을 때 UI 미리보기용)
def _make_demo_frame(width=640, height=480, camera_name="CAM-01") -> np.ndarray:
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frame[:] = (12, 18, 30)

    # ROI 박스
    roi = (int(width * 0.3), int(height * 0.2),
           int(width * 0.7), int(height * 0.8))
    frame = draw_roi(frame, roi)

    # 더미 바운딩 박스
    frame = draw_person_box(frame,
                             (80, 120, 200, 380), 3, "Loitering", "HIGH")
    frame = draw_person_box(frame,
                             (400, 150, 520, 420), 7, "Normal", "LOW")
    draw_fps(frame, 25.3)

    # 카메라 라벨
    cv2.putText(frame, camera_name, (width - 110, 24),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (80, 120, 180), 1, cv2.LINE_AA)
    return frame


def _demo_alerts():
    return [
        {"track_id": 3, "event_type": "loitering", "risk": "HIGH",
         "timestamp": "14:32:00", "entry_count": 5, "dwell_seconds": 148},
        {"track_id": 11, "event_type": "weapon", "risk": "MEDIUM",
         "timestamp": "14:29:00", "entry_count": 1, "dwell_seconds": 12},
    ]


def _demo_track_states():
    return {
        3:  {"risk": "HIGH",   "dwell_seconds": 148, "entry_count": 5},
        7:  {"risk": "LOW",    "dwell_seconds": 38,  "entry_count": 1},
        11: {"risk": "MEDIUM", "dwell_seconds": 12,  "entry_count": 1},
        14: {"risk": "LOW",    "dwell_seconds": 12,  "entry_count": 1},
    }


# 메인 레이아웃
sidebar_cfg = render_sidebar()
roi           = sidebar_cfg["roi"]
conf          = sidebar_cfg["conf"]
entry_thr     = sidebar_cfg["entry_threshold"]
camera_name   = sidebar_cfg["camera_name"]
uploaded_file = sidebar_cfg["uploaded_file"]
input_mode    = sidebar_cfg["mode"]

# 서성거림 tracker entry_threshold 동기화
st.session_state["loitering_tracker"].entry_threshold = entry_thr

# 상단 타이틀 바
st.markdown(
    f"""
    <div class='atm-topbar'>
        <div>
            <span class='atm-brand'>🛡️ ATM Guard</span>
            <span style='font-size:12px;color:#4b5563;margin-left:12px;'>
                ATM 이상행동 감지 시스템
            </span>
        </div>
        <div class='atm-cam'>📷 {camera_name}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# 메인 컬럼 (영상 / 알림 패널) 
col_video, col_panel = st.columns([2, 1.6], gap="medium")

with col_video:
    # FPS 표시 플레이스홀더
    fps_placeholder = st.empty()
    # 영상 출력 플레이스홀더
    frame_placeholder = st.empty()

with col_panel:
    st.markdown("<div class='panel-box'>", unsafe_allow_html=True)
    alert_placeholder   = st.empty()
    gauge_placeholder   = st.empty()
    st.markdown("</div>", unsafe_allow_html=True)


# 하단 (사건 로그 / 통계 차트) 
st.markdown("---")
col_log, col_chart = st.columns([1.2, 1], gap="medium")

with col_log:
    log_placeholder = st.empty()

with col_chart:
    chart_placeholder = st.empty()


# 처리 루틴
def _render_panels(alerts, track_states):
    with alert_placeholder.container():
        render_alert_panel(alerts)
        render_risk_gauges(track_states)
    with log_placeholder.container():
        render_event_log()
    with chart_placeholder.container():
        render_hourly_chart()


# 영상 없을 때: 데모 화면 
if uploaded_file is None:
    demo_frame = _make_demo_frame(camera_name=camera_name)
    demo_rgb   = cv2.cvtColor(demo_frame, cv2.COLOR_BGR2RGB)
    fps_placeholder.markdown(
        "<p style='font-size:11px;color:#4b5563;margin:0 0 4px;'>영상을 업로드하면 분석이 시작됩니다</p>",
        unsafe_allow_html=True,
    )
    frame_placeholder.image(demo_rgb, use_container_width=True,
                             caption="📌 미리보기 (더미 데이터)")
    _render_panels(_demo_alerts(), _demo_track_states())
    st.stop()


# 이미지 처리 
if input_mode == "image":
    file_bytes = np.frombuffer(uploaded_file.read(), np.uint8)
    frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    if frame is None:
        st.error("이미지를 읽을 수 없습니다.")
        st.stop()

    # 모델 lazy load
    if st.session_state["model"] is None:
        with st.spinner("🔄 모델 로딩 중..."):
            from models.detector import load_model
            st.session_state["model"] = load_model()

    model = st.session_state["model"]
    alerts, track_states = [], {}

    if model is not None:
        from models.detector import run_detection
        from logic.weapon import detect_weapons

        result = run_detection(model, frame, conf=conf)
        if result and result.boxes:
            weapons = detect_weapons(result.boxes, model.names)
            for w in weapons:
                frame = draw_weapon_box(frame, w["xyxy"], w["track_id"],
                                        w["cls_name"], w["conf"])
                alerts.append({
                    "track_id": w["track_id"], "event_type": "weapon",
                    "risk": "HIGH",
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "entry_count": 1, "dwell_seconds": 0,
                })
                track_states[w["track_id"]] = {"risk": "HIGH",
                                                "dwell_seconds": 0,
                                                "entry_count": 1}
    else:
        st.warning("⚠️ 모델 파일(weights/best.pt) 없음 — 더미 결과 표시")
        alerts = _demo_alerts()
        track_states = _demo_track_states()

    if roi:
        frame = draw_roi(frame, roi)

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame_placeholder.image(rgb, use_container_width=True)
    _render_panels(alerts, track_states)
    st.stop()


# 영상 처리 (프레임 스트리밍) 
with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
    tmp.write(uploaded_file.read())
    tmp_path = tmp.name

cap = cv2.VideoCapture(tmp_path)
if not cap.isOpened():
    st.error("영상 파일을 열 수 없습니다.")
    os.unlink(tmp_path)
    st.stop()

video_fps  = cap.get(cv2.CAP_PROP_FPS) or 25.0
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

# 모델 lazy load
if st.session_state["model"] is None:
    with st.spinner("🔄 모델 로딩 중..."):
        from models.detector import load_model
        st.session_state["model"] = load_model()

model = st.session_state["model"]
loitering_tracker: LoiteringTracker = st.session_state["loitering_tracker"]
loitering_tracker.reset_all()

track_states = {}
active_alerts = []
logged_ids = set()

prev_time = time.time()
frame_idx = 0

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame_idx += 1

    # 추론 
    weapons_detected = []
    person_boxes = []

    if model is not None:
        from models.detector import run_tracking
        result = run_tracking(model, frame, conf=conf)

        if result and result.boxes:
            weapons_detected = detect_weapons(result.boxes, model.names)

            for box in result.boxes:
                if box.id is None:
                    continue
                tid  = int(box.id[0].item())
                xyxy = box.xyxy[0].tolist()
                cx, cy = center_of_box(xyxy)
                inside = is_inside_roi(cx, cy, roi)

                lo_state = loitering_tracker.update(tid, inside, fps=video_fps)
                weapon_now = any(w["track_id"] == tid for w in weapons_detected)
                risk = calculate_risk(
                    lo_state["entry_count"],
                    lo_state["dwell_seconds"],
                    weapon_now,
                )
                status = ("Weapon"   if weapon_now else
                          "Loitering" if lo_state["is_loitering"] else "Normal")

                track_states[tid] = {
                    "risk": risk,
                    "dwell_seconds": lo_state["dwell_seconds"],
                    "entry_count": lo_state["entry_count"],
                }
                person_boxes.append((xyxy, tid, status, risk))

                # 이상행동 → alert 추가 (중복 방지: 5프레임마다)
                if status != "Normal" and (tid not in logged_ids or frame_idx % 75 == 0):
                    logged_ids.add(tid)
                    evt = "weapon" if weapon_now else "loitering"
                    alert_entry = {
                        "track_id": tid,
                        "event_type": evt,
                        "risk": risk,
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                        "entry_count": lo_state["entry_count"],
                        "dwell_seconds": lo_state["dwell_seconds"],
                    }
                    # 기존 동일 ID 교체
                    active_alerts = [a for a in active_alerts if a["track_id"] != tid]
                    active_alerts.insert(0, alert_entry)
                    if frame_idx % 150 == 0:
                        append_event(tid, evt, risk)

    else:
        # 모델 없음 → 더미
        track_states  = _demo_track_states()
        active_alerts = _demo_alerts()

    # 프레임 그리기 
    if roi:
        frame = draw_roi(frame, roi)

    for xyxy, tid, status, risk in person_boxes:
        frame = draw_person_box(frame, xyxy, tid, status, risk)

    for w in weapons_detected:
        frame = draw_weapon_box(frame, w["xyxy"], w["track_id"],
                                 w["cls_name"], w["conf"])

    # FPS 계산
    now = time.time()
    fps_val = 1.0 / max(now - prev_time, 1e-6)
    prev_time = now
    frame = draw_fps(frame, fps_val)

    # 카메라 이름
    cv2.putText(frame, camera_name,
                (frame.shape[1] - 120, 24),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                (80, 120, 180), 1, cv2.LINE_AA)

    # Streamlit 출력 
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    fps_placeholder.markdown(
        f"<span style='font-size:11px;color:#4b5563;'>"
        f"프레임 {frame_idx}/{total_frames} | FPS {fps_val:.1f}</span>",
        unsafe_allow_html=True,
    )
    frame_placeholder.image(rgb, use_container_width=True)

    # 패널은 매 30프레임마다 갱신 (성능)
    if frame_idx % 30 == 1:
        _render_panels(active_alerts, track_states)

    # Streamlit 멈춤 방지
    time.sleep(max(0, 1 / video_fps - (time.time() - now)))

cap.release()
os.unlink(tmp_path)

# 영상 종료 후 최종 패널 갱신
_render_panels(active_alerts, track_states)
st.success("✅ 영상 분석 완료")
