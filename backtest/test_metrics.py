# metrics.py
# 負責計算回測績效指標
# 包含：Sharpe ratio、最大回撤、最大回撤期間、年化報酬率

import pandas as pd
import numpy as np


def calc_sharpe(pnl_daily: pd.Series,
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
    std_daily = pnl_daily.std()

    if std_daily == 0:
        return 0.0
    
    std_annual = np.sqrt(periods_per_year) * pnl_daily.mean() / std_daily

    return round(std_annual, 2)

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
    cumulative_return_ = (1 + cumulative_return).cumprod()
    high_watermark = cumulative_return_.cummax()

    # 計算每日回撤
    drawdown = high_watermark - cumulative_return_

    # 最大回撤
    max_drawdown = drawdown.min()

    # 計算回撤期間
    drawdown_duration = 0
    max_drawdown_duration = 0

    for drawdown in drawdown:
        if drawdown < 0:
            drawdown_duration += 1
            max_drawdown_duration = max(drawdown_duration, max_drawdown_duration) 
        else:
            drawdown_duration = 0

    result = {
        'max_drawdown': max_drawdown,
        'max_drawdown_period': max_drawdown_duration
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
    
    # apr = annualized percentage return
    n_period = len(cumulative_return)
    apr = (1 + cumulative_return) ** (periods_per_year / n_period) - 1

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
    split_ratio = int(len(results) * train_ratio)
    result_train = results[:split_ratio]
    result_test = results[split_ratio:]

    def _calc_metrics(df: pd.DataFrame) -> dict:
        # 重新計算測試集的累積報酬（從 0 開始）
        pnl_daily = df['pnl_daily']
        pnl_cumulative = (1 + pnl_daily).cumprod()

        metric = {
            'sharpe_ratio': calc_sharpe(pnl_daily, periods_per_year),
            'apr': calc_apr(pnl_daily, periods_per_year),
            'max_drawdown': calc_max_drawdown(pnl_cumulative)['max_drawdown'],
            'max_drawdown_duration': calc_max_drawdown(pnl_cumulative)['max_drawdown_duration']
        }

        return metric

    # 印出摘要
    summary = {
        'train': _calc_metrics(result_train),
        'test': _calc_metrics(result_test)
    }

    for split_name, metric in summary.items():
        print('\n 訓練集') if 'train' == split_name else print('\n測試集')
        print(f'夏普比率: {metric['sharpe_ratio']}')
        print(f'年化率: {metric['apr']}')
        print(f'最大回撤: {metric['max_drawdown']}')
        print(f'最大回撤時間: {metric['max_drawdown_duration']}')

    return summary
# ============================================================
# 直接執行此檔案時的測試用範例
# ============================================================
if __name__ == "__main__":
    import sys
    import os
    sys.path.append(os.path.join(os.path.join(__file__), ".."))
    import pandas as pd
    import numpy as np
    from data.loader import load_multiple
    from strategy.cointegration import cadf_test
    from strategy.signals import generate_signals, calc_zscore
    from backtest.engine import run_backtest

    data = load_multiple(['GLD', 'GDX'])
    gld = data['GLD']['Close']
    gdx = data['GDX']['Close']

    gld_in_sample = gld[gld.index >= gld.index.max() - pd.DateOffset(months=9)]
    gdx_in_sample = gdx[gdx.index >= gdx.index.max() - pd.DateOffset(months=9)]

    gld_in_sample, gdx_in_sample = gld_in_sample.align(gdx_in_sample, join='inner')

    cadf_result = cadf_test(gld_in_sample, gdx_in_sample)
    half_life = cadf_result['half_life']
    hedge_ratio = cadf_result['hedge_ratio']
    spread = cadf_result['spread']

    lookback = int(half_life)
    zscore = calc_zscore(spread, lookback)
    signals = generate_signals(zscore, entry_zscore=2.0, exit_zscore=0.4)

    backtest_result = run_backtest(gld_in_sample, gdx_in_sample, hedge_ratio, signals)
    summary = summarize()