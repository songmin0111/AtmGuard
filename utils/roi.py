# utils/roi.py
"""
ROI(관심 구역) 관련 유틸리티
- 중심점이 ROI 내부인지 판단
- ROI 좌표 직렬화/역직렬화 (session_state 저장용)
"""

def center_of_box(xyxy):

    x1,y1,x2,y2=xyxy

    cx=(x1+x2)/2
    cy=(y1+y2)/2

    return cx,cy


def is_inside_roi(

    cx,
    cy,
    roi

):

    if roi is None:

        return False

    x1,y1,x2,y2=roi

    return (

        x1<=cx<=x2

        and

        y1<=cy<=y2

    )


def roi_area(roi):

    if roi is None:

        return 0

    x1,y1,x2,y2=roi

    return (

        x2-x1

    )*(

        y2-y1

    )