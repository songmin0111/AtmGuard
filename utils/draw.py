"""
Bounding Box Drawing
"""

import cv2


RISK_COLOR={

"LOW":(0,255,0),

"MEDIUM":(0,165,255),

"HIGH":(0,0,255)

}


def draw_roi(

    frame,
    roi

):

    if roi is None:

        return frame

    x1,y1,x2,y2=roi

    cv2.rectangle(

        frame,

        (x1,y1),

        (x2,y2),

        (255,0,0),

        2

    )

    cv2.putText(

        frame,

        "ROI",

        (

        x1,

        y1-10

        ),

        cv2.FONT_HERSHEY_SIMPLEX,

        0.6,

        (255,0,0),

        2

    )

    return frame


def draw_person_box(

    frame,

    xyxy,

    tid,

    status,

    risk

):

    x1,y1,x2,y2=map(

        int,

        xyxy

    )

    color=RISK_COLOR[risk]

    cv2.rectangle(

        frame,

        (x1,y1),

        (x2,y2),

        color,

        2

    )

    label=(

    f"ID {tid}"

    f" {status}"

    f" {risk}"

    )

    cv2.putText(

        frame,

        label,

        (

        x1,

        y1-5

        ),

        cv2.FONT_HERSHEY_SIMPLEX,

        0.5,

        color,

        2

    )

    return frame


def draw_weapon_box(

    frame,

    xyxy,

    tid,

    cls,

    conf

):

    x1,y1,x2,y2=map(

        int,

        xyxy

    )

    cv2.rectangle(

        frame,

        (x1,y1),

        (x2,y2),

        (0,0,255),

        3

    )

    cv2.putText(

        frame,

        f"{cls} {conf:.2f}",

        (

        x1,

        y1-5

        ),

        cv2.FONT_HERSHEY_SIMPLEX,

        0.6,

        (0,0,255),

        2

    )

    return frame


def draw_fps(

    frame,

    fps

):

    cv2.putText(

        frame,

        f"FPS {fps:.1f}",

        (10,30),

        cv2.FONT_HERSHEY_SIMPLEX,

        0.8,

        (255,255,255),

        2

    )

    return frame