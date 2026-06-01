# ATM GUARD 메인 Streamlit 앱
import cv2
import time
import tempfile
import os
from datetime import datetime

import numpy as np
import streamlit as st

# 모델 관련
from models.detector import (
    load_model,
    run_detection,
    run_tracking
)

# 이상행동 로직
from logic.loitering import LoiteringTracker
from logic.weapon import detect_weapons
from logic.risk import calculate_risk

# 시각화
from utils.draw import (
    draw_roi,
    draw_person_box,
    draw_weapon_box,
    draw_fps
)

# roi 계산
from utils.roi import (
    center_of_box, # 객체 중심좌표 계산
    is_inside_roi # roi 내부 여부 판단
)

# 로그 저장
from utils.logger import append_event


# UI 패널
from ui.alert_panel import (
    render_alert_panel,
    render_risk_gauges
)

from ui.stats import (
    render_event_log,
    render_hourly_chart
)


# streamlit 기본 설정
st.set_page_config(
    page_title="ATM GUARD",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 최초 1회만 생성할 객체(session 유지)
# yolo 모델 로딩
if "model" not in st.session_state:
    st.session_state.model=load_model()

# 서성거림 상태
if "tracker" not in st.session_state:
    st.session_state.tracker=LoiteringTracker()

# roi 정보
if "roi" not in st.session_state:
    st.session_state.roi=None

# 현재 경고 목록
if "alerts" not in st.session_state:
    st.session_state.alerts=[]

# id별 상태 저장
if "track_states" not in st.session_state:
    st.session_state.track_states={}


model=st.session_state.model
tracker=st.session_state.tracker

st.title("🛡️ ATM GUARD")

# 업로드
uploaded = st.file_uploader(
    "영상 / 이미지 업로드",
    type=["mp4", "avi", "png", "jpg", "jpeg"]
)

# 업로드 아래 설정 영역 병렬 배치
conf_col, roi_col = st.columns([1, 2])

with conf_col:
    conf = st.slider("Confidence", 0.1, 1.0, 0.4)

with roi_col:
    st.markdown("### ROI 설정")
    row1 = st.columns(2)
    
    with row1[0]:
        x1 = st.number_input("ROI x1", 0, 2000, 200)

    with row1[1]:
        y1 = st.number_input("ROI y1", 0, 2000, 100)

    row2 = st.columns(2)

    with row2[0]:
        x2 = st.number_input("ROI x2", 0, 2000, 500)

    with row2[1]:
        y2 = st.number_input("ROI y2", 0, 2000, 400)
    
roi = (x1, y1, x2, y2) if (x2 > x1 and y2 > y1) else None
st.session_state.roi = roi

# UI 영역 생성
video_area = st.empty()
st.divider()

bottom1,bottom2=st.columns([2,1])
# 하단 로그
log_area=bottom1.empty()

# 통계 그래프
chart_area=bottom2.empty()
panel1,panel2=st.columns([1,1])

# 알림 패널
alert_area=panel1.empty()

# 위험도 패널
risk_area=panel2.empty()

# 초기 렌더
with log_area:
    render_event_log()

with alert_area:
    render_alert_panel(st.session_state.alerts)  # 초기엔 [] 이므로 "정상 운영" 표시됨

with risk_area:
    render_risk_gauges(st.session_state.track_states)

# 우측 패널 - 업데이트 함수 -> 우측/하단 패널 일괄 갱신: 루프 끝난 후 호출
def update_ui():

    # 이상행동 카드 갱신
    with alert_area:
        render_alert_panel(st.session_state.alerts)

    # 위험도 패널 갱신
    with risk_area:
        render_risk_gauges(st.session_state.track_states)
        
    with log_area:
        render_event_log()

    with chart_area:
        render_hourly_chart()

# 업로드 없으면 대기
if uploaded is None:
    st.info("영상을 업로드하세요")
    st.stop()


# 이미지 OR 영상
suffix=uploaded.name.split(".")[-1].lower()
is_image=suffix.lower() in ["png","jpg","jpeg"]


# 이미지 처리
if is_image:

    file_bytes=np.frombuffer(uploaded.read(), np.uint8)
    frame=cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

    roi=st.session_state.roi
    result=run_detection(model, frame, conf)
    alerts=[]
    
    if result is not None:
        weapons = detect_weapons(result.boxes, model.names)

        for w in weapons:
            frame = draw_weapon_box(
                frame, w["xyxy"], w["track_id"], w["cls_name"], w["conf"]
            )
            alerts.append({
                "track_id":    w["track_id"],
                "event_type":  "weapon",
                "risk":        "HIGH",
                "entry_count": 1,
                "dwell_seconds": 0
            })

    if roi:
        frame = draw_roi(frame, roi)

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    video_area.image(rgb, width=700)

    st.session_state.alerts = alerts
    st.session_state.track_states = {}
    update_ui()
    st.stop()
    

# 영상 처리
# tempfile을 with 블록으로 관리
tmp_path = None
cap = None

try:
    # 임시파일 저장
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
        tmp.write(uploaded.read())
        tmp_path = tmp.name

    cap = cv2.VideoCapture(tmp_path)

    fps_video = cap.get(cv2.CAP_PROP_FPS)
    if fps_video <= 0:
        fps_video = 25.0

    # 새 영상 → tracker 초기화
    tracker.state = {}

    frame_count = 0
    prev_time   = time.time()

    # 누적 alerts / track_states (루프 전체에서 최신 상태 유지)
    alerts       = []
    track_states = {}

    # 프레임 루프
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        roi = st.session_state.roi

        result = run_tracking(model, frame, conf)

        frame_alerts  = []
        frame_weapons = []

        if result is not None:
            frame_weapons = detect_weapons(result.boxes, model.names)

            for box in result.boxes:
                if box.id is None:
                    continue

                tid  = int(box.id[0])
                xyxy = box.xyxy[0].tolist()
                cx, cy = center_of_box(xyxy)
                inside = is_inside_roi(cx, cy, roi)

                state = tracker.update(tid, inside, fps_video)

                has_weapon = any(w["track_id"] == tid for w in frame_weapons)
                risk = calculate_risk(
                    state["entry_count"],
                    state["dwell_seconds"],
                    has_weapon
                )

                if has_weapon:
                    status = "Weapon"
                elif state["is_loitering"]:
                    status = "Loitering"
                else:
                    status = "Normal"

                frame = draw_person_box(frame, xyxy, tid, status, risk)

                track_states[tid] = {
                    "risk":          risk,
                    "entry_count":   state["entry_count"],
                    "dwell_seconds": state["dwell_seconds"]
                }

                if status != "Normal":
                    frame_alerts.append({
                        "track_id":      tid,
                        "event_type":    status.lower(),
                        "risk":          risk,
                        "entry_count":   state["entry_count"],
                        "dwell_seconds": state["dwell_seconds"],
                        "timestamp":     datetime.now().strftime("%H:%M:%S")
                    })

        if roi:
            frame = draw_roi(frame, roi)

        for w in frame_weapons:
            frame = draw_weapon_box(
                frame, w["xyxy"], w["track_id"], w["cls_name"], w["conf"]
            )

        # FPS 계산 0 나누기 방지
        now      = time.time()
        elapsed  = now - prev_time
        fps_now  = 1.0 / elapsed if elapsed > 0 else 0.0
        prev_time = now

        frame = draw_fps(frame, fps_now)
        rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # 영상 프레임은 매 프레임 갱신
        video_area.image(rgb, width=700)

        # session_state 갱신은 하되
        # update_ui()는 루프 안에서 호출하지 않음
        # -> Streamlit 재실행 트리거 방지
        if frame_alerts:
            alerts = frame_alerts   # 최신 alert로 교체
        st.session_state.alerts       = alerts
        st.session_state.track_states = track_states

except Exception as e:
    st.error(f"영상 처리 중 오류 발생: {e}")

finally:
    if cap is not None:
        cap.release()
    if tmp_path and os.path.exists(tmp_path):
        try:
            os.remove(tmp_path)
        except Exception:
            pass  # 삭제 실패해도 앱은 계속 동작

# 루프 종료 후 UI 최종 갱신 
update_ui()
st.success("✅ 분석 완료")
