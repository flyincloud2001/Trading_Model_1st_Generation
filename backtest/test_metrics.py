# metrics.py
# 負責計算回測績效指標
# 包含：Sharpe ratio、最大回撤、最大回撤期間、年化報酬率




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

    # 計算每日回撤

    # 最大回撤

    # 計算回撤期間


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

    def _calc_metrics(df: pd.DataFrame) -> dict:
        # 重新計算測試集的累積報酬（從 0 開始）

    # 印出摘要


# ============================================================
# 直接執行此檔案時的測試用範例
# ============================================================
if __name__ == "__main__":