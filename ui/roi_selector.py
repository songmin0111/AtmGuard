import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import numpy as np


def render_roi_selector(frame):

    st.markdown("#### 📍 ROI 설정")

    canvas = st_canvas(

        fill_color="rgba(0,100,255,0.15)",

        stroke_width=2,

        stroke_color="#2E86FF",

        background_image=Image.fromarray(frame),

        drawing_mode="rect",

        key="roi_canvas",

        width=frame.shape[1],

        height=frame.shape[0],

    )

    roi=None

    if canvas.json_data:

        objs=canvas.json_data["objects"]

        if len(objs):

            obj=objs[-1]

            x1=int(obj["left"])
            y1=int(obj["top"])

            x2=int(x1+obj["width"])
            y2=int(y1+obj["height"])

            roi=(x1,y1,x2,y2)

    return roi