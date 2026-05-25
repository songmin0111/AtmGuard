# ui/sidebar.py
"""
사이드바: 입력 소스 선택 (영상 업로드 / 이미지 업로드)
+ ROI 좌표 수동 입력
+ 시스템 설정 (confidence, entry_threshold)
"""

import streamlit as st


def render_sidebar() -> dict:
    """
    사이드바 렌더링.
    returns: {
        "mode"             : "video" | "image" | None,
        "uploaded_file"    : UploadedFile | None,
        "roi"              : (x1, y1, x2, y2) | None,
        "conf"             : float,
        "entry_threshold"  : int,
        "camera_name"      : str,
    }
    """
    with st.sidebar:
        st.markdown(
            """
            <div style='
                display:flex; align-items:center; gap:10px;
                padding: 12px 0 20px 0; border-bottom: 1px solid #e2e8f0;
                margin-bottom: 20px;
            '>
                <span style='font-size:22px;'>🛡️</span>
                <div>
                    <div style='font-size:17px; font-weight:700;
                         letter-spacing:.04em; color:#1d4ed8;'>ATM GUARD</div>
                    <div style='font-size:11px; color:#6b7280;
                         letter-spacing:.08em;'>ATM 이상행동 감지 시스템</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 카메라 이름 
        camera_name = st.text_input("📷 카메라 이름", value="CAM-01", key="camera_name")

        st.markdown("---")

        # 입력 소스 선택 
        st.markdown("#### 📂 입력 소스 선택")
        mode = st.radio(
            "",
            options=["영상 업로드", "이미지 업로드"],
            horizontal=True,
            key="input_mode",
            label_visibility="collapsed",
        )

        uploaded_file = None
        if mode == "영상 업로드":
            uploaded_file = st.file_uploader(
                "mp4 / avi 파일 업로드",
                type=["mp4", "avi", "mov"],
                key="video_uploader",
            )
        else:
            uploaded_file = st.file_uploader(
                "jpg / png 파일 업로드",
                type=["jpg", "jpeg", "png"],
                key="image_uploader",
            )

        st.markdown("---")

        # ROI 설정 
        st.markdown("#### 📍 ROI (ATM 영역) 설정")
        st.caption("ATM 기기가 위치한 픽셀 좌표를 입력하세요.")

        col1, col2 = st.columns(2)
        with col1:
            roi_x1 = st.number_input("x1", value=200, step=10, key="roi_x1")
            roi_y1 = st.number_input("y1", value=100, step=10, key="roi_y1")
        with col2:
            roi_x2 = st.number_input("x2", value=500, step=10, key="roi_x2")
            roi_y2 = st.number_input("y2", value=400, step=10, key="roi_y2")

        roi = (roi_x1, roi_y1, roi_x2, roi_y2) if roi_x2 > roi_x1 and roi_y2 > roi_y1 else None

        st.markdown("---")

        # 탐지 설정 
        st.markdown("#### ⚙️ 탐지 설정")
        conf = st.slider("Confidence Threshold", 0.1, 0.9, 0.4, 0.05, key="conf")
        entry_threshold = st.slider(
            "서성거림 판단 진입 횟수", 2, 10, 5, 1, key="entry_threshold"
        )

        st.markdown("---")
        st.caption("© ATM GUARD · Computer Vision Project")

    mode_key = "video" if mode == "영상 업로드" else "image"

    return {
        "mode": mode_key,
        "uploaded_file": uploaded_file,
        "roi": roi,
        "conf": conf,
        "entry_threshold": entry_threshold,
        "camera_name": camera_name,
    }
