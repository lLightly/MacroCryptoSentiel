# README.md (новый: добавьте этот файл в корень проекта)
# MacroCryptoSentinel

Это дашборд для мониторинга макро-индикаторов криптовалют (BTC и ETH) с использованием VIX и COT отчетов.

## Установка
1. Клонируйте репозиторий.
2. Установите зависимости: `pip install -r requirements.txt`
3. Запустите: `streamlit run app.py`

## Функции
- **BITCOIN Dashboard**: Графики цены BTC, VIX отклонений, COT индексов, net positions, open interest.
- **BTC COT Details**: Детальные COT графики для BTC.
- **ETHUSDT Dashboard**: Аналогично для ETH.
- **ETH COT Details**: Детальные COT графики для ETH.
- Обновление данных: Кнопка для фетча свежих данных.

## Данные
- COT от CFTC (BTC и ETH).
- Цены от Yahoo Finance (BTC-USD, ETH-USD, ^VIX, ^GSPC).
- Хранятся в `data/raw/` и `data/processed/`.

## Структура
- `app.py`: Streamlit дашборд.
- `main.py`: Обновление данных.
- `src/`: Модули для фетча, анализа, утилит.