# CCTV 모니터링 페이지

import os
import time

import cv2
import streamlit as st
from PIL import Image
from streamlit_drawable_canvas import st_canvas

from config import CANVAS_WIDTH
from event_logic import LoiteringStateManager
from roi_utils import (
    convert_canvas_rect_to_original,
    extract_first_frame,
    save_uploaded_video,
)
from services.analysis_service import run_image_analysis, run_video_analysis, show_analysis_summary
from state.session_state import full_reset, reset_analysis

IMAGE_EXTS = {".jpg", ".jpeg", ".png"}
VIDEO_EXTS = {".mp4", ".avi", ".mov"}


def render() -> None:
    st.markdown('<div class="section-title">CCTV 모니터링</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-sub">CCTV 영상 분석 결과를 확인합니다.</div>',
        unsafe_allow_html=True,
    )

    uploaded = st.file_uploader(
        "영상 / 이미지 업로드",
        type=["mp4", "avi", "mov", "jpg", "jpeg", "png"],
        help="지원 형식: mp4, avi, mov, jpg, jpeg, png",
        label_visibility="collapsed",
    )

    if uploaded is None:
        _render_upload_hint()
        return

    ext = os.path.splitext(uploaded.name)[-1].lower()
    if ext not in IMAGE_EXTS | VIDEO_EXTS:
        st.error(f"지원하지 않는 파일 형식입니다: {ext}")
        return

    if ext in IMAGE_EXTS:
        model = st.session_state.get("_model")
        run_image_analysis(model, uploaded)
        return

    _handle_video(uploaded)


def _render_upload_hint() -> None:
    st.markdown("""
    <div class="upload-hint">
        <div style="font-size:3rem;margin-bottom:12px;">🖥️</div>
        <div style="font-weight:700;font-size:1.1rem;color:#0f172a;margin-bottom:8px;">
            분석할 CCTV 영상을 업로드하세요
        </div>
        <div style="color:#64748b;font-size:0.88rem;">
            영상 또는 이미지를 업로드하면 이상행동 분석 결과가 표시됩니다.
        </div>
        <div style="margin-top:20px;font-size:0.78rem;color:#94a3b8;">
            지원 형식 · 영상: mp4 / avi / mov &nbsp;|&nbsp; 이미지: jpg / jpeg / png
        </div>
    </div>
    """, unsafe_allow_html=True)


def _handle_video(uploaded) -> None:
    video_id = f"{uploaded.name}_{uploaded.size}"

    if st.session_state.current_video_id != video_id:
        full_reset()
        st.session_state.current_video_id = video_id
        video_path = save_uploaded_video(uploaded)
        st.session_state.video_path = video_path

        first_frame = extract_first_frame(video_path)
        if first_frame is None:
            st.error("영상에서 첫 프레임을 읽을 수 없습니다.")
            return

        st.session_state.first_frame   = first_frame
        st.session_state.loitering_mgr = LoiteringStateManager()

    video_path  = st.session_state.video_path
    first_frame = st.session_state.first_frame

    # 단계 1: ROI 설정
    if not st.session_state.analysis_started:
        _render_roi_canvas(first_frame)
        return

    # 단계 2: 분석 완료 → 메트릭만, 표/트랙킹통계 없음
    if st.session_state.analysis_done:
        show_analysis_summary()
        if st.button("🔄 다시 분석하기"):
            reset_analysis()
            st.rerun()
        return

    # 단계 3: 영상 분석 루프
    _render_video_loop(video_path)


def _render_roi_canvas(first_frame) -> None:
    st.subheader("✂️ ATM 주변 ROI 설정")
    st.info("아래 영상 위에서 마우스로 드래그하여 ATM 접근 구역을 지정하세요.")

    orig_h, orig_w = first_frame.shape[:2]
    canvas_w = min(CANVAS_WIDTH, orig_w)
    canvas_h = int(orig_h * canvas_w / orig_w)

    frame_rgb = cv2.cvtColor(first_frame, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(frame_rgb).resize((canvas_w, canvas_h))

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

    if (
        canvas_result.json_data is not None
        and len(canvas_result.json_data.get("objects", [])) > 0
    ):
        last_obj = canvas_result.json_data["objects"][-1]
        roi = convert_canvas_rect_to_original(
            last_obj, canvas_w, canvas_h, orig_w, orig_h
        )
        if roi is not None:
            st.session_state.roi              = roi
            st.session_state.analysis_started = True
            st.success("✅ ROI 설정 완료 → 분석 시작!")
            st.rerun()
        else:
            st.warning("ROI가 너무 작습니다. 더 크게 드래그해주세요.")


def _render_video_loop(video_path: str) -> None:
    model = st.session_state.get("_model")

    if st.button("🔄 ROI 재설정", key=f"reset_btn_{int(time.time() * 1000)}"):
        reset_analysis()
        st.rerun()

    # 영상만 전체 너비로 표시, 이벤트 로그 없음
    video_placeholder = st.empty()
    run_video_analysis(model, video_path, video_placeholder)
