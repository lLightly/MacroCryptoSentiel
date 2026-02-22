# src/analytics/backtest.py
from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

import backtrader as bt
import pandas as pd
import pyfolio as pf

from src.analytics.signal_generator import generate_signals
from src.config.settings import get_settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('app.log', encoding='utf-8')
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)


@dataclass
class BacktestResult:
    equity_curve: pd.DataFrame
    metrics: Dict[str, float]
    trade_log_path: Optional[str]


class MacroStrategy(bt.Strategy):
    params = (
        ("asset", "BTC"),
        ("dfs", None),
        ("signals", None),
        ("fee", 0.001),
    )

    def __init__(self):
        s = get_settings()
        self._trailing_stop = float(s.backtest.trailing_stop_pct)

        signals_df: Optional[pd.DataFrame] = self.p.signals
        if signals_df is None or signals_df.empty:
            signals_df = generate_signals(self.p.dfs, self.p.asset)

        if signals_df is None or signals_df.empty:
            self.signals = pd.DataFrame(columns=["total_score", "signal", "confidence"]).set_index(pd.DatetimeIndex([]))
        else:
            tmp = signals_df.copy()
            tmp["date"] = pd.to_datetime(tmp["date"]).dt.normalize()
            self.signals = tmp.set_index("date")

        self.high_watermark: Optional[float] = None
        self.dates: list[pd.Timestamp] = []
        self.equity_list: list[float] = []

        Path(s.backtest.trade_log_dir).mkdir(exist_ok=True)
        self._log_path = Path(s.backtest.trade_log_dir) / f"trades_{self.p.asset.lower()}.csv"
        self._log_file = open(self._log_path, "w", newline="", encoding="utf-8")
        self._log_writer = csv.writer(self._log_file)
        self._log_writer.writerow(
            ["date", "price", "total_score", "dyn_min_score", "confidence", "signal_flag", "position_size", "equity", "event"]
        )

    def next(self):
        ts = pd.Timestamp(self.datetime.datetime(0)).normalize()
        price = float(self.data.close[0])
        equity = float(self.broker.getvalue())
        pos_size = float(self.position.size)

        event = "HOLD"
        total = 0.0
        conf = 0.0
        sig_flag = 0
        dyn_thr = None

        if pos_size > 0:
            if self.high_watermark is None:
                self.high_watermark = price
            self.high_watermark = max(self.high_watermark, price)
            if (price / self.high_watermark - 1) <= -self._trailing_stop:
                self.close()
                event = "TRAIL_STOP"

        if ts in self.signals.index:
            row = self.signals.loc[ts]
            total = float(row.get("total_score", 0.0))
            conf = float(row.get("confidence", 0.0))
            sig_flag = int(row.get("signal", 0))
            dyn_thr = float(row.get("dyn_min_score")) if "dyn_min_score" in row else None

            if sig_flag == 1 and pos_size <= 0:
                cash = float(self.broker.getcash())
                alloc = max(0.0, min(1.0, conf))
                size = (cash * alloc) / price * (1 - self.p.fee)
                if size > 0:
                    self.buy(size=size)
                    self.high_watermark = price
                    event = "BUY"

            elif sig_flag == 0 and pos_size > 0 and event == "HOLD":
                self.close()
                event = "EXIT"

        self.dates.append(ts)
        self.equity_list.append(equity)

        self._log_writer.writerow(
            [
                ts.date().isoformat(),
                f"{price:.2f}",
                f"{total:.3f}",
                "" if dyn_thr is None else f"{dyn_thr:.3f}",
                f"{conf:.3f}",
                sig_flag,
                f"{pos_size:.6f}",
                f"{equity:.2f}",
                event,
            ]
        )

    def stop(self):
        try:
            self._log_file.close()
        except Exception:
            pass


