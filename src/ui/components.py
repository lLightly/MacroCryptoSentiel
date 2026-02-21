from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from src.analytics.statistics import get_deviation_levels, get_quantile_thresholds
from src.config.settings import get_settings

DEFAULT_TEMPLATE = "plotly_dark"


def _pad(fig: go.Figure, x: pd.Series, padding_days: int) -> go.Figure:
    pad = pd.Timedelta(days=padding_days)
    fig.update_xaxes(range=[x.min() - pad, x.max() + pad])
    return fig


def _set_x_range(fig: go.Figure, x_range_min, x_range_max, padding_days: int) -> None:
    if x_range_min is None or x_range_max is None:
        return
    pad = pd.Timedelta(days=padding_days)
    fig.update_xaxes(range=[x_range_min - pad, x_range_max + pad])


def candlestick(
    df: pd.DataFrame,
    title: str,
    padding_days: int | None = None,
    x_range_min=None,
    x_range_max=None,
) -> go.Figure:
    s = get_settings()
    padding_days = padding_days if padding_days is not None else s.ui.plot_padding_days

    fig = go.Figure(
        go.Candlestick(
            x=df["date"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name=title.split()[0],
        )
    )
    _set_x_range(fig, x_range_min, x_range_max, padding_days)
    if x_range_min is None or x_range_max is None:
        _pad(fig, df["date"], padding_days)

    fig.update_layout(
        title=title,
        template=DEFAULT_TEMPLATE,
        height=600,
        xaxis_rangeslider_visible=False,
        yaxis_title="Price USD",
        hovermode="x unified",
        showlegend=False,
    )
    return fig


def vix_deviation(
    df: pd.DataFrame,
    sigma_levels=None,
    padding_days: int | None = None,
    x_range_min=None,
    x_range_max=None,
) -> go.Figure:
    s = get_settings()
    padding_days = padding_days if padding_days is not None else s.ui.plot_padding_days
    sigma_levels = sigma_levels if sigma_levels is not None else s.ui.sigma_levels

    levels = get_deviation_levels(df, sigma_levels=list(sigma_levels))
    thresh = get_quantile_thresholds(df["deviation_pct"])

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["deviation_pct"],
            mode="lines",
            name="Deviation %",
            line=dict(color="deepskyblue", width=2),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[df["date"].min(), df["date"].max()],
            y=[levels["mean"]] * 2,
            mode="lines",
            name="Mean",
            line=dict(color="red", width=2),
        )
    )

    for sigma in sigma_levels:
        dash = "dash" if sigma == 1 else "solid"
        for sign, color in [("+", "orange"), ("-", "limegreen")]:
            fig.add_trace(
                go.Scatter(
                    x=[df["date"].min(), df["date"].max()],
                    y=[levels[f"{sign}{sigma}σ"]] * 2,
                    mode="lines",
                    name=f"{sign}{sigma}σ",
                    line=dict(color=color, dash=dash),
                )
            )

    fig.add_hline(
        y=thresh["p95"],
        line=dict(color="red", dash="dot", width=2),
        annotation_text=f"p95 = {thresh['p95']:.1f}%",
        annotation_position="bottom right",
    )
    fig.add_hline(y=thresh["p90"], line=dict(color="orange", dash="dot"), annotation_text=f"p90 = {thresh['p90']:.1f}%")
    fig.add_hline(y=thresh["p10"], line=dict(color="lime", dash="dot"), annotation_text=f"p10 = {thresh['p10']:.1f}%")
    fig.add_hline(
        y=thresh["p5"],
        line=dict(color="limegreen", dash="dot", width=2),
        annotation_text=f"p5 = {thresh['p5']:.1f}%",
    )

    _set_x_range(fig, x_range_min, x_range_max, padding_days)
    if x_range_min is None or x_range_max is None:
        _pad(fig, df["date"], padding_days)

    fig.update_layout(
        title="VIX Mean-Reversion Deviation (%)",
        yaxis_title="Deviation (%)",
        template=DEFAULT_TEMPLATE,
        height=420,
        hovermode="x unified",
        showlegend=False,
    )
    return fig


