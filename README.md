# MacroCryptoSentinel

Streamlit-дэшборд для BTC/ETH сигналов с макро-контекстом (VIX, SPX, Nasdaq, DXY, US10Y) и Legacy COT.

## Архитектура

- `config.yaml` — единая точка настройки (UI, сигналы, ML, бэктест).
- `main.py` — обновление датасетов (raw/processed).
- `app.py` — Streamlit UI.
- `src/analytics/` — фичи, scoring, генерация сигналов, бэктест.
- `src/data_fetchers/` — загрузка данных (Yahoo + CFTC).
- `src/services/` — загрузка CSV и пайплайн обновления.
- `src/ui/` — Plotly компоненты и страницы.

## Быстрый старт

```bash
pip install -r requirements.txt
streamlit run app.py