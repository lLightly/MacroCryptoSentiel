# app.py  (2026-02 — полный вариант: все вкладки, уникальные keys для plotly_chart,
# удалён use_container_width (deprecated/removed), цвета/стили сохранены)

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import datetime as dt
from pathlib import Path

# ---- local modules ---------------------------------------------------------
from main import main as update_data
from src.analytics.statistics import get_deviation_levels

# ---- page & layout ---------------------------------------------------------
st.set_page_config(page_title="MacroCryptoSentinel", layout="wide")
st.title("MacroCryptoSentinel")

# ---------------------------------------------------------------------------
#                                I/O helpers
# ---------------------------------------------------------------------------
DATA_DIR = Path("data/processed")

FILES = {
    "vix": DATA_DIR / "vix_processed.csv",
    "btc_cot": DATA_DIR / "btc_cot_processed.csv",
    "btc": DATA_DIR / "btc_price.csv",
    "eth_cot": DATA_DIR / "eth_cot_processed.csv",
    "eth": DATA_DIR / "eth_price.csv",
    "spx": DATA_DIR / "spx_price.csv",
    "nasdaq": DATA_DIR / "nasdaq_price.csv",
    "dxy": DATA_DIR / "dxy_price.csv",
    "us10y": DATA_DIR / "us10y_price.csv",
}


@st.cache_data(show_spinner=False)
def load_csv(path: Path, tz_aware: bool = True) -> pd.DataFrame | None:
    if not path.exists():
        return None
    df = pd.read_csv(path)
    if "date" in df.columns:
        if tz_aware:
            df["date"] = pd.to_datetime(df["date"], utc=True).dt.tz_localize(None)
        else:
            df["date"] = pd.to_datetime(df["date"])
    return df


def all_data_loaded(dict_dfs: dict[str, pd.DataFrame | None]) -> bool:
    return all(df is not None and not df.empty for df in dict_dfs.values())


def filter_df(df: pd.DataFrame, start: dt.date, end: dt.date) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    return df[df["date"].dt.date.between(start, end)].reset_index(drop=True)


# ---------------------------------------------------------------------------
#                   0. Fetch / refresh raw & processed data
# ---------------------------------------------------------------------------
if st.button("Обновить все данные"):
    with st.spinner("Скачиваю и обрабатываю данные…"):
        update_data()
        st.cache_data.clear()
    st.success("Данные обновлены!")

# ---------------------------------------------------------------------------
#                   1. Load every processed dataset
# ---------------------------------------------------------------------------
dfs = {key: load_csv(path) for key, path in FILES.items()}

if not all_data_loaded(dfs):
    st.error("Не все данные загружены — нажмите кнопку обновления.")
    st.stop()

# ---------------------------------------------------------------------------
#                   2. Date-range slider (global min-max)
# ---------------------------------------------------------------------------
all_dates = pd.concat([df["date"] for df in dfs.values() if df is not None])
global_min, global_max = all_dates.min().date(), all_dates.max().date()

default_start = dt.date(global_max.year - 3, 1, 1)
if default_start < global_min:
    default_start = global_min

start_date, end_date = st.slider(
    "Выберите диапазон дат",
    min_value=global_min,
    max_value=global_max,
    value=(default_start, global_max),
    format="DD.MM.YYYY",
)

# convenience getter per asset (‘BTC’ / ‘ETH’)
def get_filtered(asset: str):
    price_key = "btc" if asset == "BTC" else "eth"
    cot_key = "btc_cot" if asset == "BTC" else "eth_cot"
    df_price = filter_df(dfs[price_key], start_date, end_date)
    df_cot = filter_df(dfs[cot_key], start_date, end_date)
    df_vix = filter_df(dfs["vix"], start_date, end_date)
    df_spx = filter_df(dfs["spx"], start_date, end_date)
    df_nasdaq = filter_df(dfs["nasdaq"], start_date, end_date)
    df_dxy = filter_df(dfs["dxy"], start_date, end_date)
    df_us10y = filter_df(dfs["us10y"], start_date, end_date)
    return df_price, df_vix, df_cot, df_spx, df_nasdaq, df_dxy, df_us10y


