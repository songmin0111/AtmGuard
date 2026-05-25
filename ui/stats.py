# ui/stats.py
"""
통계 시각화 패널 + 사건 로그 테이블 (하단)
"""

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from utils.logger import load_events


RISK_PLOTLY = {"HIGH": "#ef4444", "MEDIUM": "#f97316", "LOW": "#22c55e"}


def _load_df() -> pd.DataFrame:
    rows = load_events()
    if not rows:
        return pd.DataFrame(columns=["timestamp", "track_id", "event_type",
                                      "risk_level", "admin_action"])
    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    return df


def render_event_log():
    """사건 로그 테이블 (하단 왼쪽)"""
    st.markdown(
        "<p style='font-size:13px;font-weight:700;color:#374151;"
        "letter-spacing:.03em;margin-bottom:8px;'>📋 사건 이력 로그</p>",
        unsafe_allow_html=True,
    )

    df = _load_df()
    if df.empty:
        st.caption("아직 기록된 이벤트가 없습니다.")
        return

    RISK_COLOR_MAP = {"HIGH": "background-color:#3d0f0f;",
                      "MEDIUM": "background-color:#3d2000;",
                      "LOW": "background-color:#0f2d1a;"}

    display = df[["timestamp", "track_id", "event_type", "risk_level", "admin_action"]].copy()
    display.columns = ["시간", "ID", "이벤트", "위험도", "대응"]
    display["시간"] = display["시간"].dt.strftime("%H:%M:%S")
    display["이벤트"] = display["이벤트"].map(
        {"loitering": "서성거림", "weapon": "무기 감지", "normal": "정상"}).fillna(display["이벤트"])
    display["대응"] = display["대응"].map(
        {"dispatched": "✅ 출동", "false_positive": "❌ 오탐", "pending": "⏳ 대기"}).fillna(display["대응"])

    st.dataframe(display.head(20), use_container_width=True, hide_index=True)

    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇ CSV 내보내기", csv_bytes, "atm_guard_events.csv", "text/csv",
        use_container_width=True
    )


def render_hourly_chart():
    """시간대별 이상행동 통계 막대 그래프 (하단 오른쪽)"""
    st.markdown(
        "<p style='font-size:13px;font-weight:700;color:#374151;"
        "letter-spacing:.03em;margin-bottom:8px;'>📈 시간대별 이상행동 통계</p>",
        unsafe_allow_html=True,
    )

    df = _load_df()

    # 빈 데이터 → 더미 표시
    if df.empty or "timestamp" not in df or df["timestamp"].isna().all():
        _render_dummy_chart()
        return

    df = df[df["event_type"] != "normal"].dropna(subset=["timestamp"])
    if df.empty:
        st.caption("감지된 이상행동이 없습니다.")
        return

    df["hour"] = df["timestamp"].dt.hour
    hours = list(range(9, 21))

    fig = go.Figure()
    for risk in ["HIGH", "MEDIUM", "LOW"]:
        sub = df[df["risk_level"] == risk]
        counts = [sub[sub["hour"] == h].shape[0] for h in hours]
        fig.add_trace(go.Bar(
            x=[f"{h:02d}시" for h in hours],
            y=counts,
            name=risk,
            marker_color=RISK_PLOTLY[risk],
            marker_line_width=0,
        ))

    fig.update_layout(
        barmode="stack",
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font=dict(color="#374151", size=11),
        legend=dict(orientation="h", y=-0.2, x=0),
        margin=dict(l=10, r=10, t=10, b=30),
        height=220,
        xaxis=dict(showgrid=False, tickfont=dict(size=10), color="#6b7280"),
        yaxis=dict(gridcolor="#f1f5f9", tickfont=dict(size=10), color="#6b7280"),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _render_dummy_chart():
    """데이터 없을 때 예시 차트"""
    hours = [f"{h:02d}시" for h in range(9, 21)]
    import random
    random.seed(42)

    fig = go.Figure()
    for risk, vals in [
        ("HIGH",   [0,0,1,0,2,1,0,3,1,0,2,1]),
        ("MEDIUM", [1,0,2,1,1,0,2,1,0,1,2,0]),
        ("LOW",    [2,1,1,2,0,1,1,0,2,1,0,1]),
    ]:
        fig.add_trace(go.Bar(
            x=hours, y=vals, name=risk,
            marker_color=RISK_PLOTLY[risk], marker_line_width=0,
        ))

    fig.update_layout(
        barmode="stack",
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font=dict(color="#374151", size=11),
        legend=dict(orientation="h", y=-0.2, x=0),
        margin=dict(l=10, r=10, t=10, b=30),
        height=220,
        xaxis=dict(showgrid=False, tickfont=dict(size=10), color="#6b7280"),
        yaxis=dict(gridcolor="#f1f5f9", tickfont=dict(size=10), color="#6b7280"),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
