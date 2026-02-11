# MacroCryptoSentinel/app.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from main import main as update_data
from src.analytics.statistics import get_deviation_levels

st.set_page_config(page_title="MacroCryptoSentinel", layout="wide")

st.title("MacroCryptoSentinel — VIX Mean Reversion Deviation Chart")

if st.button("Обновить все данные"):
    with st.spinner("Скачиваю и обрабатываю данные..."):
        update_data()
    st.success("Данные обновлены!")

vix_processed_path = "data/processed/vix_processed.csv"

if os.path.exists(vix_processed_path):
    df_vix = pd.read_csv(vix_processed_path)
    df_vix["date"] = pd.to_datetime(df_vix["date"], utc=True, errors='coerce')
    df_vix["date"] = df_vix["date"].dt.tz_localize(None)
    df_vix = df_vix.dropna(subset=["date"]).reset_index(drop=True)

    st.success("VIX данные загружены!")

    # Параметры (можно вынести в sidebar позже)
    window = 252
    sigma_levels = [1, 2]

    # Таблица последних значений
    recent_df = df_vix[["date", "close", "deviation_pct", "rolling_mean"]].tail(20).copy()
    recent_df["date"] = recent_df["date"].dt.strftime("%d.%m.%Y")
    recent_df["close"] = recent_df["close"].round(2)
    recent_df["rolling_mean"] = recent_df["rolling_mean"].round(2)
    recent_df["deviation_pct"] = recent_df["deviation_pct"].apply(lambda x: f"{x:+.1f}%")

    recent_df.rename(columns={
        "date": "Дата",
        "close": "VIX Close",
        "deviation_pct": "% Отклонение",
        "rolling_mean": "Среднее (252д)"
    }, inplace=True)

    st.subheader("Последние значения")
    st.dataframe(recent_df, use_container_width=True)

    # Статические уровни
    levels = get_deviation_levels(df_vix, sigma_levels=sigma_levels)

    # График
    st.subheader(f"График отклонений VIX в % от скользящего среднего ({window} дней)")

    fig = go.Figure()

    # Синяя линия — отклонение
    fig.add_trace(go.Scatter(
        x=df_vix["date"], y=df_vix["deviation_pct"],
        mode="lines", name="Отклонение %", line=dict(color="deepskyblue", width=2)
    ))

    # Красная — среднее
    fig.add_trace(go.Scatter(
        x=[df_vix["date"].min(), df_vix["date"].max()],
        y=[levels["mean"], levels["mean"]],
        mode="lines", name="Среднее", line=dict(color="red", width=2)
    ))

    # Оранжевые +σ
    for level in sigma_levels:
        y = levels[f"+{level}σ"]
        fig.add_trace(go.Scatter(
            x=[df_vix["date"].min(), df_vix["date"].max()],
            y=[y, y],
            mode="lines", name=f"+{level}σ",
            line=dict(color="orange", dash="dash" if level == 1 else "solid")
        ))

    # Зелёные -σ
    for level in sigma_levels:
        y = levels[f"-{level}σ"]
        fig.add_trace(go.Scatter(
            x=[df_vix["date"].min(), df_vix["date"].max()],
            y=[y, y],
            mode="lines", name=f"-{level}σ",
            line=dict(color="limegreen", dash="dash" if level == 1 else "solid")
        ))

    fig.update_layout(
        title="VIX Mean Reversion Deviation Chart",
        xaxis_title="Дата",
        yaxis_title="Отклонение (%)",
        template="plotly_dark",
        height=600,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    st.plotly_chart(fig, use_container_width=True)

    # Sidebar со статистикой отклонений
    st.sidebar.header("Уровни отклонений")
    st.sidebar.metric("Среднее", f"{levels['mean']:+.2f}%")
    for level in sigma_levels:
        st.sidebar.metric(f"+{level}σ", f"{levels[f'+{level}σ']:+.2f}%")
        st.sidebar.metric(f"-{level}σ", f"{levels[f'-{level}σ']:+.2f}%")

else:
    st.error("Данные не найдены!")
    st.info("Нажмите кнопку обновления.")

st.caption(
    "• Синяя линия — текущее отклонение VIX в % от скользящего среднего.\n"
    "• Красная — среднее отклонение по всей истории.\n"
    "• Оранжевые/зелёные — статические ±1σ и ±2σ уровни (горизонтальные)."
)