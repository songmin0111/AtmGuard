# ──────────────────────────────────────────────
# app.py  —  ATM Guard MVP  Streamlit 진입점
# ──────────────────────────────────────────────

import os
import time
import cv2
import numpy as np
import streamlit as st
from PIL import Image
from streamlit_drawable_canvas import st_canvas

from config import (
    ALLOWED_VIDEO_EXTENSIONS,
    DEFAULT_CONF_THRESHOLD,
    CANVAS_WIDTH,
    WEAPON_CLASS_NAMES,
    RISK_COLORS_HEX,
    PAGE_TITLE,
    PAGE_ICON,
    SIDEBAR_TITLE,
    MED_DWELL_SECONDS,
    HIGH_DWELL_SECONDS,
    MED_ENTRY_COUNT,
    HIGH_ENTRY_COUNT,
    MODEL_PATH,
)
from inference import load_model, run_tracking
from roi_utils import (
    extract_first_frame,
    get_video_fps,
    save_uploaded_video,
    convert_canvas_rect_to_original,
    get_box_center,
    is_center_inside_roi,
)
from event_logic import LoiteringStateManager
from draw_utils import draw_roi, draw_person_box, draw_weapon_alert, draw_fps


# ══════════════════════════════════════════════
# 페이지 설정
# ══════════════════════════════════════════════
st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout="wide",
)


