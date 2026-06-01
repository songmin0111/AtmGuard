"""
이상행동 알림 패널 + 위험도 패널

[수정]
- 출동/오탐 버튼 클릭 시 update_admin_action()으로 CSV 행 업데이트
- render_alert_panel이 log_area를 받아서 버튼 후 로그 즉시 갱신
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
    return (
        f"<span style='background:{color};color:white;"
        f"padding:3px 10px;border-radius:12px;"
        f"font-size:11px;font-weight:700;'>{risk}</span>"
    )

def render_alert_panel(active_alerts, log_area=None):
    
    st.markdown("### 🚨 이상행동 감지 알림")

    if not active_alerts:
        st.success("정상 운영 — 이상행동 없음")
        return

    for alert in active_alerts[:5]:
        tid   = alert["track_id"]
        risk  = alert["risk"]
        event = EVENT_NAME.get(alert["event_type"], "Unknown")
        cnt   = alert.get("entry_count",   0)
        dwell = alert.get("dwell_seconds", 0)

        st.markdown(
            f"""
            <div style='background:{RISK_BG[risk]};
                        border-left:6px solid {RISK_BORDER[risk]};
                        padding:12px;border-radius:10px;margin-bottom:10px;'>
              <div style='display:flex;justify-content:space-between;'>
                <b>{RISK_ICON[risk]} ID #{tid:02d}</b>
                {risk_badge(risk)}
              </div>
              <div>{event}</div>
              <div style='font-size:12px;color:#64748b;margin-top:4px;'>
                ROI 진입 {cnt}회 | 체류 {dwell:.0f}초
              </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    top = active_alerts[0]
    st.markdown("---")
    st.caption(f"관리자 대응 (ID #{top['track_id']:02d})")

    col1, col2 = st.columns(2)

    with col1:
        # 출동 버튼 → CSV의 해당 행 admin_action = "dispatched"
        if st.button("🚔 출동 명령",
                     key=f"dispatch_{top['track_id']}_{top['event_type']}",
                     use_container_width=True):
            update_admin_action(top["track_id"], top["event_type"], "dispatched")
            st.success("✅ 출동 명령 기록 완료")
            if log_area:
                from ui.stats import render_event_log
                with log_area:
                    render_event_log()

    with col2:
        # 오탐 버튼 → CSV의 해당 행 admin_action = "false_positive"
        if st.button("❌ 오탐 처리",
                     key=f"false_{top['track_id']}_{top['event_type']}",
                     use_container_width=True):
            update_admin_action(top["track_id"], top["event_type"], "false_positive")
            st.info("ℹ️ 오탐 처리 기록 완료")
            if log_area:
                from ui.stats import render_event_log
                with log_area:
                    render_event_log()


def render_risk_gauges(track_states):
    
    st.markdown("### 📊 추적 ID별 위험도")

    if not track_states:
        st.caption("추적 대상 없음")
        return

    items = sorted(
        track_states.items(),
        key=lambda x: (-x[1]["entry_count"], -x[1]["dwell_seconds"])
    )

    cols = st.columns(2)
    for idx, (tid, state) in enumerate(items[:6]):
        risk  = state["risk"]
        cnt   = state["entry_count"]
        dwell = state["dwell_seconds"]
        score = min(cnt * 20 + dwell / 120 * 40, 100)

        with cols[idx % 2]:
            st.markdown(
                f"""
                <div style='background:{RISK_BG[risk]};padding:12px;
                            border-radius:10px;margin-bottom:10px;'>
                  <b>ID #{tid:02d}</b><br>
                  ROI 진입 {cnt}회<br>
                  체류 {dwell:.0f}초<br>
                  위험도 {risk}
                  <div style='background:#e5e7eb;height:7px;
                              border-radius:8px;margin-top:8px;'>
                    <div style='width:{score}%;background:{RISK_COLOR[risk]};
                                height:100%;border-radius:8px;'></div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True
            )
