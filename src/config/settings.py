from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import yaml


CONFIG_PATH = Path("config.yaml")

def _as_date(v: Any, default: dt.date) -> dt.date:
    if v is None:
        return default
    if isinstance(v, dt.date):
        return v
    try:
        return dt.date.fromisoformat(str(v))
    except Exception:
        return default

def _get(d: Dict[str, Any], path: str, default: Any) -> Any:
    cur: Any = d
    for k in path.split("."):
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


@dataclass(frozen=True)
class UISettings:
    plot_padding_days: int
    sigma_levels: List[int]
    default_years: int
    slider_step_days: int


@dataclass(frozen=True)
class AssetSettings:
    btc_price_start: str
    eth_price_start: str
    btc_cot_min_date: dt.date
    eth_cot_min_date: dt.date
    macro_min_date: dt.date
    conclusion_min_date: dt.date


@dataclass(frozen=True)
class COTSettings:
    weeks_in_year: int
    default_years: int

    @property
    def default_weeks(self) -> int:
        return int(self.weeks_in_year * self.default_years)


@dataclass(frozen=True)
class SignalsSettings:
    step_days: int
    start_fraction: float
    min_start_bars: int
    min_price_rows: int
    min_feature_rows: int
    dyn_min_score_base: float
    dyn_min_score_vix_scale: float
    dyn_min_score_vix_divisor: float


@dataclass(frozen=True)
class MLSettings:
    n_splits: int
    n_estimators: int
    random_state: int
    n_jobs: int
    target_horizon_days: int
    min_train_rows: int
    pred_to_score_divisor: float


@dataclass(frozen=True)
class ScoringSettings:
    verdict_strong_buy: float
    verdict_buy: float
    verdict_neutral_band: float
    verdict_strong_sell: float

    trend_filter_enabled: bool
    trend_penalty_multiplier: float

    vix_enabled: bool
    vix_strong_risk_off_score: float
    vix_risk_off_score: float
    vix_strong_risk_on_score: float
    vix_risk_on_score: float

    momentum_enabled: bool
    momentum_strong_move_pct: float
    momentum_score: float

    liquidity_enabled: bool
    liquidity_dxy_strong_pct: float
    liquidity_us10y_spike_pct: float
    liquidity_score_each: float

    correlation_enabled: bool
    corr_threshold: float
    corr_base: float
    corr_slope: float

    cot_enabled: bool

    ml_enabled: bool


@dataclass(frozen=True)
class BacktestSettings:
    initial_capital_default: float
    fee_default: float
    trailing_stop_pct: float
    trade_log_dir: str


@dataclass(frozen=True)
class Settings:
    raw: Dict[str, Any]
    data_dir: str
    files: Dict[str, str]

    ui: UISettings
    assets: AssetSettings
    cot: COTSettings
    signals: SignalsSettings
    ml: MLSettings
    scoring: ScoringSettings
    backtest: BacktestSettings


_SETTINGS: Settings | None = None


