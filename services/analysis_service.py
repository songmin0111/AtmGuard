# 영상 / 이미지 추론 

from __future__ import annotations

import os
import time
import tempfile

import cv2
import streamlit as st

from config import DEFAULT_CONF_THRESHOLD, WEAPON_CLASS_NAMES
from draw_utils import draw_roi, draw_person_box, draw_weapon_alert, draw_fps
from event_logic import LoiteringStateManager
from roi_utils import get_box_center, get_video_fps, is_center_inside_roi


def run_image_analysis(model, uploaded) -> None:
    if model is None:
        st.error("모델이 로드되지 않았습니다. weights/best.pt 를 확인해주세요.")
        return

    conf_threshold = st.sidebar.slider(
        "Confidence", 0.1, 0.9, DEFAULT_CONF_THRESHOLD, 0.05, key="img_conf",
    )

    suffix = os.path.splitext(uploaded.name)[-1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded.read())
        tmp_path = tmp.name

    frame = cv2.imread(tmp_path)
    if frame is None:
        st.error("이미지를 읽을 수 없습니다.")
        return

    from inference import run_tracking
    try:
        results, class_names = run_tracking(model, frame, conf_threshold)
    except Exception as exc:
        st.error(f"추론 오류: {exc}")
        return

    weapon_count = 0
    if results and results[0].boxes is not None:
        for box in results[0].boxes:
            cls_id   = int(box.cls[0].item())
            cls_name = class_names.get(cls_id, "")
            x1, y1, x2, y2 = [int(v) for v in box.xyxy[0]]
            conf  = float(box.conf[0])
            color = (0, 0, 220) if cls_name in WEAPON_CLASS_NAMES else (128, 128, 128)
            if cls_name in WEAPON_CLASS_NAMES:
                weapon_count += 1
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, f"{cls_name} {conf:.2f}", (x1, y1 - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2, cv2.LINE_AA)

    if weapon_count > 0:
        draw_weapon_alert(frame, weapon_count)

    st.image(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), use_column_width=True)
    if weapon_count:
        st.error(f"🚨 무기 {weapon_count}건 감지됨!")
    else:
        st.success("이상행동 없음 (이미지 단일 추론)")


def run_video_analysis(model, video_path: str, video_placeholder) -> None:
    """영상 루프. 이벤트 로그 패널 없이 video_placeholder 만 사용."""
    if model is None:
        st.error("모델이 로드되지 않았습니다.")
        return

    from inference import run_tracking

    conf_threshold = st.sidebar.slider(
        "Confidence", 0.1, 0.9, DEFAULT_CONF_THRESHOLD, 0.05, key="vid_conf",
    )

    roi: tuple = st.session_state.roi
    mgr: LoiteringStateManager = st.session_state.loitering_mgr
    video_fps   = get_video_fps(video_path)
    fps_history: list[float] = []

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        st.error("영상 파일을 열 수 없습니다.")
        return

    while cap.isOpened():
        t0 = time.perf_counter()
        ret, frame = cap.read()
        if not ret:
            break

        frame = frame.copy()
        
        mgr.next_frame()

        try:
            results, class_names = run_tracking(model, frame, conf_threshold)
        except Exception as exc:
            st.warning(f"추론 오류 (스킵): {exc}")
            continue

        weapon_count = 0
        weapon_boxes = []
        active_ids   = set()

        if results and len(results) > 0 and results[0].boxes is not None:
            for box in results[0].boxes:
                cls_id   = int(box.cls[0].item())
                cls_name = class_names.get(cls_id, "")

                if cls_name in WEAPON_CLASS_NAMES:
                    weapon_count += 1
                    x1, y1, x2, y2 = box.xyxy[0]
                    weapon_boxes.append((x1.item(), y1.item(), x2.item(), y2.item()))
                    continue

                if box.id is None:
                    continue

                track_id = int(box.id[0].item())
                x1, y1, x2, y2 = box.xyxy[0]
                bbox = (x1.item(), y1.item(), x2.item(), y2.item())
                cx, cy = get_box_center(bbox)
                inside = is_center_inside_roi(cx, cy, roi)
                mgr.update(track_id, bbox, inside, video_fps, frame)
                active_ids.add(track_id)

        all_ids = set(mgr.get_all_states().keys())
        for tid in all_ids - active_ids:
            mgr.mark_lost(tid)
        mgr.cleanup_lost()

        if weapon_count > 0:
            mgr.log_weapon_event(weapon_count)
        
        draw_roi(frame, roi)

        all_states = mgr.get_all_states()
        for tid in active_ids:
            if tid in all_states:
                draw_person_box(frame, all_states[tid])

        for wb in weapon_boxes:
            wx1, wy1, wx2, wy2 = [int(v) for v in wb]
            cv2.rectangle(frame, (wx1, wy1), (wx2, wy2), (0, 0, 220), 2)
            cv2.putText(frame, "WEAPON", (wx1, wy1 - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 220), 2, cv2.LINE_AA)

        if weapon_count > 0:
            draw_weapon_alert(frame, weapon_count)
        
        # 이벤트별 프레임 저장 (최대 30개, 480p 리사이즈)
        _save_event_frames(mgr, frame)

        elapsed = time.perf_counter() - t0
        cur_fps = 1.0 / elapsed if elapsed > 0 else 0.0
        fps_history.append(cur_fps)
        if len(fps_history) > 30:
            fps_history.pop(0)
        draw_fps(frame, sum(fps_history) / len(fps_history))

        video_placeholder.image(
            cv2.cvtColor(frame, cv2.COLOR_BGR2RGB),
            channels="RGB",
            use_column_width=True,
        )

    cap.release()
    st.session_state.fps_history             = fps_history
    st.session_state.tracking_stats_snapshot = mgr.get_stats()
    st.session_state.analysis_done           = True
    st.rerun()


