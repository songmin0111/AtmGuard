# 위험 이벤트 페이지

import streamlit as st
from event_logic import LoiteringStateManager


def render() -> None:
    st.markdown('<div class="section-title">위험 이벤트</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-sub">감지된 이상행동을 확인하고 관리자 대응을 기록하세요.</div>',
        unsafe_allow_html=True,
    )

    mgr: LoiteringStateManager = st.session_state.loitering_mgr
    events = mgr.get_events()

    if not events:
        st.info("감지된 이벤트가 없습니다. CCTV 모니터링 페이지에서 영상을 분석해주세요.")
        return

    # 상세 모달이 열려있으면 모달만 표시 
    open_modal = st.session_state.get("open_modal_idx", None)
    if open_modal is not None and 0 <= open_modal < len(events):
        _render_modal(events[open_modal], open_modal, mgr)
        return

    # 테이블 헤더 
    COLS = [1, 1.5, 1.2, 1.5, 1.5, 1.5, 1.2]
    HEADERS = ["ID", "체류시간", "위험도", "서성거림 감지", "무기탐지", "관리대응 여부", "상세보기"]
    header_cols = st.columns(COLS)
    for col, h in zip(header_cols, HEADERS):
        col.markdown(f"**{h}**")
    st.markdown('<hr style="margin:4px 0 8px 0;">', unsafe_allow_html=True)

    # MED/HIGH/WEAPON만, track_id별 최고 위험도 1개 
    # events 전체를 순회하며 track_id별 최고 위험도 이벤트 인덱스 저장
    RISK_ORDER = {"HIGH": 3, "MED": 2, "LOW": 1, "NORMAL": 0}
    best_idx: dict = {}   # track_id → (idx, event)
    weapon_list = []

    for idx, e in enumerate(events):
        if e.track_id < 0:
            weapon_list.append((idx, e))
            continue
        if e.risk_level not in ("MED", "HIGH"):
            continue
        prev = best_idx.get(e.track_id)
        if prev is None or RISK_ORDER[e.risk_level] >= RISK_ORDER[prev[1].risk_level]:
            best_idx[e.track_id] = (idx, e)

    deduped = sorted(weapon_list + list(best_idx.values()), key=lambda x: x[0], reverse=True)

    for real_idx, e in deduped:
        _render_event_row(e, real_idx, COLS)
        st.markdown('<hr style="margin:6px 0;border-color:#e2e8f0;">', unsafe_allow_html=True)


# 이벤트 행 (상세보기 버튼만) 