# ══════════════════════════════════════════════
# Session State 초기화
# ══════════════════════════════════════════════
def _init_session_state():
    defaults = {
        "roi": None,                  # (x1,y1,x2,y2) 원본 좌표
        "first_frame": None,          # np.ndarray BGR
        "analysis_started": False,
        "current_video_id": None,     # 업로드 파일명 + 크기로 구분
        "events": [],                 # EventLog 리스트
        "loitering_mgr": None,        # LoiteringStateManager 인스턴스
        "video_path": None,           # 임시 저장 경로
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _reset_analysis():
    """ROI + 분석 상태만 초기화 (영상은 유지)."""
    st.session_state.roi              = None
    st.session_state.analysis_started = False
    st.session_state.events           = []
    st.session_state.loitering_mgr    = LoiteringStateManager()


def _full_reset():
    """영상 포함 전체 초기화."""
    _reset_analysis()
    st.session_state.first_frame      = None
    st.session_state.current_video_id = None
    st.session_state.video_path       = None


_init_session_state()


# ══════════════════════════════════════════════
# 모델 로드 (캐싱)
# ══════════════════════════════════════════════
model = None
try:
    model = load_model()
except FileNotFoundError as e:
    st.error(str(e))
except Exception as e:
    st.error(f"모델 로드 중 오류가 발생했습니다: {e}")


# ══════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════
with st.sidebar:
    st.title(SIDEBAR_TITLE)
    st.markdown("---")

    conf_threshold = st.slider(
        "Confidence Threshold",
        min_value=0.1,
        max_value=0.9,
        value=DEFAULT_CONF_THRESHOLD,
        step=0.05,
        help=(
            "임계값을 높이면 더 확실한 객체만 탐지하지만 "
            "놓치는 객체가 늘어날 수 있습니다. "
            "오탐을 줄이고 싶으면 값을 높이세요."
        ),
    )

    st.markdown("---")
    st.subheader("Loitering 위험도 기준")
    st.markdown(
        f"""
| 위험도 | 조건 |
|--------|------|
| 🟢 LOW  | ROI 진입 |
| 🟠 MED  | 체류 **{MED_DWELL_SECONDS}초** 이상 또는 진입 **{MED_ENTRY_COUNT}회** 이상 |
| 🔴 HIGH | 체류 **{HIGH_DWELL_SECONDS}초** 이상 또는 진입 **{HIGH_ENTRY_COUNT}회** 이상 |
        """
    )

    st.markdown("---")
    st.subheader("모델 정보")
    model_ok = os.path.exists(MODEL_PATH)
    st.markdown(
        f"{'✅' if model_ok else '❌'} `{MODEL_PATH}`"
    )
    if model is not None:
        st.subheader("감지 클래스")
        for cls_id, cls_name in model.names.items():
            st.markdown(f"- `{cls_id}`: {cls_name}")


# ══════════════════════════════════════════════
# 메인 영역 헤더
# ══════════════════════════════════════════════
st.title("🛡️ ATM Guard — 이상행동 감지 시스템")
st.caption("CCTV 영상을 업로드하고, ATM 주변 ROI를 지정하면 자동으로 분석을 시작합니다.")
st.markdown("---")


# ══════════════════════════════════════════════
# STEP 1 : 영상 업로드
# ══════════════════════════════════════════════
uploaded = st.file_uploader(
    "📂 CCTV 영상 업로드",
    type=["mp4", "avi", "mov"],
    help="mp4 / avi / mov 파일만 지원합니다.",
)

if uploaded is None:
    st.info("분석할 CCTV 영상을 업로드해주세요.")
    st.stop()

# 확장자 이중 검증
ext = os.path.splitext(uploaded.name)[-1].lower()
if ext not in ALLOWED_VIDEO_EXTENSIONS:
    st.error("지원하지 않는 파일 형식입니다. mp4, avi, mov 파일만 업로드해주세요.")
    st.stop()

# 새 영상이면 전체 초기화
video_id = f"{uploaded.name}_{uploaded.size}"
if st.session_state.current_video_id != video_id:
    _full_reset()
    st.session_state.current_video_id = video_id
    # 임시 파일로 저장
    video_path = save_uploaded_video(uploaded)
    st.session_state.video_path = video_path
    # 첫 프레임 추출
    first_frame = extract_first_frame(video_path)
    if first_frame is None:
        st.error("영상에서 첫 프레임을 읽을 수 없습니다. 다른 영상을 업로드해주세요.")
        st.stop()
    st.session_state.first_frame = first_frame
    st.session_state.loitering_mgr = LoiteringStateManager()

video_path   = st.session_state.video_path
first_frame  = st.session_state.first_frame


# ══════════════════════════════════════════════
# STEP 2 : ROI 설정 (분석 전)
# ══════════════════════════════════════════════
if not st.session_state.analysis_started:
    st.subheader("📍 ATM 주변 ROI 설정")
    st.info(
        "아래 영상 위에서 **마우스로 드래그**하여 ATM 접근 구역을 지정하세요. "
        "사각형을 그리면 즉시 분석이 시작됩니다."
    )

    orig_h, orig_w = first_frame.shape[:2]

    # canvas 크기 계산 (비율 유지)
    canvas_w = min(CANVAS_WIDTH, orig_w)
    canvas_h = int(orig_h * canvas_w / orig_w)

    # PIL 이미지 변환 (매번 새로 생성 → background_image 오류 방지)
    frame_rgb  = cv2.cvtColor(first_frame, cv2.COLOR_BGR2RGB)
    pil_image  = Image.fromarray(frame_rgb).resize((canvas_w, canvas_h))

    canvas_result = st_canvas(
        fill_color="rgba(0, 180, 255, 0.15)",
        stroke_width=2,
        stroke_color="#00b4ff",
        background_image=pil_image,
        update_streamlit=True,
        height=canvas_h,
        width=canvas_w,
        drawing_mode="rect",
        key="roi_canvas",
    )

    # ROI 추출
    if (
        canvas_result.json_data is not None
        and len(canvas_result.json_data.get("objects", [])) > 0
    ):
        objects = canvas_result.json_data["objects"]
        # 마지막 사각형 사용
        last_obj = objects[-1]
        roi = convert_canvas_rect_to_original(
            last_obj, canvas_w, canvas_h, orig_w, orig_h
        )
        if roi is not None:
            st.session_state.roi = roi
            st.session_state.analysis_started = True
            st.success(f"✅ ROI 설정 완료: {roi}  →  분석을 시작합니다!")
            st.rerun()
        else:
            st.warning("ROI가 너무 작습니다. 더 크게 드래그해주세요.")
    else:
        st.warning("먼저 ATM 주변 영역을 ROI로 드래그해서 지정해주세요.")

    st.stop()


# ══════════════════════════════════════════════
# STEP 3 : 영상 분석 루프
# ══════════════════════════════════════════════
roi = st.session_state.roi
mgr: LoiteringStateManager = st.session_state.loitering_mgr

if model is None:
    st.error("모델이 로드되지 않았습니다. weights/best.pt 를 확인해주세요.")
    st.stop()

col_video, col_info = st.columns([3, 1])

with col_video:
    st.subheader("🎥 실시간 분석")
    if st.button("🔄 ROI 재설정", key="reset_btn"):
        _reset_analysis()
        st.rerun()
    video_placeholder = st.empty()

with col_info:
    st.subheader("🚨 이벤트 로그")
    event_placeholder = st.empty()

# ── FPS 계산용 변수 ────────────────────────────
video_fps   = get_video_fps(video_path)
fps_history = []
frame_times = []

cap = cv2.VideoCapture(video_path)
if not cap.isOpened():
    st.error("영상 파일을 열 수 없습니다.")
    st.stop()

roi_x1, roi_y1, roi_x2, roi_y2 = roi

while cap.isOpened():
    t0 = time.perf_counter()

    ret, frame = cap.read()
    if not ret:
        break  # 영상 끝

    # 원본 프레임 복사 → overlay 잔상 방지
    frame = frame.copy()

    # ── YOLO + ByteTrack 추론 ──────────────────
    try:
        results, class_names = run_tracking(model, frame, conf_threshold)
    except Exception as e:
        st.warning(f"추론 오류 (프레임 스킵): {e}")
        continue

    # ── per-frame 초기화 ───────────────────────
    weapon_count = 0
    weapon_boxes = []          # 이번 프레임 weapon bbox 목록
    active_track_ids = set()   # 이번 프레임에 실제 감지된 ID만

    if results and len(results) > 0:
        boxes = results[0].boxes

        if boxes is not None and len(boxes) > 0:
            for box in boxes:
                cls_id   = int(box.cls[0].item())
                cls_name = class_names.get(cls_id, "")

                # ── 1) Weapon 감지 (track_id 없어도 OK) ──
                if cls_name in WEAPON_CLASS_NAMES:
                    weapon_count += 1
                    x1, y1, x2, y2 = box.xyxy[0]
                    weapon_boxes.append((x1.item(), y1.item(), x2.item(), y2.item()))
                    continue

                # ── 2) track_id 없는 객체는 loitering 스킵 ──
                if box.id is None:
                    continue

                track_id = int(box.id[0].item())
                x1, y1, x2, y2 = box.xyxy[0]
                bbox = (x1.item(), y1.item(), x2.item(), y2.item())
                cx, cy = get_box_center(bbox)
                current_inside = is_center_inside_roi(cx, cy, roi)

                # ── 3) Loitering 상태 업데이트 ─────────
                mgr.update(track_id, bbox, current_inside, video_fps)
                active_track_ids.add(track_id)

    # weapon 이벤트 로깅
    if weapon_count > 0:
        mgr.log_weapon_event(weapon_count)

    # ── Overlay 그리기 ─────────────────────────
    draw_roi(frame, roi)

    # 이번 프레임에 감지된 ID만 bbox 표시 (잔상 방지)
    all_states = mgr.get_all_states()
    for tid in active_track_ids:
        if tid in all_states:
            draw_person_box(frame, all_states[tid])

    # weapon bbox 표시
    for wb in weapon_boxes:
        wx1, wy1, wx2, wy2 = [int(v) for v in wb]
        cv2.rectangle(frame, (wx1, wy1), (wx2, wy2), (0, 0, 220), 2)
        cv2.putText(frame, "WEAPON", (wx1, wy1 - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 220), 2, cv2.LINE_AA)

    if weapon_count > 0:
        draw_weapon_alert(frame, weapon_count)

    # FPS 계산
    elapsed = time.perf_counter() - t0
    cur_fps = 1.0 / elapsed if elapsed > 0 else 0.0
    fps_history.append(cur_fps)
    if len(fps_history) > 30:
        fps_history.pop(0)
    avg_fps = sum(fps_history) / len(fps_history)

    draw_fps(frame, avg_fps)

    # ── Streamlit 에 프레임 출력 ───────────────
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    video_placeholder.image(frame_rgb, channels="RGB", use_column_width=True)

    # ── 이벤트 로그 (MED/HIGH만 표시) ──────────
    import pandas as pd
    events = mgr.get_events()
    important = [e for e in events if e.risk_level in ("MED", "HIGH")]
    if important:
        ev_rows = []
        for e in reversed(important[-10:]):
            ev_rows.append({
                "시각": e.timestamp,
                "ID": f"#{e.track_id}" if e.track_id >= 0 else "WEAPON",
                "유형": "서성거림" if e.event_type == "loitering" else "무기탐지",
                "위험도": e.risk_level,
            })
        event_placeholder.dataframe(
            pd.DataFrame(ev_rows), hide_index=True, use_container_width=True
        )

cap.release()

# ── 분석 완료 요약 ─────────────────────────────
st.success("✅ 영상 분석이 완료되었습니다.")
st.markdown("---")
st.subheader("📋 분석 요약")

events = mgr.get_events()
high_cnt   = sum(1 for e in events if e.risk_level == "HIGH")
med_cnt    = sum(1 for e in events if e.risk_level == "MED")
weapon_cnt = sum(1 for e in events if e.event_type == "weapon")
avg_fps_final = sum(fps_history) / len(fps_history) if fps_history else 0.0

c1, c2, c3, c4 = st.columns(4)
c1.metric("🔴 HIGH 이벤트", high_cnt)
c2.metric("🟠 MED 이벤트",  med_cnt)
c3.metric("🔫 Weapon 감지", weapon_cnt)
c4.metric("⚡ 평균 FPS",   f"{avg_fps_final:.1f}")

if events:
    import pandas as pd
    final_rows = [
        {
            "시각":    e.timestamp,
            "ID":     f"#{e.track_id}" if e.track_id >= 0 else "WEAPON",
            "유형":   "서성거림" if e.event_type == "loitering" else "무기탐지",
            "위험도": e.risk_level,
            "체류(s)": f"{e.dwell_seconds:.1f}",
            "진입횟수": e.entry_count,
        }
        for e in events
    ]
    st.dataframe(pd.DataFrame(final_rows), hide_index=True, use_container_width=True)
else:
    st.info("감지된 이상행동 이벤트가 없습니다.")

# ROI 재설정 (분석 후)
if st.button("🔄 다시 분석하기"):
    _reset_analysis()
    st.rerun()