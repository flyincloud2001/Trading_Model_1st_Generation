# kelly.py
# 負責用 Kelly 公式計算最優槓桿與建議倉位大小
# 設計原則：
#   - 輸入來自 backtest/engine.py 的 daily_pnl
#   - 用移動視窗動態更新，避免過度依賴遠期歷史
#   - 預設使用半 Kelly（Half-Kelly）作為實際槓桿
#   - 同時設定最大槓桿上限，防止極端情況

import pandas as pd
import numpy as np


# ============================================================
# 可調整參數區
# ============================================================
DEFAULT_LOOKBACK = 126        # 移動視窗長度，預設半年（126 個交易日）
DEFAULT_HALF_KELLY = True     # 是否使用半 Kelly，預設 True
DEFAULT_MAX_LEVERAGE = 2.0    # 最大槓桿上限，預設 2 倍（符合散戶 Reg T 限制）


def calc_kelly_leverage(daily_pnl: pd.Series,
                        lookback: int = DEFAULT_LOOKBACK,
                        half_kelly: bool = DEFAULT_HALF_KELLY,
                        max_leverage: float = DEFAULT_MAX_LEVERAGE) -> pd.Series:
    """
    用移動視窗 Kelly 公式計算每日建議槓桿。

    Kelly 公式：f* = mean(daily_pnl) / var(daily_pnl)
    Half-Kelly ：f  = f* / 2

    參數：
        daily_pnl    : 每日淨損益序列（來自 backtest/engine.py）
        lookback     : 移動視窗長度（天數），預設 126（半年）
                       例如 lookback = 126，代表用過去 126 天的損益計算 Kelly
        half_kelly   : 是否使用半 Kelly，預設 True
                       書中建議：因為報酬分布非 Gaussian，Kelly 通常過於激進
        max_leverage : 最大槓桿上限，預設 2.0
                       例如帳戶有 $100,000，槓桿 2.0 代表最多持倉 $200,000

    回傳：
        leverage : 每日建議槓桿序列
                   例如：
                   Date
                   2010-08-05    1.23    ← 建議用 1.23 倍槓桿
                   2010-08-06    1.18    ← 策略近期表現略差，槓桿降低
                   2010-08-09    1.31    ← 策略表現回升，槓桿提高
                   dtype: float64
                   前 lookback-1 天為 NaN（資料不足無法計算）
    """
    # 計算移動視窗內的平均報酬與變異數
    rolling_mean = daily_pnl.rolling(window=lookback).mean()
    rolling_var = daily_pnl.rolling(window=lookback).var()

    # 防止變異數為零（避免除以零）
    rolling_var = rolling_var.replace(0, np.nan)

    # Kelly 公式：f* = mean / var
    kelly_leverage = rolling_mean / rolling_var

    # 若使用半 Kelly
    if half_kelly:
        kelly_leverage = kelly_leverage / 2

    # 限制在 0 到 max_leverage 之間
    # 負值代表策略近期虧損，建議不持倉（設為 0）
    leverage = kelly_leverage.clip(lower=0.0, upper=max_leverage)

    return leverage


def calc_position_size(account_equity: float,
                       leverage: float,
                       price_y: float,
                       price_x: float,
                       hedge_ratio: float) -> dict:
    """
    根據帳戶權益與建議槓桿，計算實際建議持倉股數。

    參數：
        account_equity : 帳戶總權益（美元）
                         例如：100000.0（$10 萬）
        leverage       : 當日建議槓桿（來自 calc_kelly_leverage）
                         例如：1.23
        price_y        : 當日 Y 資產的收盤價
                         例如：GLD 收盤價 $165.32
        price_x        : 當日 X 資產的收盤價
                         例如：GDX 收盤價 $32.18
        hedge_ratio    : 當日動態 hedge ratio
                         例如：1.6766

    回傳：
        position : 建議持倉股數的字典
                   例如：
                   {
                       "capital_deployed": 123000.0,  ← 實際部署資金 $123,000
                       "shares_y": 372,               ← 建議持有 372 股 GLD
                       "shares_x": 623                ← 建議持有 623 股 GDX
                                                         （= 372 * 1.6766，取整數）
                   }
    """
    # 實際部署資金
    capital_deployed = account_equity * leverage

    # Y 腿：投入 capital_deployed / 2
    shares_y = int(capital_deployed / 2 / price_y)

    # X 腿：投入 capital_deployed / 2（對稱），與 hedge_ratio 無關
    shares_x = int(capital_deployed / 2 / price_x)

    position = {
        "capital_deployed": round(capital_deployed, 2),
        "shares_y": shares_y,
        "shares_x": shares_x
    }

    return position
# share_y * price_y = capital_deployed / 2
# share_x * price_x = (capital_deployed / 2 / price_y) * hedge_ratio * price_x = capital_deployed / 2 
def summarize_leverage(leverage: pd.Series) -> None:
    """
    印出槓桿序列的統計摘要，方便檢查風險管理效果。

    參數：
        leverage : 每日建議槓桿序列
    """
    leverage_clean = leverage.dropna()
    print(f"\n[kelly] 槓桿統計摘要：")
    print(f"  平均槓桿   : {leverage_clean.mean():.4f}")
    print(f"  最大槓桿   : {leverage_clean.max():.4f}")
    print(f"  最小槓桿   : {leverage_clean.min():.4f}")
    print(f"  槓桿為零天數: {(leverage_clean == 0).sum()} 天")
    print(f"  （槓桿為零代表策略近期虧損，建議不持倉）")


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
    from strategy.signals import calc_zscore, generate_signals
    from backtest.engine import run_backtest

    # 載入資料
    data = load_multiple(["GLD", "GDX"])
    gld = data["GLD"]["Close"]
    gdx = data["GDX"]["Close"]

    # 執行策略流程
    coint_result = cadf_test(gld, gdx)
    lookback = int(coint_result["half_life"])
    hedge_ratios = calc_rolling_hedge_ratio(gld, gdx, lookback)
    spread = calc_spread(gld, gdx, hedge_ratios)
    zscore = calc_zscore(spread, lookback)
    signals = generate_signals(zscore)
    results = run_backtest(gld, gdx, hedge_ratios, signals)

    # 計算 Kelly 槓桿
    leverage = calc_kelly_leverage(results["daily_pnl"])
    summarize_leverage(leverage)

    # 計算今日建議持倉（假設帳戶 $100,000）
    today_leverage = leverage.dropna().iloc[-1]
    today_price_y = gld.iloc[-1]
    today_price_x = gdx.iloc[-1]
    today_hedge_ratio = hedge_ratios.dropna().iloc[-1]

    position = calc_position_size(
        account_equity=100000.0,
        leverage=today_leverage,
        price_y=today_price_y,
        price_x=today_price_x,
        hedge_ratio=today_hedge_ratio
    )

    print(f"\n[kelly] 今日建議持倉：")
    print(f"  部署資金 : ${position['capital_deployed']:,.2f}")
    print(f"  GLD 股數 : {position['shares_y']} 股")
    print(f"  GDX 股數 : {position['shares_x']} 股")