# ---------------------------------------------------------------------------
#                   3. Tabs
# ---------------------------------------------------------------------------
(
    tab_btc,
    tab_eth,
    tab_macro,
    tab_conclusion,
) = st.tabs(
    [
        "BITCOIN Dashboard",
        "ETHUSDT Dashboard",
        "Macro Context",
        "Conclusion",
    ]
)

PADDING = pd.Timedelta(days=7)

# ---------------------------------------------------------------------------
#                   3-A. BITCOIN DASHBOARD
# ---------------------------------------------------------------------------
with tab_btc:
    df_btc, df_vix, df_cot, *_ = get_filtered("BTC")

    # --- BTC Price candlestick
    if not df_btc.empty:
        fig = go.Figure(
            go.Candlestick(
                x=df_btc["date"],
                open=df_btc["open"],
                high=df_btc["high"],
                low=df_btc["low"],
                close=df_btc["close"],
                name="BTC-USD",
            )
        )
        fig.update_xaxes(
            range=[df_btc["date"].min() - PADDING, df_btc["date"].max() + PADDING]
        )
        fig.update_layout(
            title="BTC Price (Binance)",
            xaxis_rangeslider_visible=False,
            yaxis_title="Price USD",
            template="plotly_dark",
            height=600,
            hovermode="x unified",
            showlegend=False,
        )
        st.plotly_chart(fig, key="btc_dash_price")

    # --- VIX mean-reversion deviation
    if not df_vix.empty:
        levels = get_deviation_levels(df_vix, sigma_levels=[1, 2])
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=df_vix["date"],
                y=df_vix["deviation_pct"],
                mode="lines",
                name="Отклонение %",
                line=dict(color="deepskyblue", width=2),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=[df_vix["date"].min(), df_vix["date"].max()],
                y=[levels["mean"], levels["mean"]],
                mode="lines",
                name="Среднее",
                line=dict(color="red", width=2),
            )
        )
        for level in [1, 2]:
            dash = "dash" if level == 1 else "solid"
            fig.add_trace(
                go.Scatter(
                    x=[df_vix["date"].min(), df_vix["date"].max()],
                    y=[levels[f"+{level}σ"], levels[f"+{level}σ"]],
                    mode="lines",
                    name=f"+{level}σ",
                    line=dict(color="orange", dash=dash),
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=[df_vix["date"].min(), df_vix["date"].max()],
                    y=[levels[f"-{level}σ"], levels[f"-{level}σ"]],
                    mode="lines",
                    name=f"-{level}σ",
                    line=dict(color="limegreen", dash=dash),
                )
            )
        fig.update_xaxes(
            range=[df_vix["date"].min() - PADDING, df_vix["date"].max() + PADDING]
        )
        fig.update_layout(
            title="VIX Mean-Reversion Deviation (%)",
            yaxis_title="Отклонение (%)",
            template="plotly_dark",
            height=400,
            hovermode="x unified",
            showlegend=False,
        )
        st.plotly_chart(fig, key="btc_dash_vix")

    # --- BTC COT indexes
    if not df_cot.empty:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=df_cot["date"],
                y=df_cot["COT_Index_Large_Inverted_26w"],
                name="Large Inverted",
                line=dict(color="deepskyblue", width=2),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df_cot["date"],
                y=df_cot["COT_Index_Comm_26w"],
                name="Commercial",
                line=dict(color="orange", width=2),
            )
        )
        fig.add_hline(y=80, line_color="green", line_dash="dash")
        fig.add_hline(y=20, line_color="red", line_dash="dash")
        fig.update_xaxes(
            range=[df_cot["date"].min() - PADDING, df_cot["date"].max() + PADDING]
        )
        fig.update_layout(
            title="COT Indexes BTC (26 w)",
            yaxis=dict(range=[0, 100]),
            yaxis_title="Percents",
            template="plotly_dark",
            height=400,
            hovermode="x unified",
            showlegend=False,
        )
        st.plotly_chart(fig, key="btc_dash_cot_idx")

    # --- Net positions
    if not df_cot.empty:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(x=df_cot["date"], y=df_cot["Comm_Net"], name="Commercial", line=dict(color="red"))
        )
        fig.add_trace(
            go.Scatter(x=df_cot["date"], y=df_cot["Large_Specs_Net"], name="Large Specs", line=dict(color="limegreen"))
        )
        fig.add_trace(
            go.Scatter(x=df_cot["date"], y=df_cot["Small_Traders_Net"], name="Small Traders", line=dict(color="deepskyblue"))
        )
        fig.update_xaxes(
            range=[df_cot["date"].min() - PADDING, df_cot["date"].max() + PADDING]
        )
        fig.update_layout(
            title="Net Positions",
            yaxis_title="Net Contracts",
            template="plotly_dark",
            height=400,
            hovermode="x unified",
            showlegend=False,
        )
        st.plotly_chart(fig, key="btc_dash_net")

    # --- Z-Score
    if not df_cot.empty:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=df_cot["date"],
                y=df_cot["Z_Score_Large"],
                name="Z-Score",
                line=dict(color="yellow", width=2),
            )
        )
        fig.add_hline(y=2, line_color="red", line_dash="dash")
        fig.add_hline(y=-2, line_color="green", line_dash="dash")
        fig.update_xaxes(
            range=[df_cot["date"].min() - PADDING, df_cot["date"].max() + PADDING]
        )
        fig.update_layout(
            title="COT Z-Score (Large Specs, 2 y)",
            yaxis_title="Z-Score",
            template="plotly_dark",
            height=400,
            hovermode="x unified",
            showlegend=False,
        )
        st.plotly_chart(fig, key="btc_dash_z")

    # --- Open interest
    if not df_cot.empty:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=df_cot["date"],
                y=df_cot["open_interest_all"],
                name="Open Interest",
                line=dict(color="purple", width=2),
            )
        )
        fig.update_xaxes(
            range=[df_cot["date"].min() - PADDING, df_cot["date"].max() + PADDING]
        )
        fig.update_layout(
            title="Open Interest BTC",
            yaxis_title="Contracts",
            template="plotly_dark",
            height=400,
            hovermode="x unified",
            showlegend=False,
        )
        st.plotly_chart(fig, key="btc_dash_oi")