def cot_index(
    df: pd.DataFrame,
    asset: str,
    padding_days: int | None = None,
    x_range_min=None,
    x_range_max=None,
) -> go.Figure:
    s = get_settings()
    padding_days = padding_days if padding_days is not None else s.ui.plot_padding_days

    thresh_comm = get_quantile_thresholds(df["COT_Index_Comm_26w"])
    thresh_large = get_quantile_thresholds(df["COT_Index_Large_26w"])

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["date"], y=df["COT_Index_Large_26w"], name="Large", line=dict(color="deepskyblue", width=2)))
    fig.add_trace(go.Scatter(x=df["date"], y=df["COT_Index_Comm_26w"], name="Commercial", line=dict(color="orange", width=2)))

    fig.add_hline(y=thresh_comm["p95"], line=dict(color="red", dash="dot"), annotation_text=f"Comm p95 = {thresh_comm['p95']}")
    fig.add_hline(y=thresh_comm["p5"], line=dict(color="limegreen", dash="dot"), annotation_text=f"Comm p5 = {thresh_comm['p5']}")
    fig.add_hline(y=thresh_large["p95"], line=dict(color="red", dash="dot"), annotation_text=f"Large p95 = {thresh_large['p95']}")
    fig.add_hline(y=thresh_large["p5"], line=dict(color="limegreen", dash="dot"), annotation_text=f"Large p5 = {thresh_large['p5']}")

    fig.add_hline(y=80, line_color="green", line_dash="dash")
    fig.add_hline(y=20, line_color="red", line_dash="dash")

    _set_x_range(fig, x_range_min, x_range_max, padding_days)
    if x_range_min is None or x_range_max is None:
        _pad(fig, df["date"], padding_days)

    fig.update_layout(
        title=f"COT Indexes {asset} (26w)",
        yaxis=dict(range=[0, 100]),
        yaxis_title="Percent",
        template=DEFAULT_TEMPLATE,
        height=420,
        hovermode="x unified",
        showlegend=False,
    )
    return fig


def net_positions(
    df: pd.DataFrame,
    padding_days: int | None = None,
    x_range_min=None,
    x_range_max=None,
) -> go.Figure:
    s = get_settings()
    padding_days = padding_days if padding_days is not None else s.ui.plot_padding_days

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["date"], y=df["Comm_Net"], name="Commercial", line=dict(color="red")))
    fig.add_trace(go.Scatter(x=df["date"], y=df["Large_Specs_Net"], name="Large", line=dict(color="limegreen")))
    fig.add_trace(go.Scatter(x=df["date"], y=df["Small_Traders_Net"], name="Small", line=dict(color="deepskyblue")))

    _set_x_range(fig, x_range_min, x_range_max, padding_days)
    if x_range_min is None or x_range_max is None:
        _pad(fig, df["date"], padding_days)

    fig.update_layout(
        title="Net Positions",
        yaxis_title="Net Contracts",
        template=DEFAULT_TEMPLATE,
        height=400,
        hovermode="x unified",
        showlegend=False,
    )
    return fig


def z_score(
    df: pd.DataFrame,
    padding_days: int | None = None,
    x_range_min=None,
    x_range_max=None,
) -> go.Figure:
    s = get_settings()
    padding_days = padding_days if padding_days is not None else s.ui.plot_padding_days

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["date"], y=df["Z_Score_Large"], name="Z-Score", line=dict(color="yellow", width=2)))
    fig.add_hline(y=2, line_color="red", line_dash="dash")
    fig.add_hline(y=-2, line_color="green", line_dash="dash")

    _set_x_range(fig, x_range_min, x_range_max, padding_days)
    if x_range_min is None or x_range_max is None:
        _pad(fig, df["date"], padding_days)

    fig.update_layout(
        title="COT Z-Score (Large, 2y)",
        yaxis_title="Z-Score",
        template=DEFAULT_TEMPLATE,
        height=400,
        hovermode="x unified",
        showlegend=False,
    )
    return fig


def open_interest(
    df: pd.DataFrame,
    asset: str,
    padding_days: int | None = None,
    x_range_min=None,
    x_range_max=None,
) -> go.Figure:
    s = get_settings()
    padding_days = padding_days if padding_days is not None else s.ui.plot_padding_days

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["date"], y=df["open_interest_all"], name="Open Interest", line=dict(color="purple", width=2)))

    _set_x_range(fig, x_range_min, x_range_max, padding_days)
    if x_range_min is None or x_range_max is None:
        _pad(fig, df["date"], padding_days)

    fig.update_layout(
        title=f"Open Interest {asset}",
        yaxis_title="Contracts",
        template=DEFAULT_TEMPLATE,
        height=400,
        hovermode="x unified",
        showlegend=False,
    )
    return fig


def normalised_performance(
    series_map: dict[str, pd.DataFrame],
    padding_days: int | None = None,
    x_range_min=None,
    x_range_max=None,
) -> go.Figure:
    s = get_settings()
    padding_days = padding_days if padding_days is not None else s.ui.plot_padding_days

    fig = go.Figure()
    min_date, max_date = None, None

    for name, df in series_map.items():
        pct = (df["close"] / df["close"].iloc[0] - 1) * 100
        fig.add_trace(go.Scatter(x=df["date"], y=pct, name=name))
        min_date = df["date"].min() if min_date is None else min(min_date, df["date"].min())
        max_date = df["date"].max() if max_date is None else max(max_date, df["date"].max())

    _set_x_range(fig, x_range_min, x_range_max, padding_days)
    if x_range_min is None or x_range_max is None:
        _pad(fig, pd.Series([min_date, max_date]), padding_days)

    fig.update_layout(
        title="Risk-On / Risk-Off (normalised % change)",
        yaxis_title="% change",
        template=DEFAULT_TEMPLATE,
        height=400,
        hovermode="x unified",
        showlegend=False,
    )
    return fig


