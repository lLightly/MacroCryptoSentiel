# app.py
from __future__ import annotations

import datetime as dt
import pandas as pd
import streamlit as st
import logging

from main import main as update_data
from src.analytics.signal_generator import generate_conclusion
from src.config.settings import get_settings
from src.services.data_loader import all_data_loaded, filter_df, load_dataset
from src.ui.dashboards import backtesting_dashboard, btc_dashboard, eth_dashboard, macro_dashboard

logging.basicConfig(level=logging.DEBUG, filename='app.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s', encoding='utf-8')

st.set_page_config(page_title="MacroCryptoSentinel — Global Compass", layout="wide")
st.title("🧭 MacroCryptoSentinel — Global Compass")

settings = get_settings()
DATASETS: list[str] = list(settings.files.keys())

if st.button("Обновить все данные"):
    with st.spinner("Скачиваю и обрабатываю данные…"):
        update_data()
        st.cache_data.clear()
    st.success("Данные обновлены!")


@st.cache_data(show_spinner=False)
def _cached_ds(name: str):
    return load_dataset(name)


dfs: dict[str, pd.DataFrame | None] = {name: _cached_ds(name) for name in DATASETS}

if not all_data_loaded(dfs):
    st.error("Не все данные загружены — нажмите кнопку обновления.")
    st.stop()


def _cot_default_start(cot_df: pd.DataFrame | None, asset_min_date: dt.date, weeks_back: int) -> dt.date:
    if cot_df is None or cot_df.empty or "date" not in cot_df.columns:
        return asset_min_date

    cot_dates = sorted(pd.to_datetime(cot_df["date"]).dt.date.unique())

    if not cot_dates:
        return asset_min_date

    if len(cot_dates) <= weeks_back + 5:
        return max(asset_min_date, cot_dates[0])

    return max(asset_min_date, cot_dates[-weeks_back - 1])


all_dates = pd.concat([df["date"] for df in dfs.values() if df is not None and "date" in df.columns])
global_max_date: dt.date = pd.to_datetime(all_dates.max()).date()

btc_cot_df = dfs.get("btc_cot")
eth_cot_df = dfs.get("eth_cot")

btc_min_date = max(
    settings.assets.btc_cot_min_date,
    pd.to_datetime(btc_cot_df["date"]).min().date()
    if btc_cot_df is not None and not btc_cot_df.empty
    else settings.assets.btc_cot_min_date,
)

eth_min_date = max(
    settings.assets.eth_cot_min_date,
    pd.to_datetime(eth_cot_df["date"]).min().date()
    if eth_cot_df is not None and not eth_cot_df.empty
    else settings.assets.eth_cot_min_date,
)

weeks_back = settings.cot.default_weeks

default_btc_start = _cot_default_start(btc_cot_df, btc_min_date, weeks_back)
default_eth_start = _cot_default_start(eth_cot_df, eth_min_date, weeks_back)

macro_min_date = settings.assets.macro_min_date
default_macro_start = max(macro_min_date, dt.date(global_max_date.year - settings.ui.default_years, 1, 1))

conclusion_min_date = settings.assets.conclusion_min_date


def _filtered(asset: str, start: dt.date, end: dt.date):
    price_key = asset.lower()
    cot_key = f"{price_key}_cot"
    return (
        filter_df(dfs.get(price_key), start, end),
        filter_df(dfs.get("vix"), start, end),
        filter_df(dfs.get(cot_key), start, end),
        filter_df(dfs.get("spx"), start, end),
        filter_df(dfs.get("nasdaq"), start, end),
        filter_df(dfs.get("dxy"), start, end),
        filter_df(dfs.get("us10y"), start, end),
    )


tab_names = ["BITCOIN Dashboard", "ETH Dashboard", "Macro Context", "Conclusion"]
tab_names.append("Trend Validation" if settings.compass_mode else "Backtesting")

tab_btc, tab_eth, tab_macro, tab_conclusion, tab_last = st.tabs(tab_names)

slider_step = dt.timedelta(days=int(settings.ui.slider_step_days))


with tab_btc:
    start_date, end_date = st.slider(
        "Выберите диапазон дат для BTC",
        min_value=btc_min_date,
        max_value=global_max_date,
        value=(default_btc_start, global_max_date),
        step=slider_step,
        format="DD.MM.YYYY",
        key="btc_slider",
    )
    btc_dashboard(_filtered("BTC", start_date, end_date))


with tab_eth:
    start_date, end_date = st.slider(
        "Выберите диапазон дат для ETH",
        min_value=eth_min_date,
        max_value=global_max_date,
        value=(default_eth_start, global_max_date),
        step=slider_step,
        format="DD.MM.YYYY",
        key="eth_slider",
    )
    eth_dashboard(_filtered("ETH", start_date, end_date))


with tab_macro:
    start_date, end_date = st.slider(
        "Выберите диапазон дат для Macro Context",
        min_value=macro_min_date,
        max_value=global_max_date,
        value=(default_macro_start, global_max_date),
        step=slider_step,
        format="DD.MM.YYYY",
        key="macro_slider",
    )
    macro_dashboard(_filtered("BTC", start_date, end_date))


with tab_conclusion:
    end_date = st.slider(
        "Выберите дату обзора (as of)",
        min_value=conclusion_min_date,
        max_value=global_max_date,
        value=global_max_date,
        step=dt.timedelta(days=1),
        format="DD.MM.YYYY",
        key="concl_slider",
    )

    filtered_dfs = {k: filter_df(v, conclusion_min_date, end_date) for k, v in dfs.items() if v is not None}

    concl = generate_conclusion(filtered_dfs)

    if isinstance(concl, tuple) and len(concl) == 3:
        per_asset, combined_score, combined_verdict = concl
        combined_narrative = ""
    else:
        per_asset, combined_score, combined_verdict, combined_narrative = concl

    st.subheader("🧭 Global Compass — факторы и режим")

    has_data = False

    for asset, item in per_asset.items():
        if len(item) == 4:
            df_table, total, asset_verdict, confidence = item  # legacy
            narrative = ""
        else:
            df_table, total, asset_verdict, confidence, narrative = item  # compass

        if asset_verdict == "No data":
            st.markdown(f"### {asset}: No data in selected range")
            continue

        has_data = True
        st.markdown(f"### {asset}")

        if not df_table.empty:
            st.dataframe(df_table.style.format({"Score": "{:+.2f}"}), width="stretch")

        st.markdown(f"**Итог ({asset}): {total:+.2f} → {asset_verdict}** \n**Confidence:** {confidence:.2f}")

        if narrative:
            st.markdown("**Narrative:**")
            st.markdown(narrative)

    if not has_data:
        st.warning("Нет данных в выбранном диапазоне.")
    else:
        st.markdown(
            f"""
---
### <span style="font-size:24px">Комбинированный обзор рынка</span>
**Суммарный балл**: {combined_score:+.2f}
**Вердикт**: **{combined_verdict}**
""",
            unsafe_allow_html=True,
        )
        if combined_narrative:
            st.markdown("---")
            st.markdown(combined_narrative)


with tab_last:
    backtesting_dashboard(dfs, btc_min_date, eth_min_date, global_max_date)


st.caption("MacroCryptoSentinel — Global Compass: Macro + COT regime interpretation for BTC/ETH.")