# account.py
# 負責從 IBKR 紙本帳戶讀取持倉與帳戶權益
# 使用 ib_insync 套件連接 IBKR TWS 或 IB Gateway

import pandas as pd
from ib_insync import IB, Stock, util


# ============================================================
# 可調整參數區
# ============================================================
DEFAULT_HOST = "127.0.0.1"   # TWS 或 IB Gateway 的本機位址
DEFAULT_PORT = 7497           # 紙本帳戶預設 port（實盤帳戶為 7496）
DEFAULT_CLIENT_ID = 1         # 客戶端 ID，同時連接多個程式時需設不同值


def connect_ibkr(host: str = DEFAULT_HOST,
                 port: int = DEFAULT_PORT,
                 client_id: int = DEFAULT_CLIENT_ID) -> IB:
    """
    連接 IBKR TWS 或 IB Gateway。

    參數：
        host      : TWS 主機位址，預設本機 "127.0.0.1"
        port      : 連接埠，紙本帳戶預設 7497
        client_id : 客戶端 ID，預設 1

    回傳：
        ib : 已連接的 IB 物件，供其他函數使用
    """
    ib = IB()
    ib.connect(host, port, clientId=client_id)
    print(f"[account] 已連接 IBKR（{host}:{port}，clientId={client_id}）")
    return ib


def disconnect_ibkr(ib: IB) -> None:
    """
    中斷 IBKR 連接。

    參數：
        ib : 已連接的 IB 物件
    """
    ib.disconnect()
    print("[account] 已中斷 IBKR 連接")


def get_account_equity(ib: IB) -> float:
    """
    從 IBKR 帳戶讀取目前的淨值（Net Liquidation Value）。

    參數：
        ib : 已連接的 IB 物件

    回傳：
        equity : 帳戶淨值（美元）
                 例如：102345.67，代表目前帳戶淨值為 $102,345.67
    """
    account_values = ib.accountValues()
    for item in account_values:
        if item.tag == "NetLiquidation" and item.currency == "USD":
            equity = float(item.value)
            print(f"[account] 帳戶淨值：${equity:,.2f}")
            return equity

    raise ValueError("[account] 無法讀取帳戶淨值，請確認 IBKR 連接正常。")


def get_positions(ib: IB) -> pd.DataFrame:
    """
    從 IBKR 帳戶讀取目前所有持倉。

    參數：
        ib : 已連接的 IB 物件

    回傳：
        positions : 持倉 DataFrame
                    例如：
                          symbol  position  avg_cost  market_price  unrealized_pnl
                    0        GLD       372    165.32        167.45          791.96
                    1        GDX      -623     32.18         31.95          143.29
    """
    raw_positions = ib.positions()

    if not raw_positions:
        print("[account] 目前沒有持倉。")
        return pd.DataFrame()

    rows = []
    for pos in raw_positions:
        rows.append({
            "symbol": pos.contract.symbol,
            "position": pos.position,
            "avg_cost": round(pos.avgCost, 4),
            "market_price": round(pos.marketPrice, 4),
            "unrealized_pnl": round(
                pos.position * (pos.marketPrice - pos.avgCost), 2
            )
        })

    positions = pd.DataFrame(rows)
    print(f"\n[account] 目前持倉：")
    print(positions.to_string(index=False))
    return positions


# ============================================================
# 直接執行此檔案時的測試用範例
# ============================================================
if __name__ == "__main__":
    ib = connect_ibkr()
    equity = get_account_equity(ib)
    positions = get_positions(ib)
    disconnect_ibkr(ib)