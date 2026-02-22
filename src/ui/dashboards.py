from __future__ import annotations
import datetime as dt
import streamlit as st

from src.analytics.signal_generator import generate_signals
from src.analytics.trend_validation import run_trend_validation
from src.config.settings import get_settings
from src.services.data_loader import filter_df
from src.ui import components


def _asset_dashboard(asset: str, dfs):
    df_price, df_vix, df_cot, *_ = dfs
    asset_lc = asset.lower()

    if not df_price.empty:
        st.plotly_chart(
            components.candlestick(df_price, f"{asset} Price"),
            width="stretch",
            key=f"{asset_lc}_price"
        )

    if not df_vix.empty:
        st.plotly_chart(
            components.vix_deviation(df_vix),
            width="stretch",
            key=f"{asset_lc}_vix_dev"
        )

    if not df_cot.empty:
        st.plotly_chart(
            components.cot_index(df_cot, asset=asset),
            width="stretch",
            key=f"{asset_lc}_cot_index"
        )
        st.plotly_chart(
            components.net_positions(df_cot),
            width="stretch",
            key=f"{asset_lc}_net_pos"
        )
        st.plotly_chart(
            components.z_score(df_cot),
            width="stretch",
            key=f"{asset_lc}_z_score"
        )
        st.plotly_chart(
            components.open_interest(df_cot, asset=asset),
            width="stretch",
            key=f"{asset_lc}_oi"
        )


btc_dashboard = lambda dfs: _asset_dashboard("BTC", dfs)
eth_dashboard = lambda dfs: _asset_dashboard("ETH", dfs)


def macro_dashboard(dfs):
    df_btc, _df_vix, _cot, df_spx, df_nasdaq, df_dxy, df_us10y = dfs
    all_dfs = [df_btc, df_spx, df_nasdaq, df_dxy, df_us10y]

    overall_min = min(
        [df["date"].min() for df in all_dfs if not df.empty and "date" in df.columns],
        default=None
    )
    overall_max = max(
        [df["date"].max() for df in all_dfs if not df.empty and "date" in df.columns],
        default=None
    )

    if not df_btc.empty and not df_spx.empty and not df_nasdaq.empty:
        st.plotly_chart(
            components.normalised_performance(
                {"BTC %": df_btc, "S&P 500 %": df_spx, "Nasdaq %": df_nasdaq},
                x_range_min=overall_min,
                x_range_max=overall_max,
            ),
            width="stretch",
            key="macro_risk",
        )

    if not df_btc.empty and not df_dxy.empty and not df_us10y.empty:
        st.plotly_chart(
            components.liquidity_vacuum(df_btc, df_dxy, df_us10y, x_range_min=overall_min, x_range_max=overall_max),
            width="stretch",
            key="macro_liq",
        )

    if not df_btc.empty and not df_spx.empty:
        st.plotly_chart(
            components.rolling_correlation(
                df_btc, df_spx, window=60, min_periods=20,
                x_range_min=overall_min, x_range_max=overall_max
            ),
            width="stretch",
            key="macro_corr",
        )


def trend_validation_dashboard(dfs, btc_min: dt.date, eth_min: dt.date, global_max: dt.date):
    s = get_settings()

    st.header("🧭 Trend Validation (Global Compass)")
    st.caption(
        "Ежемесячная оценка режима (Bullish/Neutral/Bearish). "
        "Модель портфеля: держим актив только в Bullish Trend, иначе кеш. "
        "Без комиссий/трейлинг-стопов."
    )

    col1, col2 = st.columns([2, 1])
    with col1:
        asset = st.selectbox("Актив", ["BTC", "ETH"], index=0, key="trend_asset")

    with col2:
        initial_capital = st.number_input(
            "Стартовый капитал ($)",
            min_value=1.0,
            value=float(s.backtest.initial_capital_default),
            step=10.0,
            key="trend_capital"
        )

    min_d = btc_min if asset == "BTC" else eth_min
    default_s = max(min_d, dt.date(global_max.year - s.ui.default_years, 1, 1))

    start_date, end_date = st.slider(
        f"Диапазон дат для {asset}",
        min_value=min_d,
        max_value=global_max,
        value=(default_s, global_max),
        format="DD.MM.YYYY",
        key="trend_slider",
    )

    data_sig = (asset, str(start_date), str(end_date), float(initial_capital))

    def _cached_validation(_sig):
        _asset, _s_date_str, _e_date_str, _cap = _sig
        _s_date = dt.date.fromisoformat(_s_date_str)
        _e_date = dt.date.fromisoformat(_e_date_str)
        return run_trend_validation(dfs, _asset, initial_capital=_cap, start_date=_s_date, end_date=_e_date)

    with st.spinner("Считаю Trend Validation..."):
        result = _cached_validation(data_sig)

    if result.equity_curve.empty:
        st.warning("Недостаточно данных в выбранном периоде.")
        return

    st.plotly_chart(
        components.equity_curve_chart(result.equity_curve, initial_capital=initial_capital, signals=result.signals),
        width="stretch",
        key=f"equity_curve_compass_{asset}",
    )

    m = result.metrics
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Compass доходность", f"{m.get('total_return', 0.0) * 100:+.2f}%")
    c2.metric("B&H доходность", f"{m.get('bh_total_return', 0.0) * 100:+.2f}%")
    c3.metric("Trend accuracy", f"{m.get('trend_accuracy', 0.0) * 100:.1f}%")
    c4.metric("Coverage", f"{m.get('trend_coverage', 0.0) * 100:.1f}%")
    c5.metric("DD reduction", f"{m.get('dd_reduction', 0.0) * 100:+.2f}pp")

    with st.expander("Подробнее: риск/качество режима"):
        st.write(
            {
                "Sharpe (Compass)": round(float(m.get("sharpe", 0.0)), 2),
                "Sharpe (B&H)": round(float(m.get("bh_sharpe", 0.0)), 2),
                "Max DD (Compass)": f"{float(m.get('max_dd', 0.0)) * 100:.2f}%",
                "Max DD (B&H)": f"{float(m.get('bh_max_dd', 0.0)) * 100:.2f}%",
                "Horizon months": int(m.get("horizon_months", 3)),
            }
        )

    if result.confusion:
        st.write(
            {
                "Bullish correct": result.confusion.get("bull_correct", 0),
                "Bullish wrong": result.confusion.get("bull_wrong", 0),
                "Bearish correct": result.confusion.get("bear_correct", 0),
                "Bearish wrong": result.confusion.get("bear_wrong", 0),
                "Evaluated": result.confusion.get("evaluated", 0),
            }
        )

    df_signals_all = generate_signals(dfs, asset)
    df_signals = filter_df(df_signals_all, start_date, end_date)

    if st.checkbox("Показать таблицу режимов (сигналов)"):
        cols = [c for c in ["date", "verdict", "total_score", "position", "confidence"] if c in df_signals.columns]
        st.dataframe(
            df_signals.sort_values("date", ascending=False)
            .head(80)[cols]
            .style.format({"total_score": "{:+.2f}", "confidence": "{:.2f}"}),
            width="stretch",
        )

    if st.checkbox("Показать daily equity log"):
        st.dataframe(
            result.equity_curve.sort_values("date", ascending=False).head(120).style.format({"Equity": "{:,.2f}"}),
            width="stretch",
        )


