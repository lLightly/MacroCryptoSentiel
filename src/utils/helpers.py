# MacroCryptoSentinel/src/utils/helpers.py
from pathlib import Path
import pandas as pd
import os

def save_csv(df: pd.DataFrame, path: str):
    """
    Универсальная функция сохранения CSV с автоматическим созданием папок.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    print(f"Сохранено: {path}")