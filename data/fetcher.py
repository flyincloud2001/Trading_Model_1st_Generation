# fetcher.py
# 負責從 yfinance 下載歷史股價資料並儲存為 CSV
# 設計原則：介面統一，未來可替換為 IBKR 或其他資料來源

import yfinance as yf
import pandas as pd
import os
from datetime import datetime

# ============================================================
# 可調整參數區（未來新增策略時在此修改預設值）
# ============================================================
DEFAULT_START_DATE = "2010-01-01"   # 預設起始日期
DEFAULT_END_DATE = datetime.today().strftime("%Y-%m-%d")  # 預設結束日期（今天）
DEFAULT_DATA_DIR = os.path.join(os.path.dirname(__file__), "csv")  # CSV 儲存資料夾


def fetch_single(symbol: str,
                 start_date: str = DEFAULT_START_DATE,
                 end_date: str = DEFAULT_END_DATE,
                 data_dir: str = DEFAULT_DATA_DIR) -> pd.DataFrame:

    os.makedirs(data_dir, exist_ok=True)

    # 下載資料
    print(f"[fetcher] 正在下載 {symbol} 的資料（{start_date} 至 {end_date}）...")
    
    raw = yf.download(symbol, start=start_date, end=end_date, auto_adjust=True, progress=False)
    df = raw[["Open", "High", "Low", "Close", "Volume"]].copy()
    df.columns = ["Open", "High", "Low", "Close", "Volume"]
    df.index.name = "Date"
    df.dropna(inplace=True)

    # 檢查是否成功下載
    if df.empty:
        raise ValueError(f"[fetcher] 下載失敗：{symbol} 沒有資料，請確認股票代號是否正確。")

    # 只保留需要的欄位
    df = df[["Open", "High", "Low", "Close", "Volume"]]

    # 儲存為 CSV，檔名格式：GLD_2010-01-01_2024-01-01.csv
    filename = f"{symbol}_{start_date}_{end_date}.csv"
    filepath = os.path.join(data_dir, filename)
    df.to_csv(filepath)
    print(f"[fetcher] 已儲存至 {filepath}")

    return df


def fetch_multiple(symbols: list,
                   start_date: str = DEFAULT_START_DATE,
                   end_date: str = DEFAULT_END_DATE,
                   data_dir: str = DEFAULT_DATA_DIR) -> dict:

    data = {}
    for symbol in symbols:
        try:
            df = fetch_single(symbol, start_date, end_date, data_dir)
            data[symbol] = df
        except ValueError as e:
            print(f"[fetcher] 警告：{e}，跳過 {symbol}。")
    return data


# ============================================================
# 直接執行此檔案時的測試用範例
# ============================================================
if __name__ == "__main__":
    # 測試下載配對交易常用的股票
    test_symbols = ["GLD", "GDX", "EWA", "EWC", "USO", "BNO"]
    fetch_multiple(test_symbols)