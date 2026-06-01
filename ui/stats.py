"""
통계 패널
- 사건 로그
- 시간대별 이상행동 차트
"""

import streamlit as st
import pandas as pd
import plotly.express as px

from utils.logger import (
    LOG_PATH,
    init_log
)


def load_df():

    init_log()

    try:

        df = pd.read_csv(
            LOG_PATH
        )

    except:

        return pd.DataFrame()

    if len(df)==0:

        return pd.DataFrame()

    df["time"]=pd.to_datetime(
        df["time"]
    )

    return df


def render_event_log():

    st.markdown(
    "### 📋 사건 로그"
    )

    df=load_df()

    if df.empty:

        st.info(
        "기록 없음"
        )

        return

    display=df.copy()

    display["time"]=(
        display["time"]
        .dt.strftime(
        "%H:%M:%S"
        )
    )

    display.columns=[

        "시간",
        "ID",
        "이벤트",
        "위험도",
        "관리자조치"

    ]

    display["이벤트"]=(
        display["이벤트"]
        .replace({

        "loitering": "서성거림",
        "weapon": "ATM 파손 위험"

        })
    )
    
    display["관리자조치"]=(
    display["관리자조치"]
    .replace({

        "dispatched":"출동",
        "false_positive":"오탐",
        "":"-"

    })
)

    st.dataframe(

        display.iloc[::-1],

        use_container_width=True,

        hide_index=True

    )


def render_hourly_chart():

    st.markdown(
    """### 📈 시간대별 이상행동"""
    )

    df=load_df()

    if df.empty:
        st.info("데이터 없음")
        return

    df["hour"]=(df["time"].dt.hour)

    hourly=(

        df.groupby(["hour","risk"])
        .size()
        .reset_index(name="count")

    )

    fig=px.bar(

        hourly,
        x="hour",
        y="count",
        color="risk",
        barmode="stack"

    )

    fig.update_layout(height=300)

    st.plotly_chart(
        fig,
        use_container_width=True,
)