def backtesting_dashboard(dfs, btc_min: dt.date, eth_min: dt.date, global_max: dt.date):
    """
    If compass_mode=true: show Trend Validation.
    If compass_mode=false: show legacy trading backtest UI (kept for backward compatibility).
    """
    s = get_settings()

    if s.compass_mode:
        return trend_validation_dashboard(dfs, btc_min, eth_min, global_max)

    # Legacy UI (original)
    from src.analytics.backtest import run_backtest

    st.header("🔍 Backtesting сигналов (Long-only)")

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        asset = st.selectbox("Актив", ["BTC", "ETH"], index=0)

    with col2:
        initial_capital = st.number_input(
            "Стартовый капитал ($)",
            min_value=1.0,
            value=float(s.backtest.initial_capital_default),
            step=10.0
        )

    with col3:
        fee_pct = st.number_input(
            "Комиссия (%)",
            min_value=0.0,
            max_value=1.0,
            value=float(s.backtest.fee_default) * 100,
            step=0.05
        ) / 100

    min_d = btc_min if asset == "BTC" else eth_min
    default_s = max(min_d, dt.date(global_max.year - s.ui.default_years, 1, 1))

    start_date, end_date = st.slider(
        f"Диапазон дат для {asset}",
        min_value=min_d,
        max_value=global_max,
        value=(default_s, global_max),
        format="DD.MM.YYYY",
        key=f"backtest_{asset.lower()}_slider",
    )

    data_sig = (asset, start_date, end_date, float(initial_capital), float(fee_pct), global_max)

    def _cached_backtest(_sig):
        _asset, _s_date, _e_date, _cap, _fee, _gmax = _sig
        return run_backtest(dfs, _asset, initial_capital=_cap, fee_pct=_fee, start_date=_s_date, end_date=_e_date)

    with st.spinner("Выполняю бэктест..."):
        result = _cached_backtest(data_sig)

    if result.equity_curve.empty:
        st.warning("Недостаточно данных в выбранном периоде.")
        return

    st.plotly_chart(
        components.equity_curve_chart(result.equity_curve, initial_capital=initial_capital),
        width="stretch",
        key=f"equity_curve_{asset}"
    )

    m = result.metrics
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Итоговая доходность", f"{m.get('total_return', 0) * 100:+.2f}%")
    c2.metric("Sharpe", f"{m.get('sharpe', 0):.2f}")
    c3.metric("Sortino", f"{m.get('sortino', 0):.2f}")
    c4.metric("Max DD", f"{m.get('max_dd', 0) * 100:+.2f}%")
    c5.metric("Calmar", f"{m.get('calmar', 0):.2f}")

    df_signals_all = generate_signals(dfs, asset)
    df_signals = filter_df(df_signals_all, start_date, end_date)

    if st.checkbox("Показать таблицу сигналов"):
        st.dataframe(
            df_signals.sort_values("date", ascending=False)
            .head(50)[["date", "verdict", "total_score", "dyn_min_score", "signal", "confidence"]]
            .style.format({"total_score": "{:+.2f}", "dyn_min_score": "{:.2f}", "confidence": "{:.2f}"}),
            width="stretch",
        )

    if st.checkbox("Показать daily equity log"):
        st.dataframe(
            result.equity_curve.sort_values("date", ascending=False).head(100).style.format({"Equity": "{:,.2f}"}),
            width="stretch",
        )

    if result.trade_log_path:
        st.caption(f"Trade log: {result.trade_log_path}")