def _slice_price(df: pd.DataFrame, start_date=None, end_date=None) -> pd.DataFrame:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    df = df.sort_values("date").reset_index(drop=True)
    if start_date is not None:
        df = df[df["date"] >= pd.to_datetime(start_date)]
    if end_date is not None:
        df = df[df["date"] <= pd.to_datetime(end_date)]
    return df.reset_index(drop=True)


def run_backtest(
    dfs: Dict[str, pd.DataFrame],
    asset: str,
    initial_capital: float,
    fee_pct: float,
    start_date=None,
    end_date=None,
) -> BacktestResult:
    logger.debug(f"Running backtest for {asset}, capital={initial_capital}, fee={fee_pct}, start={start_date}, end={end_date}")

    asset_key = asset.lower()

    if asset_key not in dfs or dfs[asset_key] is None or dfs[asset_key].empty:
        return BacktestResult(pd.DataFrame(), {"total_return": 0.0, "sharpe": 0.0, "sortino": 0.0, "max_dd": 0.0, "calmar": 0.0}, None)

    df_price = _slice_price(dfs[asset_key], start_date=start_date, end_date=end_date)
    if df_price.empty:
        return BacktestResult(pd.DataFrame(), {"total_return": 0.0, "sharpe": 0.0, "sortino": 0.0, "max_dd": 0.0, "calmar": 0.0}, None)

    signals = generate_signals(dfs, asset=asset)
    if start_date is not None or end_date is not None:
        tmp = signals.copy()
        tmp["date"] = pd.to_datetime(tmp["date"]).dt.normalize()
        if start_date is not None:
            tmp = tmp[tmp["date"] >= pd.to_datetime(start_date)]
        if end_date is not None:
            tmp = tmp[tmp["date"] <= pd.to_datetime(end_date)]
        signals = tmp.reset_index(drop=True)

    cerebro = bt.Cerebro(stdstats=False)
    data = bt.feeds.PandasData(dataname=df_price.set_index("date"))
    cerebro.adddata(data)
    cerebro.addstrategy(MacroStrategy, dfs=dfs, asset=asset, fee=fee_pct, signals=signals)
    cerebro.broker.setcash(initial_capital)
    cerebro.broker.setcommission(commission=fee_pct)

    strats = cerebro.run()
    strat: MacroStrategy = strats[0]

    equity_curve = pd.DataFrame({"date": strat.dates, "close": df_price["close"].values[: len(strat.dates)], "Equity": strat.equity_list})
    equity_curve["date"] = pd.to_datetime(equity_curve["date"]).dt.normalize()
    logger.debug(f"Equity curve: {equity_curve.tail().to_dict()}")

    if len(equity_curve) < 2:
        metrics = {"total_return": 0.0, "sharpe": 0.0, "sortino": 0.0, "max_dd": 0.0, "calmar": 0.0}
        return BacktestResult(equity_curve, metrics, str(strat._log_path))

    returns = equity_curve.set_index("date")["Equity"].pct_change().dropna()
    if returns.empty or returns.std() == 0 or returns.isna().any():
        total_return = float((equity_curve["Equity"].iloc[-1] - initial_capital) / initial_capital)
        metrics = {"total_return": total_return, "sharpe": 0.0, "sortino": 0.0, "max_dd": 0.0, "calmar": 0.0}
        return BacktestResult(equity_curve, metrics, str(strat._log_path))

    perf_stats = pf.timeseries.perf_stats(returns)
    metrics = {
        "total_return": float(perf_stats.get("Total return", 0.0)),
        "sharpe": float(perf_stats.get("Sharpe ratio", 0.0)),
        "sortino": float(perf_stats.get("Sortino ratio", 0.0)),
        "max_dd": float(perf_stats.get("Max drawdown", 0.0)),
        "calmar": float(perf_stats.get("Calmar ratio", 0.0)),
    }
    logger.debug(f"Backtest metrics: {metrics}")
    return BacktestResult(equity_curve, metrics, str(strat._log_path))