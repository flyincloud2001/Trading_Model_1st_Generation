# hedge_ratio.py
# 負責用移動視窗 OLS 動態計算 hedge ratio 與 spread
# 設計原則：look-back 預設為半衰期，但可手動覆蓋
import pandas as pd
from statsmodels.tools import add_constant
from statsmodels.regression.linear_model import OLS


def calc_rolling_hedge_ratio(series_y: pd.Series,
                              series_x: pd.Series,
                              lookback: int) -> pd.Series:
    """
    用移動視窗 OLS 動態計算每日的 hedge ratio。

    參數：
        series_y : 因變數價格序列（例如 GLD 收盤價）
        series_x : 自變數價格序列（例如 GDX 收盤價）
        lookback : 移動視窗長度（天數），建議設為半衰期
                   例如 lookback = 23，代表每次用過去 23 天的資料計算 hedge ratio

    回傳：
        hedge_ratios : 每日的 hedge ratio 序列
                       例如：
                       Date
                       2010-02-05    1.6821
                       2010-02-08    1.6734
                       2010-02-09    1.6799
                       dtype: float64
                       前 lookback-1 天為 NaN（資料不足無法計算）
    """
    # 取出過去 lookback 天的資料
    hedge_ratios = pd.Series(index=series_y.index, dtype=float)

    for i in range(lookback, len(series_y)+1):

        y_window = series_y[i-lookback: i]
        x_window = series_x[i-lookback: i]

        # OLS 回歸
        X = add_constant(x_window)
        OLS_result = OLS(y_window, X).fit()
        hedge_ratio = OLS_result.params.iloc[1]
        hedge_ratios[i - 1] = hedge_ratio

    return hedge_ratios


def calc_spread(series_y: pd.Series,
                series_x: pd.Series,
                hedge_ratios: pd.Series) -> pd.Series:
    """
    根據動態 hedge ratio 計算每日的 spread。
    公式：spread = series_y - hedge_ratio * series_x

    參數：
        series_y     : 因變數價格序列（例如 GLD 收盤價）
        series_x     : 自變數價格序列（例如 GDX 收盤價）
        hedge_ratios : 每日的 hedge ratio 序列（來自 calc_rolling_hedge_ratio）

    回傳：
        spread : 每日的 spread 序列
                 例如：
                 Date
                 2010-02-05    0.43
                 2010-02-08   -0.21
                 2010-02-09    0.18
                 dtype: float64
    """
    spread = series_y - hedge_ratios* series_x

    return spread


# ============================================================
# 直接執行此檔案時的測試用範例
# ============================================================
if __name__ == "__main__":
    # 先做 CADF 取得半衰期
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
    from data.loader import load_multiple
    from strategy.cointegration import cadf_test
    import pandas as pd

    data = load_multiple(['GLD', 'GDX'])
    gld = data['GLD']['Close']
    gdx = data['GDX']['Close']

    gld = gld[gld.index >= gld.index.max() - pd.DateOffset(years=2)]
    gdx = gdx[gdx.index >= gdx.index.max() - pd.DateOffset(years=2)]

    cadf_result = cadf_test(gld, gdx)
    half_life = cadf_result['half_life']

    # 計算動態 hedge ratio 與 spread
    hedge_ratios = calc_rolling_hedge_ratio(gld, gdx, int(half_life))
    spread = calc_spread(gld, gdx, hedge_ratios)
    
    print(hedge_ratios.dropna().head())
    print(hedge_ratios.dropna().tail())
    print(spread.dropna().tail())