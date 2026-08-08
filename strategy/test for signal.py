# signals.py
# 負責計算 Z-score 並生成 Bollinger Bands 進出場信號
# 進場條件：|Z-score| > entryZscore
# 出場條件：|Z-score| < exitZscore
# 設計前提：spread 來自固定 hedge ratio 的 OLS 殘差，長期均值為 0
import pandas as pd



def calc_zscore(spread: pd.Series,
                lookback: int) -> pd.Series:
    """
    計算 spread 的移動 Z-score。
    公式：Z = spread / 移動標準差

    設計說明：
        因為 spread 來自 OLS 殘差，長期均值理論上為 0，
        所以分子直接用 spread 本身，不需要減去移動平均。
        分母仍用 rolling std，以反映 out-of-sample 期間的波動變化。

    參數：
        spread   : spread 的時間序列（來自 cadf_test 的 residuals）
        lookback : 計算移動標準差的視窗長度（建議設為半衰期）
                   例如 lookback = 14，代表用過去 14 天計算標準差

    回傳：
        zscore : 每日的 Z-score 序列
                 例如：
                 Date
                 2010-02-05    1.23
                 2010-02-08   -0.45
                 2010-02-09    2.11
                 dtype: float64
                 前 lookback-1 天為 NaN（rolling std 資料不足）
    """
    # 只用 rolling std，不減 rolling mean（OLS 殘差均值為 0）
    rolling_std = spread.rolling(window=lookback).std()
    zscore = spread/rolling_std

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
        其他時間           → 維持前一個倉位（ffill）

    參數：
        zscore       : Z-score 序列（來自 calc_zscore）
        entry_zscore : 進場閾值，預設 2.0
        exit_zscore  : 出場閾值，預設 0.0
                       注意：預設 0.0 代表平倉條件永遠不成立，
                             實際出場靠 Z-score 穿越對面閾值觸發反向信號

    回傳：
        signals : 包含 zscore 與 signal 的 DataFrame
                  例如（entry_zscore=2.0, exit_zscore=0.0）：
                              zscore  signal
                  Date
                  2010-02-05    1.23     0.0   ← 介於閾值之間，ffill 前值（初始為 0）
                  2010-02-08   -0.45     0.0   ← 同上
                  2010-02-09    2.11    -1.0   ← Z > +2.0，做空 spread
                  2010-02-10   -2.34     1.0   ← Z < -2.0，做多 spread
    """
    # 進場信號：spread 偏高做空，偏低做多
    signals = pd.DataFrame(index=zscore.index)
    signals['zscore'] = zscore
    signals['signal'] = 0.0

    signals.loc[zscore > entry_zscore, 'signal'] = -1
    signals.loc[zscore < -entry_zscore, 'signal'] = 1

    # 出場信號：spread 回歸均值，平倉
    signals.loc[zscore.abs() < exit_zscore] = 0
    
    # 介於進出場閾值之間的時間點設為 NaN，再用前值填充（維持倉位）
    signals.loc[(zscore.abs() <= entry_zscore) &
                (zscore.abs() >= -entry_zscore), 
                'signal'] = None

    signals['signal'] = signals['signal'].ffill().fillna(0.0)

    return signals

# ============================================================
# 直接執行此檔案時的測試用範例
# ============================================================
if __name__ == "__main__":
    # 載入資料

    # 以全部資料長度 T 為 in-sample，取得固定 hedge ratio 與 residuals
    # 實際使用時，in-sample 應為回測起始日往回推 T 天，out-of-sample 才是回測區間

    # spread 直接取 cadf_test 的 OLS 殘差（均值為 0）

    # 計算 Z-score 與信號