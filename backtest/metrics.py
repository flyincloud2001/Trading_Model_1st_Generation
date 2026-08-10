# metrics.py
# 負責計算回測績效指標
# 包含：Sharpe ratio、最大回撤、最大回撤期間、年化報酬率

import pandas as pd
import numpy as np


def calc_sharpe(daily_pnl: pd.Series,
                periods_per_year: int = 252) -> float:
    """
    計算年化 Sharpe ratio。
    公式：Sharpe = sqrt(periods_per_year) * mean(daily_pnl) / std(daily_pnl)
    注意：配對交易為市場中性策略，不需扣除無風險利率。

    參數：
        daily_pnl        : 每日損益序列
        periods_per_year : 一年的交易期數，日線預設 252

    回傳：
        sharpe : 年化 Sharpe ratio
                 例如：1.87，代表每承受一單位風險可獲得 1.87 單位報酬
    """
    if daily_pnl.std() == 0:
        return 0.0
    sharpe = np.sqrt(periods_per_year) * daily_pnl.mean() / daily_pnl.std()
    return round(sharpe, 4)


def calc_max_drawdown(cumulative_return: pd.Series) -> dict:
    """
    計算最大回撤與最大回撤期間。

    最大回撤：從高點到低點的最大跌幅
    最大回撤期間：從高點到恢復高點所需的最長天數

    參數：
        cumulative_return : 累積報酬序列
                            例如：
                            Date
                            2010-02-05    0.0023
                            2010-02-08    0.0038
                            2010-02-09    0.0030
                            dtype: float64

    回傳：
        result : 包含最大回撤與期間的字典
                 例如：
                 {
                     "max_drawdown": -0.1053,      ← 最大回撤 10.53%
                     "max_drawdown_duration": 120  ← 最長 120 天才恢復高點
                 }
    """
    # 計算高水位（High Watermark）
    equity = 1 + cumulative_return
    high_watermark = equity.cummax()

    # 計算每日回撤
    drawdown = (equity - high_watermark) / high_watermark

    # 最大回撤
    max_drawdown = drawdown.min()

    # 計算回撤期間
    drawdown_duration = 0
    max_drawdown_duration = 0
    for dd in drawdown:
        if dd < 0:
            drawdown_duration += 1
            max_drawdown_duration = max(max_drawdown_duration, drawdown_duration)
        else:
            drawdown_duration = 0

    result = {
        "max_drawdown": round(max_drawdown, 4),
        "max_drawdown_duration": max_drawdown_duration
    }
    return result


def calc_apr(cumulative_return: pd.Series,
             periods_per_year: int = 252) -> float:
    """
    計算年化報酬率（APR）。
    公式：APR = (1 + total_return) ^ (periods_per_year / n_periods) - 1

    參數：
        cumulative_return : 累積報酬序列
        periods_per_year  : 一年的交易期數，日線預設 252

    回傳：
        apr : 年化報酬率
              例如：0.124，代表年化報酬 12.4%
              注意：若回測期間不足一年，此數字可能極端，需謹慎解讀
    """
    n_periods = len(cumulative_return)
    if n_periods < periods_per_year:
        print("[metrics] 警告：回測期間不足一年，APR 數值僅供參考。")

    total_return = cumulative_return.iloc[-1]
    apr = (1 + total_return) ** (periods_per_year / n_periods) - 1
    return round(apr, 4)


def summarize(results: pd.DataFrame,
              train_ratio: float = 0.5,
              periods_per_year: int = 252) -> dict:
    """
    對回測結果計算完整績效摘要。
    自動將資料分為訓練集與測試集，分別計算績效。

    參數：
        results          : 來自 engine.py 的回測結果 DataFrame
        train_ratio      : 訓練集比例，預設 0.5（前 50% 為訓練集）
        periods_per_year : 一年的交易期數，預設 252

    回傳：
        summary : 包含訓練集與測試集績效的字典
                  例如：
                  {
                      "train": {
                          "sharpe": 2.31,
                          "apr": 0.183,
                          "max_drawdown": -0.072,
                          "max_drawdown_duration": 45
                      },
                      "test": {
                          "sharpe": 1.54,
                          "apr": 0.124,
                          "max_drawdown": -0.105,
                          "max_drawdown_duration": 120
                      }
                  }
    """
    # 分割訓練集與測試集
    split_idx = int(len(results) * train_ratio)
    train = results.iloc[:split_idx]
    test = results.iloc[split_idx:]

    def _calc_metrics(df: pd.DataFrame) -> dict:
        # 重新計算測試集的累積報酬（從 0 開始）
        cumret = (1 + df["daily_pnl"]).cumprod() - 1
        dd = calc_max_drawdown(cumret)
        return {
            "sharpe": calc_sharpe(df["daily_pnl"], periods_per_year),
            "apr": calc_apr(cumret, periods_per_year),
            "max_drawdown": dd["max_drawdown"],
            "max_drawdown_duration": dd["max_drawdown_duration"]
        }

    summary = {
        "train": _calc_metrics(train),
        "test": _calc_metrics(test)
    }

    # 印出摘要
    for split_name, metrics in summary.items():
        print(f"\n[metrics] {'訓練集' if split_name == 'train' else '測試集'} 績效：")
        print(f"  Sharpe Ratio         : {metrics['sharpe']}")
        print(f"  年化報酬率 APR       : {metrics['apr']:.2%}")
        print(f"  最大回撤             : {metrics['max_drawdown']:.2%}")
        print(f"  最大回撤期間         : {metrics['max_drawdown_duration']} 天")

    return summary


# ============================================================
# 直接執行此檔案時的測試用範例
# ============================================================
if __name__ == "__main__":
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
    from data.loader import load_multiple
    from strategy.cointegration import cadf_test
    from strategy.signals import calc_zscore, generate_signals
    from backtest.engine import run_backtest

    data = load_multiple(["GLD", "GDX"])
    gld = data["GLD"]["Close"]
    gdx = data["GDX"]["Close"]

    coint_result = cadf_test(gld, gdx)
    lookback = int(coint_result["half_life"])

    hedge_ratios = calc_rolling_hedge_ratio(gld, gdx, lookback)
    spread = calc_spread(gld, gdx, hedge_ratios)
    zscore = calc_zscore(spread, lookback)
    signals = generate_signals(zscore)

    results = run_backtest(gld, gdx, hedge_ratios, signals)
    summary = summarize(results)