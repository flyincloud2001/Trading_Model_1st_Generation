# tracker.py
# 負責計算即時 P&L 並監控 Z-score 信號
# 當信號觸發時同時印出至 terminal 並寫入 log 檔案

import os
import logging
import pandas as pd
from datetime import datetime


# ============================================================
# 可調整參數區
# ============================================================
DEFAULT_LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
DEFAULT_LOG_FILE = os.path.join(
    DEFAULT_LOG_DIR,
    f"monitor_{datetime.today().strftime('%Y%m%d')}.log"
)


def setup_logger(log_file: str = DEFAULT_LOG_FILE) -> logging.Logger:
    """
    設定 logger，同時輸出至 terminal 和 log 檔案。

    參數：
        log_file : log 檔案路徑，預設為 monitor/logs/monitor_YYYYMMDD.log

    回傳：
        logger : 設定好的 logger 物件
    """
    # 建立 log 資料夾（若不存在則自動建立）
    os.makedirs(DEFAULT_LOG_DIR, exist_ok=True)

    logger = logging.getLogger("monitor")
    logger.setLevel(logging.INFO)

    # 避免重複加入 handler
    if logger.handlers:
        return logger

    # 格式：[時間] 訊息
    formatter = logging.Formatter(
        fmt="[%(asctime)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Terminal handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Log 檔案 handler
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.info(f"[tracker] Logger 初始化完成，log 檔案：{log_file}")
    return logger


def calc_realtime_pnl(positions: pd.DataFrame,
                      current_prices: dict) -> dict:
    """
    根據目前持倉與即時股價計算未實現 P&L。

    參數：
        positions     : 持倉 DataFrame（來自 account.get_positions）
                        例如：
                              symbol  position  avg_cost
                        0        GLD       372    165.32
                        1        GDX      -623     32.18

        current_prices : 各股票的即時股價字典
                         例如：
                         {
                             "GLD": 167.45,
                             "GDX": 31.95
                         }

    回傳：
        pnl_summary : P&L 摘要字典
                      例如：
                      {
                          "GLD_pnl": 791.96,    ← GLD 持倉未實現損益
                          "GDX_pnl": 143.29,    ← GDX 持倉未實現損益
                          "total_pnl": 935.25   ← 總未實現損益
                      }
    """
    pnl_summary = {}
    total_pnl = 0.0

    for _, row in positions.iterrows():
        symbol = row["symbol"]
        if symbol not in current_prices:
            continue

        current_price = current_prices[symbol]
        pnl = row["position"] * (current_price - row["avg_cost"])
        pnl_summary[f"{symbol}_pnl"] = round(pnl, 2)
        total_pnl += pnl

    pnl_summary["total_pnl"] = round(total_pnl, 2)
    return pnl_summary


def check_signal(zscore_latest: float,
                 entry_zscore: float = 2.0,
                 exit_zscore: float = 0.0,
                 logger: logging.Logger = None) -> str:
    """
    根據最新 Z-score 判斷目前信號狀態並發出警示。

    參數：
        zscore_latest : 最新的 Z-score 數值
                        例如：2.34
        entry_zscore  : 進場閾值，預設 2.0
        exit_zscore   : 出場閾值，預設 0.0
        logger        : logger 物件，若為 None 則只印出至 terminal

    回傳：
        signal_status : 信號狀態字串
                        可能的值：
                        "ENTER_SHORT" → Z > +entry_zscore，建議做空 spread
                        "ENTER_LONG"  → Z < -entry_zscore，建議做多 spread
                        "EXIT"        → |Z| < exit_zscore，建議平倉
                        "HOLD"        → 其他情況，維持目前倉位
    """
    if zscore_latest > entry_zscore:
        signal_status = "ENTER_SHORT"
        message = (
            f"[tracker] 🔴 信號觸發：ENTER_SHORT｜"
            f"Z-score = {zscore_latest:.4f} > {entry_zscore}｜"
            f"建議做空 Y，做多 X"
        )
    elif zscore_latest < -entry_zscore:
        signal_status = "ENTER_LONG"
        message = (
            f"[tracker] 🟢 信號觸發：ENTER_LONG｜"
            f"Z-score = {zscore_latest:.4f} < -{entry_zscore}｜"
            f"建議做多 Y，做空 X"
        )
    elif abs(zscore_latest) < exit_zscore:
        signal_status = "EXIT"
        message = (
            f"[tracker] 🟡 信號觸發：EXIT｜"
            f"Z-score = {zscore_latest:.4f}，spread 回歸均值｜"
            f"建議平倉"
        )
    else:
        signal_status = "HOLD"
        message = (
            f"[tracker] ⚪ 維持倉位：HOLD｜"
            f"Z-score = {zscore_latest:.4f}"
        )

    # 輸出至 terminal 和 log 檔案
    if logger:
        logger.info(message)
    else:
        print(message)

    return signal_status


def run_monitor(zscore_series: pd.Series,
                positions: pd.DataFrame,
                current_prices: dict,
                entry_zscore: float = 2.0,
                exit_zscore: float = 0.0) -> None:
    """
    執行完整的監控流程：
    1. 計算即時 P&L
    2. 檢查最新 Z-score 信號
    3. 將結果同時輸出至 terminal 和 log 檔案

    參數：
        zscore_series  : Z-score 時間序列（來自 strategy/signals.py）
        positions      : 目前持倉（來自 account.get_positions）
        current_prices : 各股票即時股價字典
        entry_zscore   : 進場閾值，預設 2.0
        exit_zscore    : 出場閾值，預設 0.0
    """
    logger = setup_logger()

    # 計算即時 P&L
    pnl_summary = calc_realtime_pnl(positions, current_prices)
    logger.info(
        f"[tracker] 即時 P&L｜"
        f"總損益：${pnl_summary['total_pnl']:,.2f}"
    )

    # 檢查最新 Z-score 信號
    zscore_latest = zscore_series.dropna().iloc[-1]
    check_signal(zscore_latest, entry_zscore, exit_zscore, logger)


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

    # 載入資料並計算 Z-score
    data = load_multiple(["GLD", "GDX"])
    gld = data["GLD"]["Close"]
    gdx = data["GDX"]["Close"]

    coint_result = cadf_test(gld, gdx)
    lookback = int(coint_result["half_life"])
    hedge_ratios = calc_rolling_hedge_ratio(gld, gdx, lookback)
    spread = calc_spread(gld, gdx, hedge_ratios)
    zscore = calc_zscore(spread, lookback)

    # 模擬持倉與即時股價（不連接 IBKR）
    mock_positions = pd.DataFrame([
        {"symbol": "GLD", "position": 372, "avg_cost": 165.32},
        {"symbol": "GDX", "position": -623, "avg_cost": 32.18}
    ])
    mock_prices = {"GLD": 167.45, "GDX": 31.95}

    # 執行監控
    run_monitor(zscore, mock_positions, mock_prices)