MAX_EVENT_FRAMES = 30   # 메모리 절약: 최대 30개까지만 보관
FRAME_SAVE_WIDTH = 640  # 저장 해상도 (480p 수준)

def _save_event_frames(mgr, frame) -> None:
    """
    현재 프레임에서 이상행동/무기 이벤트가 새로 생겼으면
    해당 이벤트 인덱스에 리사이즈된 프레임을 저장한다.
    최대 MAX_EVENT_FRAMES 개 초과 시 오래된 항목 자동 삭제.
    """
    events = mgr.get_events()
    frames_dict: dict = st.session_state.get("event_frames", {})
    frame_risks: dict = st.session_state.get("event_frame_risks", {})

    RISK_ORDER = {
        "NORMAL": 0,
        "LOW": 1,
        "MED": 2,
        "HIGH": 3,
    }

    for idx, e in enumerate(events):
        prev_risk = frame_risks.get(idx, "NORMAL")
        
        should_save = (
            idx not in frames_dict
            or RISK_ORDER.get(e.risk_level, 0) > RISK_ORDER.get(prev_risk, 0)
        )

        if not should_save:
            continue

        # 새 이벤트 → 프레임 리사이즈 후 저장
        h, w = frame.shape[:2]
        scale = FRAME_SAVE_WIDTH / w
        small = cv2.resize(frame, (FRAME_SAVE_WIDTH, int(h * scale)))
        frames_dict[idx] = small.copy()
        frame_risks[idx] = e.risk_level

        # 최대 개수 초과 시 가장 오래된 것 삭제
        if len(frames_dict) > MAX_EVENT_FRAMES:
            oldest_key = min(frames_dict.keys())
            del frames_dict[oldest_key]
            frame_risks.pop(oldest_key, None)

    st.session_state.event_frames = frames_dict
    st.session_state.event_frame_risks = frame_risks


def show_analysis_summary() -> None:
    """분석 완료 후 메트릭 카드 4개만 표시. 표/트랙킹 통계 없음."""
    mgr: LoiteringStateManager = st.session_state.loitering_mgr
    events      = mgr.get_events()
    fps_history = st.session_state.fps_history

    st.success("✅ 영상 분석 완료")

    high_cnt   = sum(1 for e in events if e.risk_level == "HIGH")
    med_cnt    = sum(1 for e in events if e.risk_level == "MED")
    weapon_cnt = sum(1 for e in events if e.event_type == "weapon")
    avg_fps    = sum(fps_history) / len(fps_history) if fps_history else 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🔴 HIGH",  high_cnt)
    c2.metric("🟠 MED",   med_cnt)
    c3.metric("🔫 무기",  weapon_cnt)
    c4.metric("⚡ FPS",   f"{avg_fps:.1f}")
