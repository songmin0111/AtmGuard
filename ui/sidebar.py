# 사이드바 네비게이션

import streamlit as st

from config import (
    MED_DWELL_SECONDS,
    HIGH_DWELL_SECONDS,
    MED_ENTRY_COUNT,
    HIGH_ENTRY_COUNT,
)
from event_logic import LoiteringStateManager


def render_sidebar(model) -> None:
    with st.sidebar:
        _render_logo()
        _render_nav()
        st.markdown('<hr style="border-color:#1e293b;margin:16px 0;">', unsafe_allow_html=True)
        _render_risk_legend()


def _render_logo() -> None:
    st.markdown("""
    <div style="padding:16px 8px 8px 8px;">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">
            <div style="background:#1d4ed8;border-radius:8px;width:34px;height:34px;
                        display:flex;align-items:center;justify-content:center;font-size:18px;">🛡️</div>
            <div>
                <div style="font-weight:800;font-size:1.05rem;color:#f1f5f9;">ATM Guard</div>
                <div style="font-size:0.72rem;color:#94a3b8;">ATM 이상행동 감지 시스템</div>
            </div>
        </div>
    </div>
    <hr style="border-color:#1e293b;margin:10px 0 14px 0;">
    <div style="font-size:0.7rem;color:#475569;letter-spacing:.08em;padding:0 4px 6px 4px;">메뉴</div>
    """, unsafe_allow_html=True)


def _render_nav() -> None:
    mgr: LoiteringStateManager = st.session_state.get("loitering_mgr")
    events = mgr.get_events() if mgr else []
    unconfirmed = sum(
        1 for e in events
        if e.response_status == "미확인" and e.risk_level in ("MED", "HIGH")
    )

    pages = ["CCTV 모니터링", "위험 이벤트", "통계 분석"]
    icons = ["🖥️", "⚠️", "📊"]

    for icon, pg in zip(icons, pages):
        badge = f" 🔴{unconfirmed}" if (pg == "위험 이벤트" and unconfirmed > 0) else ""
        label = f"{icon}  {pg}{badge}"
        is_active = st.session_state.get("page") == pg

        container = st.container()
        with container:
            if is_active:
                st.markdown('<div class="nav-active">', unsafe_allow_html=True)
            if st.button(label, key=f"nav_{pg}"):
                st.session_state.page = pg
                st.rerun()
            if is_active:
                st.markdown("</div>", unsafe_allow_html=True)


def _render_risk_legend() -> None:
    st.markdown(f"""
    <div style="font-size:0.7rem;color:#475569;letter-spacing:.08em;padding:0 4px 6px 4px;">위험도 기준</div>
    <div style="font-size:0.8rem;padding:0 4px;line-height:1.8;">
        <span style="color:#4ade80;">● LOW</span> — ROI 진입<br>
        <span style="color:#fb923c;">● MED</span> — 체류 {MED_DWELL_SECONDS}s↑ 또는 진입 {MED_ENTRY_COUNT}회↑<br>
        <span style="color:#f87171;">● HIGH</span> — 체류 {HIGH_DWELL_SECONDS}s↑ 또는 진입 {HIGH_ENTRY_COUNT}회↑
    </div>
    """, unsafe_allow_html=True)