# ---------------------------------------------------------------------------
#                   3-C. ETHUSDT DASHBOARD
# ---------------------------------------------------------------------------
with tab_eth:
    df_eth, df_vix, df_eth_cot, *_ = get_filtered("ETH")

    if not df_eth.empty:
        fig = go.Figure(
            go.Candlestick(
                x=df_eth["date"],
                open=df_eth["open"],
                high=df_eth["high"],
                low=df_eth["low"],
                close=df_eth["close"],
                name="ETH-USD",
            )
        )
        fig.update_xaxes(
            range=[df_eth["date"].min() - PADDING, df_eth["date"].max() + PADDING]
        )
        fig.update_layout(
            title="ETH Price (Binance)",
            xaxis_rangeslider_visible=False,
            yaxis_title="Price USD",
            template="plotly_dark",
            height=600,
            hovermode="x unified",
            showlegend=False,
        )
        st.plotly_chart(fig, key="eth_dash_price")

    if not df_vix.empty:
        levels = get_deviation_levels(df_vix, sigma_levels=[1, 2])
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=df_vix["date"],
                y=df_vix["deviation_pct"],
                mode="lines",
                name="Отклонение %",
                line=dict(color="deepskyblue", width=2),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=[df_vix["date"].min(), df_vix["date"].max()],
                y=[levels["mean"], levels["mean"]],
                mode="lines",
                name="Среднее",
                line=dict(color="red", width=2),
            )
        )
        for level in [1, 2]:
            dash = "dash" if level == 1 else "solid"
            fig.add_trace(
                go.Scatter(
                    x=[df_vix["date"].min(), df_vix["date"].max()],
                    y=[levels[f"+{level}σ"], levels[f"+{level}σ"]],
                    mode="lines",
                    name=f"+{level}σ",
                    line=dict(color="orange", dash=dash),
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=[df_vix["date"].min(), df_vix["date"].max()],
                    y=[levels[f"-{level}σ"], levels[f"-{level}σ"]],
                    mode="lines",
                    name=f"-{level}σ",
                    line=dict(color="limegreen", dash=dash),
                )
            )
        fig.update_xaxes(
            range=[df_vix["date"].min() - PADDING, df_vix["date"].max() + PADDING]
        )
        fig.update_layout(
            title="VIX Mean-Reversion Deviation (%)",
            yaxis_title="Отклонение (%)",
            template="plotly_dark",
            height=400,
            hovermode="x unified",
            showlegend=False,
        )
        st.plotly_chart(fig, key="eth_dash_vix")

    if not df_eth_cot.empty:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=df_eth_cot["date"],
                y=df_eth_cot["COT_Index_Large_Inverted_26w"],
                name="Large Inverted",
                line=dict(color="deepskyblue", width=2),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df_eth_cot["date"],
                y=df_eth_cot["COT_Index_Comm_26w"],
                name="Commercial",
                line=dict(color="orange", width=2),
            )
        )
        fig.add_hline(y=80, line_color="green", line_dash="dash")
        fig.add_hline(y=20, line_color="red", line_dash="dash")
        fig.update_xaxes(
            range=[df_eth_cot["date"].min() - PADDING, df_eth_cot["date"].max() + PADDING]
        )
        fig.update_layout(
            title="COT Indexes ETH (26 w)",
            yaxis=dict(range=[0, 100]),
            yaxis_title="Percents",
            template="plotly_dark",
            height=400,
            hovermode="x unified",
            showlegend=False,
        )
        st.plotly_chart(fig, key="eth_dash_cot_idx")

    if not df_eth_cot.empty:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(x=df_eth_cot["date"], y=df_eth_cot["Comm_Net"], name="Commercial", line=dict(color="red"))
        )
        fig.add_trace(
            go.Scatter(x=df_eth_cot["date"], y=df_eth_cot["Large_Specs_Net"], name="Large Specs", line=dict(color="limegreen"))
        )
        fig.add_trace(
            go.Scatter(x=df_eth_cot["date"], y=df_eth_cot["Small_Traders_Net"], name="Small Traders", line=dict(color="deepskyblue"))
        )
        fig.update_xaxes(
            range=[df_eth_cot["date"].min() - PADDING, df_eth_cot["date"].max() + PADDING]
        )
        fig.update_layout(
            title="Net Positions ETH",
            yaxis_title="Net Contracts",
            template="plotly_dark",
            height=400,
            hovermode="x unified",
            showlegend=False,
        )
        st.plotly_chart(fig, key="eth_dash_net")

    if not df_eth_cot.empty:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=df_eth_cot["date"],
                y=df_eth_cot["Z_Score_Large"],
                name="Z-Score",
                line=dict(color="yellow", width=2),
            )
        )
        fig.add_hline(y=2, line_color="red", line_dash="dash")
        fig.add_hline(y=-2, line_color="green", line_dash="dash")
        fig.update_xaxes(
            range=[df_eth_cot["date"].min() - PADDING, df_eth_cot["date"].max() + PADDING]
        )
        fig.update_layout(
            title="COT Z-Score (Large Specs, 2 y)",
            yaxis_title="Z-Score",
            template="plotly_dark",
            height=400,
            hovermode="x unified",
            showlegend=False,
        )
        st.plotly_chart(fig, key="eth_dash_z")

    if not df_eth_cot.empty:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=df_eth_cot["date"],
                y=df_eth_cot["open_interest_all"],
                name="Open Interest",
                line=dict(color="purple", width=2),
            )
        )
        fig.update_xaxes(
            range=[df_eth_cot["date"].min() - PADDING, df_eth_cot["date"].max() + PADDING]
        )
        fig.update_layout(
            title="Open Interest ETH",
            yaxis_title="Contracts",
            template="plotly_dark",
            height=400,
            hovermode="x unified",
            showlegend=False,
        )
        st.plotly_chart(fig, key="eth_dash_oi")

