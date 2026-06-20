# 통계 분석 페이지

import plotly.graph_objects as go
import streamlit as st

from event_logic import LoiteringStateManager


def _dedupe_events(events: list) -> list:
    """
    통계용 이벤트 중복 제거.
    같은 사람 track_id는 가장 높은 위험도 이벤트 1개만 남기고,
    weapon 이벤트는 별도 사건으로 유지한다.
    """
    RISK_ORDER = {
        "NORMAL": 0,
        "LOW": 1,
        "MED": 2,
        "HIGH": 3,
    }

    best_by_track = {}
    weapon_events = []

    for e in events:
        # 무기 이벤트는 track_id가 -1이므로 별도 사건으로 유지
        if e.track_id < 0:
            weapon_events.append(e)
            continue

        prev = best_by_track.get(e.track_id)

        if prev is None:
            best_by_track[e.track_id] = e
            continue

        prev_score = RISK_ORDER.get(prev.risk_level, 0)
        curr_score = RISK_ORDER.get(e.risk_level, 0)

        # 같은 track_id면 더 높은 위험도만 남김
        if curr_score >= prev_score:
            best_by_track[e.track_id] = e

    return weapon_events + list(best_by_track.values())


def render() -> None:
    st.markdown('<div class="section-title">통계 분석</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-sub">위험도 분포를 확인합니다.</div>',
        unsafe_allow_html=True,
    )

    mgr: LoiteringStateManager = st.session_state.loitering_mgr

    raw_events = mgr.get_events()
    events = _dedupe_events(raw_events)

    _render_summary_metrics(events)
    st.markdown("<br>", unsafe_allow_html=True)

    _render_risk_pie(events)


def _render_summary_metrics(events: list) -> None:
    total_events = len(events)
    high_cnt = sum(1 for e in events if e.risk_level == "HIGH")

    dwell_vals = [
        e.dwell_seconds
        for e in events
        if e.dwell_seconds > 0
    ]
    avg_dwell = sum(dwell_vals) / max(len(dwell_vals), 1)

    false_rate = round(
        sum(1 for e in events if e.response_status == "오탐")
        / max(total_events, 1)
        * 100,
        1,
    )

    avg_m = int(avg_dwell // 60)
    avg_s = int(avg_dwell % 60)

    cols = st.columns(4)
    metrics = [
        (total_events, "오늘 감지 이벤트"),
        (high_cnt, "HIGH 이벤트"),
        (f"{avg_m}m {avg_s:02d}s", "평균 체류시간"),
        (f"{false_rate}%", "오탐 처리율"),
    ]

    for col, (val, label) in zip(cols, metrics):
        col.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-val">{val}</div>
                <div class="metric-label">{label}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_risk_pie(events: list) -> None:
    st.markdown("**위험도 분포**")

    color_map = {
        "LOW": "#16a34a",
        "MED": "#ea580c",
        "HIGH": "#dc2626",
    }

    risk_counts = {
        "LOW": sum(1 for e in events if e.risk_level == "LOW"),
        "MED": sum(1 for e in events if e.risk_level == "MED"),
        "HIGH": sum(1 for e in events if e.risk_level == "HIGH"),
    }

    filtered = {
        k: v
        for k, v in risk_counts.items()
        if v > 0
    }

    if filtered:
        labels = list(filtered.keys())
        values = list(filtered.values())
        colors = [color_map[k] for k in labels]

        fig = go.Figure(
            go.Pie(
                labels=labels,
                values=values,
                hole=0.55,
                marker_colors=colors,
            )
        )

        fig.update_layout(
            margin=dict(l=0, r=0, t=10, b=0),
            height=220,
            showlegend=True,
            paper_bgcolor="white",
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("이벤트 데이터가 없습니다.")