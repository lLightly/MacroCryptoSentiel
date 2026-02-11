# MacroCryptoSentinel/src/analytics/indicators.py
# (Оставляем как есть — для COT, когда вернёшься к нему)
def cot_index(series, window=26):
    lo = series.rolling(window).min()
    hi = series.rolling(window).max()
    return 100 * (series - lo) / (hi - lo)

def build_indicators(df):
    df["COT_Index_Comm_26w"] = cot_index(df["Comm_Net"], 26).round(2)
    df["COT_Index_Large_26w"] = cot_index(df["Large_Specs_Net"], 26).round(2)
    df["COT_Index_Large_Inverted_26w"] = (100 - df["COT_Index_Large_26w"]).round(2)
    return df