# allocator.py
# 負責多策略的資本配置
# 使用 Kelly 公式的多策略版本：F* = C^(-1) * M
# 設計原則：
#   - 輸入為多個策略的 daily_pnl
#   - 輸出為每個策略的建議資本比例
#   - 預設使用半 Kelly
#   - 未來新增策略時只需傳入新的 daily_pnl，不需修改此模組

import numpy as np
import pandas as pd


# ============================================================
# 可調整參數區
# ============================================================
DEFAULT_HALF_KELLY = True      # 是否使用半 Kelly，預設 True
DEFAULT_MAX_ALLOCATION = 0.5   # 單一策略最大資本比例，預設 50%
DEFAULT_MIN_ALLOCATION = 0.0   # 單一策略最小資本比例，預設 0%（不允許負配置）
DEFAULT_LOOKBACK = 126         # 計算均值與共變異數的移動視窗，預設半年


def calc_portfolio_allocation(strategy_pnls: dict,
                               lookback: int = DEFAULT_LOOKBACK,
                               half_kelly: bool = DEFAULT_HALF_KELLY,
                               max_allocation: float = DEFAULT_MAX_ALLOCATION,
                               min_allocation: float = DEFAULT_MIN_ALLOCATION) -> pd.Series:
    """
    用 Kelly 公式的多策略版本計算每個策略的最優資本配置比例。

    Kelly 多策略公式：F* = C^(-1) * M
        M : 各策略的平均報酬向量
        C : 各策略報酬的共變異數矩陣

    參數：
        strategy_pnls  : 以策略名稱為 key，daily_pnl 序列為 value 的字典
                         例如：
                         {
                             "GLD_GDX": pd.Series([0.0023, 0.0015, -0.0008, ...]),
                             "EWA_EWC": pd.Series([0.0011, 0.0031, -0.0005, ...])
                         }
        lookback       : 計算均值與共變異數的移動視窗長度，預設 126 天
        half_kelly     : 是否使用半 Kelly，預設 True
        max_allocation : 單一策略最大資本比例，預設 0.5（50%）
        min_allocation : 單一策略最小資本比例，預設 0.0（0%）

    回傳：
        allocation : 每個策略的建議資本比例
                     例如：
                     GLD_GDX    0.35    ← 分配 35% 資本給 GLD/GDX 配對
                     EWA_EWC    0.28    ← 分配 28% 資本給 EWA/EWC 配對
                     dtype: float64
                     注意：各策略比例加總不一定等於 1，
                           剩餘資本視為現金部位
    """
    # 將所有策略的 daily_pnl 合併成一個 DataFrame
    pnl_df = pd.DataFrame(strategy_pnls).dropna()

    # 只使用最近 lookback 天的資料
    pnl_df = pnl_df.tail(lookback)

    if len(pnl_df) < 2:
        raise ValueError(
            f"[allocator] 資料不足，至少需要 2 筆資料，目前只有 {len(pnl_df)} 筆。"
        )

    # 計算平均報酬向量 M
    # 例如：M = [0.0018, 0.0012]（GLD_GDX 平均每日賺 0.18%，EWA_EWC 賺 0.12%）
    M = pnl_df.mean().values

    # 計算共變異數矩陣 C
    # 例如：C = [[0.0001, 0.00003],
    #             [0.00003, 0.00008]]
    # 對角線是各策略的變異數，非對角線是策略之間的共變異數
    C = pnl_df.cov().values

    # 確認 C 可逆（若策略完全相關則不可逆）
    if np.linalg.matrix_rank(C) < len(M):
        raise ValueError(
            "[allocator] 共變異數矩陣不可逆，"
            "可能有兩個策略的報酬完全相關，請移除其中一個。"
        )

    # Kelly 公式：F* = C^(-1) * M
    C_inv = np.linalg.inv(C)
    kelly_weights = C_inv @ M

    # 若使用半 Kelly
    if half_kelly:
        kelly_weights = kelly_weights / 2

    # 限制在 min_allocation 到 max_allocation 之間
    kelly_weights = np.clip(kelly_weights, min_allocation, max_allocation)

    # 轉為 pandas Series，以策略名稱為 index
    allocation = pd.Series(
        kelly_weights,
        index=list(strategy_pnls.keys())
    )

    return allocation


def calc_capital_per_strategy(account_equity: float,
                               allocation: pd.Series) -> pd.Series:
    """
    根據帳戶權益與資本配置比例，計算每個策略的實際分配資金。

    參數：
        account_equity : 帳戶總權益（美元）
                         例如：100000.0（$10 萬）
        allocation     : 每個策略的資本比例（來自 calc_portfolio_allocation）
                         例如：
                         GLD_GDX    0.35
                         EWA_EWC    0.28

    回傳：
        capital : 每個策略的實際分配資金（美元）
                  例如：
                  GLD_GDX    35000.0    ← GLD/GDX 配對分配 $35,000
                  EWA_EWC    28000.0    ← EWA/EWC 配對分配 $28,000
                  dtype: float64
    """
    capital = allocation * account_equity
    return capital.round(2)


def summarize_allocation(allocation: pd.Series,
                          account_equity: float) -> None:
    """
    印出資本配置摘要。

    參數：
        allocation     : 每個策略的資本比例
        account_equity : 帳戶總權益（美元）
    """
    capital = calc_capital_per_strategy(account_equity, allocation)
    total_allocated = capital.sum()
    cash = account_equity - total_allocated

    print(f"\n[allocator] 資本配置摘要（帳戶淨值：${account_equity:,.2f}）：")
    for strategy, alloc in allocation.items():
        print(
            f"  {strategy:<15}："
            f"配置比例 {alloc:.2%}，"
            f"分配資金 ${capital[strategy]:,.2f}"
        )
    print(f"  {'現金部位':<15}：${cash:,.2f}（{cash/account_equity:.2%}）")
    print(f"  {'總配置資金':<15}：${total_allocated:,.2f}（{total_allocated/account_equity:.2%}）")


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

    # 模擬兩個配對策略的 daily_pnl
    pairs = {
        "GLD_GDX": ["GLD", "GDX"],
        "EWA_EWC": ["EWA", "EWC"]
    }

    strategy_pnls = {}
    for pair_name, (sym_y, sym_x) in pairs.items():
        try:
            data = load_multiple([sym_y, sym_x])
            y = data[sym_y]["Close"]
            x = data[sym_x]["Close"]

            coint_result = cadf_test(y, x)
            lookback = int(coint_result["half_life"])
            hedge_ratios = calc_rolling_hedge_ratio(y, x, lookback)
            spread = calc_spread(y, x, hedge_ratios)
            zscore = calc_zscore(spread, lookback)
            signals = generate_signals(zscore)
            results = run_backtest(y, x, hedge_ratios, signals)

            strategy_pnls[pair_name] = results["daily_pnl"]
            print(f"[allocator] {pair_name} 策略載入完成。")

        except Exception as e:
            print(f"[allocator] {pair_name} 載入失敗：{e}")

    if len(strategy_pnls) >= 2:
        # 計算資本配置
        allocation = calc_portfolio_allocation(strategy_pnls)
        summarize_allocation(allocation, account_equity=100000.0)
    else:
        print("[allocator] 策略數量不足，無法計算多策略配置。")