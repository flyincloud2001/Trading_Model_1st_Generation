# cointegration.py
# 負責共整合檢定與半衰期計算
# 目前實作：CADF 檢定（適用於兩個資產的配對）
import numpy as np
from statsmodels.tsa.stattools import adfuller
from statsmodels.regression.linear_model import OLS
from statsmodels.tools import add_constant
import pandas as pd
import matplotlib.pyplot as plt



def calc_halflife(spread: pd.Series) -> float:
    """
    計算 spread 序列的半衰期。
    原理：對 spread 的差分做 OLS 回歸，求出均值回歸速度 lambda，
          再用公式 half_life = -log(2) / lambda 推導。

    參數：
        spread : spread 的時間序列
                 例如：
                 Date
                 2010-01-04   -0.32
                 2010-01-05    0.15
                 2010-01-06   -0.08
                 dtype: float64

    回傳：
        half_life : 半衰期（天數）
                    例如：23.4，代表 spread 平均需要 23.4 天回到偏離量的一半
    """
    # 計算 spread 的一階差分
    spread_lag = spread.shift(1)
    delta_spread = spread - spread_lag

    # 移除 NaN
    spread_lag.dropna(inplace=True)
    delta_spread.dropna(inplace=True)

    # OLS 回歸：delta_spread = lambda * spread_lag + mu
    X = add_constant(spread_lag)
    result = OLS(delta_spread, X).fit()

    delta_spread = delta_spread[delta_spread.index >=
                        delta_spread.index.max() - pd.DateOffset(years=2)]
    spread_lag = spread_lag[spread_lag.index >=
                        spread_lag.index.max() - pd.DateOffset(years=2)]
    
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.scatter(spread_lag, delta_spread)
    ax.set_xlabel('spread')
    ax.set_ylabel('delta_spread')
    ax.grid()
    plt.show()

    # mu is the mean of spread in the long term
    lambda_ = result.params.iloc[1]

    # 防止 lambda 為正（代表不均值回歸）
    if lambda_ >= 0:
        raise ValueError(
            f'{lambda_} >= 0, 均值不回歸'
        )

    half_life = - np.log(2)/ lambda_

    return round(half_life, 2)


def cadf_test(series_y: pd.Series,
              series_x: pd.Series,
              significance: float = 0.05) -> dict:
    """
    對兩個資產進行 CADF 共整合檢定。    
    步驟：
        1. 用 OLS 對 series_y ~ series_x 回歸，取殘差
        2. 對殘差做 ADF 檢定
        3. 判斷是否共整合

    參數：
        series_y     : 因變數價格序列（例如 GLD 的收盤價）
        series_x     : 自變數價格序列（例如 GDX 的收盤價）
        significance : 顯著水準，預設 0.05（即 95% 信心水準）
                       例如設為 0.05，p-value < 0.05 才視為共整合

    回傳：
        result : 包含檢定結果的字典
                 例如：
                 {
                     "is_cointegrated": True,
                     "p_value": 0.032,
                     "hedge_ratio": 1.6766,
                     "half_life": 23.4,
                     "adf_statistic": -3.56
                 }
    """
    # 只取最近兩年的資料
    series_x = series_x[series_x.index >=
                        series_x.index.max() - pd.DateOffset(years=2)]
    series_y = series_y[series_y.index >=
                        series_y.index.max() - pd.DateOffset(years=2)]
    
    # 步驟一：OLS 回歸取殘差
    X = add_constant(series_x)
    OLS_result = OLS(series_y, X).fit()
    predictions = OLS_result.fittedvalues
    hedge_ratio = OLS_result.params.iloc[1]
    
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.scatter(series_x, series_y, s=0.3)
    ax.plot(series_x, predictions, c='red', linewidth=0.5, label='linear fit')
    ax.legend()
    ax.set_title('linear relationship between two asset prices')
    plt.tight_layout()
    plt.show()

    # 步驟二：對殘差做 ADF 檢定
    residuals = OLS_result.resid
    adf_result = adfuller(residuals, autolag="AIC")
    p_value = adf_result[1]
    adf_statistics = adf_result[0]

    # 步驟三：判斷是否共整合
    is_cointegrated = p_value <  significance

    # 計算半衰期
    try:
        half_life = calc_halflife(residuals)
    except ValueError:
        half_life = None
    
    # 印出檢定結果
    data = {
        "is_cointegrated": is_cointegrated,
        "p_value": round(p_value, 5),
        "adf_statistics": round(adf_statistics, 2),
        "hedge_ratio(fixed)": round(hedge_ratio, 2),
        "half_life": half_life
    }

    print(data)
    print(f"[cointegration] CADF 檢定結果：")
    print(f"  共整合：{is_cointegrated}（p-value = {p_value:.4f}）")
    print(f"  Hedge Ratio：{hedge_ratio:.4f}")
    print(f"  半衰期：{half_life} 天")

    return data

# ============================================================
# 直接執行此檔案時的測試用範例
# ============================================================
if __name__ == "__main__":
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
    from data.loader import load_multiple

    result = load_multiple(['GLD', 'GDX'])
    result['GLD'], result['GDX'] = result['GLD'].align(result['GDX'], join="inner")
    cadf_result = cadf_test(
        result['GLD']['Close'],
        result['GDX']['Close']
    )
