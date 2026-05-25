# ui/alert_panel.py
"""
이상행동 알림 패널 
"""

import streamlit as st
from logic.risk import RISK_COLOR
from utils.logger import append_event

RISK_ICON  = {"HIGH": "🚨", "MEDIUM": "⚠️", "LOW": "ℹ️"}
EVENT_KO   = {"loitering": "서성거림 감지", "weapon": "ATM 파손 시도 감지", "normal": "정상"}

# 라이트 테마 색상
RISK_BG_LIGHT = {
    "HIGH":   "#fff1f2",   # 연한 빨강
    "MEDIUM": "#fff7ed",   # 연한 주황
    "LOW":    "#f0fdf4",   # 연한 초록
}
RISK_BORDER = {
    "HIGH":   "#fca5a5",
    "MEDIUM": "#fdba74",
    "LOW":    "#86efac",
}
RISK_TEXT = {
    "HIGH":   "#991b1b",
    "MEDIUM": "#9a3412",
    "LOW":    "#166534",
}
RISK_BADGE_BG = {
    "HIGH":   "#ef4444",
    "MEDIUM": "#f97316",
    "LOW":    "#22c55e",
}


def _risk_badge(risk: str) -> str:
    bg = RISK_BADGE_BG.get(risk, "#6b7280")
    return (
        f"<span style='background:{bg};color:#fff;"
        f"padding:2px 10px;border-radius:12px;"
        f"font-size:11px;font-weight:700;letter-spacing:.05em;'>{risk}</span>"
    )


def render_alert_panel(active_alerts: list[dict]):
    high_count = sum(1 for a in active_alerts if a["risk"] == "HIGH")

    # ── 헤더: st.columns 대신 순수 HTML flex로 처리 (overflow 방지) ──
    badge_html = (
        f"<div style='background:#ef4444;color:#fff;border-radius:50%;"
        f"min-width:22px;height:22px;display:flex;align-items:center;"
        f"justify-content:center;font-weight:700;font-size:12px;"
        f"padding:0 4px;'>{high_count}</div>"
        if high_count else ""
    )
    st.markdown(
        f"""
        <div style='display:flex;align-items:center;justify-content:space-between;
        margin:0 0 10px;overflow:hidden;'>
            <p style='font-size:14px;font-weight:700;color:#374151;margin:0;'>
                🔔 이상행동 감지 알림
            </p>
            {badge_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not active_alerts:
        st.markdown(
            "<div style='background:#f0fdf4;border:1px solid #86efac;"
            "border-radius:10px;padding:14px 16px;"
            "color:#166534;font-size:13px;text-align:center;'>"
            "✅ 정상 운영 — 이상행동 없음</div>",
            unsafe_allow_html=True,
        )
        return

    # Alert 카드 
    for alert in active_alerts[:5]:
        tid   = alert["track_id"]
        risk  = alert["risk"]
        etype = alert["event_type"]
        bg     = RISK_BG_LIGHT.get(risk, "#f9fafb")
        border = RISK_BORDER.get(risk, "#d1d5db")
        txt    = RISK_TEXT.get(risk, "#374151")
        icon   = RISK_ICON.get(risk, "•")
        label  = EVENT_KO.get(etype, etype)
        dwell  = alert.get("dwell_seconds", 0)
        cnt    = alert.get("entry_count", 0)

        st.markdown(
            f"""
            <div style='background:{bg};border:1.5px solid {border};
            border-radius:10px;padding:11px 14px;margin-bottom:8px;
            box-shadow:0 1px 3px rgba(0,0,0,.06);'>
                <div style='display:flex;justify-content:space-between;
                align-items:center;margin-bottom:4px;'>
                    <span style='font-size:13px;font-weight:700;color:{txt};'>
                        {icon} ID #{tid:02d} — {label}
                    </span>
                    {_risk_badge(risk)}
                </div>
                <div style='font-size:11px;color:#6b7280;'>
                    출입 {cnt}회 &nbsp;|&nbsp; 체류 {dwell:.0f}초 &nbsp;|&nbsp; {alert.get("timestamp","")}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 관리자 대응 버튼
    if active_alerts:
        top = active_alerts[0]
        st.markdown(
            f"<p style='font-size:12px;color:#6b7280;margin:10px 0 4px;'>"
            f"👤 관리자 대응 (ID #{top['track_id']:02d})</p>",
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🚔 출동 명령", key=f"dispatch_{top['track_id']}",
                         use_container_width=True):
                append_event(top["track_id"], top["event_type"], top["risk"], "dispatched")
                st.success(f"출동 명령 전송 — ID #{top['track_id']:02d}")
                st.session_state["active_alerts"] = [
                    a for a in st.session_state.get("active_alerts", [])
                    if a["track_id"] != top["track_id"]
                ]
        with c2:
            if st.button("✖ 오탐 처리", key=f"fp_{top['track_id']}",
                         use_container_width=True):
                append_event(top["track_id"], top["event_type"], top["risk"], "false_positive")
                st.info(f"오탐 처리 완료 — ID #{top['track_id']:02d}")
                st.session_state["active_alerts"] = [
                    a for a in st.session_state.get("active_alerts", [])
                    if a["track_id"] != top["track_id"]
                ]


def render_risk_gauges(track_states: dict):
    if not track_states:
        return

    st.markdown(
        "<p style='font-size:13px;font-weight:700;color:#374151;"
        "letter-spacing:.03em;margin:16px 0 8px;'>📊 추적 ID별 위험도</p>",
        unsafe_allow_html=True,
    )

    GAUGE_BG = {"HIGH": "#fff1f2", "MEDIUM": "#fff7ed", "LOW": "#f0fdf4"}
    GAUGE_BD = {"HIGH": "#fca5a5", "MEDIUM": "#fdba74", "LOW": "#86efac"}
    GAUGE_TXT= {"HIGH": "#991b1b", "MEDIUM": "#9a3412", "LOW": "#166534"}

    items = sorted(track_states.items(), key=lambda x: -x[1].get("entry_count", 0))
    cols  = st.columns(2)

    for idx, (tid, state) in enumerate(items[:6]):
        risk  = state.get("risk", "LOW")
        dwell = state.get("dwell_seconds", 0)
        pct   = min(state.get("entry_count", 0) * 20, 100)
        color = RISK_BADGE_BG.get(risk, "#22c55e")
        bg    = GAUGE_BG.get(risk, "#f9fafb")
        bd    = GAUGE_BD.get(risk, "#d1d5db")
        txt   = GAUGE_TXT.get(risk, "#374151")

        with cols[idx % 2]:
            st.markdown(
                f"""
                <div style='background:{bg};border:1.5px solid {bd};
                border-radius:8px;padding:8px 10px;margin-bottom:8px;
                box-shadow:0 1px 2px rgba(0,0,0,.04);'>
                    <div style='display:flex;justify-content:space-between;'>
                        <span style='font-size:12px;font-weight:600;color:{txt};'>
                            ID #{tid:02d}
                        </span>
                        <span style='font-size:10px;color:{color};font-weight:700;'>
                            {risk}
                        </span>
                    </div>
                    <div style='font-size:10px;color:#6b7280;'>체류 {dwell:.0f}s</div>
                    <div style='background:#e5e7eb;border-radius:4px;
                    height:6px;margin-top:5px;overflow:hidden;'>
                        <div style='width:{pct}%;background:{color};height:100%;
                        border-radius:4px;transition:width .3s;'></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
