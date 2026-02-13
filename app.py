import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import datetime
import os
from main import main as update_data
from src.analytics.statistics import get_deviation_levels
from src.analytics.signal_generator import generate_cot_large_signal, generate_cot_comm_signal

st.set_page_config(page_title="MacroCryptoSentinel", layout="wide")
st.title("MacroCryptoSentinel")

if st.button("Обновить все данные"):
    with st.spinner("Скачиваю и обрабатываю данные..."):
        update_data()
    st.success("Данные обновлены!")

# Пути к файлам
vix_path = "data/processed/vix_processed.csv"
cot_path = "data/processed/btc_cot_processed.csv"
btc_path = "data/processed/btc_price.csv"

# Загрузка полных данных
df_vix_full = df_cot_full = df_btc_full = None

if os.path.exists(vix_path):
    df_vix_full = pd.read_csv(vix_path)
    df_vix_full["date"] = pd.to_datetime(df_vix_full["date"], utc=True).dt.tz_localize(None)

if os.path.exists(cot_path):
    df_cot_full = pd.read_csv(cot_path)
    df_cot_full["date"] = pd.to_datetime(df_cot_full["date"])

if os.path.exists(btc_path):
    df_btc_full = pd.read_csv(btc_path)
    df_btc_full["date"] = pd.to_datetime(df_btc_full["date"], utc=True).dt.tz_localize(None)

if not all([df_vix_full is not None, df_cot_full is not None, df_btc_full is not None]):
    st.error("Не все данные загружены! Нажмите кнопку обновления.")
    st.stop()

# Общий диапазон дат для слайдера
all_min_dates = [df["date"].min().date() for df in [df_vix_full, df_cot_full, df_btc_full]]
all_max_dates = [df["date"].max().date() for df in [df_vix_full, df_cot_full, df_btc_full]]
overall_min_date = max(all_min_dates)
overall_max_date = min(all_max_dates)

# Инициализация session_state
if "date_range" not in st.session_state:
    default_start = datetime.date(overall_max_date.year - 3, 1, 1)
    if default_start < overall_min_date:
        default_start = overall_min_date
    st.session_state.date_range = (default_start, overall_max_date)

# Единый слайдер перед вкладками
st.markdown("---")
st.subheader("Временной диапазон")
st.slider(
    "Выберите диапазон дат",
    min_value=overall_min_date,
    max_value=overall_max_date,
    value=st.session_state.date_range,
    format="DD.MM.YYYY",
    key="date_range"
)

# Функция фильтрации (используем .dt.date для надёжности, чтобы избежать проблем с таймзонами/временем)
def get_filtered_dfs():
    start_date = st.session_state.date_range[0]
    end_date = st.session_state.date_range[1]
    
    df_btc = df_btc_full[df_btc_full["date"].dt.date.between(start_date, end_date)].reset_index(drop=True)
    df_vix = df_vix_full[df_vix_full["date"].dt.date.between(start_date, end_date)].reset_index(drop=True)
    df_cot = df_cot_full[df_cot_full["date"].dt.date.between(start_date, end_date)].reset_index(drop=True)
    
    return df_btc, df_vix, df_cot

# Вкладки
tab_bitcoin, tab_cot = st.tabs(["BITCOIN Dashboard", "BTC COT Details"])