def _render_event_row(e, real_idx: int, cols: list) -> None:
    mgr: LoiteringStateManager = st.session_state.loitering_mgr
    tid_str         = f"#{e.track_id}" if e.track_id >= 0 else "WEAPON"
    loiter_detected = e.event_type == "loitering"
    weapon_detected = e.event_type == "weapon"
    status          = e.response_status

    # 분석 완료 후엔 EventLog 스냅샷 사용, 분석 중엔 TrackState 최신값 사용
    analysis_done = st.session_state.get("analysis_done", True)
    
    if not analysis_done and e.track_id >= 0:
        live_dwell = mgr.get_live_dwell(e.track_id)
        dwell_sec  = live_dwell if live_dwell >= 0 else e.dwell_seconds
        
        live_risk  = mgr.get_live_risk(e.track_id)
        risk_level = live_risk if live_risk else e.risk_level
        
        live_state = mgr.get_all_states().get(e.track_id)
        entry_count = live_state.entry_count if live_state else e.entry_count
    
    else:
        dwell_sec  = e.dwell_seconds
        risk_level = e.risk_level
        entry_count = e.entry_count
        
    mins = int(dwell_sec // 60)
    secs = int(dwell_sec % 60)

    row = st.columns(cols)
    row[0].markdown(f"**{tid_str}**")
    row[1].markdown(f"{mins}m {secs:02d}s")
    row[2].markdown(
        f'<span class="badge badge-{risk_level}">● {risk_level}</span>',
        unsafe_allow_html=True,
    )
    row[3].markdown(
        f'<span style="color:{"#dc2626" if loiter_detected else "#94a3b8"};">'
        f'{"감지됨" if loiter_detected else "미감지"}</span>',
        unsafe_allow_html=True,
    )
    row[4].markdown(
        f'<span style="color:{"#ea580c" if weapon_detected else "#94a3b8"};">'
        f'{"감지 의심" if weapon_detected else "미감지"}</span>',
        unsafe_allow_html=True,
    )
    status_color = {"미확인": "#6b7280", "출동": "#2563eb", "오탐": "#4b5563"}.get(status, "#6b7280")
    row[5].markdown(
        f'<span style="color:{status_color};font-weight:600;">{status}</span>',
        unsafe_allow_html=True,
    )

    # 상세보기 버튼 — 클릭하면 모달 인덱스 저장 후 rerun
    if row[6].button("상세보기", key=f"detail_{real_idx}_{e.timestamp}"):
        st.session_state.open_modal_idx = real_idx
        st.rerun()


# 상세 모달 (전체 페이지 오버레이 스타일) 

def _render_modal(e, real_idx: int, mgr: LoiteringStateManager) -> None:
    tid_str         = f"#{e.track_id}" if e.track_id >= 0 else "WEAPON"
    loiter_detected = e.event_type == "loitering"
    weapon_detected = e.event_type == "weapon"
    status          = e.response_status

    # 체류시간 / 위험도 / 진입횟수 최신값
    if e.track_id >= 0:
        live_dwell   = mgr.get_live_dwell(e.track_id)
        dwell_sec    = live_dwell if live_dwell >= 0 else e.dwell_seconds
        live_risk    = mgr.get_live_risk(e.track_id)
        risk_level   = live_risk if live_risk else e.risk_level
        live_state   = mgr.get_all_states().get(e.track_id)
        entry_count  = live_state.entry_count if live_state else e.entry_count
    else:
        dwell_sec    = e.dwell_seconds
        risk_level   = e.risk_level
        entry_count  = e.entry_count
    mins       = int(dwell_sec // 60)
    secs       = int(dwell_sec % 60)
    risk_color = {"HIGH": "#dc2626", "MED": "#ea580c", "LOW": "#16a34a"}.get(risk_level, "#6b7280")
    risk_desc       = {
        "HIGH": "ROI 내부 체류 시간이 기준값을 초과하고, 동일 객체가 ATM 접근 구역 주변에서 반복적으로 머무는 경우 부여됩니다.",
        "MED":  "ROI 진입 횟수가 기준을 초과하거나 체류 시간이 중간 단계 이상입니다.",
        "LOW":  "ROI에 진입한 상태입니다. 계속 모니터링 중입니다.",
    }.get(risk_level, "")

    # 모달 헤더 
    title_col, close_col = st.columns([8, 1])
    with title_col:
        st.markdown(
            f'<div style="font-size:1.15rem;font-weight:700;color:#0f172a;">'
            f'📋 감지 결과 상세 · {tid_str}</div>'
            f'<div style="font-size:0.78rem;color:#64748b;margin-bottom:1rem;">'
            f'CAM-01 · ATM 부스 · {e.timestamp}</div>',
            unsafe_allow_html=True,
        )
    with close_col:
        if st.button("✕ 닫기", key="modal_close"):
            st.session_state.open_modal_idx = None
            st.rerun()

    st.markdown('<hr style="margin:0 0 1.2rem 0;">', unsafe_allow_html=True)

    # 본문: 왼쪽 = 감지 프레임 플레이스홀더 / 오른쪽 = 상세 정보 
    left_col, right_col = st.columns([1.2, 1])

    with left_col:
        import cv2
        # 이벤트 인덱스에 저장된 프레임 사용
        event_frames: dict = st.session_state.get("event_frames", {})
        saved_frame = event_frames.get(real_idx)
        if saved_frame is not None:
            frame_disp = saved_frame.copy()
            h, w = frame_disp.shape[:2]
            border_color_bgr = {"HIGH": (0,0,220), "MED": (0,140,255), "LOW": (0,200,0)}.get(risk_level, (128,128,128))
            cv2.rectangle(frame_disp, (0,0), (w-1,h-1), border_color_bgr, 6)
            st.image(cv2.cvtColor(frame_disp, cv2.COLOR_BGR2RGB), use_column_width=True)
        else:
            st.markdown("""
            <div style="background:#1e293b;border-radius:10px;height:220px;
                        display:flex;align-items:center;justify-content:center;
                        color:#475569;font-size:0.85rem;">
                🎥 감지 프레임 없음<br>
                <span style="font-size:0.75rem;">(분석 중 캡처된 프레임이 여기 표시됩니다)</span>
            </div>
            """, unsafe_allow_html=True)

        # 위험도 설명 박스
        st.markdown(f"""
        <div style="background:#f8fafc;border-left:4px solid {risk_color};
                    border-radius:6px;padding:12px 14px;margin-top:12px;
                    font-size:0.83rem;color:#374151;">
            {risk_desc}
        </div>
        """, unsafe_allow_html=True)

    with right_col:
        # 상세 정보 테이블
        st.markdown(f"""
        <div style="background:#fff;border-radius:10px;border:1px solid #e2e8f0;overflow:hidden;">
            <table style="width:100%;border-collapse:collapse;font-size:0.85rem;">
                <tr style="border-bottom:1px solid #f1f5f9;">
                    <td style="padding:10px 14px;color:#64748b;width:40%;">객체 ID</td>
                    <td style="padding:10px 14px;font-weight:600;">{tid_str}</td>
                </tr>
                <tr style="border-bottom:1px solid #f1f5f9;">
                    <td style="padding:10px 14px;color:#64748b;">발생 시각</td>
                    <td style="padding:10px 14px;">{e.timestamp}</td>
                </tr>
                <tr style="border-bottom:1px solid #f1f5f9;">
                    <td style="padding:10px 14px;color:#64748b;">위치</td>
                    <td style="padding:10px 14px;">CAM-01 · ATM 부스</td>
                </tr>
                <tr style="border-bottom:1px solid #f1f5f9;">
                    <td style="padding:10px 14px;color:#64748b;">체류 시간</td>
                    <td style="padding:10px 14px;">{mins}m {secs:02d}s</td>
                </tr>
                <tr style="border-bottom:1px solid #f1f5f9;">
                    <td style="padding:10px 14px;color:#64748b;">진입 횟수</td>
                    <td style="padding:10px 14px;">{entry_count}회</td>
                </tr>
                <tr style="border-bottom:1px solid #f1f5f9;">
                    <td style="padding:10px 14px;color:#64748b;">위험도</td>
                    <td style="padding:10px 14px;">
                        <span style="color:{risk_color};font-weight:700;">● {risk_level}</span>
                    </td>
                </tr>
                <tr style="border-bottom:1px solid #f1f5f9;">
                    <td style="padding:10px 14px;color:#64748b;">감지 유형</td>
                    <td style="padding:10px 14px;">{'서성거림 감지' if loiter_detected else '무기탐지'}</td>
                </tr>
                <tr style="border-bottom:1px solid #f1f5f9;">
                    <td style="padding:10px 14px;color:#64748b;">무기탐지</td>
                    <td style="padding:10px 14px;color:{'#ea580c' if weapon_detected else '#94a3b8'};">
                        {'감지 의심' if weapon_detected else '미감지'}
                    </td>
                </tr>
                <tr>
                    <td style="padding:10px 14px;color:#64748b;">관리자 대응</td>
                    <td style="padding:10px 14px;font-weight:600;">{status}</td>
                </tr>
            </table>
        </div>
        """, unsafe_allow_html=True)

        # 대응 버튼 (미확인일 때만)
        if status == "미확인":
            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
            b1, b2 = st.columns(2)
            if b1.button("🚔 출동 명령", key="modal_dispatch", use_container_width=True):
                mgr.update_event_response(real_idx, "출동")
                st.session_state.open_modal_idx = None
                st.rerun()
            if b2.button("✕ 오탐 처리", key="modal_false", use_container_width=True):
                mgr.update_event_response(real_idx, "오탐")
                st.session_state.open_modal_idx = None
                st.rerun()