def get_settings() -> Settings:
    global _SETTINGS
    if _SETTINGS is not None:
        return _SETTINGS

    raw = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    files = dict(raw.get("files", {}))

    ui_raw = raw.get("ui", {})
    ui = UISettings(
        plot_padding_days=int(ui_raw.get("plot_padding_days", raw.get("plot_padding_days", 7))),
        sigma_levels=list(ui_raw.get("sigma_levels", raw.get("sigma_levels", [1, 2]))),
        default_years=int(ui_raw.get("default_years", 3)),
        slider_step_days=int(ui_raw.get("slider_step_days", 7)),
    )

    assets_raw = raw.get("assets", {})
    btc_raw = assets_raw.get("btc", {})
    eth_raw = assets_raw.get("eth", {})
    assets = AssetSettings(
        btc_price_start=str(btc_raw.get("price_start", "2014-09-17")),
        eth_price_start=str(eth_raw.get("price_start", "2015-08-07")),
        btc_cot_min_date=_as_date(btc_raw.get("cot_min_date"), dt.date(2020, 5, 12)),
        eth_cot_min_date=_as_date(eth_raw.get("cot_min_date"), dt.date(2023, 3, 28)),
        macro_min_date=_as_date(assets_raw.get("macro_min_date"), dt.date(2014, 9, 17)),
        conclusion_min_date=_as_date(assets_raw.get("conclusion_min_date"), dt.date(2020, 5, 12)),
    )

    cot_raw = raw.get("cot", {})
    cot = COTSettings(
        weeks_in_year=int(cot_raw.get("weeks_in_year", 52)),
        default_years=int(cot_raw.get("default_years", 3)),
    )

    sig_raw = raw.get("signals", {})
    dyn_raw = sig_raw.get("dyn_min_score", {})
    signals = SignalsSettings(
        step_days=int(sig_raw.get("step_days", 7)),
        start_fraction=float(sig_raw.get("start_fraction", 0.5)),
        min_start_bars=int(sig_raw.get("min_start_bars", 200)),
        min_price_rows=int(sig_raw.get("min_price_rows", 300)),
        min_feature_rows=int(sig_raw.get("min_feature_rows", 50)),
        dyn_min_score_base=float(dyn_raw.get("base", 1.5)),
        dyn_min_score_vix_scale=float(dyn_raw.get("vix_scale", 0.3)),
        dyn_min_score_vix_divisor=float(dyn_raw.get("vix_divisor", 50.0)),
    )

    ml_raw = raw.get("ml", {})
    ml = MLSettings(
        n_splits=int(ml_raw.get("n_splits", 5)),
        n_estimators=int(ml_raw.get("n_estimators", 120)),
        random_state=int(ml_raw.get("random_state", 42)),
        n_jobs=int(ml_raw.get("n_jobs", -1)),
        target_horizon_days=int(ml_raw.get("target_horizon_days", 30)),
        min_train_rows=int(ml_raw.get("min_train_rows", 50)),
        pred_to_score_divisor=float(ml_raw.get("pred_to_score_divisor", 5.0)),
    )

    sc_raw = raw.get("scoring", {})
    vt = sc_raw.get("verdict_thresholds", {})
    tf = sc_raw.get("trend_filter", {})
    vix = sc_raw.get("vix", {})
    mom = sc_raw.get("momentum", {})
    liq = sc_raw.get("liquidity", {})
    corr = sc_raw.get("correlation", {})

    scoring = ScoringSettings(
        verdict_strong_buy=float(vt.get("strong_buy", 4.0)),
        verdict_buy=float(vt.get("buy", 1.5)),
        verdict_neutral_band=float(vt.get("neutral_band", 1.0)),
        verdict_strong_sell=float(vt.get("strong_sell", -4.0)),
        trend_filter_enabled=bool(tf.get("enabled", True)),
        trend_penalty_multiplier=float(tf.get("penalty_multiplier", 0.5)),
        vix_enabled=bool(_get(sc_raw, "vix.enabled", True)),
        vix_strong_risk_off_score=float(_get(vix, "strong_risk_off.score", -3.0)),
        vix_risk_off_score=float(_get(vix, "risk_off.score", -1.8)),
        vix_strong_risk_on_score=float(_get(vix, "strong_risk_on.score", 3.0)),
        vix_risk_on_score=float(_get(vix, "risk_on.score", 1.8)),
        momentum_enabled=bool(_get(sc_raw, "momentum.enabled", True)),
        momentum_strong_move_pct=float(mom.get("strong_move_pct", 18)),
        momentum_score=float(mom.get("score", 0.9)),
        liquidity_enabled=bool(_get(sc_raw, "liquidity.enabled", True)),
        liquidity_dxy_strong_pct=float(liq.get("dxy_strong_pct", 6)),
        liquidity_us10y_spike_pct=float(liq.get("us10y_spike_pct", 12)),
        liquidity_score_each=float(liq.get("score_each", 0.8)),
        correlation_enabled=bool(_get(sc_raw, "correlation.enabled", True)),
        corr_threshold=float(corr.get("threshold", 0.82)),
        corr_base=float(corr.get("base", 0.7)),
        corr_slope=float(corr.get("slope", -0.7)),
        cot_enabled=bool(_get(sc_raw, "cot.enabled", True)),
        ml_enabled=bool(_get(sc_raw, "ml.enabled", True)),
    )

    bt_raw = raw.get("backtest", {})
    backtest = BacktestSettings(
        initial_capital_default=float(bt_raw.get("initial_capital_default", 100.0)),
        fee_default=float(bt_raw.get("fee_default", 0.001)),
        trailing_stop_pct=float(bt_raw.get("trailing_stop_pct", 0.15)),
        trade_log_dir=str(bt_raw.get("trade_log_dir", "logs")),
    )

    _SETTINGS = Settings(
        raw=raw,
        data_dir=str(raw.get("data_dir", "data/processed")),
        files=files,
        ui=ui,
        assets=assets,
        cot=cot,
        signals=signals,
        ml=ml,
        scoring=scoring,
        backtest=backtest,
    )
    return _SETTINGS