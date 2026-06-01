"""
이상행동 알림 패널 + 위험도 패널
"""

import streamlit as st
from utils.logger import append_event


RISK_COLOR = {

    "LOW": "#22c55e",
    "MEDIUM": "#f59e0b",
    "HIGH": "#ef4444"

}

RISK_BG = {

    "LOW": "#f0fdf4",
    "MEDIUM": "#fffbeb",
    "HIGH": "#fff1f2"

}

RISK_BORDER = {

    "LOW": "#86efac",
    "MEDIUM": "#fcd34d",
    "HIGH": "#fca5a5"

}

EVENT_NAME = {

    "loitering": "서성거림 감지",
    "weapon": "ATM 파손 시도",
    "normal": "정상"

}

RISK_ICON = {

    "LOW": "🟢",
    "MEDIUM": "🟠",
    "HIGH": "🔴"

}


def risk_badge(risk):

    color = RISK_COLOR.get(risk,"#64748b")

    return f"""

    <span style='

    background:{color};
    color:white;

    padding:3px 10px;

    border-radius:12px;

    font-size:11px;

    font-weight:700;

    '>

    {risk}

    </span>

    """

def render_alert_panel(active_alerts):

    st.markdown("""
    ### 🚨 이상행동 감지 알림
    """)

    if not active_alerts:

        st.success(
            "정상 운영 — 이상행동 없음"
        )

        return

    for alert in active_alerts[:5]:

        tid = alert["track_id"]

        risk = alert["risk"]

        event = EVENT_NAME.get(

            alert["event_type"],
            "Unknown"

        )

        cnt = alert.get(
            "entry_count",
            0
        )

        dwell = alert.get(
            "dwell_seconds",
            0
        )

        bg = RISK_BG[risk]

        border = RISK_BORDER[risk]

        icon = RISK_ICON[risk]

        st.markdown(

            f"""
            <div style='
            background:{bg};
            border-left:6px solid {border};
            padding:12px;
            border-radius:10px;
            margin-bottom:10px;
            '>

            <div style='
            display:flex;
            justify-content:space-between;
            '>

            <b>
            {icon} ID #{tid:02d}
            </b>

            {risk_badge(risk)}

            </div>

            <div>
            {event}
            </div>

            <div style='
            font-size:12px;
            color:#64748b;
            margin-top:4px;
            '>

            ROI 진입 {cnt}회 |
            체류 {dwell:.0f}초

            </div>

            </div>

            """,

        unsafe_allow_html=True

        )

    top = active_alerts[0]

    st.markdown("---")

    st.caption(
        f"관리자 대응 (ID #{top['track_id']:02d})"
    )

    col1, col2 = st.columns(2)

    with col1:

        if st.button(

            "🚔 출동 명령",

            key=f"dispatch_{top['track_id']}",

            use_container_width=True

        ):

            append_event(

                top["track_id"],
                top["event_type"],
                top["risk"],
                "dispatched"

            )

            st.success("출동 명령 완료")

    with col2:

        if st.button(

            "❌ 오탐 처리",

            key=f"false_{top['track_id']}",

            use_container_width=True

        ):

            append_event(

                top["track_id"],
                top["event_type"],
                top["risk"],
                "false_positive"

            )

            st.info("오탐 처리 완료")


def render_risk_gauges(track_states):

    st.markdown(

    """
    ### 📊 추적 ID별 위험도
    """

    )

    if not track_states:
        st.caption("추적 대상 없음")
        return

    cols = st.columns(2)

    items = sorted(

        track_states.items(),

        key=lambda x:

        (

        -x[1]["entry_count"],

        -x[1]["dwell_seconds"]

        )

    )

    for idx,(tid,state) in enumerate(items[:6]):

        risk = state["risk"]

        cnt = state["entry_count"]

        dwell = state["dwell_seconds"]

        score = min(cnt*20+dwell/120*40, 100)

        color = RISK_COLOR[risk]

        bg = RISK_BG[risk]

        with cols[idx%2]:

            st.markdown(

                f"""
                <div style="
                background:{bg};
                padding:12px;
                border-radius:10px;
                margin-bottom:10px;
                ">

                <b>ID #{tid:02d}</b><br>

                ROI 진입 {cnt}회<br>

                체류 {dwell:.0f}초<br>

                위험도 {risk}

                <div style="
                background:#e5e7eb;
                height:7px;
                border-radius:8px;
                margin-top:8px;
                ">

                <div style="
                width:{score}%;
                background:{color};
                height:100%;
                border-radius:8px;
                ">
                </div>

                </div>

                </div>
                """,

                unsafe_allow_html=True

                )