# ---------------------------------------------------------------------------
#                   3-E. MACRO Context
# ---------------------------------------------------------------------------
with tab_macro:
    df_btc, df_vix, _, df_spx, df_nasdaq, df_dxy, df_us10y = get_filtered("BTC")

    if not df_btc.empty and not df_spx.empty and not df_nasdaq.empty:
        df_btc = df_btc.copy()
        df_spx = df_spx.copy()
        df_nasdaq = df_nasdaq.copy()

        df_btc["btc_pct"] = (df_btc["close"] / df_btc["close"].iloc[0] - 1) * 100
        df_spx["spx_pct"] = (df_spx["close"] / df_spx["close"].iloc[0] - 1) * 100
        df_nasdaq["nasdaq_pct"] = (df_nasdaq["close"] / df_nasdaq["close"].iloc[0] - 1) * 100

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_btc["date"], y=df_btc["btc_pct"], name="BTC %", line=dict(color="orange")))
        fig.add_trace(go.Scatter(x=df_spx["date"], y=df_spx["spx_pct"], name="S&P 500 %", line=dict(color="green")))
        fig.add_trace(go.Scatter(x=df_nasdaq["date"], y=df_nasdaq["nasdaq_pct"], name="Nasdaq %", line=dict(color="blue")))
        m = min(df_btc["date"].min(), df_spx["date"].min(), df_nasdaq["date"].min())
        M = max(df_btc["date"].max(), df_spx["date"].max(), df_nasdaq["date"].max())
        fig.update_xaxes(range=[m - PADDING, M + PADDING])
        fig.update_layout(
            title="Risk-On / Risk-Off (normalised % change)",
            yaxis_title="% change",
            template="plotly_dark",
            height=400,
            hovermode="x unified",
            showlegend=False,
        )
        st.plotly_chart(fig, key="macro_risk")

    if not df_btc.empty and not df_dxy.empty and not df_us10y.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_btc["date"], y=df_btc["close"], name="BTC", yaxis="y1", line=dict(color="orange")))
        fig.add_trace(go.Scatter(x=df_dxy["date"], y=df_dxy["close"], name="DXY", yaxis="y2", line=dict(color="red")))
        fig.add_trace(go.Scatter(x=df_us10y["date"], y=df_us10y["close"], name="US10Y", yaxis="y3", line=dict(color="purple")))
        m = min(df_btc["date"].min(), df_dxy["date"].min(), df_us10y["date"].min())
        M = max(df_btc["date"].max(), df_dxy["date"].max(), df_us10y["date"].max())
        fig.update_xaxes(range=[m - PADDING, M + PADDING])
        fig.update_layout(
            template="plotly_dark",
            title="Liquidity Vacuum: BTC / DXY / US10Y",
            yaxis=dict(title="BTC Price", side="left"),
            yaxis2=dict(title="DXY", overlaying="y", side="right"),
            yaxis3=dict(title="US10Y", overlaying="y", side="right", anchor="free", position=1),
            height=400,
            hovermode="x unified",
            showlegend=False,
        )
        st.plotly_chart(fig, key="macro_liq")

    # -------- Rolling Correlation (fixed: normalize dates, daily grid, ffill SPX) ------------
    if not df_btc.empty and not df_spx.empty:
        # Нормализуем даты (убираем время / тайзону) и вычисляем границы
        btc_min, btc_max = df_btc["date"].min().normalize(), df_btc["date"].max().normalize()
        spx_min, spx_max = df_spx["date"].min().normalize(), df_spx["date"].max().normalize()
        start = min(btc_min, spx_min)
        end = max(btc_max, spx_max)

        # Дневная сетка
        date_range = pd.date_range(start=start, end=end, freq="D")

        # Серии: normalize + set_index + reindex на дневную сетку
        btc_series = (
            df_btc.assign(date=df_btc["date"].dt.normalize())
            .set_index("date")["close"]
            .reindex(date_range)
        )
        spx_series = (
            df_spx.assign(date=df_spx["date"].dt.normalize())
            .set_index("date")["close"]
            .reindex(date_range)
            .ffill()  # заполняем выходные/праздники S&P предыдущим значением
        )

        # Собираем DataFrame и убираем дни без BTC
        prices = pd.DataFrame({"btc": btc_series, "spx": spx_series})
        prices = prices.dropna(subset=["btc"])  # требуется, чтобы были реальные дни BTC

        if prices.empty:
            st.warning("Нет пересекающихся данных по BTC в выбранном диапазоне.")
        elif prices["spx"].isna().all():
            st.warning("Нет данных по S&P 500 в выбранном диапазоне — корреляция не может быть рассчитана.")
        else:
            # Скользящая корреляция: окно 60 дней, min_periods=20 (как в оригинале можно изменить)
            prices["corr"] = prices["btc"].rolling(window=60, min_periods=20).corr(prices["spx"])

            corr_series = prices["corr"].dropna()
            if corr_series.empty:
                st.warning("Недостаточно пересекающихся данных для расчёта корреляции (требуется ≥20 дней в окне).")
            else:
                if len(corr_series) < 30:
                    st.info(f"Корреляция рассчитана на {len(corr_series)} днях (рекомендуется ≥30 для надёжности).")

                fig = go.Figure()
                fig.add_trace(
                    go.Scatter(
                        x=corr_series.index,
                        y=corr_series.values,
                        name="60d corr",
                        line=dict(color="cyan", width=2),
                    )
                )
                fig.add_hline(y=0.8, line_dash="dash", line_color="red")
                fig.add_hline(y=0.0, line_dash="dot", line_color="gray")
                fig.add_hline(y=-0.8, line_dash="dash", line_color="green")
                fig.update_xaxes(range=[date_range.min() - PADDING, date_range.max() + PADDING])
                fig.update_layout(
                    template="plotly_dark",
                    title="BTC / S&P 500 Rolling Correlation (60 d, daily grid, ffill SPX)",
                    yaxis=dict(range=[-1, 1], title="Correlation"),
                    height=400,
                    hovermode="x unified",
                    showlegend=False,
                )
                st.plotly_chart(fig, key="macro_corr")
    else:
        st.warning("Нет данных по BTC или S&P 500 в выбранном диапазоне.")

