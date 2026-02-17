# README.md (обновленный: добавьте описание новых фич)
# MacroCryptoSentinel

Это дашборд для мониторинга макро-индикаторов криптовалют (BTC и ETH) с использованием VIX, COT отчетов и макро-контекста.

## Установка
1. Клонируйте репозиторий.
2. Установите зависимости: `pip install -r requirements.txt`
3. Запустите: `streamlit run app.py`

## Функции
- **BITCOIN Dashboard / ETHUSDT Dashboard**: Графики цены, VIX отклонений, COT индексов, net positions, open interest, Z-Score.
- **BTC COT Details / ETH COT Details**: Детальные COT графики включая Z-Score.
- **Macro Context**: Графики Risk-On/Risk-Off, Liquidity Vacuum, Rolling Correlation.
- **Conclusion**: Алгоритмический Scorecard с баллами и вердиктом (Strong Buy/Neutral/Sell).
- Обновление данных: Кнопка для фетча свежих данных.

## Данные
- COT от CFTC (BTC и ETH).
- Цены от Yahoo Finance (BTC-USD, ETH-USD, ^VIX, ^GSPC, ^IXIC, DX-Y.NYB, ^TNX).
- Хранятся в `data/raw/` и `data/processed/`.

## Структура
- `app.py`: Streamlit дашборд.
- `main.py`: Обновление данных.
- `src/`: Модули для фетча, анализа, утилит.