# logic/loitering.py
"""
서성거림(Loitering) 감지 모듈
- ROI 출입 횟수 카운팅
- 체류 시간 누적
- 이상행동 트리거 여부 판단
"""

from logic.risk import calculate_risk


class LoiteringTracker:

    def __init__(self):

        self.state={}

    def update(

        self,
        tid,
        inside,
        fps=25

    ):

        if tid not in self.state:

            self.state[tid]={

                "inside":False,

                "entry_count":0,

                "dwell_frames":0,

                "risk":"LOW"

            }

        s=self.state[tid]

        if not s["inside"] and inside:

            s["entry_count"]+=1 # ROI 진입 시 카운트

        if inside:

            s["dwell_frames"]+=1 # ROI 안에 있는 동안 누적

        dwell=s["dwell_frames"]/fps

        risk=calculate_risk(

            s["entry_count"],
            dwell,
            False

        )

        s["risk"]=risk
        s["inside"]=inside

        return{

            "entry_count":
                s["entry_count"],

            "dwell_seconds":
                dwell,

            "risk":
                risk,

            "is_loitering":

                s["entry_count"]>=5
                or dwell>=120

        }