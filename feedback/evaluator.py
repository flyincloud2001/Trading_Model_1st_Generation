# evaluator.py
# 負責比較實際交易結果與回測預測結果，定期重新檢定共整合
# 觸發頻率：建議每週執行一次（週末收盤後）
# 輸出：CSV 報告 + log 檔案

import os
import pandas as pd
import numpy as np
from datetime import datetime
from monitor.tracker import setup_logger


# ============================================================
# 可調整參數區
# ============================================================
DEFAULT_REPORT_DIR = os.path.join(os.path.dirname(__file__), "reports")
DEFAULT_DIVERGENCE_THRESHOLD = 0.3   # 實際 vs 回測 Sharpe 差距警示閾值
                                      # 例如 0.3 代表實際 Sharpe 比回測低 30% 時警示


def compare_pnl(actual_pnl: pd.Series,
                backtest_pnl: pd.Series,
                logger=None) -> dict:
    """
    比較實際 P&L 與回測預測 P&L 的差距。

    參數：
        actual_pnl   : 實際交易的每日損益序列
                       例如：
                       Date
                       2024-01-02    0.0019
                       2024-01-03   -0.0012
                       2024-01-04    0.0031
                       dtype: float64

        backtest_pnl : 回測預測的每日損益序列（同一時間段）
                       例如：
                       Date
                       2024-01-02    0.0023
                       2024-01-03   -0.0008
                       2024-01-04    0.0027
                       dtype: float64

    回傳：
        comparison : 比較結果字典
                     例如：
                     {
                         "actual_sharpe": 1.21,
                         "backtest_sharpe": 1.87,
                         "sharpe_divergence": 0.35,    ← 差距 35%，超過閾值
                         "actual_apr": 0.089,
                         "backtest_apr": 0.134,
                         "mean_pnl_diff": -0.0004,     ← 實際每日平均比回測少 0.04%
                         "is_diverged": True            ← 是否超過警示閾值
                     }
    """
    if logger is None:
        logger = setup_logger()

    # 對齊日期
    common_dates = actual_pnl.index.intersection(backtest_pnl.index)
    actual = actual_pnl.loc[common_dates]
    backtest = backtest_pnl.loc[common_dates]

    if len(common_dates) == 0:
        raise ValueError("[evaluator] 實際與回測的日期沒有重疊，無法比較。")

    # 計算各自的 Sharpe ratio
    def _sharpe(pnl):
        if pnl.std() == 0:
            return 0.0
        return round(np.sqrt(252) * pnl.mean() / pnl.std(), 4)

    # 計算各自的 APR
    def _apr(pnl):
        cumret = (1 + pnl).cumprod() - 1
        n = len(pnl)
        return round((1 + cumret.iloc[-1]) ** (252 / n) - 1, 4)

    actual_sharpe = _sharpe(actual)
    backtest_sharpe = _sharpe(backtest)

    # 計算 Sharpe 差距比例
    if backtest_sharpe != 0:
        sharpe_divergence = abs(
            (actual_sharpe - backtest_sharpe) / backtest_sharpe
        )
    else:
        sharpe_divergence = 0.0

    is_diverged = sharpe_divergence > DEFAULT_DIVERGENCE_THRESHOLD

    comparison = {
        "actual_sharpe": actual_sharpe,
        "backtest_sharpe": backtest_sharpe,
        "sharpe_divergence": round(sharpe_divergence, 4),
        "actual_apr": _apr(actual),
        "backtest_apr": _apr(backtest),
        "mean_pnl_diff": round((actual - backtest).mean(), 6),
        "is_diverged": is_diverged
    }

    # 印出比較結果
    logger.info(f"[evaluator] P&L 比較結果：")
    logger.info(f"  實際 Sharpe    : {actual_sharpe}")
    logger.info(f"  回測 Sharpe    : {backtest_sharpe}")
    logger.info(f"  Sharpe 差距    : {sharpe_divergence:.2%}")
    logger.info(f"  實際 APR       : {comparison['actual_apr']:.2%}")
    logger.info(f"  回測 APR       : {comparison['backtest_apr']:.2%}")
    logger.info(f"  每日平均損益差 : {comparison['mean_pnl_diff']:.6f}")

    if is_diverged:
        logger.info(
            f"[evaluator] ⚠️  警示：實際績效與回測差距 {sharpe_divergence:.2%}，"
            f"超過閾值 {DEFAULT_DIVERGENCE_THRESHOLD:.2%}。"
            f"建議重新檢查策略或考慮暫停交易。"
        )

    return comparison