# ---------------------------------------------------------------------------
#                   3-F. CONCLUSION — version 2.0
# ---------------------------------------------------------------------------
with tab_conclusion:
    st.subheader("Алгоритмическая таблица")

    def pct_change(df: pd.DataFrame, n: int = 30) -> float:
        if len(df) < n + 1:
            return 0.0
        return (df["close"].iloc[-1] / df["close"].iloc[-n - 1] - 1) * 100

    latest = {
        "vix": dfs["vix"]["close"].iloc[-1] if not dfs["vix"].empty else 0,
        "vix_dev": dfs["vix"]["deviation_pct"].iloc[-1] if not dfs["vix"].empty else 0,
        "dxy_30d": pct_change(dfs["dxy"]),
        "us10y_30d": pct_change(dfs["us10y"]),
    }

    df_corr_full = pd.merge(
        dfs["btc"][["date", "close"]],
        dfs["spx"][["date", "close"]],
        on="date",
        suffixes=("_btc", "_spx"),
    )
    if len(df_corr_full) >= 60:
        latest["corr_spx"] = df_corr_full["close_btc"].rolling(60).corr(df_corr_full["close_spx"]).iloc[-1]
    else:
        latest["corr_spx"] = 0.0

    for asset, cot_key in [("BTC", "btc_cot"), ("ETH", "eth_cot")]:
        cot = dfs[cot_key]
        latest[f"{asset}_z"] = cot["Z_Score_Large"].iloc[-1] if not cot.empty else 0
        latest[f"{asset}_cot_large"] = cot["COT_Index_Large_Inverted_26w"].iloc[-1] if not cot.empty else 50
        latest[f"{asset}_mom"] = pct_change(dfs[asset.lower()])

    def score_asset(asset: str) -> tuple[pd.DataFrame, float, str]:
        rows = []

        if latest["vix"] > 30:
            rows.append(("VIX > 30", -1, "Высокая волатильность → Risk-off"))
        elif latest["vix"] < 15:
            rows.append(("VIX < 15", +1, "Низкая волатильность → Risk-on"))

        vix_levels = get_deviation_levels(dfs["vix"])
        if latest["vix_dev"] > vix_levels["+2σ"]:
            rows.append(("VIX Dev > +2σ", -1, "Сильно перекуплен VIX"))
        elif latest["vix_dev"] < vix_levels["-2σ"]:
            rows.append(("VIX Dev < -2σ", +1, "Сильно перепродан VIX"))

        mom = latest[f"{asset}_mom"]
        if mom > 15:
            rows.append((f"{asset} +15% (30d)", +0.5, "Сильный бычий импульс"))
        elif mom < -15:
            rows.append((f"{asset} −15% (30d)", -0.5, "Сильный медвежий импульс"))

        z = latest[f"{asset}_z"]
        if z > 2:
            rows.append(("COT z > 2", -1, "Large Specs over-long"))
        elif z < -2:
            rows.append(("COT z < -2", +1, "Large Specs over-short"))

        idx = latest[f"{asset}_cot_large"]
        if idx > 80:
            rows.append(("COT Large Inv > 80", +1, "Крайне бычий"))
        elif idx < 20:
            rows.append(("COT Large Inv < 20", -1, "Крайне медвежий"))

        if latest["corr_spx"] > 0.8:
            rows.append(("BTC-S&P Corr > 0.8", -0.5, "Зависимость от акций"))

        liq_score = 0
        if latest["dxy_30d"] > 5:
            liq_score -= 0.5
        elif latest["dxy_30d"] < -5:
            liq_score += 0.5
        if latest["us10y_30d"] > 10:
            liq_score -= 0.5
        elif latest["us10y_30d"] < -10:
            liq_score += 0.5
        if liq_score != 0:
            rows.append(("Liquidity composite", liq_score, "DXY & US10Y 30d move"))

        df = pd.DataFrame(rows, columns=["Factor", "Score", "Rationale"])
        total = df["Score"].sum()
        verdict = (
            "Strong Buy" if total >= 2
            else "Buy" if total > 0
            else "Neutral" if total == 0
            else "Sell" if total > -2
            else "Strong Sell"
        )
        return df, total, verdict

    for asset in ["BTC", "ETH"]:
        st.markdown(f"### {asset}")
        df_sc, tot, ver = score_asset(asset)
        st.dataframe(df_sc.style.format({"Score": "{:+.1f}"}))
        st.markdown(f"**Итог ({asset}): {tot:+.1f} → {ver}**")

    combined = sum(score_asset(a)[1] for a in ["BTC", "ETH"]) / 2
    st.markdown(
        f"""
        ---
        ### <span style="font-size:22px">Комбинированный обзор рынка</span>

        **Суммарный балл**: {combined:+.1f}  
        **Вердикт**: {'🚀 Сильный лонг' if combined>=2 else '📈 лонг' if combined>0 else '⚖️ Нейтрально' if combined==0 else '🔻 Шорт' if combined>-2 else '🛑 Сильный шорт'}
        """,
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
#                      footer
# ---------------------------------------------------------------------------
st.caption("MacroCryptoSentinel — система оценки вероятностей для BTC и ETH с макро-контекстом.")