# === BITCOIN Dashboard ===
with tab_bitcoin:
    df_btc, df_vix, df_cot = get_filtered_dfs()

    # BTC Candlestick
    fig_btc = go.Figure(data=go.Candlestick(
        x=df_btc["date"],
        open=df_btc["open"],
        high=df_btc["high"],
        low=df_btc["low"],
        close=df_btc["close"],
        name="BTC-USD"
    ))
    if not df_btc.empty:
        padding = pd.Timedelta(days=7)
        fig_btc.update_xaxes(range=[df_btc["date"].min() - padding, df_btc["date"].max() + padding])
    fig_btc.update_layout(
        title="BTC Price (Binance)",
        xaxis_rangeslider_visible=False,
        yaxis_title="Price USD",
        template="plotly_dark",
        height=600,
        hovermode="x unified"
    )
    st.plotly_chart(fig_btc, use_container_width=True, key="btc_candlestick_main")

    # VIX Deviation
    if not df_vix.empty:
        levels = get_deviation_levels(df_vix, sigma_levels=[1, 2])
        fig_vix_dev = go.Figure()
        fig_vix_dev.add_trace(go.Scatter(x=df_vix["date"], y=df_vix["deviation_pct"],
                                         mode="lines", name="Отклонение %", line=dict(color="deepskyblue", width=2)))
        fig_vix_dev.add_trace(go.Scatter(x=[df_vix["date"].min(), df_vix["date"].max()], y=[levels["mean"], levels["mean"]],
                                         mode="lines", name="Среднее", line=dict(color="red", width=2)))
        for level in [1, 2]:
            fig_vix_dev.add_trace(go.Scatter(x=[df_vix["date"].min(), df_vix["date"].max()], y=[levels[f"+{level}σ"], levels[f"+{level}σ"]],
                                             mode="lines", name=f"+{level}σ", line=dict(color="orange", dash="dash" if level == 1 else "solid")))
            fig_vix_dev.add_trace(go.Scatter(x=[df_vix["date"].min(), df_vix["date"].max()], y=[levels[f"-{level}σ"], levels[f"-{level}σ"]],
                                             mode="lines", name=f"-{level}σ", line=dict(color="limegreen", dash="dash" if level == 1 else "solid")))
        
        padding = pd.Timedelta(days=7)
        fig_vix_dev.update_xaxes(range=[df_vix["date"].min() - padding, df_vix["date"].max() + padding])
        
        fig_vix_dev.update_layout(
            title="VIX Mean Reversion Deviation (%)",
            yaxis_title="Отклонение (%)",
            template="plotly_dark",
            showlegend=False,
            height=400,
            hovermode="x unified"
        )
        st.plotly_chart(fig_vix_dev, use_container_width=True, key="vix_deviation_main")

    # COT Indexes
    if not df_cot.empty:
        fig_indexes = go.Figure()
        fig_indexes.add_trace(go.Scatter(x=df_cot["date"], y=df_cot["COT_Index_Large_Inverted_26w"],
                                         name="Large Inverted", line=dict(color="deepskyblue", width=2)))
        fig_indexes.add_trace(go.Scatter(x=df_cot["date"], y=df_cot["COT_Index_Comm_26w"],
                                         name="Commercial", line=dict(color="orange", width=2)))
        for level in [20, 80]:
            fig_indexes.add_hline(y=level, line_dash="dash", line_color="red" if level == 20 else "green")
        
        padding = pd.Timedelta(days=7)
        fig_indexes.update_xaxes(range=[df_cot["date"].min() - padding, df_cot["date"].max() + padding])
        
        fig_indexes.update_layout(
            title="COT Indexes BTC (26w)",
            yaxis_title="Percents",
            yaxis=dict(range=[0, 100]),
            template="plotly_dark",
            showlegend=False,
            height=400,
            hovermode="x unified"
        )
        st.plotly_chart(fig_indexes, use_container_width=True, key="cot_indexes_main")

    # Net Positions
    if not df_cot.empty:
        fig_net = go.Figure()
        fig_net.add_trace(go.Scatter(x=df_cot["date"], y=df_cot["Comm_Net"], name="Commercial", line=dict(color="red")))
        fig_net.add_trace(go.Scatter(x=df_cot["date"], y=df_cot["Large_Specs_Net"], name="Large Speculators", line=dict(color="limegreen")))
        fig_net.add_trace(go.Scatter(x=df_cot["date"], y=df_cot["Small_Traders_Net"], name="Small Traders", line=dict(color="deepskyblue")))
        
        padding = pd.Timedelta(days=7)
        fig_net.update_xaxes(range=[df_cot["date"].min() - padding, df_cot["date"].max() + padding])
        
        fig_net.update_layout(
            title="Net Positions",
            yaxis_title="Net Contracts",
            template="plotly_dark",
            showlegend=False,
            height=400,
            hovermode="x unified"
        )
        st.plotly_chart(fig_net, use_container_width=True, key="net_positions_main")

    # Open Interest
    if not df_cot.empty:
        fig_oi = go.Figure()
        fig_oi.add_trace(go.Scatter(x=df_cot["date"], y=df_cot["open_interest_all"], name="Open Interest", line=dict(color="purple", width=2)))
        
        padding = pd.Timedelta(days=7)
        fig_oi.update_xaxes(range=[df_cot["date"].min() - padding, df_cot["date"].max() + padding])
        
        fig_oi.update_layout(
            title="Open Interest BTC",
            yaxis_title="Contracts",
            template="plotly_dark",
            showlegend=False,
            height=400,
            hovermode="x unified"
        )
        st.plotly_chart(fig_oi, use_container_width=True, key="oi_main")

