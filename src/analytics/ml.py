from __future__ import annotations

import logging

import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import TimeSeriesSplit

from src.config.settings import get_settings

logger = logging.getLogger(__name__)

FEATURES = ["vix_dev", "cot_comm", "cot_large_inv", "mom_30d", "dxy_30d", "us10y_30d", "spx_corr", "above_200ma"]


def train_ml_model(df_features: pd.DataFrame) -> RandomForestRegressor:
    s = get_settings()

    if not s.scoring.ml_enabled or len(df_features) < s.ml.min_train_rows:
        return RandomForestRegressor()

    X = df_features[FEATURES]
    y = df_features["target"]

    model = RandomForestRegressor(
        n_estimators=s.ml.n_estimators,
        random_state=s.ml.random_state,
        n_jobs=s.ml.n_jobs,
    )

    tscv = TimeSeriesSplit(n_splits=s.ml.n_splits)
    for train_idx, _val_idx in tscv.split(X):
        # OPTIMIZED: .take обычно быстрее/дешевле .iloc на массиве индексов, поведение идентично (позиционное).
        model.fit(X.take(train_idx), y.take(train_idx))

    return model