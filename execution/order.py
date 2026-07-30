# order.py
# 負責向 IBKR 紙本帳戶送出配對交易的訂單
# 設計原則：
#   - 同時處理兩條腿（Y 和 X）
#   - 預設使用市價單
#   - 兩條腿之間間隔 1 秒，避免執行風險
#   - 所有訂單都寫入 log 檔案

import time
import logging
import pandas as pd
from ib_insync import IB, Stock, MarketOrder, LimitOrder
from monitor.tracker import setup_logger


# ============================================================
# 可調整參數區
# ============================================================
DEFAULT_LEG_INTERVAL = 1.0      # 兩條腿之間的間隔秒數，預設 1 秒
DEFAULT_ORDER_TYPE = "MKT"      # 訂單類型，預設市價單（"MKT" 或 "LMT"）
DEFAULT_EXCHANGE = "SMART"      # IBKR 的智慧路由，自動選擇最佳交易所


def _create_contract(symbol: str,
                     exchange: str = DEFAULT_EXCHANGE) -> Stock:
    """
    建立 IBKR 的股票合約物件。

    參數：
        symbol   : 股票代號，例如 "GLD"
        exchange : 交易所，預設 "SMART"（IBKR 智慧路由）

    回傳：
        contract : IBKR Stock 合約物件
                   例如：Stock("GLD", "SMART", "USD")
    """
    return Stock(symbol, exchange, "USD")


def _create_order(action: str,
                  quantity: int,
                  order_type: str = DEFAULT_ORDER_TYPE,
                  limit_price: float = None):
    """
    建立 IBKR 的訂單物件。

    參數：
        action      : 買賣方向，"BUY" 或 "SELL"
        quantity    : 股數，例如 372
        order_type  : 訂單類型，"MKT"（市價）或 "LMT"（限價）
        limit_price : 限價單價格，order_type="LMT" 時才需要

    回傳：
        order : IBKR 訂單物件
                例如：MarketOrder("BUY", 372)
    """
    if order_type == "MKT":
        return MarketOrder(action, quantity)
    elif order_type == "LMT":
        if limit_price is None:
            raise ValueError("[order] 限價單必須提供 limit_price。")
        return LimitOrder(action, quantity, limit_price)
    else:
        raise ValueError(f"[order] 不支援的訂單類型：{order_type}")


def send_pair_order(ib: IB,
                    signal: str,
                    symbol_y: str,
                    symbol_x: str,
                    shares_y: int,
                    shares_x: int,
                    order_type: str = DEFAULT_ORDER_TYPE,
                    leg_interval: float = DEFAULT_LEG_INTERVAL,
                    limit_price_y: float = None,
                    limit_price_x: float = None,
                    logger: logging.Logger = None) -> dict:
    """
    送出配對交易的兩條腿訂單。

    倉位邏輯：
        signal = "ENTER_LONG"  → 做多 Y（BUY），做空 X（SELL）
        signal = "ENTER_SHORT" → 做空 Y（SELL），做多 X（BUY）
        signal = "EXIT"        → 平倉（根據目前持倉方向反向操作）

    參數：
        ib            : 已連接的 IB 物件（來自 monitor/account.py）
        signal        : 信號狀態（來自 monitor/tracker.py）
                        例如："ENTER_LONG"、"ENTER_SHORT"、"EXIT"
        symbol_y      : Y 資產代號，例如 "GLD"
        symbol_x      : X 資產代號，例如 "GDX"
        shares_y      : Y 資產股數，例如 372
        shares_x      : X 資產股數，例如 623
        order_type    : 訂單類型，預設 "MKT"
        leg_interval  : 兩條腿之間的間隔秒數，預設 1.0
        limit_price_y : Y 資產限價（order_type="LMT" 時才需要）
        limit_price_x : X 資產限價（order_type="LMT" 時才需要）
        logger        : logger 物件

    回傳：
        result : 訂單結果字典
                 例如：
                 {
                     "signal": "ENTER_LONG",
                     "leg_y": {
                         "symbol": "GLD",
                         "action": "BUY",
                         "shares": 372,
                         "order_id": 101
                     },
                     "leg_x": {
                         "symbol": "GDX",
                         "action": "SELL",
                         "shares": 623,
                         "order_id": 102
                     }
                 }
    """
    if logger is None:
        logger = setup_logger()

    # 根據信號決定每條腿的方向
    if signal == "ENTER_LONG":
        action_y = "BUY"
        action_x = "SELL"
    elif signal == "ENTER_SHORT":
        action_y = "SELL"
        action_x = "BUY"
    elif signal == "EXIT":
        action_y = "SELL"
        action_x = "BUY"
    elif signal == "HOLD":
        logger.info("[order] 信號為 HOLD，不送出任何訂單。")
        return {}
    else:
        raise ValueError(f"[order] 不支援的信號：{signal}")

    result = {"signal": signal}

    # 送出第一條腿（Y）
    contract_y = _create_contract(symbol_y)
    order_y = _create_order(action_y, shares_y, order_type, limit_price_y)
    trade_y = ib.placeOrder(contract_y, order_y)
    result["leg_y"] = {
        "symbol": symbol_y,
        "action": action_y,
        "shares": shares_y,
        "order_id": trade_y.order.orderId
    }
    logger.info(
        f"[order] 第一條腿已送出｜"
        f"{action_y} {shares_y} 股 {symbol_y}｜"
        f"訂單 ID：{trade_y.order.orderId}"
    )

    # 等待間隔
    time.sleep(leg_interval)

    # 送出第二條腿（X）
    contract_x = _create_contract(symbol_x)
    order_x = _create_order(action_x, shares_x, order_type, limit_price_x)
    trade_x = ib.placeOrder(contract_x, order_x)
    result["leg_x"] = {
        "symbol": symbol_x,
        "action": action_x,
        "shares": shares_x,
        "order_id": trade_x.order.orderId
    }
    logger.info(
        f"[order] 第二條腿已送出｜"
        f"{action_x} {shares_x} 股 {symbol_x}｜"
        f"訂單 ID：{trade_x.order.orderId}"
    )

    return result


def cancel_all_orders(ib: IB,
                      logger: logging.Logger = None) -> None:
    """
    取消所有未成交的訂單。
    用於收盤前或緊急情況下清除所有掛單。

    參數：
        ib     : 已連接的 IB 物件
        logger : logger 物件
    """
    if logger is None:
        logger = setup_logger()

    open_trades = ib.openTrades()
    if not open_trades:
        logger.info("[order] 目前沒有未成交訂單。")
        return

    for trade in open_trades:
        ib.cancelOrder(trade.order)
        logger.info(
            f"[order] 已取消訂單｜"
            f"訂單 ID：{trade.order.orderId}｜"
            f"{trade.contract.symbol}"
        )


# ============================================================
# 直接執行此檔案時的測試用範例
# ============================================================
if __name__ == "__main__":
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
    from monitor.account import connect_ibkr, disconnect_ibkr

    # 連接 IBKR 紙本帳戶
    ib = connect_ibkr()

    # 模擬送出 ENTER_LONG 信號（GLD/GDX 配對）
    result = send_pair_order(
        ib=ib,
        signal="ENTER_LONG",
        symbol_y="GLD",
        symbol_x="GDX",
        shares_y=372,
        shares_x=623
    )

    print(f"\n[order] 訂單結果：")
    print(result)

    disconnect_ibkr(ib)