# === BTC COT Details ===
with tab_cot:
    df_btc, df_vix, df_cot = get_filtered_dfs()

    if not df_cot.empty:
        fig_indexes = go.Figure()
        fig_indexes.add_trace(go.Scatter(x=df_cot["date"], y=df_cot["COT_Index_Large_Inverted_26w"],
                                         name="Large Inverted", line=dict(color="deepskyblue", width=2)))
        fig_indexes.add_trace(go.Scatter(x=df_cot["date"], y=df_cot["COT_Index_Comm_26w"],
                                         name="Commercial", line=dict(color="orange", width=2)))
        for level in [20, 80]:
            fig_indexes.add_hline(y=level, line_dash="dash", line_color="red" if level == 20 else "green")
        
        padding = pd.Timedelta(days=7)
        fig_indexes.update_xaxes(range=[df_cot["date"].min() - pd.Timedelta(days=7), df_cot["date"].max() + padding])
        
        fig_indexes.update_layout(
            title="COT Indexes BTC (26w)",
            yaxis=dict(range=[0, 100]),
            yaxis_title="Percents",
            template="plotly_dark",
            showlegend=False,
            height=400,
            hovermode="x unified"
        )
        st.plotly_chart(fig_indexes, use_container_width=True, key="cot_indexes_detail")

    if not df_cot.empty:
        fig_net = go.Figure()
        fig_net.add_trace(go.Scatter(x=df_cot["date"], y=df_cot["Comm_Net"], name="Commercial", line=dict(color="red")))
        fig_net.add_trace(go.Scatter(x=df_cot["date"], y=df_cot["Large_Specs_Net"], name="Large Speculators", line=dict(color="limegreen")))
        fig_net.add_trace(go.Scatter(x=df_cot["date"], y=df_cot["Small_Traders_Net"], name="Small Traders", line=dict(color="deepskyblue")))
        
        padding = pd.Timedelta(days=7)
        fig_net.update_xaxes(range=[df_cot["date"].min() - padding, df_cot["date"].max() + padding])
        
        fig_net.update_layout(
            title="Net Positions",
            yaxis_title="Net Contracts",
            template="plotly_dark",
            showlegend=False,
            height=400,
            hovermode="x unified"
        )
        st.plotly_chart(fig_net, use_container_width=True, key="net_positions_detail")

    if not df_cot.empty:
        fig_oi = go.Figure()
        fig_oi.add_trace(go.Scatter(x=df_cot["date"], y=df_cot["open_interest_all"], name="Open Interest", line=dict(color="purple", width=2)))
        
        padding = pd.Timedelta(days=7)
        fig_oi.update_xaxes(range=[df_cot["date"].min() - padding, df_cot["date"].max() + padding])
        
        fig_oi.update_layout(
            title="Open Interest BTC",
            yaxis_title="Contracts",
            template="plotly_dark",
            showlegend=False,
            height=400,
            hovermode="x unified"
        )
        st.plotly_chart(fig_oi, use_container_width=True, key="oi_detail")

st.caption("MacroCryptoSentinel — макро-дэшборд для BTC с VIX и COT.")