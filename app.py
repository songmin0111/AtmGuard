# 역할: 페이지 설정 / CSS 주입 / session_state 초기화 / 사이드바 / 라우팅
# 분석 로직·UI 상세는 각 모듈에 위임한다.

import streamlit as st

from config import PAGE_ICON, PAGE_TITLE
from inference import load_model
from state.session_state import init_session_state
from ui.sidebar import render_sidebar
from ui.styles import load_css

# 페이지 설정 (반드시 최상단) 
st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout="wide",
)

# CSS 주입 
load_css()

# session_state 초기화 
init_session_state()

# 모델 로드 (캐시) 
_model = None
try:
    _model = load_model()
except FileNotFoundError as e:
    st.error(str(e))
except Exception as e:
    st.error(f"모델 로드 중 오류: {e}")

# pages 가 session_state 를 통해 모델에 접근할 수 있도록 저장
st.session_state["_model"] = _model

# 사이드바 렌더링 
render_sidebar(_model)

# 페이지 라우팅 
page = st.session_state.get("page", "CCTV 모니터링")

if page == "CCTV 모니터링":
    from pages.cctv_page import render
    render()

elif page == "위험 이벤트":
    from pages.events_page import render
    render()

elif page == "통계 분석":
    from pages.stats_page import render
    render()
