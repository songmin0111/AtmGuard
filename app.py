# ATM GUARD 메인 Streamlit 앱
import cv2
import time
import tempfile
import os
from datetime import datetime

import numpy as np
import streamlit as st

from models.detector import (
    load_model,
    run_detection,
    run_tracking
)

from logic.loitering import (
    LoiteringTracker
)

from logic.weapon import (
    detect_weapons
)

from logic.risk import (
    calculate_risk
)

from utils.draw import (
    draw_roi,
    draw_person_box,
    draw_weapon_box,
    draw_fps
)

from utils.roi import (
    center_of_box,
    is_inside_roi
)

from utils.logger import (
    append_event
)

from ui.alert_panel import (
    render_alert_panel,
    render_risk_gauges
)

from ui.stats import (
    render_event_log,
    render_hourly_chart
)

from ui.roi_selector import (
    render_roi_selector
)


st.set_page_config(

    page_title="ATM GUARD",

    layout="wide",

    initial_sidebar_state="collapsed"

)


if "model" not in st.session_state:

    st.session_state.model=load_model()

if "tracker" not in st.session_state:

    st.session_state.tracker=LoiteringTracker()

if "roi" not in st.session_state:

    st.session_state.roi=None

if "alerts" not in st.session_state:

    st.session_state.alerts=[]

if "track_states" not in st.session_state:

    st.session_state.track_states={}


model=st.session_state.model

tracker=st.session_state.tracker


st.title(

"🛡 ATM GUARD"

)

left,right=st.columns(

[3,1]

)


with left:

    uploaded=st.file_uploader(

        "영상 / 이미지 업로드",

        type=[

            "mp4",

            "avi",

            "png",

            "jpg",

            "jpeg"

        ]

    )

with right:

    conf=st.slider(

        "Confidence",

        0.1,

        1.0,

        0.4

    )

    if st.button(

        "ROI 초기화"

    ):

        st.session_state.roi=None


video_area=st.empty()

st.divider()

bottom1,bottom2=st.columns(

[2,1]

)

log_area=bottom1.empty()

chart_area=bottom2.empty()


panel1,panel2=st.columns(

[1,1]

)

alert_area=panel1.empty()

risk_area=panel2.empty()


def update_ui():

    with alert_area:

        render_alert_panel(

            st.session_state.alerts

        )

    with risk_area:

        render_risk_gauges(

            st.session_state.track_states

        )

    with log_area:

        render_event_log()

    with chart_area:

        render_hourly_chart()


if uploaded is None:

    st.info(

    "영상을 업로드하세요"

    )

    st.stop()


suffix=uploaded.name.split(

"."

)[-1]


is_image=suffix.lower() in [

"png",

"jpg",

"jpeg"

]


if is_image:

    file_bytes=np.frombuffer(

        uploaded.read(),

        np.uint8

    )

    frame=cv2.imdecode(

        file_bytes,

        cv2.IMREAD_COLOR

    )

    rgb=cv2.cvtColor(

        frame,

        cv2.COLOR_BGR2RGB

    )

    if st.session_state.roi is None:

        roi=render_roi_selector(

            rgb

        )

        if roi:

            st.session_state.roi=roi

    roi=st.session_state.roi

    result=run_detection(

        model,

        frame,

        conf

    )

    alerts=[]

    track_states={}

    if result:

        weapons=detect_weapons(

            result.boxes,

            model.names

        )

        for w in weapons:

            frame=draw_weapon_box(

                frame,

                w["xyxy"],

                w["track_id"],

                w["cls_name"],

                w["conf"]

            )

            alerts.append({

                "track_id":

                w["track_id"],

                "event_type":

                "weapon",

                "risk":

                "HIGH",

                "entry_count":1,

                "dwell_seconds":0

            })

    if roi:

        frame=draw_roi(

            frame,

            roi

        )

    rgb=cv2.cvtColor(

        frame,

        cv2.COLOR_BGR2RGB

    )

    video_area.image(

        rgb,

        use_container_width=True

    )

    st.session_state.alerts=alerts

    st.session_state.track_states=track_states

    update_ui()

    st.stop()


temp=tempfile.NamedTemporaryFile(

    delete=False,

    suffix=".mp4"

)

temp.write(

    uploaded.read()

)

temp.close()


cap=cv2.VideoCapture(

    temp.name

)


fps=cap.get(

cv2.CAP_PROP_FPS

)

if fps==0:

    fps=25


tracker.reset_all()

frame_count=0

prev=time.time()


while cap.isOpened():

    ret,frame=cap.read()

    if not ret:

        break

    frame_count+=1

    roi=st.session_state.roi

    rgb=cv2.cvtColor(

        frame,

        cv2.COLOR_BGR2RGB

    )

    if roi is None:

        roi=render_roi_selector(

            rgb

        )

        if roi:

            st.session_state.roi=roi

            roi=st.session_state.roi

    result=run_tracking(

        model,

        frame,

        conf

    )

    weapons=[]

    alerts=[]

    track_states={}

    if result:

        weapons=detect_weapons(

            result.boxes,

            model.names

        )

        for box in result.boxes:

            if box.id is None:

                continue

            tid=int(

            box.id[0]

            )

            xyxy=box.xyxy[0].tolist()

            cx,cy=center_of_box(

                xyxy

            )

            inside=is_inside_roi(

                cx,

                cy,

                roi

            )

            state=tracker.update(

                tid,

                inside,

                fps

            )

            weapon=any(

                x["track_id"]==tid

                for x in weapons

            )

            risk=calculate_risk(

                state["entry_count"],

                state["dwell_seconds"],

                weapon

            )

            status="Normal"

            if weapon:

                status="Weapon"

            elif state["is_loitering"]:

                status="Loitering"

            frame=draw_person_box(

                frame,

                xyxy,

                tid,

                status,

                risk

            )

            track_states[tid]={

                "risk":

                risk,

                "entry_count":

                state["entry_count"],

                "dwell_seconds":

                state["dwell_seconds"]

            }

            if status!="Normal":

                alerts.append({

                    "track_id":

                    tid,

                    "event_type":

                    status.lower(),

                    "risk":

                    risk,

                    "entry_count":

                    state["entry_count"],

                    "dwell_seconds":

                    state["dwell_seconds"],

                    "timestamp":

                    datetime.now().strftime(

                    "%H:%M:%S"

                    )

                })

    if roi:

        frame=draw_roi(

            frame,

            roi

        )

    for w in weapons:

        draw_weapon_box(

            frame,

            w["xyxy"],

            w["track_id"],

            w["cls_name"],

            w["conf"]

        )

    now=time.time()

    fps_now=1/(

    now-prev

    )

    prev=now

    frame=draw_fps(

        frame,

        fps_now

    )

    rgb=cv2.cvtColor(

        frame,

        cv2.COLOR_BGR2RGB

    )

    video_area.image(

        rgb,

        use_container_width=True

    )

    st.session_state.alerts=alerts

    st.session_state.track_states=track_states

    if frame_count%30==0:

        update_ui()

cap.release()

os.remove(

temp.name

)

update_ui()

st.success(

"✅ 분석 완료"

)