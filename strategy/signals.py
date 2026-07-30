# signals.py
# 負責計算 Z-score 並生成 Bollinger Bands 進出場信號
# 進場條件：|Z-score| > entryZscore
# 出場條件：|Z-score| < exitZscore

import pandas as pd


def calc_zscore(spread: pd.Series,
                lookback: int) -> pd.Series:
    """
    計算 spread 的移動 Z-score。
    公式：Z = (spread - 移動平均) / 移動標準差

    參數：
        spread   : spread 的時間序列
        lookback : 計算移動平均與標準差的視窗長度（建議設為半衰期）
                   例如 lookback = 23

    回傳：
        zscore : 每日的 Z-score 序列
                 例如：
                 Date
                 2010-02-05    1.23
                 2010-02-08   -0.45
                 2010-02-09    2.11
                 dtype: float64
    """
    rolling_mean = spread.rolling(window=lookback).mean()
    rolling_std = spread.rolling(window=lookback).std()
    zscore = (spread - rolling_mean) / rolling_std
    return zscore


def generate_signals(zscore: pd.Series,
                     entry_zscore: float = 2.0,
                     exit_zscore: float = 0.0) -> pd.DataFrame:
    """
    根據 Z-score 生成 Bollinger Bands 進出場信號。

    信號邏輯：
        Z > +entry_zscore  → spread 偏高 → 做空 Y，做多 X（signal = -1）
        Z < -entry_zscore  → spread 偏低 → 做多 Y，做空 X（signal = +1）
        |Z| < exit_zscore  → 回歸均值 → 平倉（signal = 0）
        其他時間           → 維持前一個倉位

    參數：
        zscore       : Z-score 序列
        entry_zscore : 進場閾值，預設 2.0
        exit_zscore  : 出場閾值，預設 0.0

    回傳：
        signals : 包含 zscore 與 signal 的 DataFrame
                  例如：
                              zscore  signal
                  Date
                  2010-02-05    1.23     NaN   ← 尚未達到進場條件，維持前一狀態
                  2010-02-08   -0.45     0.0   ← |Z| < exit_zscore，平倉
                  2010-02-09    2.11    -1.0   ← Z > entry_zscore，做空 spread
                  2010-02-10   -2.34     1.0   ← Z < -entry_zscore，做多 spread
    """
    signals = pd.DataFrame(index=zscore.index)
    signals["zscore"] = zscore
    signals["signal"] = 0.0

    # 進場信號
    signals.loc[zscore > entry_zscore, "signal"] = -1.0   # 做空 spread
    signals.loc[zscore < -entry_zscore, "signal"] = 1.0   # 做多 spread

    # 出場信號
    signals.loc[zscore.abs() < exit_zscore, "signal"] = 0.0  # 平倉

    # 將沒有信號的時間點設為 NaN，再用前值填充（維持倉位）
    signals.loc[
        (zscore.abs() <= entry_zscore) &
        (zscore.abs() >= exit_zscore),
        "signal"
    ] = None

    signals["signal"] = signals["signal"].ffill().fillna(0.0)

    return signals


# ============================================================
# 直接執行此檔案時的測試用範例
# ============================================================
if __name__ == "__main__":
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
    from data.loader import load_multiple
    from strategy.cointegration import cadf_test
    from strategy.hedge_ratio import calc_rolling_hedge_ratio, calc_spread

    data = load_multiple(["GLD", "GDX"])
    gld = data["GLD"]["Close"]
    gdx = data["GDX"]["Close"]

    # 取得半衰期
    coint_result = cadf_test(gld, gdx)
    lookback = int(coint_result["half_life"])

    # 計算 spread
    hedge_ratios = calc_rolling_hedge_ratio(gld, gdx, lookback)
    spread = calc_spread(gld, gdx, hedge_ratios)

    # 計算 Z-score 與信號
    zscore = calc_zscore(spread, lookback)
    signals = generate_signals(zscore, entry_zscore=2.0, exit_zscore=0.0)

    print(f"\n信號（最後十筆）：")
    print(signals.tail(10))