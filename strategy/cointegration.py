# cointegration.py
# 負責共整合檢定與半衰期計算
# 目前實作：CADF 檢定（適用於兩個資產的配對）

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller
from statsmodels.regression.linear_model import OLS
from statsmodels.tools import add_constant
import matplotlib.pyplot as plt

def calc_halflife(spread: pd.Series) -> float:

    # 計算 spread 的一階差分
    spread_lag = spread.shift(1)
    delta_spread = spread - spread_lag

    # 移除 NaN
    spread_lag = spread_lag.dropna()
    delta_spread = delta_spread.dropna()

    # OLS 回歸：delta_spread = lambda * spread_lag + mu
    # mu is the mean of spread in the long term
    X = add_constant(spread_lag)
    result = OLS(delta_spread, X).fit()
    lambda_ = result.params.iloc[1]

    # 防止 lambda 為正（代表不均值回歸）
    if lambda_ >= 0:
        raise ValueError(
            f"[cointegration] lambda = {lambda_:.4f} >= 0，此 spread 不具均值回歸特性。"
        )

    half_life = -np.log(2) / lambda_
    return round(half_life, 2)


def cadf_test(series_y: pd.Series,
              series_x: pd.Series,
              significance: float = 0.05) -> dict:

    # 步驟一：OLS 回歸取殘差
    X = add_constant(series_x)
    ols_result = OLS(series_y, X).fit()
    hedge_ratio = ols_result.params.iloc[1]
    residuals = ols_result.resid

    # 步驟二：對殘差做 ADF 檢定
    adf_result = adfuller(residuals, autolag="AIC")
    adf_statistic = adf_result[0]
    p_value = adf_result[1]

    # 步驟三：判斷是否共整合
    is_cointegrated = p_value < significance

    # 計算半衰期
    try:
        half_life = calc_halflife(pd.Series(residuals))
    except ValueError:
        half_life = None

    result = {
        "is_cointegrated": is_cointegrated,
        "p_value": round(p_value, 4),
        "hedge_ratio": round(hedge_ratio, 4),
        "half_life": half_life,
        "adf_statistic": round(adf_statistic, 4),
        "spread": residuals
    }

    # 印出檢定結果
    print(f"[cointegration] CADF 檢定結果：")
    print(f"  共整合：{is_cointegrated}（p-value = {p_value:.4f}）")
    print(f"  Hedge Ratio：{hedge_ratio:.4f}")
    print(f"  半衰期：{half_life} 天")

    # 繪製spread隨時間的演變
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(residuals, label='Residuals')
    ax.legend()
    ax.set_title('Residuals')
    plt.tight_layout()
    plt.show()

    return result


# ============================================================
# 直接執行此檔案時的測試用範例
# ============================================================
if __name__ == "__main__":
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
    from data.loader import load_multiple

    data = load_multiple(["GLD", "GDX"])

    gld = data['GLD']['Close']
    gdx = data['GDX']['Close']

    gld =  gld[gld.index >= gld.index.max() - pd.DateOffset(months=8)]
    gdx =  gdx[gdx.index >= gdx.index.max() - pd.DateOffset(months=8)]

    gld, gdx = gld.align(gdx, join='inner')

    cadf_result = cadf_test(gld, gdx)