def recheck_cointegration(series_y: pd.Series,
                           series_x: pd.Series,
                           symbol_y: str,
                           symbol_x: str,
                           significance: float = 0.05,
                           logger=None) -> dict:
    """
    重新執行 CADF 共整合檢定，確認配對是否仍然有效。
    書中強調：共整合關係可能隨時間失效，需定期重新檢定。

    參數：
        series_y    : Y 資產的最新價格序列
        series_x    : X 資產的最新價格序列
        symbol_y    : Y 資產代號，例如 "GLD"
        symbol_x    : X 資產代號，例如 "GDX"
        significance: 顯著水準，預設 0.05

    回傳：
        result : 共整合檢定結果字典
                 例如：
                 {
                     "pair": "GLD_GDX",
                     "is_cointegrated": True,
                     "p_value": 0.028,
                     "half_life": 21.3,
                     "checked_at": "2024-01-07"
                 }
    """
    if logger is None:
        logger = setup_logger()

    # 呼叫 strategy/cointegration.py 的 CADF 檢定
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
    from strategy.cointegration import cadf_test

    pair_name = f"{symbol_y}_{symbol_x}"
    logger.info(f"[evaluator] 重新檢定 {pair_name} 的共整合關係...")

    coint_result = cadf_test(series_y, series_x, significance)

    result = {
        "pair": pair_name,
        "is_cointegrated": coint_result["is_cointegrated"],
        "p_value": coint_result["p_value"],
        "half_life": coint_result["half_life"],
        "checked_at": datetime.today().strftime("%Y-%m-%d")
    }

    if not result["is_cointegrated"]:
        logger.info(
            f"[evaluator] ⚠️  警示：{pair_name} 共整合關係已失效！"
            f"（p-value = {result['p_value']}）"
            f"建議暫停此配對的交易。"
        )
    else:
        logger.info(
            f"[evaluator] ✅ {pair_name} 共整合關係仍然有效。"
            f"（p-value = {result['p_value']}，半衰期 = {result['half_life']} 天）"
        )

    return result


def save_report(comparison: dict,
                cointegration_results: list,
                report_dir: str = DEFAULT_REPORT_DIR) -> None:
    """
    將比較結果與共整合檢定結果儲存為 CSV 和 log 檔案。

    參數：
        comparison             : compare_pnl 的輸出字典
        cointegration_results  : 多個配對的 recheck_cointegration 輸出字典清單
                                 例如：
                                 [
                                     {"pair": "GLD_GDX", "is_cointegrated": True, ...},
                                     {"pair": "EWA_EWC", "is_cointegrated": False, ...}
                                 ]
        report_dir             : 報告儲存資料夾
    """
    os.makedirs(report_dir, exist_ok=True)
    today = datetime.today().strftime("%Y%m%d")

    # 儲存 P&L 比較結果為 CSV
    comparison_df = pd.DataFrame([comparison])
    comparison_df["report_date"] = today
    comparison_path = os.path.join(report_dir, f"pnl_comparison_{today}.csv")
    comparison_df.to_csv(comparison_path, index=False)
    print(f"[evaluator] P&L 比較報告已儲存：{comparison_path}")

    # 儲存共整合檢定結果為 CSV
    coint_df = pd.DataFrame(cointegration_results)
    coint_path = os.path.join(report_dir, f"cointegration_{today}.csv")
    coint_df.to_csv(coint_path, index=False)
    print(f"[evaluator] 共整合檢定報告已儲存：{coint_path}")


def run_weekly_feedback(actual_pnl: pd.Series,
                        backtest_pnl: pd.Series,
                        pairs: dict) -> None:
    """
    執行完整的每週回饋流程：
    1. 比較實際 P&L 與回測 P&L
    2. 重新檢定所有配對的共整合關係
    3. 儲存 CSV 報告與 log

    參數：
        actual_pnl   : 實際交易的每日損益序列
        backtest_pnl : 回測預測的每日損益序列
        pairs        : 配對字典，key 為配對名稱，value 為 (series_y, series_x, symbol_y, symbol_x)
                       例如：
                       {
                           "GLD_GDX": (gld_series, gdx_series, "GLD", "GDX"),
                           "EWA_EWC": (ewa_series, ewc_series, "EWA", "EWC")
                       }
    """
    logger = setup_logger()
    logger.info(f"[evaluator] 開始執行每週回饋分析...")

    # 步驟一：比較 P&L
    comparison = compare_pnl(actual_pnl, backtest_pnl, logger)

    # 步驟二：重新檢定共整合
    cointegration_results = []
    for pair_name, (series_y, series_x, symbol_y, symbol_x) in pairs.items():
        result = recheck_cointegration(
            series_y, series_x, symbol_y, symbol_x, logger=logger
        )
        cointegration_results.append(result)

    # 步驟三：儲存報告
    save_report(comparison, cointegration_results)

    logger.info(f"[evaluator] 每週回饋分析完成。")


# ============================================================
# 直接執行此檔案時的測試用範例
# ============================================================
if __name__ == "__main__":
    import sys
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

    # 模擬實際 P&L（用回測結果加入隨機誤差模擬）
    actual_pnl = results["daily_pnl"] * 0.85 + np.random.normal(0, 0.0002, len(results))
    actual_pnl = pd.Series(actual_pnl.values, index=results.index)

    # 執行每週回饋
    pairs = {
        "GLD_GDX": (gld, gdx, "GLD", "GDX")
    }
    run_weekly_feedback(
        actual_pnl=actual_pnl,
        backtest_pnl=results["daily_pnl"],
        pairs=pairs
    )