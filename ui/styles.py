# CSS 파일을 읽어 Streamlit에 주입하는 로더

import os
import streamlit as st


def load_css(css_path: str = None) -> None:
    """
    assets/styles.css 를 읽어 st.markdown 으로 주입한다.
    css_path 를 지정하지 않으면 이 파일 기준으로 ../assets/styles.css 를 사용한다.
    """
    if css_path is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        css_path = os.path.join(base_dir, "assets", "styles.css")

    if not os.path.exists(css_path):
        st.warning(f"CSS 파일을 찾을 수 없습니다: {css_path}")
        return

    with open(css_path, "r", encoding="utf-8") as f:
        css_content = f.read()

    st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