def liquidity_vacuum(
    df_btc: pd.DataFrame,
    df_dxy: pd.DataFrame,
    df_us10y: pd.DataFrame,
    padding_days: int | None = None,
    x_range_min=None,
    x_range_max=None,
) -> go.Figure:
    s = get_settings()
    padding_days = padding_days if padding_days is not None else s.ui.plot_padding_days

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_btc["date"], y=df_btc["close"], name="BTC", yaxis="y1", line=dict(color="orange")))
    fig.add_trace(go.Scatter(x=df_dxy["date"], y=df_dxy["close"], name="DXY", yaxis="y2", line=dict(color="red")))
    fig.add_trace(go.Scatter(x=df_us10y["date"], y=df_us10y["close"], name="US10Y", yaxis="y3", line=dict(color="purple")))

    min_date = min(df_btc["date"].min(), df_dxy["date"].min(), df_us10y["date"].min())
    max_date = max(df_btc["date"].max(), df_dxy["date"].max(), df_us10y["date"].max())

    _set_x_range(fig, x_range_min, x_range_max, padding_days)
    if x_range_min is None or x_range_max is None:
        _pad(fig, pd.Series([min_date, max_date]), padding_days)

    fig.update_layout(
        template=DEFAULT_TEMPLATE,
        title="Liquidity Vacuum: BTC / DXY / US10Y",
        yaxis=dict(title="Prices", side="left"),
        yaxis2=dict(overlaying="y", visible=False),
        yaxis3=dict(overlaying="y", visible=False),
        height=400,
        hovermode="x unified",
        showlegend=False,
    )
    return fig


def rolling_correlation(
    df_btc: pd.DataFrame,
    df_spx: pd.DataFrame,
    window: int = 60,
    min_periods: int = 20,
    padding_days: int | None = None,
    x_range_min=None,
    x_range_max=None,
) -> go.Figure:
    s = get_settings()
    padding_days = padding_days if padding_days is not None else s.ui.plot_padding_days

    btc_min, btc_max = df_btc["date"].min().normalize(), df_btc["date"].max().normalize()
    spx_min, spx_max = df_spx["date"].min().normalize(), df_spx["date"].max().normalize()

    start, end = min(btc_min, spx_min), max(btc_max, spx_max)
    date_range = pd.date_range(start=start, end=end, freq="D")

    btc_series = df_btc.assign(date=df_btc["date"].dt.normalize()).set_index("date")["close"].reindex(date_range)
    spx_series = df_spx.assign(date=df_spx["date"].dt.normalize()).set_index("date")["close"].reindex(date_range).ffill()

    prices = pd.DataFrame({"btc": btc_series, "spx": spx_series}).dropna(subset=["btc"])
    corr_series = prices["btc"].rolling(window=window, min_periods=min_periods).corr(prices["spx"])

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=corr_series.index, y=corr_series.values, name=f"{window}d corr", line=dict(color="cyan", width=2)))
    fig.add_hline(y=0.8, line_dash="dash", line_color="red")
    fig.add_hline(y=0.0, line_dash="dot", line_color="gray")
    fig.add_hline(y=-0.8, line_dash="dash", line_color="green")

    _set_x_range(fig, x_range_min, x_range_max, padding_days)
    if x_range_min is None or x_range_max is None:
        _pad(fig, pd.Series(corr_series.index), padding_days)

    fig.update_layout(
        template=DEFAULT_TEMPLATE,
        title=f"BTC / S&P 500 Rolling Correlation ({window}d)",
        yaxis=dict(range=[-1, 1], title="Correlation"),
        height=400,
        hovermode="x unified",
        showlegend=False,
    )
    return fig


def equity_curve_chart(
    df: pd.DataFrame,
    initial_capital: float,
    padding_days: int | None = None,
    x_range_min=None,
    x_range_max=None,
) -> go.Figure:
    s = get_settings()
    padding_days = padding_days if padding_days is not None else s.ui.plot_padding_days

    fig = go.Figure()
    if df.empty:
        fig.update_layout(title="No equity data", template=DEFAULT_TEMPLATE)
        return fig

    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["Equity"],
            mode="lines",
            name="Strategy Equity",
            line=dict(color="#00ff9d", width=3),
            hovertemplate="Date: %{x|%d.%m.%Y}<br>Equity: $%{y:,.2f}<extra></extra>",
        )
    )

    if "close" in df.columns and df["close"].iloc[0] > 0:
        bh_coins = initial_capital / df["close"].iloc[0]
        bh_equity = bh_coins * df["close"]
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=bh_equity,
                mode="lines",
                name="Buy & Hold",
                line=dict(color="deepskyblue", width=2, dash="dash"),
                hovertemplate="Date: %{x|%d.%m.%Y}<br>B&H: $%{y:,.2f}<extra></extra>",
            )
        )

    fig.add_hline(y=initial_capital, line_dash="dash", line_color="gray", annotation_text="Initial Capital")

    _set_x_range(fig, x_range_min, x_range_max, padding_days)
    if x_range_min is None or x_range_max is None:
        _pad(fig, df["date"], padding_days)

    fig.update_layout(
        title="Equity Curve: Strategy vs Buy & Hold",
        yaxis_title="Equity (USD)",
        template=DEFAULT_TEMPLATE,
        height=520,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig